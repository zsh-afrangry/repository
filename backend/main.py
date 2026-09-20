import logging
import os
from contextlib import asynccontextmanager

from app.database import engine
from app.models.bill import Base
from app.routers import bill_router, calendar_router, dashboard_router, tag_router, weather_router
from app.database import SessionLocal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.tradesim.db.session import close_tradesim_connections
from app.tradesim.router import router as tradesim_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the portal schema (includes TradeSim's simulation_records,
    # which now shares this same MySQL database) and seed defaults.
    Base.metadata.create_all(bind=engine)
    from app.crud.tag import seed_default_tags

    with SessionLocal() as db:
        seed_default_tags(db)

    try:
        yield
    finally:
        close_tradesim_connections()


app = FastAPI(title="KnowledgeMap API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bill_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(tag_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(tradesim_router, prefix="/api/tradesim/v1")


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # 绑定地址：127.0.0.1（C1，2026-09-20 已获批准 — docs/5 §16 C1）。
    # 此前是 0.0.0.0，而本项目**没有任何鉴权**，/api/... 里还包含会产生第三方费用的
    # LLM 分析端点 ⇒ 那等于把账单数据和付费接口开放给同网段任何设备（CORS 白名单只
    # 约束浏览器，对 curl / 脚本毫无作用）。改绑后只有本机能访问。
    # ⚠ 若日后确实需要局域网/手机访问：不要只把这里改回 0.0.0.0，先给路由加上 API-key
    # 依赖（AGENTS.md「Running the project」有同样的告警）。
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("KM_BACKEND_PORT", "8010")), reload=True)
