"""Initialize persistent lab storage and import PDFs without replacing originals."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

MAX_UPLOAD_BYTES = 4 * 1024**3
MAX_EXPANDED_BYTES = 8 * 1024**3
MAX_PDFS = 20_000
MAX_ARCHIVE_ENTRIES = 100_000
TOOLS = ('python3', 'bash', 'qpdf', 'pdfinfo', 'pdftotext', 'awk', 'column', 'sed', 'grep', 'find', 'sort', 'uniq')
EXCLUDED = {'gui-runs', 'part1-results', 'part1-test-results', 'pdfwork', 'qdf', '__pycache__', '.uploads'}


def initialize(observations, dataset, seed=None):
    """Seed missing assignment files; preserve saved scripts, results and notes."""
    observations.mkdir(parents=True, exist_ok=True)
    dataset.mkdir(parents=True, exist_ok=True)
    copied = 0
    if seed and seed.is_dir():
        seed_observations = seed / 'observations'
        for source in sorted(seed_observations.rglob('*')):
            relative = source.relative_to(seed_observations)
            if source.is_symlink() or any(p in EXCLUDED for p in relative.parts) or source.name in ('gui-notes.json', 'scan_resources.sh'):
                continue
            target = observations / relative
            if source.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied += 1
    for name in ('tools', 'marks', 'othermarks', 'vectors', 'bags', 'fv', 'classes', 'gui-scripts', 'gui-runs', '.uploads'):
        (observations / name).mkdir(exist_ok=True)
    if not (observations / 'all').exists():
        (observations / 'all').write_text('')
    # A stopped container may leave an incomplete upload or extraction behind.
    for path in (observations / '.uploads').glob('upload-*.upload'):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    for path in dataset.glob('.import-*'):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
    return copied


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def upload_name(value):
    name = str(value).replace('\\', '/').split('/')[-1]
    if not name or len(name) > 240 or Path(name).suffix.lower() not in ('.pdf', '.zip'):
        raise ValueError('Choose a PDF file or a ZIP archive containing PDFs.')
    return name


def import_dataset(upload, filename, dataset, observations, progress=lambda **_: None):
    """Stage and validate every PDF before installing any; never overwrite evidence."""
    filename = upload_name(filename)
    dataset.mkdir(parents=True, exist_ok=True)
    records = {}
    rejected = []
    expanded = entries = pdf_count = 0
    existing = {}
    for path in sorted(dataset.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.suffix.lower() == '.pdf':
            existing[path.name[:5].upper()] = path
    with tempfile.TemporaryDirectory(prefix='.import-', dir=dataset) as directory:
        staging = Path(directory)

        def copy_stream(source, target):
            nonlocal expanded
            with target.open('xb') as out:
                while block := source.read(1024 * 1024):
                    expanded += len(block)
                    if expanded > MAX_EXPANDED_BYTES:
                        raise ValueError('The expanded archive exceeds the 8 GiB import limit.')
                    out.write(block)

        def add_pdf(path, name):
            nonlocal pdf_count
            pdf_count += 1
            if pdf_count > MAX_PDFS:
                raise ValueError('This import exceeds the 20,000 PDF limit.')
            with path.open('rb') as handle:
                if b'%PDF-' not in handle.read(1024):
                    rejected.append(name)
                    path.unlink()
                    progress(status='extracting', message=f'Reading PDFs: {pdf_count:,} checked; {len(rejected):,} non-PDF files skipped', pdfs=pdf_count, rejected=len(rejected))
                    return
            checksum = digest(path)
            base = re.sub(r'[^A-Za-z0-9._-]', '_', Path(name).stem)[:170] + '.pdf'
            document = base[:5].upper() if re.fullmatch(r'[A-Za-z0-9]{5}', Path(base).stem[:5]) else checksum[:5].upper()
            if not re.fullmatch(r'[A-Za-z0-9]{5}', Path(base).stem[:5]):
                base = document + '-' + base
            if document in records:
                if records[document]['digest'] != checksum:
                    raise ValueError(f'Two different PDFs use document ID {document}. Give each PDF a unique first five filename characters and import again.')
            else:
                records[document] = {'path': path, 'name': base, 'digest': checksum}
            progress(status='extracting', message=f'Reading PDFs: {pdf_count:,} found', pdfs=pdf_count, expandedBytes=expanded)

        def archive(path, depth=0):
            nonlocal entries
            if depth > 2:
                raise ValueError('Too many nested ZIP archives. Import the innermost dataset ZIP instead.')
            with zipfile.ZipFile(path) as bundle:
                for item in bundle.infolist():
                    entries += 1
                    if entries > MAX_ARCHIVE_ENTRIES:
                        raise ValueError('The archive has too many entries.')
                    name = item.filename.replace('\\', '/')
                    parts = PurePosixPath(name)
                    if parts.is_absolute() or '..' in parts.parts or any(':' in p for p in parts.parts):
                        raise ValueError('The archive contains an unsafe path. No PDFs were installed.')
                    if stat.S_ISLNK(item.external_attr >> 16):
                        raise ValueError('ZIP archives containing symbolic links are not supported.')
                    if item.is_dir():
                        continue
                    suffix = parts.suffix.lower()
                    if suffix not in ('.pdf', '.zip'):
                        continue
                    if item.flag_bits & 1:
                        raise ValueError('Password-protected ZIP files are not supported. Extract them first and import the PDFs.')
                    if item.file_size > MAX_EXPANDED_BYTES - expanded:
                        raise ValueError('The expanded archive exceeds the 8 GiB import limit.')
                    target = staging / f'entry-{entries}.part'
                    with bundle.open(item) as source:
                        copy_stream(source, target)
                    if suffix == '.zip':
                        archive(target, depth + 1)
                        target.unlink()
                    else:
                        add_pdf(target, parts.name)

        if filename.lower().endswith('.zip'):
            archive(upload)
        else:
            target = staging / 'single.part'
            with upload.open('rb') as source:
                copy_stream(source, target)
            add_pdf(target, filename)
        if not records:
            raise ValueError('No valid PDFs were found. Files named .pdf must contain a PDF header; choose your PDF dataset ZIP or original PDF files.')
        progress(status='validating', message='Checking document IDs and existing originals', pdfs=pdf_count)
        new, skipped = [], 0
        for document, record in records.items():
            if document in existing:
                if digest(existing[document]) != record['digest']:
                    raise ValueError(f'Document {document} already has a different original PDF. Nothing was replaced; give the new file a different document ID.')
                skipped += 1
            else:
                new.append((document, record))
        installed = []
        try:
            for document, record in new:
                target = dataset / record['name']
                # Linking is atomic and fails if the destination already exists.
                os.link(record['path'], target)
                installed.append(target)
                progress(status='installing', message=f'Adding PDFs: {len(installed):,} of {len(new):,}', pdfs=pdf_count)
            all_path = observations / 'all'
            current = [v.strip() for v in all_path.read_text().splitlines() if v.strip()] if all_path.is_file() else []
            known = set(current)
            # Include reimported PDFs too, restoring missing IDs without changing tool membership.
            current += sorted(set(records) - known)
            with tempfile.NamedTemporaryFile(mode='w', dir=observations, delete=False, prefix='.all-') as out:
                all_temp = Path(out.name)
                out.write('\n'.join(current) + ('\n' if current else ''))
            try:
                os.replace(all_temp, all_path)
            finally:
                all_temp.unlink(missing_ok=True)
        except BaseException:
            for path in installed:
                path.unlink(missing_ok=True)
            raise
    notice = f' {len(rejected):,} files named .pdf did not contain PDF data and were skipped: ' + ', '.join(rejected[:20]) + (' …' if len(rejected) > 20 else '') if rejected else ''
    return {'imported': len(new), 'skipped': skipped, 'rejected': rejected, 'pdfs': pdf_count,
            'message': f'{len(new):,} PDFs added; {skipped:,} existing PDFs kept. Your lab is ready to investigate.' + notice}
