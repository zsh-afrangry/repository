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


class AssistantBillImportBatch(Base):
    __tablename__ = "assistant_bill_import_batches"
    batch_id = Column(String(64), primary_key=True)
    source_type = Column(String(32), nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    file_name = Column(String(255), nullable=False)
    total_rows = Column(Integer, nullable=False)
    inserted_count = Column(Integer, nullable=False)
    skipped_count = Column(Integer, nullable=False)
    created_tags_json = Column(Text, nullable=False)
    request_key = Column(String(128), nullable=False, unique=True)
    run_id = Column(String(96), nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssistantBillOrigin(Base):
    __tablename__ = "assistant_bill_origins"
    source_key = Column(String(96), primary_key=True)
    batch_id = Column(String(64), ForeignKey("assistant_bill_import_batches.batch_id", ondelete="RESTRICT"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="SET NULL"), nullable=True, index=True)
    row_hash = Column(String(64), nullable=False)
    source_json = Column(Text, nullable=False)
    imported_at = Column(DateTime, server_default=func.now(), nullable=False)
