#!/usr/bin/env python3
"""Create a consistent private portal snapshot; never add the result to Git."""
import argparse
import os
from pathlib import Path
import shutil
import sqlite3

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('destination',type=Path)
p.add_argument('--legacy-files',type=Path)
a=p.parse_args()
if a.destination.exists():
    raise SystemExit('Destination exists; choose a new snapshot directory')
os.umask(0o077)
a.destination.mkdir(parents=True)
for source in a.source.iterdir():
    if source.name.startswith('users.db') or '.bak' in source.name:
        continue
    if source.is_symlink():
        raise SystemExit('Refusing a symlink in private state')
    target=a.destination/source.name
    if source.is_dir(): shutil.copytree(source,target,symlinks=False)
    else: shutil.copy2(source,target)
if a.legacy_files and a.legacy_files.exists():
    (a.destination/'files').mkdir(exist_ok=True)
    for source in a.legacy_files.iterdir():
        target=a.destination/'files'/source.name
        if source.is_file() and not source.is_symlink():
            if target.exists() and target.read_bytes()!=source.read_bytes():
                raise SystemExit('Conflicting legacy release file; inspect manually')
            shutil.copy2(source,target)
with sqlite3.connect(f'file:{a.source / "users.db"}?mode=ro',uri=True) as src:
    with sqlite3.connect(a.destination/'users.db') as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise SystemExit('Database integrity check failed')
print('Private snapshot created; SQLite integrity: ok')
