"""Regression checks for the supplied strict-mode resource investigation."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_server import make_pdf

SCRIPT = Path(__file__).parent / 'examples/part1-investigation-fixed.sh'


@unittest.skipUnless(shutil.which('qpdf') and shutil.which('column'), 'PDF tools required')
class ResourceScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.obs = self.base/'observations'
        self.dataset = self.base/'dataset'
        self.run = self.base/'run'
        (self.obs/'tools').mkdir(parents=True)
        self.dataset.mkdir()
        self.run.mkdir()
        self.env = {**os.environ, 'PDF_OBSERVATIONS_DIR':str(self.obs),
                    'PDF_DATASET_DIR':str(self.dataset), 'PDF_RUN_DIR':str(self.run)}

    def tearDown(self):
        self.temp.cleanup()

    def execute(self):
        return subprocess.run(['bash',str(SCRIPT)],env=self.env,capture_output=True,text=True,timeout=20)

    def test_zero_overlap_and_qpdf_warning_do_not_abort_the_summary(self):
        (self.obs/'all').write_text('DEMO1\nDEMO2\nMISS1\n')
        (self.obs/'tools/pr01').write_text('DEMO1\n')
        (self.obs/'tools/pr02').write_text('OTHER\n')
        (self.obs/'tools/pr03').write_text('')
        make_pdf(self.dataset/'DEMO1.pdf')
        make_pdf(self.dataset/'DEMO2.pdf')
        damaged=self.dataset/'DEMO2.pdf'
        damaged.write_bytes(re.sub(rb'startxref\n[0-9]+',b'startxref\n0',damaged.read_bytes()))
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.dataset.glob('*.pdf')}
        result=self.execute()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PART 1 COMPLETE',result.stdout)
        self.assertIn('QPDF WARNING',result.stdout)
        self.assertIn('DEMO2\tFont', (self.run/'all-resources.tsv').read_text())
        self.assertIn('pr01\tfont\t/F\t1\t1\t100.0%', (self.run/'prefix-summary.tsv').read_text())
        self.assertEqual((self.run/'missing-pdfs.txt').read_text(),'MISS1\n')
        self.assertIn('operation succeeded with warnings',(self.run/'qpdf-errors.txt').read_text())
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.dataset.glob('*.pdf')})

    def test_empty_observation_and_exemplar_sets_produce_header_tables(self):
        (self.obs/'all').write_text('')
        (self.obs/'tools/pr01').write_text('')
        result=self.execute()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Documents expected: 0',result.stdout)
        self.assertEqual(len((self.run/'all-resources.tsv').read_text().splitlines()),1)
        self.assertEqual(len((self.run/'prefix-summary.tsv').read_text().splitlines()),1)
