#!/usr/bin/env bash
set -euo pipefail

# Paste this entire file into PDF Analyzer > Script studio > Build a script.
# Start with one tool, then use "all" for pr01 through pr15; "none" selects no tools.
export A2_TOOLS="all"
# These six named cases are outside the supplied exemplar sets. Keep them separate
# when interpreting Part 1's tool conventions. Set this to "" for exemplars only.
export A2_DOCUMENTS="CUF7M,QZ74K,GGGXC,MM5SP,MZRWQ,GKMDO"

: "${PDF_ANALYZER_HOME:?Run inside PDF Analyzer}"
: "${PDF_OBSERVATIONS_DIR:?Missing observations path}"
: "${PDF_RUN_DIR:?Missing run directory}"

python3 - <<'PY'
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, os.environ['PDF_ANALYZER_HOME'])
import lab

output = Path(os.environ['PDF_RUN_DIR'])
observations = Path(os.environ['PDF_OBSERVATIONS_DIR'])
selection = os.environ['A2_TOOLS'].strip().lower()
tools = ([f'pr{i:02d}' for i in range(1, 16)] if selection == 'all' else
         [] if selection == 'none' else [v.strip() for v in selection.split(',') if v.strip()])
if not tools and selection != 'none':
    raise SystemExit('Use A2_TOOLS="all", "none", or comma-separated IDs such as "pr01,pr12".')
if any(not re.fullmatch(r'pr(?:0[1-9]|1[0-5])', t) for t in tools):
    raise SystemExit('Tool IDs must be pr01 through pr15.')
tools = sorted(set(tools))
toolsets = {t: set(lab.lines(observations / 'tools' / t)) for t in tools}
if any(not ids for ids in toolsets.values()):
    raise SystemExit('A selected exemplar set is empty or missing. Check Lab setup and tools/pr*.')
extra = {v.strip().upper() for v in os.environ['A2_DOCUMENTS'].split(',') if v.strip()}
known = set(lab.lines(observations / 'all'))
if extra - known:
    raise SystemExit('Import these PDFs first, then use their displayed IDs: ' + ', '.join(sorted(extra-known)))
documents = sorted(extra | set().union(*toolsets.values()))
if not documents:
    raise SystemExit('Select at least one exemplar tool or document ID.')
index = lab.pdf_index()
resources, numbering, contexts, inventory, metadata, failures, warnings = [], [], [], [], [], [], []
inspected = set()

