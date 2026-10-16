"""Disposable HTTP API for bridge/browser integration; SQLite and weather stub.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
Run with --port and --token-file. Never connects to real MySQL or real weather.
"""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.assistant.router import router
from app.assistant.errors import install_errors
from app.database import get_db
from app.models.bill import Base, Tag, TagType
from app.routers.bill import router as bill_router
from app.routers.calendar import router as calendar_router
from app.routers.dashboard import router as dashboard_router
from app.routers import weather


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--token-file', required=True)
    args = parser.parse_args()
    os.environ['KM_ASSISTANT_TOKEN_FILE'] = args.token_file
    with TemporaryDirectory(prefix='km-bridge-http-') as directory:
        engine = create_engine(f'sqlite:///{directory}/test.db', connect_args={'check_same_thread': False})
        @event.listens_for(engine, 'connect')
        def functions(connection, _record):
            connection.create_function('year', 1, lambda s: int(s[:4]))
            connection.create_function('month', 1, lambda s: int(s[5:7]))
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([Tag(id=1, name='餐饮', type=TagType.category), Tag(id=2, name='午饭', type=TagType.subcategory, parent_id=1)])
            db.commit()
        app = FastAPI()
        install_errors(app)
        for item in [router, bill_router, calendar_router, dashboard_router, weather.router]: app.include_router(item, prefix='/api')
        def session():
            with Session(engine) as db: yield db
        app.dependency_overrides[get_db] = session
        weather._request_qweather = lambda path: {'code': '200', 'location': [], 'metadata': {'sources': ['offline-test']}, 'daily': [], 'hours': [], 'alerts': [], 'current': {}}
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='error', access_log=False)


if __name__ == '__main__': main()
