"""Exercise snapshot commit/recovery with real rclone transfers to an isolated local backend."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import drive_backup
import lab_setup


@unittest.skipUnless(shutil.which('rclone'), 'rclone required (included in Docker)')
class DriveBackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.remote = self.root / 'remote'
        self.environment = patch.dict(os.environ, {key: value for key, value in (
            ('PDF_LAB_DRIVE_CLIENT_ID', 'test-client'), ('PDF_LAB_DRIVE_CLIENT_SECRET', 'test-secret'),
            ('PDF_LAB_DRIVE_REFRESH_TOKEN', 'test-refresh-token'), ('PDF_LAB_DRIVE_FOLDER', 'Test Lab'))})
        self.environment.start()
        self.lab = self.manager('source')
        self.lab.restore()  # No saved backup: a first backup may now be created.
        self.assertTrue(self.lab.initialized, self.lab.status())
        (self.lab.dataset / 'DEMO1.pdf').write_bytes(b'%PDF-1.4\nfixture original\n')
        (self.lab.observations / 'all').write_text('DEMO1\n')
        (self.lab.observations / 'gui-notes.json').write_text(json.dumps({'DEMO1': 'first notes'}))
        script = self.lab.observations / 'gui-scripts/test.sh'
        script.write_text('#!/bin/bash\nprintf "document\\tvalue\\nDEMO1\\t1\\n"\n')
        script.chmod(0o755)

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def manager(self, name, scope='workspace'):
        obs, dataset = self.root / name / 'observations', self.root / name / 'dataset'
        lab_setup.initialize(obs, dataset)
        manager = drive_backup.DriveBackup(obs, dataset, scope)
        manager.remote = str(self.remote)  # Only the backend path changes; real transfer commands are exercised.
        return manager

    def backup(self):
        self.lab.changed()
        self.lab.begin_backup()
        self.lab.backup()
        self.assertEqual(self.lab.status()['status'], 'ready', self.lab.status())
        self.assertFalse(self.lab.status()['dirty'])

    def test_whole_workspace_restore_preserves_originals_results_and_permissions(self):
        subdirectory = self.lab.dataset / 'nested'
        subdirectory.mkdir()
        (subdirectory / 'DEMO2.PDF').write_bytes(b'%PDF-1.4\nsecond original\n')
        (self.lab.observations / '.uploads/incomplete.upload').write_text('incomplete')
        (self.lab.observations / 'scan_resources.sh').write_text('excluded friend script')
        (self.lab.observations / 'gui-scripts/link.sh').symlink_to('/etc/passwd')
        run = self.lab.observations / 'gui-runs/test-run'
        run.mkdir()
        (run / 'results.tsv').write_text('document\tvalue\nDEMO1\t12\n')
        (run / 'stdout.log').write_text('complete investigation output\n')
        self.backup()
        restored = self.manager('restored')
        restored.restore()
        self.assertEqual(restored.status()['status'], 'ready', restored.status())
        self.assertEqual((restored.dataset / 'DEMO1.pdf').read_bytes(), (self.lab.dataset / 'DEMO1.pdf').read_bytes())
        self.assertEqual((restored.dataset / 'nested/DEMO2.PDF').read_bytes(), (subdirectory / 'DEMO2.PDF').read_bytes())
        self.assertEqual((restored.observations / 'gui-runs/test-run/results.tsv').read_text(), 'document\tvalue\nDEMO1\t12\n')
        self.assertEqual((restored.observations / 'gui-scripts/test.sh').stat().st_mode & 0o777, 0o755)
        self.assertFalse((restored.observations / 'gui-scripts/link.sh').exists())
        self.assertFalse((restored.observations / 'scan_resources.sh').exists())
        self.assertFalse((restored.observations / '.uploads/incomplete.upload').exists())

    def test_interrupted_commit_keeps_previous_backup_and_retry_succeeds(self):
        self.backup()
        original_marker = (self.remote / 'latest.json').read_bytes()
        (self.lab.observations / 'gui-notes.json').write_text(json.dumps({'DEMO1': 'second notes'}))
        real_command = self.lab.command
        def interrupt(config, *arguments):
            if arguments[0] == 'copyto' and str(arguments[2]) == str(self.remote / 'latest.json'):
                raise ValueError('Simulated interrupted commit')
            return real_command(config, *arguments)
        self.lab.changed()
        self.lab.begin_backup()
        with patch.object(self.lab, 'command', side_effect=interrupt):
            self.lab.backup()
        self.assertEqual((self.remote / 'latest.json').read_bytes(), original_marker)
        self.assertTrue(self.lab.status()['dirty'])
        self.assertTrue(self.lab.status()['canBackup'])
        restored = self.manager('after-interruption')
        restored.restore()
        self.assertEqual(json.loads((restored.observations / 'gui-notes.json').read_text())['DEMO1'], 'first notes')
        self.backup()
        restored = self.manager('after-retry')
        restored.restore()
        self.assertEqual(json.loads((restored.observations / 'gui-notes.json').read_text())['DEMO1'], 'second notes')

    def test_changed_original_is_not_overwritten_and_bad_restore_installs_nothing(self):
        self.backup()
        original_marker = (self.remote / 'latest.json').read_bytes()
        (self.remote / 'dataset/DEMO1.pdf').write_bytes(b'%PDF-1.4\ntampered evidence\n')
        self.lab.begin_backup()
        self.lab.backup()
        self.assertEqual(self.lab.status()['status'], 'error')
        self.assertEqual((self.remote / 'dataset/DEMO1.pdf').read_bytes(), b'%PDF-1.4\ntampered evidence\n')
        self.assertEqual((self.remote / 'latest.json').read_bytes(), original_marker)
        restored = self.manager('tampered')
        restored.restore()
        self.assertEqual(restored.status()['status'], 'error')
        self.assertFalse(restored.status()['canBackup'])
        self.assertFalse((restored.observations / 'gui-notes.json').exists())
        self.assertFalse((restored.dataset / 'DEMO1.pdf').exists())

    def test_unsafe_snapshot_cannot_escape_restore_directory(self):
        self.backup()
        marker = json.loads((self.remote / 'latest.json').read_text())
        archive = self.remote / ('state-' + marker['slot'] + '.zip')
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('../escaped.txt', 'must never be extracted')
            bundle.writestr('dataset.json', '[]')
        marker['sha256'] = drive_backup.checksum(archive)
        (self.remote / 'latest.json').write_text(json.dumps(marker))
        restored = self.manager('unsafe')
        restored.restore()
        self.assertEqual(restored.status()['status'], 'error')
        self.assertFalse(any(self.root.rglob('escaped.txt')))

    def test_existing_local_workspace_and_credentials_are_kept_private(self):
        self.backup()
        restored = self.manager('existing')
        (restored.dataset / 'LOCAL.pdf').write_bytes(b'%PDF-local')
        restored.restore()
        self.assertEqual(restored.status()['status'], 'error')
        self.assertEqual((restored.dataset / 'LOCAL.pdf').read_bytes(), b'%PDF-local')
        self.assertFalse(restored.status()['canBackup'])
        status = json.dumps(restored.status())
        self.assertNotIn('test-secret', status)
        self.assertNotIn('test-refresh-token', status)
        with restored.config() as config:
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertIn('test-refresh-token', config.read_text())
        self.assertFalse(config.exists())

    def test_dataset_only_restores_ids_without_scripts_notes_or_results(self):
        self.lab.scope = 'dataset'
        self.backup()
        restored = self.manager('dataset-only', 'dataset')
        restored.restore()
        self.assertEqual(restored.status()['status'], 'ready', restored.status())
        self.assertEqual((restored.observations / 'all').read_text(), 'DEMO1\n')
        self.assertTrue((restored.dataset / 'DEMO1.pdf').exists())
        self.assertFalse((restored.observations / 'gui-notes.json').exists())
        self.assertFalse((restored.observations / 'gui-scripts/test.sh').exists())


if __name__ == '__main__':
    unittest.main()
