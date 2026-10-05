"""Fresh-lab bootstrap, nested dataset archives and evidence-preserving imports."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import lab_setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.obs = self.base/'environment/observations'
        self.dataset = self.base/'dataset'
        lab_setup.initialize(self.obs,self.dataset)

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, files, name='dataset.zip'):
        path = self.base/name
        with zipfile.ZipFile(path,'w') as archive:
            for name,data in files.items():
                archive.writestr(name,data)
        return path

    def test_seed_and_restart_preserve_user_scripts_notes_and_results(self):
        seed = self.base/'seed'
        source = seed/'observations'
        (source/'tools').mkdir(parents=True)
        (source/'gui-scripts').mkdir()
        (source/'gui-runs').mkdir()
        (source/'all').write_text('ABCDE\n')
        (source/'tools/pr01').write_text('ABCDE\n')
        helper = source/'buildvectors'
        helper.write_text('#!/bin/bash\necho hello\n');helper.chmod(0o755)
        (source/'gui-scripts/mine.sh').write_text('seed version')
        (source/'gui-runs/private.log').write_text('must not seed this')
        (source/'gui-notes.json').write_text('must not seed this')
        (source/'scan_resources.sh').write_text('friend script')
        mine = self.obs/'gui-scripts/mine.sh';mine.write_text('my saved investigation')
        notes = self.obs/'gui-notes.json';notes.write_text('{"my":"notes"}')
        results = self.obs/'gui-runs/saved.tsv';results.write_text('document\nABCDE\n')
        self.assertGreater(lab_setup.initialize(self.obs,self.dataset,seed),0)
        self.assertEqual(mine.read_text(),'my saved investigation')
        self.assertEqual(notes.read_text(),'{"my":"notes"}')
        self.assertTrue(os.access(self.obs/'buildvectors',os.X_OK))
        self.assertFalse((self.obs/'scan_resources.sh').exists())
        self.assertFalse((self.obs/'gui-runs/private.log').exists())
        (self.obs/'.uploads/upload-interrupted.upload').write_bytes(b'partial upload')
        (self.dataset/'.import-interrupted').mkdir()
        self.assertEqual(lab_setup.initialize(self.obs,self.dataset,seed),0)
        self.assertEqual(results.read_text(),'document\nABCDE\n')
        self.assertFalse((self.obs/'.uploads/upload-interrupted.upload').exists())
        self.assertFalse((self.dataset/'.import-interrupted').exists())

    def test_nested_assignment_zip_and_reimport_keep_original_hashes(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner,'w') as archive:
            archive.writestr('data/ABCDE-original.pdf',b'%PDF-1.7\noriginal evidence')
            archive.writestr('data/FGHIJ-original.pdf',b'%PDF-1.4\nsecond evidence')
            archive.writestr('manifest.txt','ignored metadata')
        upload = self.bundle({'lcwa_gov_pdf_data.zip':inner.getvalue(),'README.txt':'ignored'})
        result = lab_setup.import_dataset(upload,upload.name,self.dataset,self.obs)
        self.assertEqual(result['imported'],2)
        self.assertEqual((self.obs/'all').read_text(),'ABCDE\nFGHIJ\n')
        before = {p.name:lab_setup.digest(p) for p in self.dataset.glob('*.pdf')}
        result = lab_setup.import_dataset(upload,upload.name,self.dataset,self.obs)
        self.assertEqual((result['imported'],result['skipped']),(0,2))
        self.assertEqual(before,{p.name:lab_setup.digest(p) for p in self.dataset.glob('*.pdf')})
        self.assertFalse(list(self.dataset.glob('.import-*')))

    def test_invalid_archive_or_conflicting_id_does_not_install_partial_results(self):
        existing = self.dataset/'ABCDE.pdf';existing.write_bytes(b'%PDF-1.4\noriginal')
        before = lab_setup.digest(existing)
        for files in ({'FGHIJ.pdf':b'%PDF-1.4\nnew','ABCDE.pdf':b'%PDF-1.4\nchanged'},
                      {'FGHIJ.pdf':b'%PDF-1.4\nnew','../escaped.pdf':b'%PDF-1.4\nevil'}):
            upload = self.bundle(files)
            with self.assertRaises(ValueError):
                lab_setup.import_dataset(upload,upload.name,self.dataset,self.obs)
            self.assertEqual(lab_setup.digest(existing),before)
            self.assertEqual([p.name for p in self.dataset.glob('*.pdf')],['ABCDE.pdf'])
            self.assertEqual((self.obs/'all').read_text(),'')

    def test_mislabeled_pdf_is_reported_without_blocking_a_valid_corpus(self):
        upload = self.bundle({'ABCDE.pdf':b'%PDF-1.4\nvalid original','BAD01.pdf':b'<!DOCTYPE html>web page'})
        result = lab_setup.import_dataset(upload, upload.name, self.dataset, self.obs)
        self.assertEqual(result['imported'],1)
        self.assertEqual(result['rejected'],['BAD01.pdf'])
        self.assertIn('BAD01.pdf',result['message'])
        self.assertEqual([p.name for p in self.dataset.glob('*.pdf')],['ABCDE.pdf'])
        self.assertEqual((self.obs/'all').read_text(),'ABCDE\n')
        upload = self.bundle({'BAD01.pdf':b'<!DOCTYPE html>web page'})
        with self.assertRaisesRegex(ValueError,'No valid PDFs'):
            lab_setup.import_dataset(upload,upload.name,self.dataset,self.obs)

    def test_short_filenames_limits_and_link_rejection(self):
        upload = self.base/'a.pdf';upload.write_bytes(b'%PDF-1.4\nsmall PDF')
        lab_setup.import_dataset(upload,upload.name,self.dataset,self.obs)
        document = hashlib.sha256(upload.read_bytes()).hexdigest()[:5].upper()
        self.assertIn(document, (self.obs/'all').read_text())
        self.assertTrue(next(self.dataset.glob('*.pdf')).name.startswith(document))
        link = zipfile.ZipInfo('data/LINK1.pdf');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        bundle=self.base/'link.zip'
        with zipfile.ZipFile(bundle,'w') as archive:
            archive.writestr(link,'/outside/file.pdf')
        with self.assertRaisesRegex(ValueError,'symbolic links'):
            lab_setup.import_dataset(bundle,bundle.name,self.dataset,self.obs)
        bundle=self.bundle({'NEW01.pdf':b'%PDF-1.4\ntoo big'})
        with patch.object(lab_setup,'MAX_EXPANDED_BYTES',5),self.assertRaisesRegex(ValueError,'limit'):
            lab_setup.import_dataset(bundle,bundle.name,self.dataset,self.obs)
        self.assertFalse((self.dataset/'NEW01.pdf').exists())

    def test_container_paths_are_used_by_generated_investigations(self):
        command = ['python3','-c','import json,lab; print(json.dumps([str(lab.OBS),str(lab.DATASET)]))']
        result = subprocess.run(command,cwd=Path(__file__).parent,env={**os.environ,'PDF_OBSERVATIONS_DIR':str(self.obs),'PDF_DATASET_DIR':str(self.dataset)},check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(result.stdout),[str(self.obs),str(self.dataset)])
