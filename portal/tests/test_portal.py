import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = tempfile.TemporaryDirectory()
os.environ['THIENHA_DATA_DIR'] = DATA.name
os.environ['FLASK_SECRET_KEY'] = 'isolated-test-secret-only'
sys.path.insert(0, str(ROOT))
import app as module
from seed import seed


class PortalTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        DATA.cleanup()

    def setUp(self):
        seed()
        self.client = module.app.test_client()

    def login(self):
        stamp = datetime.now(timezone.utc).isoformat()
        with module.db() as c:
            c.execute("INSERT OR IGNORE INTO users(google_sub,email,name,created_at,last_login_at) VALUES('test-sub','test@example.invalid','Test',?,?)", (stamp,stamp))
            uid = c.execute("SELECT id FROM users WHERE email='test@example.invalid'").fetchone()['id']
            c.execute("INSERT OR REPLACE INTO account_project_licenses VALUES(?,'game-of-thien',?,1,?,?)",(uid,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),stamp,stamp))
        with self.client.session_transaction() as s:
            s['uid'] = uid
            s['csrf'] = 'test-csrf'
        return uid

    def test_public_pages_and_seed_repeatability(self):
        seed()
        with module.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM projects').fetchone()[0], 2)
        for path in ('/', '/projects','/projects/game-of-thien','/projects/xiaozhi-esp32','/firmware','/downloads','/support','/account'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get('/healthz').json['ok'])
        self.assertEqual(self.client.get('/projects/xiaozhi-esp32/install').status_code,302)
        self.login()
        self.assertEqual(self.client.get('/projects/xiaozhi-esp32/install').status_code,200)

    def test_admin_and_robot_tools_require_authentication(self):
        self.assertIn(self.client.get('/admin').status_code, (302,403))
        self.assertEqual(self.client.post('/api/xiaozhi/tools/call',json={}).status_code,401)
        self.assertEqual(self.client.get('/api/xiaozhi/account/access').status_code,401)
        self.assertTrue(self.client.get('/api/xiaozhi/health').json['ok'])
        self.assertEqual(len(self.client.get('/api/xiaozhi/tools/list').json['tools']),8)

    def test_authenticated_game_session_and_expiry(self):
        self.assertEqual(self.client.post('/projects/game-of-thien/sessions',json={}).status_code,401)
        self.login()
        payload={'csrf':'test-csrf','duration_minutes':30}
        bad=dict(payload,csrf='wrong')
        self.assertEqual(self.client.post('/projects/game-of-thien/sessions',json=bad).status_code,400)
        response=self.client.post('/projects/game-of-thien/sessions',json=payload)
        self.assertEqual(response.status_code,200)
        token=response.json['launch_url'].split('session=')[1]
        result=self.client.get('/api/game-of-thien/sessions/'+token)
        self.assertEqual({g['id'] for g in result.json['config']['games']},set(module.GAME_OF_THIEN_LIBRARY))
        self.assertEqual(result.json['config']['duration_minutes'],30)
        self.assertEqual(result.json['config']['version'],2)
        self.assertEqual((datetime.fromisoformat(result.json['expires_at'])-datetime.fromisoformat(result.json['created_at'])).total_seconds(),1800)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'],'https://gameofthien.thienha.io.vn')
        with module.db() as c:
            c.execute('UPDATE game_sessions SET expires_at=? WHERE token=?',('2000-01-01T00:00:00+00:00',token))
        self.assertEqual(self.client.get('/api/game-of-thien/sessions/'+token).status_code,410)

    def test_duration_steps_and_limits(self):
        self.login()
        for duration in (10,20,30,40,50,60):
            with self.subTest(duration=duration):
                response=self.client.post('/projects/game-of-thien/sessions',json={'csrf':'test-csrf','duration_minutes':duration})
                self.assertEqual(response.status_code,200)
                token=response.json['launch_url'].split('session=')[1]
                config=self.client.get('/api/game-of-thien/sessions/'+token).json
                self.assertEqual(config['config']['total_duration_minutes'],duration)
                self.assertEqual(len(config['config']['games']),18)
                self.assertEqual((datetime.fromisoformat(config['expires_at'])-datetime.fromisoformat(config['created_at'])).total_seconds(),duration*60)
        for invalid in (None,0,5,15,61,70,True,'10',10.5,[],{}):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.client.post('/projects/game-of-thien/sessions',json={'csrf':'test-csrf','duration_minutes':invalid}).status_code,400)
        self.assertEqual(self.client.post('/projects/game-of-thien/sessions',json=['invalid']).status_code,400)

    def test_robot_license_uses_same_database(self):
        self.login()
        response=self.client.get('/api/xiaozhi/account/access')
        self.assertEqual(response.status_code,200)
        with module.db() as c:
            self.assertIsNotNone(c.execute("SELECT name FROM sqlite_master WHERE name='tool_licenses'").fetchone())


if __name__=='__main__': unittest.main()
