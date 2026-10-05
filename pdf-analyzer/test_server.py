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
from unittest.mock import patch

import lab
import server


def make_pdf(path):
    # Two pages reuse /F3 but refer to different original font objects.
    objects = [
        '<< /Type /Catalog /Pages 2 0 R >>',
        '<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources 8 0 R >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F3 7 0 R /F5 6 0 R >> >> >>',
        '<< /Producer (Fixture producer) /Creator (Fixture creator) >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>',
        '<< /Font 9 0 R >>',
        '<< /F3 6 0 R >>',
    ]
    body = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f'{i} 0 obj\n{obj}\nendobj\n'.encode()
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
        server.JOBS.clear()
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