def save(name, headers, rows):
    with (output / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def error(document, stage, exception):
    failures.append({'document': document, 'stage': stage, 'error': str(exception)})
    print(f'{document}: {stage}: {exception}', file=sys.stderr, flush=True)

def value(objects, ref):
    if isinstance(ref, str) and re.fullmatch(r'\d+ \d+ R', ref):
        obj = objects.get('obj:' + ref, {})
        return obj.get('value', obj.get('stream', {}).get('dict', {}))
    return ref

def local_context(objects, owner, dictionary):
    holder, effective, inherited, seen = owner, dictionary, '', set()
    if '/Resources' not in dictionary and dictionary.get('/Type') not in ('/Page', '/Pages'):
        return None
    # Record inherited /Pages resources as well as direct Page/Form resources.
    while isinstance(effective, dict) and '/Resources' not in effective and effective.get('/Parent'):
        parent = effective['/Parent']
        if not isinstance(parent, str) or parent in seen:
            break
        seen.add(parent)
        candidate = value(objects, parent)
        if not isinstance(candidate, dict) or candidate.get('/Type') != '/Pages':
            break
        effective = candidate
        holder, inherited = parent, parent
    if not isinstance(effective, dict) or '/Resources' not in effective:
        return None
    declaration = effective['/Resources']
    resource_dict = value(objects, declaration)
    if not isinstance(resource_dict, dict):
        return None
    scope = declaration if isinstance(declaration, str) else holder + ':/Resources'
    kind = str(dictionary.get('/Type', 'Other')).lstrip('/')
    subtype = str(dictionary.get('/Subtype', '')).lstrip('/')
    context = 'Form' if kind == 'XObject' and subtype == 'Form' else kind
    return {'owner': owner, 'owner_type': kind, 'owner_subtype': subtype,
            'context': context, 'scope': scope, 'inherited_from': inherited,
            'has_contents': '/Contents' in dictionary,
            'contents': json.dumps(dictionary.get('/Contents', ''), ensure_ascii=False),
            'procset': json.dumps(value(objects, resource_dict.get('/ProcSet', 'absent')), ensure_ascii=False),
            'bbox': json.dumps(dictionary.get('/BBox', ''), ensure_ascii=False)}

for position, document in enumerate(documents, 1):
    print(f'[{position}/{len(documents)}] {document}', file=sys.stderr, flush=True)
    path = index.get(document)
    entry = {'document': document, 'tools': ', '.join(t for t in tools if document in toolsets[t]),
             'named_case': document in extra, 'filename': '', 'sha256': '',
             'resources_status': 'not inspected', 'metadata_status': 'not inspected'}
    inventory.append(entry)
    if not path:
        error(document, 'input', 'Original PDF is missing from this lab.')
        continue
    entry['filename'] = path.name
    try:
        with path.open('rb') as handle:
            entry['sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
        rows, warning = lab.resource_rows(document, path)
        inspected.add(document)
        entry['resources_status'] = 'ok'
        if warning:
            warnings.append({'document': document, 'stage': 'resources', 'warning': warning})
        objects, warning = lab.pdf_objects(path)
        if warning:
            print(f'{document}: qpdf recovered with warnings; inspect warnings.tsv.', file=sys.stderr)
        local = []
        for key, obj in objects.items():
            if not key.startswith('obj:'):
                continue
            definition = obj.get('value', obj.get('stream', {}).get('dict', {}))
            if isinstance(definition, dict):
                context = local_context(objects, key[4:], definition)
                if context:
                    local.append({'document': document, **context})
        contexts.extend(local)
        scope_contexts = defaultdict(set)
        for item in local:
            scope_contexts[item['scope']].add(item['context'])
        for row in rows:
            row['context'] = ', '.join(sorted(scope_contexts[row['scope']])) or 'inspect owner'
            row['resource_kind'] = ('XObject:' + (row['subtype'] or 'Unknown')
                                    if row['resource_type'] == 'XObject' else row['resource_type'])
        resources.extend(rows)
        for row in lab.numbering(rows):
            row['context'] = ', '.join(sorted(scope_contexts[row['scope']])) or 'inspect owner'
            row['numeric_indirect_entries'] = sum(bool(r['number'] and r['object']) for r in rows
                                                  if r['scope'] == row['scope']
                                                  and r['resource_type'] == row['resource_type']
                                                  and r['prefix'] == row['prefix'])
            numbering.append(row)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exception:
        entry['resources_status'] = 'error'
        inspected.discard(document)
        error(document, 'resources/context', exception)
    try:
        values = lab.metadata(document, path)
        metadata.append(values)
        entry['metadata_status'] = 'ok'
    except (OSError, ValueError, subprocess.SubprocessError) as exception:
        entry['metadata_status'] = 'error'
        error(document, 'metadata', exception)

groups = defaultdict(list)
for row in resources:
    groups[(row['document'], row['resource_type'], row['resource_name'])].append(row)
reuse = []
for (document, kind, name), group in sorted(groups.items()):
    scopes = sorted({r['scope'] for r in group})
    if len(scopes) < 2:
        continue
    targets = sorted({r['reference'] for r in group})
    relation = ('direct value present; inspect definitions' if 'direct' in targets else
                'same original object' if len(targets) == 1 else 'different original objects')
    reuse.append({'document': document, 'resource_type': kind, 'resource_name': name,
                  'scope_count': len(scopes), 'scopes': '; '.join(scopes),
                  'target_count': len(targets), 'targets': '; '.join(targets), 'relation': relation})

prefix_rows = []
for tool, members in toolsets.items():
    relevant = [r for r in resources if r['document'] in members]
    declared = defaultdict(set)
    prefixes = defaultdict(set)
    for row in relevant:
        declared[row['resource_kind']].add(row['document'])
        prefixes[(row['resource_kind'], row['prefix'])].add(row['document'])
    for (kind, prefix), ids in sorted(prefixes.items()):
        prefix_rows.append({'tool': tool, 'resource_kind': kind, 'prefix': prefix,
                            'documents_with_prefix': len(ids), 'documents_declaring_kind': len(declared[kind]),
                            'inspected_exemplars': len(members & inspected), 'expected_exemplars': len(members),
                            'declared_kind_coverage_percent': round(100*len(ids)/len(declared[kind]), 1)})

save('inventory.tsv', ['document', 'tools', 'named_case', 'filename', 'sha256', 'resources_status', 'metadata_status'], inventory)
save('resources.tsv', ['document', 'resource_type', 'resource_kind', 'subtype', 'resource_name', 'prefix',
                      'number', 'object', 'reference', 'scope', 'owner', 'context'], resources)
save('numbering.tsv', ['document', 'resource_type', 'prefix', 'scope', 'context', 'start', 'end',
                      'distinct_numbers', 'missing_between', 'suffix_equals_object', 'numeric_indirect_entries', 'entries'], numbering)
save('reuse.tsv', ['document', 'resource_type', 'resource_name', 'scope_count', 'scopes', 'target_count', 'targets', 'relation'], reuse)
save('contexts.tsv', ['document', 'owner', 'owner_type', 'owner_subtype', 'context', 'scope', 'inherited_from',
                     'has_contents', 'contents', 'procset', 'bbox'], contexts)
save('prefix-evidence.tsv', ['tool', 'resource_kind', 'prefix', 'documents_with_prefix', 'documents_declaring_kind',
                           'inspected_exemplars', 'expected_exemplars', 'declared_kind_coverage_percent'], prefix_rows)
save('metadata.tsv', ['document', 'Producer', 'Creator', 'Pages', 'PDF version', 'CreationDate', 'ModDate'], metadata)
save('tool-membership.tsv', ['document', 'tool'], [{'document': d, 'tool': t} for t, ids in toolsets.items() for d in sorted(ids)])
save('failures.tsv', ['document', 'stage', 'error'], failures)
save('warnings.tsv', ['document', 'stage', 'warning'], warnings)
versions = []
for tool, flag in [('qpdf', '--version'), ('pdfinfo', '-v')]:
    result = subprocess.run([tool, flag], capture_output=True, text=True, timeout=5)
    versions.append({'tool': tool, 'version': (result.stdout + result.stderr).strip()})
versions.append({'tool': 'Python', 'version': sys.version})
save('versions.tsv', ['tool', 'version'], versions)
print(f'Saved evidence for {len(documents)} selected PDFs; {len(failures)} failure(s).', file=sys.stderr)
print('Resource declarations are not proof of actual use. Interpret the evidence yourself.', file=sys.stderr)
raise SystemExit(1 if failures else 0)
PY
