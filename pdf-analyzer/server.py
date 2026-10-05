#!/usr/bin/env python3
"""Local PDF Analyzer API and asynchronous assignment script runner."""
import argparse
from collections import Counter, defaultdict, OrderedDict
import csv
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import threading
import time
import urllib.parse
import uuid

import lab
import inspection
import summaries

API_VERSION = 3

ROOT, OBS, DATASET = lab.ROOT, lab.OBS, lab.DATASET
STATIC = Path(__file__).resolve().parent
RESULTS = OBS / 'part1-results'
SCRIPTS = OBS / 'gui-scripts'
RUNS = OBS / 'gui-runs'
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
JOBS, PROCESSES, CACHE = {}, {}, {}
VIEW_CACHE = OrderedDict()
SUMMARY_CACHE = OrderedDict()
CATALOG = {
    'part1_resources.sh': ('Extract resource marks', 'Scan the full observation set with your Bash + qpdf extraction script.', 'none'),
    'test_part1.sh': ('Test one PDF', 'Run your supplied extraction test. Its output is kept separate from the full dataset.', 'document'),
    'buildvectors': ('Build document vectors', 'Rebuild document vectors from the existing marks directory.', 'none'),
    'buildbags': ('Build exemplar bags', 'Combine existing vectors for each exemplar tool; run after building vectors.', 'none'),
    'buildfvs': ('Build feature vectors', 'Select marks common to every exemplar; run after building bags.', 'none'),
    'buildclasses': ('Build induced classes', 'Compare document vectors with tool features; run after building feature vectors.', 'none'),
    'build1vector': ('Build one document vector', 'Build a toolmark vector for one document.', 'document'),
    'build1bag': ('Build one exemplar bag', 'Combine vectors for one tool.', 'tool'),
    'build1fv': ('Build one feature vector', 'Find common marks in a tool bag.', 'tool'),
    'build1class': ('Build one induced class', 'Find documents compatible with a tool feature vector.', 'tool'),
    'section': ('Intersect two sets', 'Find shared documents or marks in two observation sets.', 'sets'),
    'union': ('Union two sets', 'Combine two observation sets.', 'sets'),
    'minus': ('Subtract two sets', 'Find members of the first observation set absent from the second.', 'sets'),
    'subset': ('Check subset', 'Check whether the first observation set is contained in the second.', 'sets'),
    'card': ('Count set members', 'Count members of one observation set.', 'set'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_text(path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def read_table(path):
    if not path.is_file():
        return [], []
    with path.open(encoding='utf-8-sig', errors='replace', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t' if path.suffix == '.tsv' else ',')
        rows = [{key: value or '' for key, value in row.items() if key is not None} for row in reader]
        return reader.fieldnames or [], rows


def catalog():
    items = [{'id': key, 'label': label, 'description': description, 'argument': arg, 'custom': False}
             for key, (label, description, arg) in CATALOG.items() if (OBS / key).is_file()]
    for path in sorted(OBS.glob('*.sh')):
        if path.name not in CATALOG and path.name != 'scan_resources.sh':
            items.append({'id': path.name, 'label': path.stem, 'description': 'Assignment script in observations.', 'argument': 'none', 'custom': False})
    for path in sorted(SCRIPTS.glob('*.sh')):
        items.append({'id': 'custom:' + path.name, 'label': path.stem.replace('-', ' '),
                      'description': 'Your saved investigation script.', 'argument': 'none', 'custom': True})
    return items


def evidence():
    paths = [RESULTS / 'all-resources.tsv', OBS / 'all', OBS / 'producer.txt']
    paths += sorted((OBS / 'tools').glob('pr*')) + sorted((OBS / 'marks').glob('*'))
    signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths if p.is_file())
    with LOCK:
        if CACHE.get('signature') == signature:
            return CACHE['data']
        documents = lab.lines(OBS / 'all')
        _, resources = read_table(RESULTS / 'all-resources.tsv')
        producers = {}
        for line in read_text(OBS / 'producer.txt').splitlines():
            if not line.strip():
                continue
            document = line.split()[0]
            fields = dict(re.findall(r'\{(Producer|Creator):\s*(.*?)\}', line))
            producers[document] = {'document': document, 'producer': fields.get('Producer', ''), 'creator': fields.get('Creator', '')}
        index = lab.pdf_index()
        toolsets = {p.name: set(lab.lines(p)) for p in sorted((OBS / 'tools').glob('pr*')) if p.is_file()}
        members = defaultdict(list)
        for tool, ids in toolsets.items():
            for document in ids:
                members[document].append(tool)
        marksets = {p.name: set(lab.lines(p)) for p in sorted((OBS / 'marks').glob('*')) if p.is_file()}
        markcounts = Counter(doc for ids in marksets.values() for doc in ids)
        counts = Counter(r.get('document', '') for r in resources)
        prefixdocs = defaultdict(set)
        matrixdocs = defaultdict(set)
        for row in resources:
            row['tool'] = ', '.join(members[row.get('document', '')])
            prefixdocs[(row.get('resource_type', ''), row.get('prefix', ''))].add(row.get('document', ''))
            for tool in members[row.get('document', '')]:
                matrixdocs[(tool, row.get('resource_type', ''), row.get('prefix', ''))].add(row.get('document', ''))
        docs = [{'id': d, **producers.get(d, {'producer': '', 'creator': ''}), 'tools': members[d],
                 'resources': counts[d], 'marks': markcounts[d], 'available': d in index,
                 'bytes': index[d].stat().st_size if d in index else 0} for d in documents]
        tools = []
        for tool, ids in toolsets.items():
            names = Counter(producers[d]['producer'] for d in ids if d in producers and producers[d]['producer'])
            tools.append({'id': tool, 'label': names.most_common(1)[0][0] if names else tool,
                          'exemplars': len(ids), 'scanned': len(ids & set(counts))})
        summary = [{'resource_type': kind, 'prefix': prefix, 'documents': len(ids)} for (kind, prefix), ids in prefixdocs.items()]
        summary.sort(key=lambda r: (-r['documents'], r['prefix']))
        matrix = [{'tool': tool, 'resource_type': kind, 'prefix': prefix, 'documents': len(ids),
                   'exemplars': len(toolsets[tool])} for (tool, kind, prefix), ids in sorted(matrixdocs.items())]
        data = {'documents': docs, 'producers': list(producers.values()), 'resources': resources,
                'summary': summary, 'matrix': matrix, 'tools': tools, 'index': index, 'marksets': marksets}
        CACHE.update(signature=signature, data=data)
        return data


def inspection_cached(path, kind, factory, minimum=4):
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size, kind, minimum)
    with LOCK:
        if key in VIEW_CACHE:
            VIEW_CACHE.move_to_end(key)
            return VIEW_CACHE[key]
    result = factory()
    with LOCK:
        VIEW_CACHE[key] = result
        VIEW_CACHE.move_to_end(key)
        while len(VIEW_CACHE) > 8:
            VIEW_CACHE.popitem(last=False)
    return result


def result_summary(path, query):
    toolpaths = [p for p in sorted((OBS / 'tools').glob('pr*')) if p.is_file()]
    producer_path = OBS / 'producer.txt'
    inputs = [path, *toolpaths, producer_path]
    signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in inputs if p.is_file())
    options = (query.get('documentColumn', [''])[0], tuple(query.get('group', [])),
               query.get('q', [''])[0], query.get('type', [''])[0], query.get('tool', [''])[0])
    key = (signature, options)
    with LOCK:
        if key in SUMMARY_CACHE:
            SUMMARY_CACHE.move_to_end(key)
            return SUMMARY_CACHE[key]
    toolsets = {p.name: set(lab.lines(p)) for p in toolpaths}
    producers = {}
    for line in read_text(producer_path).splitlines():
        match = re.search(r'\{Producer:\s*(.*?)\}', line)
        if match and line.strip():
            producers[line.split()[0]] = match.group(1)
    labels = {}
    for name, ids in toolsets.items():
        names = Counter(producers[d] for d in ids if producers.get(d))
        labels[name] = names.most_common(1)[0][0] if names else name
    result = summaries.summarize(path, toolsets, labels, *options)
    with LOCK:
        SUMMARY_CACHE[key] = result
        while len(SUMMARY_CACHE) > 8:
            SUMMARY_CACHE.popitem(last=False)
    return result


def dashboard():
    data = evidence()
    return {'documents': data['documents'], 'summary': data['summary'], 'matrix': data['matrix'], 'tools': data['tools'],
            'counts': {'documents': len(data['documents']), 'resources': len(data['resources']),
                       'prefixes': len({r['prefix'] for r in data['resources']}), 'marks': len(data['marksets']),
                       'scanned': len({r['document'] for r in data['resources']})},
            'scripts': catalog(), 'dependencies': {name: bool(shutil.which(name)) for name in ['bash', 'qpdf', 'pdfinfo', 'pdftotext', 'awk', 'column', 'python3']},
            'token': TOKEN, 'notes': json.loads(read_text(OBS / 'gui-notes.json') or '{}'),
            'resourceSource': 'part1-results/all-resources.tsv · QDF references (may be renumbered)',
            'generatedAt': now()}


def filtered(rows, query):
    needle = query.get('q', [''])[0].lower().strip()
    kind, tool, document = (query.get(key, [''])[0] for key in ('type', 'tool', 'document'))
    output = [r for r in rows if (not needle or needle in ' '.join(str(v) for v in r.values()).lower())
              and (not kind or r.get('resource_type') == kind)
              and (not tool or tool in r.get('tool', '').split(', '))
              and (not document or r.get('document') == document)]
    sort = query.get('sort', [''])[0]
    if sort:
        def key(row):
            value = str(row.get(sort, ''))
            return (0, float(value)) if re.fullmatch(r'-?\d+(?:\.\d+)?', value) else (1, value.lower())
        output.sort(key=key, reverse=query.get('direction', ['asc'])[0] == 'desc')
    return output


def page_table(headers, rows, query):
    matches = filtered(rows, query)
    limit = max(1, min(200, int(query.get('limit', ['50'])[0])))
    offset = max(0, int(query.get('offset', ['0'])[0]))
    return {'headers': headers, 'rows': matches[offset:offset + limit], 'total': len(matches), 'offset': offset, 'limit': limit}


def job_public(job):
    return {k: v for k, v in job.items() if k != 'directory'}


def save_job(job):
    (Path(job['directory']) / 'run.json').write_text(json.dumps(job_public(job), indent=2))


def load_jobs():
    for path in RUNS.glob('*/run.json'):
        try:
            job = json.loads(path.read_text())
            job['directory'] = str(path.parent)
            if job['status'] in ('queued', 'running'):
                job.update(status='interrupted', finalized=True, endedAt=now(), error='The server stopped before this run completed.')
                save_job(job)
            JOBS[job['id']] = job
        except (OSError, ValueError, KeyError):
            continue


def table_artifacts(job):
    directory = Path(job['directory'])
    headers, rows = [], []
    if job['script'] in ('part1_resources.sh', 'test_part1.sh'):
        output = RESULTS if job['script'] == 'part1_resources.sh' else OBS / 'part1-test-results'
        for filename in ('all-resources.tsv', 'prefix-summary.tsv'):
            if (output / filename).is_file():
                shutil.copyfile(output / filename, directory / filename)
    else:
        stdout = read_text(directory / 'stdout.log')
        if stdout.strip():
            nonempty = [line for line in stdout.splitlines() if line.strip()]
            if '\t' in nonempty[0]:
                (directory / 'results.tsv').write_text(stdout)
            else:
                # Set operations return one item per line, while build helpers write files.
                rows = [{'line': i + 1, 'result': text} for i, text in enumerate(nonempty)]
                headers = ['line', 'result']
        script, args = job['script'], job.get('arguments', [])
        target = {'build1vector': 'vectors', 'build1bag': 'bags', 'build1fv': 'fv', 'build1class': 'classes'}.get(script)
        dirs = {'buildvectors': 'vectors', 'buildbags': 'bags', 'buildfvs': 'fv', 'buildclasses': 'classes'}
        if target and args:
            rows = [{'item': line} for line in lab.lines(OBS / target / args[0])]
            headers = ['item']
        elif script in dirs:
            rows = [{'file': p.name, 'entries': len(lab.lines(p))} for p in sorted((OBS / dirs[script]).iterdir()) if p.is_file()]
            headers = ['file', 'entries']
        if headers:
            with (directory / 'results.tsv').open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, delimiter='\t')
                writer.writeheader()
                writer.writerows(rows)
    job['tables'] = [{'name': p.name, 'rows': len(read_table(p)[1])} for p in sorted(directory.glob('*.tsv'))]


