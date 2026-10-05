#!/usr/bin/env bash
set -euo pipefail

# Choose a PDF with at least three pages. Verify that page 2 uses a resource
# you want to track before removing it. The corpus original is never replaced.
export A2_SOURCE_ID="QZ74K"
: "${PDF_ANALYZER_HOME:?Run inside PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run directory}"

python3 - <<'PY'
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, os.environ['PDF_ANALYZER_HOME'])
import lab

document = os.environ['A2_SOURCE_ID'].strip().upper()
source = lab.pdf_index().get(document)
if not source:
    raise SystemExit(f'Original {document} is missing. Choose an available PDF ID.')
output = Path(os.environ['PDF_RUN_DIR'])
edited = output / 'edited.pdf'
info = lab.metadata(document, source)
if int(info.get('Pages', '0')) < 3:
    raise SystemExit('Select an original PDF with at least three pages.')

def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def save(name, headers, rows):
    with (output / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

before_hash = digest(source)
command = ['qpdf', str(source), '--pages', '.', '1,3-z', '--', str(edited)]
print('Creating a separate copy with page 2 removed; original kept unchanged.', file=sys.stderr)
result = subprocess.run(command, capture_output=True, text=True, timeout=120)
if result.stderr:
    print(result.stderr, file=sys.stderr)
if result.returncode not in (0, 3) or not edited.is_file():
    raise SystemExit(f'Page extraction failed with exit {result.returncode}.')
version = subprocess.run(['qpdf', '--version'], capture_output=True, text=True, timeout=5).stdout.strip()

for variant, label, path in [('before', document, source), ('after', document + '-edited', edited)]:
    rows, warning = lab.resource_rows(label, path)
    if warning:
        print(warning, file=sys.stderr)
    save(variant + '-resources.tsv', ['document', 'resource_type', 'subtype', 'resource_name', 'prefix',
                                     'number', 'object', 'reference', 'scope', 'owner'], rows)
    save(variant + '-numbering.tsv', ['document', 'resource_type', 'prefix', 'scope', 'start', 'end',
                                     'distinct_numbers', 'missing_between', 'suffix_equals_object', 'entries'], lab.numbering(rows))
    objects, warning = lab.pdf_objects(path)
    definitions = []
    for key, obj in objects.items():
        if not key.startswith('obj:'):
            continue
        definition = obj.get('value', obj.get('stream', {}).get('dict', {}))
        # Save readable dictionary definitions, not binary stream contents.
        if isinstance(definition, dict):
            definitions.append({'document': label, 'reference': key[4:],
                                'definition': json.dumps(definition, ensure_ascii=False, sort_keys=True)})
    save(variant + '-objects.tsv', ['document', 'reference', 'definition'], definitions)
    pages = subprocess.run(['qpdf', '--show-pages', str(path)], capture_output=True, text=True, timeout=90)
    if pages.returncode not in (0, 3):
        raise SystemExit(f'Page listing failed for {variant}: {pages.stderr}')
    save(variant + '-pages.tsv', ['document', 'line', 'text'],
         [{'document': label, 'line': i, 'text': line} for i, line in enumerate(pages.stdout.splitlines(), 1)])

unchanged = digest(source) == before_hash
save('experiment.tsv', ['source_document', 'source_sha256', 'edited_sha256', 'source_unchanged',
                        'before_pages', 'after_pages', 'qpdf_version', 'qpdf_exit', 'operation', 'edited_path'],
     [{'source_document': document, 'source_sha256': before_hash, 'edited_sha256': digest(edited),
       'source_unchanged': unchanged, 'before_pages': info.get('Pages', ''),
       'after_pages': lab.metadata(document + '-edited', edited).get('Pages', ''),
       'qpdf_version': version, 'qpdf_exit': result.returncode, 'operation': 'Keep page 1 and pages 3 onward',
       'edited_path': str(edited)}])
if not unchanged:
    raise SystemExit('Original hash changed; do not interpret this run as a controlled copy-only experiment.')
print('Saved before/after evidence. Compare names, scopes, definitions and page use; do not assume what changed.', file=sys.stderr)
PY
