"""Dedicated loopback bridge, independent of Vite/dev and website authentication.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
Shared engine/services; only authenticated /api/assistant routes. No schema mutation.
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from app.assistant.errors import install_errors
from app.assistant.router import router

app = FastAPI(title='KnowledgeMap assistant bridge', docs_url=None, redoc_url=None, openapi_url=None)
install_errors(app)
app.include_router(router, prefix='/api')

if __name__ == '__main__':
    import uvicorn
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('KM_ASSISTANT_PORT', '3086')), access_log=False)
