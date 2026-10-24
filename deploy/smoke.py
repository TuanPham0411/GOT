#!/usr/bin/env python3
"""Read-only checks against portal and game origins or public hostnames."""
import argparse
import io
import json
from urllib.error import HTTPError
from urllib.request import urlopen
import wave

p=argparse.ArgumentParser()
p.add_argument('--portal',default='http://127.0.0.1:15050')
p.add_argument('--game',default='http://127.0.0.1:15080')
a=p.parse_args()
def get(origin,path):
    with urlopen(origin.rstrip('/')+path,timeout=30) as r:
        if r.status!=200: raise RuntimeError(f'{path}: HTTP {r.status}')
        return r.read()
health=json.loads(get(a.portal,'/healthz'))
assert health['ok'] and health['service']=='thienha-portal'
for path in ('/','/projects','/projects/game-of-thien','/projects/xiaozhi-esp32','/firmware','/downloads','/support','/account'):
    assert b'<!doctype html' in get(a.portal,path).lower(), path
assert json.loads(get(a.portal,'/api/xiaozhi/health'))['ok']
assert len(json.loads(get(a.portal,'/api/xiaozhi/tools/list'))['tools'])==8
assert json.loads(get(a.game,'/healthz'))['ok']
b=json.loads(get(a.game,'/api/bootstrap'))
assert len(b['topics'])==10 and len(b['games'])==18
for topic in b['topics']:
    data=json.loads(get(a.game,'/api/topic/'+topic['id']))
    assert data['items']
image=json.loads(get(a.game,'/api/topic/'+b['topics'][0]['id']))['items'][0]['image']
assert len(get(a.game,'/resource/'+image))>1000
assert get(a.game,'/thumb/'+image)[8:12]==b'WEBP'
for language in ('vi','en'):
    with wave.open(io.BytesIO(get(a.game,'/api/tts?text=Xin%20chao&lang='+language))) as w:
        assert w.getnframes()>0
try:
    get(a.portal,'/api/game-of-thien/sessions/'+'x'*32)
    raise AssertionError('Unknown game session accepted')
except HTTPError as e:
    assert e.code==404
print('PASS: portal pages, project catalog, XiaoZhi discovery, game catalog/images/thumbnails, VI/EN audio, invalid session rejection')
