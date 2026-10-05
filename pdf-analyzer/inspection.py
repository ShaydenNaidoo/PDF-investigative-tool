"""Read-only PDF strings, original object dictionaries, streams and metadata."""
from collections import Counter
import json
import mmap
from pathlib import Path
import re
import subprocess
import tempfile

import lab

MAX_INDEX_ROWS = 100_000
MAX_INDEX_CHARACTERS = 16_000_000
MAX_STREAM_BYTES = 2_000_000


def tool_output(command, limit=MAX_STREAM_BYTES, timeout=60):
    """Keep large binary streams out of memory while applying a preview limit."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run(command, stdout=output, stderr=errors, timeout=timeout)
        size = output.tell()
        output.seek(0)
        data = output.read(limit)
        errors.seek(0)
        warning = errors.read(40_000).decode('utf-8', errors='replace').strip()
    if result.returncode not in (0, 3):
        raise ValueError(warning or f'{Path(command[0]).name} failed (exit {result.returncode})')
    return data, warning, size > limit, size


def display_bytes(data):
    text = data.decode('utf-8', errors='replace')
    return text.translate({i: '·' for i in range(32) if i not in (9, 10, 13)})


def pdf_syntax(value, depth=0):
    """A readable dictionary reconstruction, preserving original references."""
    if isinstance(value, dict):
        indent = '  ' * (depth + 1)
        return '<<\n' + '\n'.join(indent + key + ' ' + pdf_syntax(child, depth + 1) for key, child in value.items()) + '\n' + '  ' * depth + '>>'
    if isinstance(value, list):
        return '[ ' + ' '.join(pdf_syntax(child, depth) for child in value) + ' ]'
    if isinstance(value, str):
        if value.startswith('u:'):
            return '(' + value[2:].replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ')'
        if value.startswith('b:'):
            return '<' + value[2:] + '>'
        return value
    if value is None:
        return 'null'
    return json.dumps(value)


def pdf_names(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith('/'):
                yield key
            yield from pdf_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from pdf_names(child)
    elif isinstance(value, str) and value.startswith('/'):
        yield value


def strings_index(path, mode='raw', minimum=4):
    rows, tags, character_count, truncated, warning = [], [], 0, False, ''
    if mode == 'raw':
        if not 2 <= minimum <= 64:
            raise ValueError('Minimum string length must be between 2 and 64')
        pattern = re.compile(rb'[\x20-\x7e]{' + str(minimum).encode() + rb',}')
        with path.open('rb') as handle:
            if path.stat().st_size:
                with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
                    for match in pattern.finditer(data):
                        if len(rows) >= MAX_INDEX_ROWS or character_count + match.end() - match.start() > MAX_INDEX_CHARACTERS:
                            truncated = True
                            break
                        value = match.group().decode('ascii')
                        rows.append({'location': f'0x{match.start():08x}', 'offset': match.start(), 'reference': '',
                                     'kind': 'file bytes', 'stream': False, 'tags': [], 'text': value})
                        character_count += len(value)
        source = f'Printable ASCII from original file bytes · minimum {minimum} characters · offsets are byte offsets'
    elif mode == 'objects':
        objects, warning = lab.pdf_objects(path)
        occurrences, documents = Counter(), Counter()
        for key, obj in objects.items():
            if not key.startswith('obj:') and key != 'trailer':
                continue
            value = obj.get('value', obj.get('stream', {}).get('dict', {}))
            ref = key[4:] if key.startswith('obj:') else ''
            text = (ref.removesuffix(' R') + ' obj\n' if ref else 'trailer\n') + pdf_syntax(value)
            if len(rows) >= MAX_INDEX_ROWS or character_count + len(text) > MAX_INDEX_CHARACTERS:
                truncated = True
                break
            names = list(pdf_names(value))
            occurrences.update(names)
            documents.update(set(names))
            kind = (value.get('/Type') or value.get('/Subtype') or ('Stream' if 'stream' in obj else 'Object')) if isinstance(value, dict) else 'Value'
            rows.append({'location': ref or 'trailer', 'reference': ref, 'kind': str(kind).lstrip('/'),
                         'stream': 'stream' in obj, 'tags': sorted(set(names)), 'text': text})
            character_count += len(text)
        tags = [{'tag': name, 'objects': documents[name], 'occurrences': count} for name, count in occurrences.most_common()]
        source = 'Decoded object dictionaries from qpdf JSON · original object references · readable reconstruction, not original whitespace'
    elif mode == 'text':
        raw, warning, truncated, _ = tool_output(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'], limit=MAX_INDEX_CHARACTERS)
        for page, text in enumerate(raw.decode('utf-8', errors='replace').split('\f'), 1):
            if text.strip():
                rows.append({'location': f'Page {page}', 'reference': '', 'kind': 'page text', 'stream': False,
                             'tags': [], 'text': text})
        source = 'Page text extracted by pdftotext · image-only scans may contain no extractable text'
    else:
        raise ValueError('Choose raw, objects, or text')
    return {'rows': rows, 'tags': tags, 'source': source, 'truncated': truncated, 'warning': warning,
            'indexLimit': f'{MAX_INDEX_ROWS:,} records or {MAX_INDEX_CHARACTERS:,} characters'}


def filtered_strings(index, query='', tag='', case_sensitive=False):
    needle = query if case_sensitive else query.casefold()
    return [row for row in index['rows'] if (not tag or tag in row['tags'])
            and (not needle or needle in (row['text'] if case_sensitive else row['text'].casefold()))]


def object_detail(path, reference, decoded=False):
    if not re.fullmatch(r'\d+(?:,\d+)?', reference):
        raise ValueError('Select a valid original object reference')
    command = ['qpdf', '--show-object=' + reference]
    data, warning, truncated, size = tool_output([*command, str(path)])
    is_stream = data.lstrip().startswith(b'Object is stream.')
    if decoded:
        if not is_stream:
            raise ValueError('This object is not a stream. Open its definition instead.')
        data, stream_warning, truncated, size = tool_output([*command, '--filtered-stream-data', str(path)])
        warning = '\n'.join(w for w in [warning, stream_warning] if w)
    return {'text': display_bytes(data), 'warning': warning, 'truncated': truncated, 'bytes': size,
            'stream': is_stream, 'source': 'Decoded original stream · may contain binary data' if decoded else 'Original object definition',
            'limit': MAX_STREAM_BYTES}


def full_metadata(document, path):
    objects, object_warning = lab.pdf_objects(path)
    trailer = objects.get('trailer', {}).get('value', {})
    info_reference = trailer.get('/Info', '')
    info = objects.get('obj:' + info_reference, {}).get('value', {}) if isinstance(info_reference, str) else info_reference
    info = info if isinstance(info, dict) else {}
    fields = [{'field': key, 'value': value[2:] if isinstance(value, str) and value.startswith('u:') else pdf_syntax(value)} for key, value in info.items()]
    # Locate XMP via the catalog's /Metadata reference, avoiding unrelated metadata streams.
    catalog_reference = trailer.get('/Root', '')
    catalog = objects.get('obj:' + catalog_reference, {}).get('value', {}) if isinstance(catalog_reference, str) else {}
    xmp_reference = catalog.get('/Metadata', '') if isinstance(catalog, dict) else ''
    xmp, warning, truncated = '', '', False
    if isinstance(xmp_reference, str) and re.fullmatch(r'\d+ \d+ R', xmp_reference):
        try:
            detail = object_detail(path, ','.join(xmp_reference.split()[:2]), decoded=True)
            xmp, warning, truncated = detail['text'], detail['warning'], detail['truncated']
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            warning = f'XMP could not be decoded: {error}'
    return {'document': document, 'filename': path.name, 'bytes': path.stat().st_size,
            'pdfinfo': lab.metadata(document, path), 'info': fields, 'infoReference': info_reference,
            'trailer': [{'field': key, 'value': pdf_syntax(value)} for key, value in trailer.items()],
            'xmp': xmp, 'xmpReference': xmp_reference, 'truncated': truncated,
            'warning': '\n'.join(w for w in [object_warning, warning] if w),
            'source': 'Original PDF · pdfinfo, Info dictionary, trailer and catalog XMP stream'}
