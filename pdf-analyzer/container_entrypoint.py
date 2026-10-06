#!/usr/bin/env python3
"""Prepare a newly mounted Render disk, then run all investigations as lab."""
import os
from pathlib import Path
import sys

if os.getuid() == 0:
    # Render mounts a new disk as root. Only these lab directories need ownership.
    for path in ('/workspace', '/workspace/home', '/workspace/environment',
                 '/workspace/environment/observations', '/workspace/dataset'):
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        os.chown(directory, 1000, 1000)
    os.setgroups([])
    os.setgid(1000)
    os.setuid(1000)

os.execv(sys.executable, [sys.executable, str(Path(__file__).with_name('server.py')), *sys.argv[1:]])