def worker(job, command):
    directory = Path(job['directory'])
    final_status = 'failed'
    try:
        with (directory / 'stdout.log').open('w') as out, (directory / 'stderr.log').open('w') as err:
            env = {**os.environ, 'PDF_OBSERVATIONS_DIR': str(OBS), 'PDF_DATASET_DIR': str(DATASET),
                   'PDF_ANALYZER_HOME': str(STATIC), 'PDF_RUN_DIR': str(directory), 'PYTHONUNBUFFERED': '1'}
            with LOCK:
                if job['status'] == 'cancelled':
                    return
                proc = subprocess.Popen(command, cwd=OBS, env=env, stdout=out, stderr=err, start_new_session=True)
                PROCESSES[job['id']] = proc
                job.update(status='running', startedAt=now())
                save_job(job)
            try:
                code = proc.wait(timeout=1800)
                final_status = 'completed' if code == 0 else 'failed'
                job['exitCode'] = code
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                job['error'] = 'Run exceeded the 30 minute limit.'
        table_artifacts(job)
    except Exception as error:
        job['error'] = str(error)
    finally:
        with LOCK:
            PROCESSES.pop(job['id'], None)
            if job['status'] != 'cancelled':
                job['status'] = final_status
            job['finalized'] = True
            job['endedAt'] = now()
            save_job(job)


