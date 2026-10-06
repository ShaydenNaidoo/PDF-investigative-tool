"""Optional Google Drive snapshots. Credentials stay in server environment settings."""
from contextlib import contextmanager
import configparser
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import zipfile


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def checksum(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(p in ('.', '..') for p in name.split('/')) or any(c in name for c in ('\\', ':', '\n', '\r')):
        raise ValueError('The Drive backup contains an unsafe filename.')
    return path


class DriveBackup:
    def __init__(self, observations, dataset, scope='workspace'):
        self.observations, self.dataset = Path(observations), Path(dataset)
        self.scope = scope
        self.credentials = [os.environ.get('PDF_LAB_DRIVE_' + key, '') for key in ('CLIENT_ID', 'CLIENT_SECRET', 'REFRESH_TOKEN')]
        self.enabled = any(self.credentials)
        folder = os.environ.get('PDF_LAB_DRIVE_FOLDER', 'PDF Analyzer Lab')
        self.remote = 'pdflab:' + folder
        self.lock = threading.RLock()
        self.latest = None
        self.initialized = False
        self.state = {'enabled': self.enabled, 'status': 'disabled', 'busy': False,
                      'dirty': False, 'lastBackup': None, 'scope': scope,
                      'message': 'Google Drive is not configured. See GOOGLE_DRIVE.md for the one-time setup.'}
        if self.enabled:
            self.state.update(status='pending', busy=True, message='Preparing Google Drive restore…')
            if not all(self.credentials) or any('\n' in value or '\r' in value for value in self.credentials):
                self.fail('Set all three Google Drive credential variables in Render Environment.')
            elif not shutil.which('rclone'):
                self.fail('The backup tool is missing. Rebuild the Docker image with rclone installed.')
            elif scope not in ('workspace', 'dataset') or not re.fullmatch(r'[A-Za-z0-9 _-]{1,80}', folder):
                self.fail('Use scope workspace or dataset and a simple, unique Drive folder name.')

    def status(self):
        with self.lock:
            return {**self.state, 'canBackup': self.enabled and self.initialized and not self.state['busy']}

    def fail(self, message):
        with self.lock:
            self.state.update(status='error', busy=False, message=message)

    @contextmanager
    def config(self):
        # rclone can refresh tokens in this private temporary file. Never expose it to the UI.
        with tempfile.TemporaryDirectory(prefix='pdf-drive-auth-') as folder:
            path = Path(folder) / 'rclone.conf'
            config = configparser.ConfigParser(interpolation=None)
            config['pdflab'] = {'type': 'drive', 'scope': 'drive.file',
                               'client_id': self.credentials[0], 'client_secret': self.credentials[1],
                               'token': json.dumps({'refresh_token': self.credentials[2],
                                                   'token_type': 'Bearer', 'expiry': '2000-01-01T00:00:00Z'})}
            with path.open('w') as handle:
                os.chmod(path, 0o600)
                config.write(handle)
            yield path

    def command(self, config, *arguments):
        result = subprocess.run(['rclone', *map(str, arguments), '--config', str(config),
                                 '--transfers', '2', '--checkers', '2', '--retries', '2',
                                 '--contimeout', '20s', '--timeout', '120s', '--stats', '0'],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=1800, text=True)
        if result.returncode:
            # External error output may contain credentials; show actionable generic errors instead.
            raise ValueError('Google Drive transfer failed. Check authorization, available Drive space and the connection, then retry.')
        return result.stdout

    def read_latest(self, config, directory):
        self.command(config, 'mkdir', self.remote)
        names = self.command(config, 'lsf', self.remote, '--files-only', '--max-depth', '1').splitlines()
        if 'latest.json' not in names:
            return None
        path = directory / 'latest.json'
        self.command(config, 'copyto', self.remote + '/latest.json', path)
        data = json.loads(path.read_text())
        if data.get('version') != 1 or data.get('slot') not in ('a', 'b') or not re.fullmatch(r'[a-f0-9]{64}', str(data.get('sha256', ''))):
            raise ValueError('The Drive backup marker is invalid. Keep the Drive backup unchanged and check its contents.')
        return data

    def restore(self):
        if not self.enabled or self.state['status'] == 'error':
            return
        try:
            with tempfile.TemporaryDirectory(prefix='.drive-restore-', dir=self.observations.parent) as temporary, self.config() as config:
                directory = Path(temporary)
                self.latest = self.read_latest(config, directory)
                if self.latest is None:
                    self.initialized = True
                    self.state.update(status='ready', busy=False, message='No completed Drive backup yet. Import PDFs and save your first backup.')
                    return
                if any(self.dataset.rglob('*.pdf')) or any((self.observations / name).exists() and
                        (any((self.observations / name).iterdir()) if (self.observations / name).is_dir() else True)
                        for name in ('gui-runs', 'gui-scripts', 'gui-notes.json')):
                    raise ValueError('Drive restore needs a fresh lab. Existing local PDFs, scripts or notes were kept; disable Drive here or use a separate empty lab.')
                archive = directory / 'state.zip'
                self.command(config, 'copyto', self.remote + '/state-' + self.latest['slot'] + '.zip', archive)
                if checksum(archive) != self.latest['sha256']:
                    raise ValueError('Drive snapshot checksum failed. No saved workspace was restored.')
                staged = directory / 'staged'
                staged.mkdir()
                with zipfile.ZipFile(archive) as bundle:
                    entries = bundle.infolist()
                    if len(entries) > 100000 or sum(item.file_size for item in entries) > 8 * 1024**3:
                        raise ValueError('The Drive workspace exceeds the restore limit.')
                    for item in entries:
                        path = safe_path(item.filename)
                        if stat.S_ISLNK(item.external_attr >> 16) or (str(path) != 'dataset.json' and path.parts[0] != 'observations'):
                            raise ValueError('The Drive snapshot contains an unsupported entry.')
                        bundle.extract(item, staged)
                        os.chmod(staged / str(path), (item.external_attr >> 16) & 0o777 or 0o600)
                records = json.loads((staged / 'dataset.json').read_text())
                if not isinstance(records, list) or len(records) > 20000:
                    raise ValueError('The Drive dataset manifest is invalid.')
                paths = []
                for record in records:
                    path = safe_path(record['path'])
                    if path.suffix.lower() != '.pdf' or not re.fullmatch(r'[a-f0-9]{64}', str(record.get('sha256', ''))):
                        raise ValueError('The Drive dataset manifest is invalid.')
                    paths.append(str(path))
                # Download exactly the originals listed in this completed snapshot, including subdirectories.
                files = directory / 'files.txt'
                files.write_text('\n'.join(paths) + ('\n' if paths else ''))
                restored_dataset = staged / 'dataset'
                restored_dataset.mkdir()
                if paths:
                    self.state['message'] = 'Restoring PDFs from Google Drive. Wait before importing or running scripts.'
                    self.command(config, 'copy', self.remote + '/dataset', restored_dataset,
                                 '--files-from-raw', files, '--checksum')
                for record in records:
                    path = restored_dataset / record['path']
                    if not path.is_file() or checksum(path) != record['sha256']:
                        raise ValueError('A PDF failed the Drive checksum check. No saved workspace was restored.')
                # Everything is validated before installing. Existing baseline files may be replaced by their saved copies.
                for source, target in ((restored_dataset, self.dataset), (staged / 'observations', self.observations)):
                    if source.is_dir():
                        for path in source.rglob('*'):
                            if path.is_file():
                                destination = target / path.relative_to(source)
                                destination.parent.mkdir(parents=True, exist_ok=True)
                                os.replace(path, destination)
                self.initialized = True
                self.state.update(status='ready', busy=False, lastBackup=self.latest.get('createdAt'),
                                  message='Restored the last completed Google Drive backup.')
        except Exception as error:
            self.fail(str(error) if isinstance(error, ValueError) else 'Drive restore failed. Check configuration and space, then restart to retry. Local files were kept.')

    def changed(self):
        if self.enabled:
            with self.lock:
                self.state['dirty'] = True

    def begin_backup(self):
        with self.lock:
            if not self.enabled:
                raise ValueError('Configure Google Drive in Render first. See GOOGLE_DRIVE.md.')
            if self.state['busy']:
                raise ValueError('A Drive restore or backup is already in progress.')
            if not self.initialized:
                raise ValueError('Drive is not ready. Fix configuration and restart the lab before backing up.')
            self.state.update(status='backing-up', busy=True, message='Backing up to Google Drive. Keep your downloads until this completes.')

    def backup(self):
        try:
            with tempfile.TemporaryDirectory(prefix='.drive-backup-', dir=self.observations.parent) as temporary, self.config() as config:
                directory = Path(temporary)
                # Read the committed slot each time; an interrupted prior attempt never replaces it.
                latest = self.read_latest(config, directory)
                slot = 'b' if latest and latest['slot'] == 'a' else 'a'
                records = [{'path': str(path.relative_to(self.dataset)), 'sha256': checksum(path)}
                           for path in sorted(self.dataset.rglob('*')) if path.is_file() and not path.is_symlink() and path.suffix.lower() == '.pdf']
                if len(records) > 20000:
                    raise ValueError('The Drive dataset exceeds the 20,000 PDF restore limit.')
                for record in records:
                    safe_path(record['path'])
                snapshot = directory / 'state.zip'
                with zipfile.ZipFile(snapshot, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr('dataset.json', json.dumps(records))
                    if self.scope == 'workspace':
                        for path in sorted(self.observations.rglob('*')):
                            relative = path.relative_to(self.observations)
                            if path.is_file() and not path.is_symlink() and not any(part.startswith('.') or part in ('__pycache__', 'pdfwork', 'qdf') for part in relative.parts) and path.name != 'scan_resources.sh':
                                archive.write(path, 'observations/' + str(relative))
                    elif (self.observations / 'all').is_file():
                        archive.write(self.observations / 'all', 'observations/all')
                    if len(archive.infolist()) > 100000 or sum(item.file_size for item in archive.infolist()) > 8 * 1024**3:
                        raise ValueError('The Drive workspace exceeds the 8 GiB restore limit. Download large results separately.')
                self.command(config, 'copy', self.dataset, self.remote + '/dataset',
                             '--include', '*.[pP][dD][fF]', '--immutable', '--checksum')
                self.command(config, 'copyto', snapshot, self.remote + '/state-' + slot + '.zip', '--checksum')
                marker = {'version': 1, 'slot': slot, 'sha256': checksum(snapshot), 'createdAt': timestamp(), 'scope': self.scope}
                latest_path = directory / 'latest.json'
                latest_path.write_text(json.dumps(marker))
                # Commit last. A failed dataset/snapshot transfer leaves the prior completed snapshot recoverable.
                self.command(config, 'copyto', latest_path, self.remote + '/latest.json', '--checksum')
                self.latest = marker
                with self.lock:
                    self.state.update(status='ready', busy=False, dirty=False, lastBackup=marker['createdAt'],
                                      message='Google Drive backup completed. This saved work can be restored after a restart.')
        except Exception as error:
            self.fail(str(error) if isinstance(error, ValueError) else 'Drive backup failed. Your local work remains available; download results and retry.')
