"""Disposable SQLite API for notes-browser.cjs; no portal database access.

对应文档：docs/13_Notes学习模块功能与视觉开发方案.md「12. 自动验证与复跑」。
Run from backend: python tests/notes_browser_server.py
"""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.bill import Base
from app.notes.router import router, seed_notes
from app.database import get_db
import uvicorn

if __name__ == '__main__':
    with TemporaryDirectory(prefix='km-notes-qa-') as directory:
        engine=create_engine(f'sqlite:///{directory}/notes.db',connect_args={'check_same_thread':False})
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seed_notes(db)
        app=FastAPI()
        app.include_router(router,prefix='/api')
        def session():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[get_db]=session
        uvicorn.run(app,host='127.0.0.1',port=8011,log_level='warning')
