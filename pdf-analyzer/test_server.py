"""Functional checks for original references, evidence paging and script lifecycle."""
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
import zlib
import subprocess
from unittest.mock import patch

import lab
import inspection
import server
import summaries
import lab_setup
import io
import os
import zipfile


def make_pdf(path):
    # Two pages reuse /F3 but refer to different original font objects.
    objects = [
        '<< /Type /Catalog /Pages 2 0 R /Metadata 10 0 R >>',
        '<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources 8 0 R /Contents 11 0 R >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F3 7 0 R /F5 6 0 R >> >> >>',
        '<< /Producer (Fixture producer) /Creator (Fixture creator) /CustomEvidence (Custom metadata clue) >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>',
        '<< /Font 9 0 R >>',
        '<< /F3 6 0 R >>',
    ]
    xmp = zlib.compress(b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><evidence>Hidden XMP clue</evidence></x:xmpmeta>')
    content = zlib.compress(b'BT /F3 12 Tf 10 50 Td (Compressed page clue) Tj ET')
    objects += [b'<< /Type /Metadata /Subtype /XML /Filter /FlateDecode /Length ' + str(len(xmp)).encode() + b' >>\nstream\n' + xmp + b'\nendstream',
                b'<< /Filter /FlateDecode /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream']
    body = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f'{i} 0 obj\n'.encode() + (obj if isinstance(obj, bytes) else obj.encode()) + b'\nendobj\n'
    xref = len(body)
    body += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    body += ''.join(f'{offset:010} 00000 n \n' for offset in offsets[1:]).encode()
    body += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R /Info 5 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    path.write_bytes(body)


@unittest.skipUnless(shutil.which('qpdf') and shutil.which('bash') and shutil.which('column'), 'PDF tools required')
class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.obs = base / 'observations'
        cls.dataset = base / 'data'
        cls.obs.mkdir()
        cls.dataset.mkdir()
        for name in ['tools', 'marks', 'gui-runs', 'part1-results']:
            (cls.obs / name).mkdir()
        (cls.obs / 'all').write_text('DEMO1\nDEMO2\n')
        (cls.obs / 'tools/pr01').write_text('DEMO1\n')
        (cls.obs / 'marks/font-present').write_text('DEMO1\nDEMO2\n')
        (cls.obs / 'producer.txt').write_text('DEMO1 {Producer: Fixture producer}{Creator: Fixture creator}\n')
        (cls.obs / 'part1-results/all-resources.tsv').write_text('document\tresource_type\tresource_name\tprefix\tnumber\tobject\nDEMO1\tFont\t/F3\t/F\t3\t6\nDEMO2\tFont\t/TT1\t/TT\t1\t7\n')
        (cls.obs / 'test_part1.sh').write_text('#!/usr/bin/env bash\nmkdir -p "$PDF_OBSERVATIONS_DIR/part1-test-results"\nprintf "document\\tresource_name\\nDEMO1\\t/F3\\n" > "$PDF_OBSERVATIONS_DIR/part1-test-results/all-resources.tsv"\n')
        make_pdf(cls.dataset / 'DEMO1-fixture.pdf')
        cls.previous = {name: getattr(server, name) for name in ['OBS', 'DATASET', 'RESULTS', 'SCRIPTS', 'RUNS']}
        server.OBS = lab.OBS = cls.obs
        server.DATASET = lab.DATASET = cls.dataset
        server.RESULTS = cls.obs / 'part1-results'
        server.SCRIPTS = cls.obs / 'gui-scripts'
        server.RUNS = cls.obs / 'gui-runs'
        server.CACHE.clear()
        server.VIEW_CACHE.clear()
        server.SUMMARY_CACHE.clear()
        server.JOBS.clear()
        server.IMPORT_STATE.clear()
        server.IMPORT_STATE['status'] = 'idle'
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        for name, value in cls.previous.items():
            setattr(server, name, value)
        lab.OBS, lab.DATASET = server.OBS, server.DATASET
        server.CACHE.clear()
        server.VIEW_CACHE.clear()
        server.SUMMARY_CACHE.clear()
        server.JOBS.clear()
        cls.tmp.cleanup()

    def request(self, path, body=None, token=True, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=10)
        request_headers = dict(headers or {})
        if body is not None:
            request_headers['Content-Type'] = 'application/json'
            if token:
                request_headers['X-Lab-Token'] = server.TOKEN
        connection.request('GET' if body is None else 'POST', path, json.dumps(body) if body is not None else None, request_headers)
        response = connection.getresponse()
        raw = response.read()
        content = json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw
        status = response.status
        connection.close()
        return status, content

    def wait_run(self, identifier):
        for _ in range(150):
            _, job = self.request('/api/jobs/' + identifier)
            if job['status'] not in ('queued', 'running'):
                if job.get('endedAt'):
                    return job
            time.sleep(.02)
        self.fail('Investigation did not finish')

    def test_original_objects_and_local_scope_reuse(self):
        rows, warning = lab.resource_rows('DEMO1', self.dataset / 'DEMO1-fixture.pdf')
        f3 = [r for r in rows if r['resource_name'] == '/F3']
        self.assertEqual({r['reference'] for r in f3}, {'6 0 R', '7 0 R'})
        self.assertEqual(len({r['scope'] for r in f3}), 2)
        numbers = lab.numbering(rows)
        self.assertIn('4', [r['missing_between'] for r in numbers])
        status, result = self.request('/api/documents/DEMO1/object?ref=6,0')
        self.assertEqual(status, 200)
        self.assertIn('/Helvetica', result['text'])
        self.assertEqual(self.request('/api/documents/DEMO1/object?ref=6;whoami')[0], 400)

    def test_evidence_paging_filter_export_and_missing_pdf(self):
        status, data = self.request('/api/dashboard')
        self.assertEqual(status, 200)
        self.assertEqual(data['counts']['documents'], 2)
        self.assertEqual(data['counts']['resources'], 2)
        _, table = self.request('/api/resources?tool=pr01&limit=1')
        self.assertEqual(table['total'], 1)
        self.assertEqual(table['rows'][0]['document'], 'DEMO1')
        _, output = self.request('/api/resources?type=Font&q=TT&export=csv')
        self.assertIn(b'DEMO2', output)
        self.assertNotIn(b'DEMO1', output)
        self.assertEqual(self.request('/api/documents/DEMO2')[0], 404)

    def test_strings_offsets_search_tags_paging_and_exports(self):
        status, data = self.request('/api/documents/DEMO1/strings?mode=raw&q=Fixture&limit=1')
        self.assertEqual(status, 200)
        self.assertEqual(len(data['rows']), 1)
        self.assertGreaterEqual(data['total'], 1)
        original = (self.dataset / 'DEMO1-fixture.pdf').read_bytes()
        row = data['rows'][0]
        self.assertTrue(original[row['offset']:].startswith(row['text'].encode('ascii')))
        _, case_sensitive = self.request('/api/documents/DEMO1/strings?mode=raw&q=fixture&case=1')
        self.assertEqual(case_sensitive['total'], 0)
        _, structural = self.request('/api/documents/DEMO1/strings?mode=objects&tag=%2FF3')
        self.assertEqual(structural['total'], 2)
        self.assertTrue(all('/F3' in r['tags'] for r in structural['rows']))
        self.assertIn('/Resources', [t['tag'] for t in structural['tags']])
        _, export = self.request('/api/documents/DEMO1/strings?mode=objects&tag=%2FF3&export=txt')
        self.assertIn(b'6 0 R', export)
        self.assertIn(b'7 0 R', export)
        _, csv = self.request('/api/documents/DEMO1/strings?mode=raw&q=Fixture&export=csv')
        self.assertIn(b'location,reference,kind,text', csv)
        self.assertEqual(self.request('/api/documents/DEMO1/strings?minimum=1')[0], 400)
        self.assertEqual(self.request('/api/documents/DEMO1/strings?mode=invalid')[0], 400)

    def test_compressed_content_and_original_stream_preview(self):
        _, raw = self.request('/api/documents/DEMO1/strings?mode=raw&q=Compressed')
        self.assertEqual(raw['total'], 0)
        _, text = self.request('/api/documents/DEMO1/strings?mode=text&q=Compressed')
        self.assertEqual(text['total'], 1)
        self.assertEqual(text['rows'][0]['location'], 'Page 1')
        _, decoded = self.request('/api/documents/DEMO1/object?ref=11,0&decoded=1')
        self.assertTrue(decoded['stream'])
        self.assertIn('Compressed page clue', decoded['text'])
        self.assertEqual(self.request('/api/documents/DEMO1/object?ref=6,0&decoded=1')[0], 400)
        self.assertEqual(self.request('/api/documents/DEMO1/object?ref=../11&decoded=1')[0], 400)
        _, exported = self.request('/api/documents/DEMO1/object?ref=11,0&decoded=1&export=txt')
        self.assertIn(b'Compressed page clue', exported)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'compressed.pdf'
            subprocess.run(['qpdf', '--object-streams=generate', str(self.dataset / 'DEMO1-fixture.pdf'), str(path)], check=True, capture_output=True)
            raw_names = inspection.strings_index(path, 'raw')
            objects = inspection.strings_index(path, 'objects')
            self.assertFalse(inspection.filtered_strings(raw_names, '/BaseFont'))
            self.assertTrue(inspection.filtered_strings(objects, tag='/BaseFont'))

    def test_full_metadata_custom_fields_xmp_and_original_ids(self):
        status, data = self.request('/api/documents/DEMO1/metadata')
        self.assertEqual(status, 200)
        self.assertEqual(data['pdfinfo']['Producer'], 'Fixture producer')
        self.assertIn({'field':'/CustomEvidence', 'value':'Custom metadata clue'}, data['info'])
        self.assertEqual(data['infoReference'], '5 0 R')
        self.assertEqual(data['xmpReference'], '10 0 R')
        self.assertIn('Hidden XMP clue', data['xmp'])
        self.assertTrue(any(row['field']=='/Root' for row in data['trailer']))
        _, exported = self.request('/api/documents/DEMO1/metadata?export=json')
        self.assertIn('Hidden XMP clue', exported['xmp'])
        _, csv = self.request('/api/documents/DEMO1/metadata?export=csv')
        self.assertIn(b'CustomEvidence', csv)
        self.assertEqual(self.request('/api/documents/DEMO1/unknown-view')[0], 404)

    def test_index_limits_are_explicit_and_do_not_change_pdf(self):
        path = self.dataset / 'DEMO1-fixture.pdf'
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch.object(inspection, 'MAX_INDEX_ROWS', 2):
            data = inspection.strings_index(path, 'raw')
        self.assertTrue(data['truncated'])
        self.assertEqual(len(data['rows']), 2)
        inspection.full_metadata('DEMO1', path)
        inspection.object_detail(path, '11,0', decoded=True)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_summary_deduplicates_pdfs_and_reports_membership_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.tsv'
            path.write_text('document\tresource_type\tprefix\nA\tFont\t/F\nA\tFont\t/F\nA\tXObject\t/Im\nB\tFont\t/TT\nC\tFont\t/F\n\tFont\t/F\n')
            toolsets = {'pr01': {'A', 'D'}, 'pr02': {'A', 'B'}, 'pr03': {'E'}}
            result = summaries.summarize(path, toolsets, {}, groups=['resource_type', 'prefix'])
            overview = {r['tool']: r for r in result['overview']}
            self.assertEqual(overview['pr01']['rows'], 3)
            self.assertEqual(overview['pr01']['documents'], 1)
            self.assertEqual(overview['pr01']['coverage'], 50)
            self.assertEqual(overview['pr02']['coverage'], 100)
            self.assertEqual(overview['pr03']['rows'], 0)
            self.assertEqual(overview['Unassigned']['coverage'], None)
            self.assertEqual(result['counts']['matchedRows'], 6)
            self.assertEqual(result['counts']['matchedDocuments'], 3)
            self.assertEqual(result['counts']['missingDocumentRows'], 1)
            self.assertEqual(result['counts']['overlapDocuments'], 1)
            font = next(r for r in result['rows'] if r['tool']=='pr01' and r['values']==['Font','/F'])
            self.assertEqual((font['rows'], font['documents']), (2, 1))
            filtered = summaries.summarize(path, toolsets, {}, groups=['prefix'], query='/TT', tool='pr02')
            self.assertEqual(filtered['counts']['matchedRows'], 1)
            self.assertEqual(filtered['overview'][0]['represented'], 2)
            self.assertEqual(filtered['overview'][0]['coverage'], 50)
            empty = summaries.summarize(path, toolsets, {}, query='no matching result')
            self.assertEqual(empty['counts']['matchedRows'], 0)
            self.assertEqual(len(empty['overview']), 3)

    def test_summary_api_covers_all_pages_and_exports_all_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.tsv'
            path.write_text('document\tresource_type\tprefix\n'+('DEMO1\tFont\t/F\n'*120)+'DEMO1\tXObject\t/Im\nDEMO2\tFont\t/TT\n')
            identifier = 'summary-fixture'
            server.JOBS[identifier] = {'id': identifier, 'directory': directory, 'tables': [{'name':'results.tsv','rows':122}]}
            try:
                url = '/api/jobs/'+identifier+'/summary?name=results.tsv&group=resource_type&group=prefix&limit=1'
                status, data = self.request(url)
                self.assertEqual(status, 200)
                self.assertEqual(data['total'], 3)
                self.assertEqual(len(data['rows']), 1)
                _, complete = self.request(url+'&export=json')
                self.assertEqual(len(complete['rows']), 3)
                self.assertEqual(data['counts']['sourceRows'], 122)
                self.assertEqual(data['overview'][0]['rows'], 121)
                self.assertEqual(data['overview'][0]['documents'], 1)
                _, output = self.request(url+'&export=csv')
                self.assertIn(b'XObject', output)
                self.assertIn(b'/TT', output)
                self.assertIn(b'group_resource_type,group_prefix', output)
                _, filtered = self.request(url+'&type=Font&q=%2FF&tool=pr01')
                self.assertEqual(filtered['counts']['matchedRows'], 120)
                self.assertEqual(filtered['overview'][0]['documents'], 1)
                self.assertEqual(filtered['counts']['sourceRows'], 122)
                self.assertEqual(self.request(url+'&group=invalid')[0], 400)
                self.assertEqual(self.request(url+'&documentColumn=missing')[0], 400)
                status, invalid_column = self.request(url+'&documentColumn=prefix')
                self.assertEqual(status, 400)
                self.assertIn('Choose document', invalid_column['error'])
                self.assertEqual(self.request(url+'&tool=unknown')[0], 400)
                self.assertEqual(self.request('/api/jobs/'+identifier+'/summary?name=../results.tsv')[0], 404)
            finally:
                server.JOBS.pop(identifier)

    def test_health_identifies_summary_support_and_unknown_run_views_fail(self):
        status, health = self.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(health['version'], server.API_VERSION)
        self.assertIn('result-summaries', health['capabilities'])
        self.assertIn('lab-setup', health['capabilities'])
        identifier = 'unknown-view-fixture'
        server.JOBS[identifier] = {'id': identifier, 'directory': str(self.obs)}
        try:
            status, data = self.request('/api/jobs/'+identifier+'/unsupported-view')
            self.assertEqual(status, 404)
            self.assertEqual(data['error'], 'Run view not found')
        finally:
            server.JOBS.pop(identifier)

    def test_setup_status_and_authenticated_pdf_import_are_persistent(self):
        original_all = (self.obs/'all').read_bytes()
        original_hash = hashlib.sha256((self.dataset/'DEMO1-fixture.pdf').read_bytes()).hexdigest()
        payload = (self.dataset/'DEMO1-fixture.pdf').read_bytes()
        def upload(name, data, token=True):
            connection = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=10)
            headers = {'Content-Type':'application/octet-stream'}
            if token:
                headers['X-Lab-Token'] = server.TOKEN
            connection.request('POST','/api/setup/import?filename='+name, data, headers)
            response = connection.getresponse()
            result = json.loads(response.read())
            status = response.status
            connection.close()
            return status, result
        def wait_import():
            for _ in range(100):
                _, data = self.request('/api/setup')
                if data['import']['status'] in ('completed','failed') and not list((self.obs/'.uploads').glob('*.upload')):
                    return data
                time.sleep(.02)
            self.fail('PDF import did not finish')
        try:
            _, setup = self.request('/api/setup')
            self.assertEqual(setup['dataset']['available'], 1)
            self.assertEqual(setup['dataset']['missing'], 1)
            self.assertEqual(upload('NEW01.pdf',payload,False)[0],403)
            self.assertEqual(upload('code.sh',payload)[0],400)
            self.assertEqual(upload('empty.pdf',b'')[0],400)
            server.JOBS['import-blocker'] = {'status':'running'}
            self.assertEqual(upload('NEW01.pdf',payload)[0],400)
            server.JOBS.pop('import-blocker')
            self.assertEqual(upload('NEW01.pdf',payload)[0],202)
            setup = wait_import()
            self.assertEqual(setup['import']['status'],'completed')
            self.assertEqual(setup['import']['imported'],1)
            self.assertEqual(setup['dataset']['available'],2)
            self.assertIn('NEW01',lab.lines(self.obs/'all'))
            self.assertEqual(self.request('/api/documents/NEW01/metadata')[0],200)
            self.assertEqual(upload('NEW01.pdf',payload)[0],202)
            self.assertEqual(wait_import()['import']['skipped'],1)
            self.assertEqual(upload('BAD01.pdf',b'not a PDF')[0],202)
            self.assertEqual(wait_import()['import']['status'],'failed')
            self.assertFalse((self.dataset/'BAD01.pdf').exists())
            self.assertEqual(original_hash,hashlib.sha256((self.dataset/'DEMO1-fixture.pdf').read_bytes()).hexdigest())
        finally:
            server.JOBS.pop('import-blocker',None)
            (self.dataset/'NEW01.pdf').unlink(missing_ok=True)
            (self.obs/'all').write_bytes(original_all)
            server.IMPORT_STATE.clear()
            server.IMPORT_STATE['status']='idle'
            server.CACHE.clear()

    def test_summary_cache_refreshes_when_results_or_exemplars_change(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base/'tools').mkdir()
            (base/'tools/pr01').write_text('A\nB\n')
            path = base/'results.tsv'
            path.write_text('document\tobservation\nA\tfirst\n')
            with patch.object(server, 'OBS', base):
                one = server.result_summary(path, {})
                self.assertEqual(one['overview'][0]['coverage'], 50)
                path.write_text('document\tobservation\nA\tfirst\nB\tsecond\n')
                two = server.result_summary(path, {})
                self.assertEqual(two['overview'][0]['coverage'], 100)
                (base/'tools/pr01').write_text('A\nB\nC\n')
                three = server.result_summary(path, {})
                self.assertEqual(three['overview'][0]['coverage'], 66.67)
                (base/'totals.tsv').write_text('prefix\tdocuments\n/F\t3\n')
                with self.assertRaisesRegex(ValueError, 'PDF document IDs'):
                    server.result_summary(base/'totals.tsv', {})

    def test_script_save_syntax_run_table_and_reload(self):
        self.assertEqual(self.request('/api/scripts', {'name':'../escape', 'source':'echo bad'})[0], 400)
        self.assertEqual(self.request('/api/scripts', {'name':'syntax', 'source':'if then'})[0], 400)
        status, saved = self.request('/api/scripts', {'name':'functional-check', 'source':'printf "document\\tvalue\\nDEMO1\\t42\\n"\n'})
        self.assertEqual(status, 200)
        status, run = self.request('/api/run', {'script':saved['id']})
        self.assertEqual(status, 202)
        job = self.wait_run(run['id'])
        self.assertEqual(job['status'], 'completed')
        _, results = self.request('/api/jobs/' + run['id'] + '/table?name=results.tsv')
        self.assertEqual(results['rows'], [{'document':'DEMO1', 'value':'42'}])
        server.load_jobs()
        self.assertEqual(server.JOBS[run['id']]['status'], 'completed')

    def test_completion_waits_for_result_snapshot(self):
        _, saved = self.request('/api/scripts', {'name':'snapshot-check', 'source':'printf \"document\\tvalue\\nDEMO1\\tcomplete\\n\"\n'})
        collecting, release = threading.Event(), threading.Event()
        original = server.table_artifacts
        def collect(job):
            collecting.set()
            release.wait(3)
            original(job)
        with patch.object(server, 'table_artifacts', collect):
            _, run = self.request('/api/run', {'script':saved['id']})
            self.assertTrue(collecting.wait(3))
            _, intermediate = self.request('/api/jobs/' + run['id'])
            self.assertEqual(intermediate['status'], 'running')
            release.set()
            job = self.wait_run(run['id'])
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['tables'][0]['rows'], 1)
        self.assertTrue(job['finalized'])

    def test_single_document_test_preserves_full_extraction(self):
        full = self.obs / 'part1-results/all-resources.tsv'
        before = hashlib.sha256(full.read_bytes()).hexdigest()
        status, run = self.request('/api/run', {'script':'test_part1.sh', 'arguments':'DEMO1'})
        self.assertEqual(status, 202)
        job = self.wait_run(run['id'])
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(before, hashlib.sha256(full.read_bytes()).hexdigest())
        self.assertEqual(job['tables'][0]['rows'], 1)

    def test_local_request_auth_and_excluded_friend_script(self):
        self.assertEqual(self.request('/api/run', {'script':'test_part1.sh'}, token=False)[0], 403)
        self.assertEqual(self.request('/api/run', {'script':'test_part1.sh'}, headers={'Origin':'https://example.com'})[0], 403)
        self.assertEqual(self.request('/api/dashboard', headers={'Host':'evil.example'})[0], 403)
        self.assertEqual(self.request('/api/run', {'script':'scan_resources.sh'})[0], 400)
        self.assertEqual(self.request('/api/run', {'script':'test_part1.sh', 'arguments':'DEMO1; touch /tmp/nope'})[0], 400)
        self.assertEqual(self.request('/server.py')[0], 404)

    def test_remote_access_key_protects_read_write_and_original_files(self):
        key = 'remote-fixture-key-' + 'x' * 32
        with patch.object(server, 'REMOTE', True), patch.object(server, 'ACCESS_KEY', key):
            for path in ('/api/dashboard', '/api/setup', '/api/jobs', '/api/resources',
                         '/api/documents/DEMO1/pdf', '/api/documents/DEMO1/metadata'):
                self.assertEqual(self.request(path)[0], 401, path)
                self.assertEqual(self.request(path, headers={'Authorization':'Bearer incorrect'})[0], 401, path)
                self.assertEqual(self.request(path, headers={'Authorization':'Bearer '+key})[0], 200, path)
            self.assertEqual(self.request('/api/health')[0], 200)
            self.assertEqual(self.request('/api/scripts', {'name':'blocked','source':'echo no'})[0], 401)
            self.assertFalse((server.SCRIPTS/'blocked.sh').exists())
            self.assertEqual(self.request('/api/scripts', {'name':'../invalid','source':'echo no'}, headers={'Authorization':'Bearer '+key})[0], 400)
            self.assertEqual(self.request('/api/scripts', {'name':'blocked','source':'echo no'}, token=False, headers={'Authorization':'Bearer '+key})[0], 403)

    def test_remote_cors_allows_pages_and_rejects_other_origins_and_hosts(self):
        origin = 'https://shaydennaidoo.github.io'
        key = 'remote-fixture-key-' + 'x' * 32
        with patch.object(server, 'REMOTE', True), patch.object(server, 'ACCESS_KEY', key), patch.object(server, 'ALLOWED_ORIGINS', {origin}), patch.object(server, 'ALLOWED_HOSTS', {'localhost','127.0.0.1','lab.onrender.com'}):
            for method, request_origin, expected in [('OPTIONS',origin,204),('OPTIONS','https://other.example',403),('GET',origin,200),('GET','https://other.example',403)]:
                connection = http.client.HTTPConnection('127.0.0.1', self.http.server_port)
                connection.request(method, '/api/dashboard', headers={'Host':'lab.onrender.com','Origin':request_origin,'Authorization':'Bearer '+key})
                response = connection.getresponse()
                self.assertEqual(response.status, expected)
                self.assertEqual(response.getheader('Access-Control-Allow-Origin'), origin if expected in (200,204) else None)
                if method == 'OPTIONS' and expected == 204:
                    self.assertIn('Authorization', response.getheader('Access-Control-Allow-Headers'))
                response.read();connection.close()
            self.assertEqual(self.request('/api/dashboard', headers={'Host':'evil.example','Authorization':'Bearer '+key})[0], 403)
            self.assertEqual(self.request('/api/scripts', {'name':'../invalid','source':'echo no'}, headers={'Origin':origin,'Authorization':'Bearer '+key})[0], 400)
            self.assertEqual(self.request('/api/scripts', {'name':'blocked','source':'echo no'}, headers={'Origin':'https://other.example','Authorization':'Bearer '+key})[0], 403)

    def test_complete_json_exports_keep_all_rows_and_unmodified_values(self):
        _, resources = self.request('/api/resources?limit=1&offset=1&export=json')
        self.assertEqual(len(resources['rows']), 2)
        _, strings = self.request('/api/documents/DEMO1/strings?mode=objects&tag=%2FF3&limit=1&offset=1&export=json')
        self.assertEqual(len(strings['rows']), 2)
        with tempfile.TemporaryDirectory() as directory:
            identifier = 'pdf-export-fixture'
            path = Path(directory)
            path.joinpath('results.tsv').write_text('document\tvalue\n'+''.join(f'DEMO1\t-{i}\n' for i in range(122)))
            output = 'FIRST LINE\n'+'evidence\n'*15000+'LAST LINE\n'
            path.joinpath('stdout.log').write_text(output)
            path.joinpath('stderr.log').write_text('a warning\n')
            server.JOBS[identifier] = {'id':identifier,'directory':directory,'tables':[{'name':'results.tsv','rows':122}]}
            try:
                _, result = self.request('/api/jobs/'+identifier+'/table?name=results.tsv&limit=1&offset=100&export=json')
                self.assertEqual(len(result['rows']), 122)
                self.assertEqual(result['rows'][-1]['value'], '-121')
                _, filtered = self.request('/api/jobs/'+identifier+'/table?name=results.tsv&q=-121&export=json')
                self.assertEqual(len(filtered['rows']), 1)
                _, report = self.request('/api/jobs/'+identifier+'/report')
                self.assertEqual(report['stdout'], output)
                self.assertEqual(report['stderr'], 'a warning\n')
                self.assertNotIn('directory', report)
            finally:
                server.JOBS.pop(identifier)

    def test_remote_startup_fails_closed_without_a_strong_access_key(self):
        env = {**os.environ, 'PDF_LAB_REMOTE':'1', 'PDF_LAB_ACCESS_KEY':'short'}
        result = subprocess.run(['python3',str(Path(server.__file__))],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('at least 32 characters', result.stderr)

    def test_serial_execution_and_cancel(self):
        _, saved = self.request('/api/scripts', {'name':'cancellation-check', 'source':'sleep 10\n'})
        _, run = self.request('/api/run', {'script':saved['id']})
        self.assertEqual(self.request('/api/run', {'script':saved['id']})[0], 400)
        status, cancelled = self.request('/api/jobs/' + run['id'] + '/cancel', {})
        self.assertEqual(status, 200)
        self.assertEqual(cancelled['status'], 'cancelled')
        for _ in range(100):
            if run['id'] not in server.PROCESSES:
                break
            time.sleep(.02)
        self.assertNotIn(run['id'], server.PROCESSES)


if __name__ == '__main__':
    unittest.main(verbosity=2)
