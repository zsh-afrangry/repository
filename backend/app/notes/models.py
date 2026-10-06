from sqlalchemy import Column, String, Integer, JSON
from app.models.bill import Base


class NoteTopic(Base):
    __tablename__ = "notes_topics"
    id = Column(String(64), primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    # A topic is the atomic write boundary. Relationships never span topics.
    data = Column(JSON, nullable=False)


class NotesSeed(Base):
    __tablename__ = "notes_seed_versions"
    id = Column(String(64), primary_key=True)
