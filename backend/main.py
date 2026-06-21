from app.database import engine
from app.models.bill import Base
from app.routers import bill_router, tag_router
from app.database import SessionLocal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Seed default tags on first run
from app.crud.tag import seed_default_tags
with SessionLocal() as db:
    seed_default_tags(db)

app = FastAPI(title="KnowledgeMap API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bill_router, prefix="/api")
app.include_router(tag_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
