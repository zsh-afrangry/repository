"""Isolated HTTP/transaction checks; SQLite only, no live data writes.

对应文档：docs/13_Notes学习模块功能与视觉开发方案.md「12. 自动验证与复跑」。
改动 Notes 的主题/目录/单元/依赖接口时复跑本文件；它不碰本机 MySQL。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.models.bill import Base
from app.notes.router import router, seed_notes
from app.notes.models import NoteTopic
from app.database import get_db

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
app = FastAPI()
app.include_router(router, prefix="/api")
def session():
    with Session(engine) as db:
        yield db
app.dependency_overrides[get_db] = session
client = TestClient(app)
checks = 0

def check(condition, label):
    global checks
    assert condition, label
    checks += 1
    print('PASS', label)

with Session(engine) as db:
    seed_notes(db)
    initial = db.scalars(select(NoteTopic)).all()
    check(len(initial) == 7 and sum(len(t.data['units']) for t in initial) == 31, 'seed migrates 31 original units including orphan content')
    seed_notes(db)
    check(len(db.scalars(select(NoteTopic)).all()) == 7, 'seed idempotent')
base = '/api/notes/topics'
r = client.post(base, json={'title':'隔离测试', 'sections':[{'id':'s1','title':'目录1','order':0},{'id':'s2','title':'目录2','order':1}]})
check(r.status_code == 201, 'create topic')
doc = r.json(); topic_id = doc.pop('id'); url = f'{base}/{topic_id}'
def put(data):
    return client.put(url, json=data)
doc['units']=[{'id':x,'sectionId':'s1','title':x,'content':'正文','tags':[]} for x in ['a','b','c']]
doc['edges']=[{'fromUnitId':'a','toUnitId':'b'}, {'fromUnitId':'b','toUnitId':'c'}]
r=put(doc);check(r.status_code==200,'atomic units and dependencies');doc=r.json();doc.pop('id')
old=dict(doc)
r=put(doc);check(r.status_code==200,'version increments');doc=r.json();doc.pop('id')
check(put(old).status_code==409,'stale write rejected')
from copy import deepcopy
for label, change in [
 ('cycle', lambda d:d['edges'].append({'fromUnitId':'c','toUnitId':'a'})),
 ('self edge', lambda d:d['edges'].append({'fromUnitId':'a','toUnitId':'a'})),
 ('dangling/cross-topic edge', lambda d:d['edges'].append({'fromUnitId':'foreign','toUnitId':'a'})),
 ('duplicate edge', lambda d:d['edges'].append(d['edges'][0])),
 ('invalid membership', lambda d:d['units'][0].update(sectionId='missing')),
 ('duplicate unit ID', lambda d:d['units'].append(d['units'][0])),
]:
    bad=deepcopy(doc);change(bad)
    check(put(bad).status_code==422, label+' rejected')
    check(client.get(url).json()['version']==doc['version'],label+' failure leaves database untouched')
check(client.delete(url,params={'version':doc['version']}).status_code==409,'nonempty topic cannot be deleted')
bad=deepcopy(doc);bad['sections']=bad['sections'][1:];bad['units']=[];bad['edges']=[]
check(put(bad).status_code==409,'directory deletion cannot silently cascade unit deletion')
doc['units'][0]['sectionId']='s2'
r=put(doc);check(r.status_code==200 and r.json()['edges']==doc['edges'],'moving membership preserves dependencies');doc=r.json();doc.pop('id')
doc['units']=[u for u in doc['units'] if u['id']!='b'];doc['edges']=[]
r=put(doc);check(r.status_code==200 and len(r.json()['units'])==2,'unit deletion preserves peers and clears affected edges');doc=r.json();doc.pop('id')
doc['units']=[];r=put(doc);doc=r.json();doc.pop('id');doc['sections']=[];r=put(doc);doc=r.json();doc.pop('id')
check(client.delete(url,params={'version':doc['version']-1}).status_code==409,'stale deletion rejected')
check(client.delete(url,params={'version':doc['version']}).status_code==204,'empty topic deletion')
check(client.get(url).status_code==404,'deleted topic missing')
check(client.post(base,json={'title':'  '}).status_code==422,'blank topic rejected')
check(client.post(base,json={'title':'test','preferredColumns':7}).status_code==422,'layout bound validated')
with Session(engine) as db:
    t=db.get(NoteTopic,'vit');db.delete(t);db.commit();seed_notes(db)
    check(db.get(NoteTopic,'vit') is None, 'deleted seed topic does not resurrect')
print(f'{checks} checks passed')
