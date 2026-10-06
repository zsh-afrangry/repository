"""Opt-in live MySQL smoke. Creates ONE marked topic, removes only that topic.
python tests/notes_mysql_smoke.py --allow-write
Requires local dev API :8010 and the configured shared MySQL database.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from uuid import uuid4
import httpx
from sqlalchemy import select, func
from app.database import SessionLocal
from app.notes.models import NoteTopic

if '--allow-write' not in sys.argv:
    raise SystemExit('Use --allow-write to create and clean up one temporary notes topic.')
client=httpx.Client(base_url='http://127.0.0.1:8010/api/notes',trust_env=False)
topic_id=None
with SessionLocal() as db:
    initial=db.scalar(select(func.count()).select_from(NoteTopic))
try:
    response=client.post('/topics',json={'title':'验收临时主题-'+uuid4().hex[:8], 'sections':[{'id':'smoke-section','title':'验收目录','order':0}]})
    response.raise_for_status(); doc=response.json();topic_id=doc.pop('id')
    doc['units']=[{'id':'a','title':'持久化 A','sectionId':'smoke-section','content':'# MySQL 持久化\n\n测试正文','tags':['临时验收']},{'id':'b','title':'持久化 B','sectionId':'smoke-section','content':'内容 B','tags':[]}]
    doc['edges']=[{'fromUnitId':'a','toUnitId':'b'}]
    response=client.put(f'/topics/{topic_id}',json=doc);response.raise_for_status();saved=response.json()
    # Fresh DB session and independent HTTP client confirm durable stored content.
    with SessionLocal() as db:
        row=db.get(NoteTopic,topic_id)
        assert row.version==2 and row.data['units'][0]['content']==doc['units'][0]['content']
        assert row.data['edges']==doc['edges']
    with httpx.Client(base_url=client.base_url,trust_env=False) as other:
        assert other.get(f'/topics/{topic_id}').json()==saved
        assert other.put(f'/topics/{topic_id}',json=doc).status_code==409
    print('PASS live MySQL JSON/Unicode, fresh-session recovery, independent HTTP read, stale-version rejection')
finally:
    if topic_id:
        # Reload version, clear units/edges, then directories, then delete our exact id.
        doc=client.get(f'/topics/{topic_id}').json();doc.pop('id')
        doc['units']=[];doc['edges']=[]
        response=client.put(f'/topics/{topic_id}',json=doc);response.raise_for_status();doc=response.json();doc.pop('id');doc['sections']=[]
        response=client.put(f'/topics/{topic_id}',json=doc);response.raise_for_status()
        response=client.delete(f'/topics/{topic_id}',params={'version':response.json()['version']});response.raise_for_status()
    client.close()
with SessionLocal() as db:
    assert db.scalar(select(func.count()).select_from(NoteTopic))==initial
print('PASS cleanup: topic count restored, original topics untouched')