def script_path(script):
    if script.startswith('custom:'):
        name = script.removeprefix('custom:')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}\.sh', name):
            raise ValueError('Invalid script name')
        path = SCRIPTS / name
    else:
        if script not in {item['id'] for item in catalog() if not item['custom']}:
            raise ValueError('Select an observation script')
        path = OBS / script
    if not path.is_file() or path.is_symlink():
        raise ValueError('Script not found')
    return path


def arguments_for(script, text):
    args = shlex.split(text)
    rule = CATALOG.get(script, ('', '', 'none'))[2]
    if rule == 'document':
        if script == 'test_part1.sh' and not args:
            return []
        if len(args) != 1 or args[0] not in lab.lines(OBS / 'all'):
            raise ValueError('Enter one valid five-character document ID')
    elif rule == 'tool':
        if len(args) != 1 or not re.fullmatch(r'pr(?:0[1-9]|1[0-5])', args[0]):
            raise ValueError('Enter one tool ID, pr01 through pr15')
    elif rule in ('set', 'sets'):
        if len(args) != (1 if rule == 'set' else 2):
            raise ValueError('Enter observation set paths, for example tools/pr01 tools/pr02')
        for arg in args:
            path = (OBS / arg).resolve()
            allowed = {'tools', 'marks', 'othermarks', 'vectors', 'fv', 'classes'}
            if not path.is_file() or (path != OBS / 'all' and (OBS not in path.parents or path.relative_to(OBS).parts[0] not in allowed)):
                raise ValueError('Choose a set in tools, marks, othermarks, vectors, fv, classes, or all')
    elif args:
        raise ValueError('This script does not accept arguments; edit a custom script to add parameters')
    return args


