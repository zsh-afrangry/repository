"""Request receipts and migration provenance, on the portal's shared Base."""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.mysql import LONGTEXT
from app.models.bill import Base


class AssistantRequest(Base):
    __tablename__ = "assistant_requests"
    request_key = Column(String(128), primary_key=True)
    payload_hash = Column(String(64), nullable=False)
    result_json = Column(Text().with_variant(LONGTEXT(), 'mysql'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssistantTaskOrigin(Base):
    __tablename__ = "assistant_task_origins"
    source_id = Column(String(96), primary_key=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="RESTRICT"), nullable=False, unique=True)
    source_json = Column(Text, nullable=False)
    imported_at = Column(DateTime, server_default=func.now(), nullable=False)
