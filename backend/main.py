import logging
import os
from contextlib import asynccontextmanager

from app.database import engine
from app.models.bill import Base
from app.routers import bill_router, calendar_router, dashboard_router, tag_router, weather_router
from app.database import SessionLocal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.tradesim.db.models import Base as TradeSimBase
from app.tradesim.db.session import close_tradesim_connections, tradesim_engine
from app.tradesim.router import router as tradesim_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the portal schema and seed its defaults during application
    # startup, preserving the existing KnowledgeMap behavior.
    Base.metadata.create_all(bind=engine)
    from app.crud.tag import seed_default_tags

    with SessionLocal() as db:
        seed_default_tags(db)

    # TradeSim uses a separate metadata registry while its relational index
    # lives in the existing KnowledgeMap database. Keep optional initialization
    # isolated so an unavailable TradeSim connection does not prevent startup.
    if os.getenv("TRADESIM_AUTO_CREATE_TABLES", "1") == "1":
        try:
            TradeSimBase.metadata.create_all(bind=tradesim_engine)
        except SQLAlchemyError:
            logger.warning(
                "TradeSim 数据库暂不可用，门户仍可启动；请检查 TRADESIM_MYSQL_URL。",
                exc_info=True,
            )

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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("KM_BACKEND_PORT", "8010")), reload=True)