def start_run(payload):
    script = str(payload.get('script', ''))
    path = script_path(script)
    args = arguments_for(script, str(payload.get('arguments', '')))
    missing = [name for name in ('bash', 'qpdf', 'awk', 'column') if not shutil.which(name)]
    if missing:
        raise ValueError('Missing tools: ' + ', '.join(missing))
    with LOCK:
        if PROCESSES or any(j['status'] in ('queued', 'running') for j in JOBS.values()):
            raise ValueError('Another investigation is running. Wait or stop it before starting a new one.')
        identifier = uuid.uuid4().hex[:12]
        directory = RUNS / identifier
        directory.mkdir(parents=True)
        # Run a frozen copy so editing during a run cannot change the investigation.
        source = directory / 'script.sh'
        source.write_text(path.read_text())
        job = {'id': identifier, 'script': script, 'label': payload.get('label') or path.stem,
               'arguments': args, 'status': 'queued', 'createdAt': now(), 'exitCode': None, 'finalized': False, 'tables': [], 'directory': str(directory)}
        JOBS[identifier] = job
        save_job(job)
        threading.Thread(target=worker, args=(job, ['bash', str(source), *args]), daemon=True).start()
        return job_public(job)


class Handler(BaseHTTPRequestHandler):
    server_version = f'PDFAnalyzer/{API_VERSION}'

    def json(self, payload, status=200):
        self.body(json.dumps(payload).encode(), 'application/json; charset=utf-8', status)

    def body(self, body, content_type, status=200, filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        host = self.headers.get('Host', '').split(':')[0]
        return host in ('127.0.0.1', 'localhost')

    def do_GET(self):
        if not self.valid_host():
            return self.json({'error': 'Local host required'}, 403)
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        try:
            if path == '/api/health':
                return self.json({'app': 'pdf-analyzer', 'version': API_VERSION,
                                  'capabilities': ['pdf-inspection', 'result-summaries']})
            if path == '/api/dashboard':
                return self.json(dashboard())
            if path == '/api/resources':
                headers = ['document', 'tool', 'resource_type', 'resource_name', 'prefix', 'number', 'object']
                rows = evidence()['resources']
                if query.get('export'):
                    return self.export(headers, filtered(rows, query), 'resource-evidence.csv')
                return self.json(page_table(headers, rows, query))
            if path == '/api/jobs':
                with LOCK:
                    jobs = [job_public(j) for j in sorted(JOBS.values(), key=lambda j: j['createdAt'], reverse=True)]
                return self.json(jobs)
            if path.startswith('/api/jobs/'):
                parts = path.split('/')
                job = JOBS.get(parts[3])
                if not job:
                    return self.json({'error': 'Run not found'}, 404)
                directory = Path(job['directory'])
                if len(parts) > 4 and parts[4] in ('table', 'summary'):
                    name = query.get('name', ['results.tsv'])[0]
                    if name not in [t['name'] for t in job['tables']]:
                        return self.json({'error': 'Result table not found'}, 404)
                    if parts[4] == 'summary':
                        summary = result_summary(directory / name, query)
                        if query.get('export', [''])[0] == 'csv':
                            group_columns = ['group_' + g for g in summary['groups']]
                            columns = ['tool', 'producer', *group_columns, 'rows', 'documents', 'exemplars', 'represented', 'coverage']
                            rows = [{**r, **dict(zip(group_columns, r['values'])), 'coverage': r['coverage'] if r['coverage'] is not None else ''} for r in summary['rows']]
                            return self.export(columns, rows, f'{job["id"]}-{Path(name).stem}-summary.csv')
                        offset = max(0, int(query.get('offset', ['0'])[0]))
                        limit = max(1, min(100, int(query.get('limit', ['50'])[0])))
                        return self.json({**summary, 'rows': summary['rows'][offset:offset + limit],
                                          'total': len(summary['rows']), 'offset': offset, 'limit': limit,
                                          'source': name, 'job': job['id']})
                    headers, rows = read_table(directory / name)
                    if query.get('export'):
                        return self.export(headers, filtered(rows, query), f'{job["id"]}-{Path(name).stem}.csv')
                    return self.json(page_table(headers, rows, query))
                if len(parts) > 4:
                    return self.json({'error': 'Run view not found'}, 404)
                return self.json({**job_public(job), 'stdout': read_text(directory / 'stdout.log')[-100000:],
                                  'stderr': read_text(directory / 'stderr.log')[-40000:]})
            if path == '/api/script':
                return self.json({'source': read_text(script_path(query.get('id', [''])[0]))})
            if path.startswith('/api/documents/'):
                parts = path.split('/')
                document = parts[3].upper()
                data = evidence()
                if document not in data['index'] or document not in {d['id'] for d in data['documents']}:
                    return self.json({'error': 'PDF is missing or document ID is unknown'}, 404)
                pdf = data['index'][document]
                action = parts[4] if len(parts) > 4 else ''
                if action == 'pdf':
                    return self.body(pdf.read_bytes(), 'application/pdf')
                if action == 'strings':
                    mode = query.get('mode', ['raw'])[0]
                    minimum = int(query.get('minimum', ['4'])[0])
                    index = inspection_cached(pdf, mode, lambda: inspection.strings_index(pdf, mode, minimum), minimum)
                    needle = query.get('q', [''])[0]
                    tag = query.get('tag', [''])[0]
                    matches = inspection.filtered_strings(index, needle, tag, query.get('case', ['0'])[0] == '1')
                    export = query.get('export', [''])[0]
                    if export == 'csv':
                        return self.export(['location', 'reference', 'kind', 'text'], matches, document + '-' + mode + '-strings.csv')
                    if export == 'txt':
                        body = '\n\n'.join(f'[{row["location"]}]\n{row["text"]}' for row in matches)
                        return self.body(body.encode('utf-8'), 'text/plain; charset=utf-8', filename=document + '-' + mode + '-strings.txt')
                    offset = max(0, int(query.get('offset', ['0'])[0]))
                    limit = max(1, min(50, int(query.get('limit', ['20'])[0])))
                    page = []
                    for row in matches[offset:offset + limit]:
                        position = row['text'].find(needle) if query.get('case', ['0'])[0] == '1' else row['text'].casefold().find(needle.casefold())
                        preview_start = max(0, position - 1000) if position >= 8000 else 0
                        page.append({**row, 'text': row['text'][preview_start:preview_start + 8000],
                                     'previewTruncated': len(row['text']) > 8000, 'previewOffset': preview_start})
                    return self.json({'rows': page, 'total': len(matches), 'indexed': len(index['rows']),
                                      'offset': offset, 'limit': limit, 'tags': index['tags'], 'source': index['source'],
                                      'truncated': index['truncated'], 'indexLimit': index['indexLimit'], 'warning': index['warning']})
                if action == 'metadata':
                    detail = inspection_cached(pdf, 'metadata', lambda: inspection.full_metadata(document, pdf))
                    export = query.get('export', [''])[0]
                    if export == 'json':
                        return self.body(json.dumps(detail, ensure_ascii=False, indent=2).encode('utf-8'),
                                         'application/json; charset=utf-8', filename=document + '-metadata.json')
                    if export == 'csv':
                        rows = [{'section': 'pdfinfo', 'field': key, 'value': value} for key, value in detail['pdfinfo'].items() if key != 'document']
                        rows += [{'section': section, **row} for section in ('info', 'trailer') for row in detail[section]]
                        return self.export(['section', 'field', 'value'], rows, document + '-metadata.csv')
                    return self.json(detail)
                if action == 'object':
                    ref = query.get('ref', [''])[0]
                    detail = inspection.object_detail(pdf, ref, decoded=query.get('decoded', ['0'])[0] == '1')
                    if query.get('export', [''])[0] == 'txt':
                        return self.body(detail['text'].encode('utf-8'), 'text/plain; charset=utf-8',
                                         filename=f'{document}-object-{ref.replace(",", "-")}.txt')
                    return self.json(detail)
                if action:
                    return self.json({'error': 'Document view not found'}, 404)
                cache_key = ('inspect', document, pdf.stat().st_mtime_ns)
                with LOCK:
                    detail = CACHE.get(cache_key)
                if detail is None:
                    rows, warning = lab.resource_rows(document, pdf)
                    detail = {'metadata': lab.metadata(document, pdf), 'resources': rows, 'numbering': lab.numbering(rows),
                              'marks': [name for name, members in data['marksets'].items() if document in members], 'warning': warning,
                              'filename': pdf.name, 'source': 'Original PDF object references · qpdf JSON'}
                    with LOCK:
                        CACHE[cache_key] = detail
                if query.get('export'):
                    return self.export(list(detail['resources'][0]) if detail['resources'] else ['document'], detail['resources'], document + '-original-resources.csv')
                return self.json(detail)
            files = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/styles.css': 'styles.css', '/scene.svg': 'scene.svg'}
            if path in files:
                file = STATIC / files[path]
                types = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml'}
                return self.body(file.read_bytes(), types[file.suffix] + '; charset=utf-8')
            self.json({'error': 'Not found'}, 404)
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            self.json({'error': str(error)}, 400)

    def export(self, headers, rows, filename):
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            # Keep CSV safe to open in spreadsheet software.
            writer.writerow({k: "'" + str(v) if str(v).startswith(('=', '+', '-', '@')) else v for k, v in row.items()})
        self.body(output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8', filename=filename)

    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Lab-Token') != TOKEN:
            return self.json({'error': 'Reload the local lab to reconnect.'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.json({'error': 'Same-origin request required'}, 403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 256000:
                raise ValueError('Invalid request size')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            path = urllib.parse.urlparse(self.path).path
            if path == '/api/run':
                return self.json(start_run(payload), 202)
            if path == '/api/scripts':
                name = str(payload.get('name', '')).removesuffix('.sh')
                if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name) or name == 'scan_resources':
                    raise ValueError('Use a script name with letters, numbers, underscores or dashes')
                source = str(payload.get('source', ''))
                if not source.strip():
                    raise ValueError('The script is empty')
                check = subprocess.run(['bash', '-n'], input=source, capture_output=True, text=True, timeout=5)
                if check.returncode:
                    raise ValueError('Bash syntax: ' + check.stderr.strip())
                SCRIPTS.mkdir(exist_ok=True)
                target = SCRIPTS / (name + '.sh')
                if target.is_symlink():
                    raise ValueError('Cannot overwrite a symlink')
                target.write_text(source)
                return self.json({'id': 'custom:' + name + '.sh', 'scripts': catalog()})
            if path == '/api/notes':
                notes = payload.get('notes')
                if not isinstance(notes, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in notes.items()):
                    raise ValueError('Notes must be text')
                (OBS / 'gui-notes.json').write_text(json.dumps(notes, indent=2))
                return self.json({'ok': True})
            if path.startswith('/api/jobs/') and path.endswith('/cancel'):
                identifier = path.split('/')[3]
                with LOCK:
                    job = JOBS.get(identifier)
                    if not job:
                        return self.json({'error': 'Run not found'}, 404)
                    if job['status'] in ('queued', 'running'):
                        job.update(status='cancelled', endedAt=now())
                        proc = PROCESSES.get(identifier)
                        if proc and proc.poll() is None:
                            os.killpg(proc.pid, signal.SIGKILL)
                        save_job(job)
                return self.json(job_public(job))
            self.json({'error': 'Not found'}, 404)
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            self.json({'error': str(error)}, 400)

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--open', action='store_true', help='Open the lab in your browser')
    args = parser.parse_args()
    RUNS.mkdir(exist_ok=True)
    url = f'http://127.0.0.1:{args.port}'
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as error:
        import urllib.request
        try:
            with urllib.request.urlopen(url + '/api/health', timeout=2) as response:
                health = json.load(response)
            if health.get('app') != 'pdf-analyzer':
                raise ValueError('Different application')
        except Exception:
            parser.error(f'Cannot start on port {args.port}: {error}. Choose another port with --port.')
        if health.get('version') != API_VERSION:
            parser.error(f'An older PDF Analyzer server is running at {url}. Stop the existing Start PDF Analyzer task and start it again to load the updated app.')
        print(f'PDF Analyzer is already running at {url}', flush=True)
        if args.open:
            import webbrowser
            webbrowser.open(url)
        raise SystemExit(0)
    load_jobs()
    print(f'PDF Analyzer running at {url}', flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with LOCK:
            for proc in PROCESSES.values():
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
        server.server_close()
