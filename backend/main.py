import json
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
from app.notes.router import router as notes_router, seed_notes

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the portal schema (includes TradeSim's simulation_records,
    # which now shares this same MySQL database) and seed defaults.
    Base.metadata.create_all(bind=engine)
    from app.crud.tag import seed_default_tags

    with SessionLocal() as db:
        seed_default_tags(db)
        seed_notes(db)

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
app.include_router(notes_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


web_config = None
if config_path := os.environ.get("KM_WEB_CONFIG"):
    from app.web_host import configure_web_host

    with open(config_path, encoding="utf-8") as config_file:
        web_config = json.load(config_file)
    configure_web_host(app, web_config)


if __name__ == "__main__":
    import uvicorn

    if web_config:
        # The launcher always enables authentication before allowing LAN binding.
        uvicorn.run(app, host=web_config["host"], port=web_config["port"],
                    proxy_headers=True, forwarded_allow_ips="127.0.0.1")
    else:
        uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("KM_BACKEND_PORT", "8010")), reload=True)
