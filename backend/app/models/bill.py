from sqlalchemy import Column, Integer, String, Numeric, Date, Time, DateTime, Enum as SAEnum, ForeignKey, Text, func
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class RecordType(str, enum.Enum):
    expense = "支出"
    income = "收入"


class ReimbursementStatus(str, enum.Enum):
    na = "无需报销"
    pending = "待报销"
    done = "已报销"


class CalendarEventTone(str, enum.Enum):
    todo = "todo"
    plan = "plan"
    meeting = "meeting"
    bill = "bill"


class TagType(str, enum.Enum):
    """Which dimension this tag belongs to."""
    category = "category"           # 大类：餐饮、交通、工资…
    subcategory = "subcategory"     # 小类：午饭、打车… (parent_id -> category tag)
    payment_platform = "payment_platform"
    payment_channel = "payment_channel"
    fund_type = "fund_type"


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    type = Column(SAEnum(TagType), nullable=False)
    parent_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    parent = relationship("Tag", remote_side="Tag.id", backref="children")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(SAEnum(RecordType), nullable=False, default=RecordType.expense)

    expense_date = Column(Date, nullable=False)
    expense_time = Column(Time, nullable=True)

    amount = Column(Numeric(12, 2), nullable=False)

    # Tag foreign keys (all nullable; income records won't have payment info)
    category_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    subcategory_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    payment_platform_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    payment_channel_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    fund_type_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)

    # Relationships for eager joins
    category = relationship("Tag", foreign_keys=[category_id])
    subcategory = relationship("Tag", foreign_keys=[subcategory_id])
    payment_platform = relationship("Tag", foreign_keys=[payment_platform_id])
    payment_channel = relationship("Tag", foreign_keys=[payment_channel_id])
    fund_type = relationship("Tag", foreign_keys=[fund_type_id])

    reimbursement_status = Column(
        SAEnum(ReimbursementStatus),
        nullable=False,
        default=ReimbursementStatus.na,
    )
    reimbursement_amount = Column(Numeric(12, 2), nullable=True)

    transaction_id = Column(String(128), nullable=True, unique=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=True)
    title = Column(String(128), nullable=False)
    detail = Column(Text, nullable=True)
    tone = Column(SAEnum(CalendarEventTone), nullable=False, default=CalendarEventTone.todo)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
