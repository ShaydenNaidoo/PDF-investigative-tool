#!/usr/bin/env python3
"""PDF investigation helpers: original references, scopes and TSV output."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
OBS = Path(os.environ.get('PDF_OBSERVATIONS_DIR', ROOT / 'environment_set/environment/observations')).resolve()
DATASET = Path(os.environ.get('PDF_DATASET_DIR', ROOT / 'environment_set/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data')).resolve()
CATEGORIES = ('Font', 'XObject', 'ColorSpace', 'ExtGState', 'Pattern', 'Shading', 'Properties')


def lines(path):
    return [x.strip() for x in path.read_text(errors='replace').splitlines() if x.strip()] if path.is_file() else []


def pdf_index():
    return {p.name[:5].upper(): p for p in sorted(DATASET.rglob('*')) if p.suffix.lower() == '.pdf'}


def pdf_objects(path):
    result = subprocess.run(['qpdf', '--json', '--json-key=qpdf', str(path)], capture_output=True, text=True, timeout=90)
    if result.returncode not in (0, 3):
        raise ValueError(result.stderr.strip() or 'qpdf could not read this PDF')
    data = json.loads(result.stdout)
    objects = data['qpdf'][1]
    return objects, result.stderr.strip()


def resource_rows(document, path):
    objects, warning = pdf_objects(path)
    def resolve(value):
        if isinstance(value, str) and re.fullmatch(r'\d+ \d+ R', value):
            obj = objects.get('obj:' + value, {})
            return obj.get('value', obj.get('stream', {}).get('dict', {}))
        return value
    rows = []
    # Inspect every resource dictionary, including Pages, Forms and non-page scopes.
    # QPDF JSON preserves source object numbers; QDF conversion can renumber them.
    def visit(value, owner, location):
        if isinstance(value, dict):
            resources = resolve(value.get('/Resources'))
            if isinstance(resources, dict):
                scope = value['/Resources'] if isinstance(value['/Resources'], str) else f'{owner}:{location}/Resources'
                for category in CATEGORIES:
                    names = resolve(resources.get('/' + category))
                    if not isinstance(names, dict):
                        continue
                    for name, target in names.items():
                        if not name.startswith('/'):
                            continue
                        match = re.search(r'(\d+)$', name)
                        number = match.group(1) if match else ''
                        prefix = name[:match.start()] if match else name
                        ref = target if isinstance(target, str) and re.fullmatch(r'\d+ \d+ R', target) else 'direct'
                        resource = resolve(target)
                        subtype = resource.get('/Subtype', '').lstrip('/') if isinstance(resource, dict) else ''
                        rows.append({'document': document, 'resource_type': category, 'subtype': subtype,
                                     'resource_name': name, 'prefix': prefix, 'number': number,
                                     'object': ref.split()[0] if ref != 'direct' else '', 'reference': ref,
                                     'scope': scope, 'owner': owner})
            for key, child in value.items():
                if key != '/Resources' and isinstance(child, (dict, list)):
                    visit(child, owner, location + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                visit(child, owner, f'{location}[{i}]')
    for key, obj in objects.items():
        if key.startswith('obj:'):
            visit(obj.get('value', obj.get('stream', {}).get('dict', {})), key[4:], '')
    # Shared indirect dictionaries are one scope even when referenced by several pages.
    unique = {(r['scope'], r['resource_type'], r['resource_name'], r['reference']): r for r in rows}
    return list(unique.values()), warning


def metadata(document, path):
    result = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    values = {}
    for line in result.stdout.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            values[key.strip()] = value.strip()
    return {'document': document, **values}


def numbering(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault((row['resource_type'], row['prefix'], row['scope']), []).append(row)
    output = []
    for (kind, prefix, scope), group in grouped.items():
        nums = sorted({int(r['number']) for r in group if r['number']})
        # Avoid allocating a huge range for object-based resource names.
        gaps = [(a + 1, b - 1) for a, b in zip(nums, nums[1:]) if b > a + 1]
        skipped = ', '.join(str(a) if a == b else f'{a}–{b}' for a, b in gaps)
        output.append({'document': group[0]['document'], 'resource_type': kind, 'prefix': prefix,
                       'scope': scope, 'start': nums[0] if nums else '', 'end': nums[-1] if nums else '',
                       'distinct_numbers': len(nums), 'missing_between': skipped,
                       'suffix_equals_object': sum(bool(r['number'] and r['object']) and int(r['number']) == int(r['object']) for r in group),
                       'entries': len(group)})
    return output


def write_tsv(rows, headers=None):
    headers = headers or (list(rows[0]) if rows else ['document', 'resource_type', 'resource_name'])
    writer = csv.DictWriter(sys.stdout, fieldnames=headers, delimiter='\t', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['resources', 'numbering', 'metadata', 'marks'])
    parser.add_argument('--document', default='')
    parser.add_argument('--tool', default='')
    parser.add_argument('--type', default='')
    parser.add_argument('--prefix', default='')
    args = parser.parse_args()
    documents = lines(OBS / 'all')
    if args.tool:
        if not re.fullmatch(r'pr(?:0[1-9]|1[0-5])', args.tool):
            parser.error('Tool must be pr01 through pr15')
        documents = lines(OBS / 'tools' / args.tool)
    if args.document:
        requested = [x.strip().upper() for x in args.document.split(',') if x.strip()]
        if any(x not in lines(OBS / 'all') for x in requested):
            parser.error('Unknown document ID')
        documents = [x for x in documents if x in requested]
    index = pdf_index()
    rows, failures = [], 0
    mark_sets = {p.name: set(lines(p)) for p in (OBS / 'marks').iterdir() if p.is_file()} if args.mode == 'marks' else {}
    for i, document in enumerate(documents):
        print(f'[{i + 1}/{len(documents)}] {document}', file=sys.stderr, flush=True)
        try:
            if args.mode == 'marks':
                rows.extend({'document': document, 'mark': name} for name, members in mark_sets.items() if document in members)
            elif document not in index:
                raise ValueError('PDF missing from dataset')
            elif args.mode == 'metadata':
                values = metadata(document, index[document])
                rows.append({key: values.get(key, '') for key in ['document', 'Producer', 'Creator', 'Pages', 'PDF version', 'CreationDate', 'ModDate']})
            else:
                resources, warning = resource_rows(document, index[document])
                if warning:
                    print(warning, file=sys.stderr)
                resources = [r for r in resources if (not args.type or r['resource_type'] == args.type) and (not args.prefix or r['prefix'] == args.prefix)]
                rows.extend(numbering(resources) if args.mode == 'numbering' else resources)
        except (ValueError, subprocess.SubprocessError, OSError) as error:
            failures += 1
            print(f'{document}: {error}', file=sys.stderr)
    write_tsv(rows)
    if failures:
        print(f'{failures} document(s) could not be inspected.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
