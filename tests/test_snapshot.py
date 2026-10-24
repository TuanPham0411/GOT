import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'deploy/snapshot_data.py'

class SnapshotTests(unittest.TestCase):
    def test_wal_state_and_legacy_files_preserved_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);source=root/'source';source.mkdir()
            legacy=root/'files';legacy.mkdir();(legacy/'release.zip').write_bytes(b'test release')
            with sqlite3.connect(source/'users.db') as c:
                c.execute('PRAGMA journal_mode=WAL')
                c.execute('CREATE TABLE example(value TEXT)')
                c.execute("INSERT INTO example VALUES ('preserve me')");c.commit()
                target=root/'snapshot'
                run=subprocess.run([sys.executable,str(SCRIPT),str(source),str(target),'--legacy-files',str(legacy)],capture_output=True)
                self.assertEqual(run.returncode,0,run.stderr.decode())
                with sqlite3.connect(target/'users.db') as copy:
                    self.assertEqual(copy.execute('SELECT value FROM example').fetchone()[0],'preserve me')
                self.assertEqual((target/'files/release.zip').read_bytes(),b'test release')
                run=subprocess.run([sys.executable,str(SCRIPT),str(source),str(target)],capture_output=True)
                self.assertNotEqual(run.returncode,0)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM example').fetchone()[0],1)

if __name__=='__main__':unittest.main()
