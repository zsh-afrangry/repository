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
    """首页日历事项的类型。

    **2026-10-06 收敛为两值**（决策与理由见 `docs/14_主页仪表盘与待做事项开发方案.md` §2.1）：

    - 原 `plan`（计划）语义统一由 `meeting` 承载；
    - 原 `bill`（账单提醒）弃用——它与账单页的 `bills` 表职责重叠，且从无数据。

    收敛时该表为 **0 行**，因此零数据迁移成本。若将来要恢复四值，需要同时改：
    本枚举、DB 列定义、`frontend/src/views/Dashboard.vue` 的类型下拉、
    以及 `.calendar-event-item.tone-*` 的配色样式，并迁移存量数据。
    """

    todo = "todo"
    meeting = "meeting"


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
    """首页日历事项：`todo` = 待做事项，`meeting` = 安排（会议/日程）。

    时间刻意保持 **`event_date` + `event_time` 两列**（决策见 docs/14 §4.2）：
    `event_time` 可空，表示"当天但未指定具体时刻"。
    判断是否过期时**不要各处手写两列比较**，统一走
    `app.crud.calendar.event_due_at()`，它会把空时间兜底成当天 23:59:59。

    ⚠️ 列注释（`comment=`）是刻意写的：本表在 2026-10-06 被 DROP + CREATE 重建过，
    当时因为模型里没写 comment，导致原库的列注释全部丢失。列注释会随
    `backend/scripts/export_schema.py` 进入版本控制，是结构文档的一部分。
    **改列时不要漏掉 comment**，否则下次重建又丢一次。
    """

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True,
                comment="日历事项主键，自增 ID")
    event_date = Column(Date, nullable=False, index=True,
                        comment="事项日期；Dashboard 日历按此字段加载和标记")
    event_time = Column(Time, nullable=True,
                        comment="事项时间；为空表示当天但未指定具体时刻，判定过期时兜底为 23:59:59")
    title = Column(String(128), nullable=False,
                   comment="事项标题，显示在日期详情弹窗中")
    detail = Column(Text, nullable=True,
                    comment="事项说明，如待办内容、会议地点等上下文")
    tone = Column(SAEnum(CalendarEventTone), nullable=False, default=CalendarEventTone.todo,
                  comment="事项类型：todo=待做事项，meeting=安排（会议/日程）")

    # 完成时间戳。NULL = 未完成。
    #
    # 2026-10-06 新增，用于「本周进度」的分子。选时间戳而非布尔值的原因：
    #   1. 能回答"何时完成的"，布尔值答不了；
    #   2. "本周完成了多少"若按完成时间过滤，历史可回溯；
    #   3. 将来做趋势/回顾不必再改表。
    # 撤销完成 = 置回 NULL，不删记录。**不要**用 0000-00-00 之类的哨兵值。
    #
    # 刻意不加索引：表规模预计几十~几百行，索引收益为零（决策见 docs/14 §2.6）。
    completed_at = Column(DateTime, nullable=True, default=None,
                          comment="完成时间；NULL 表示未完成。撤销完成即置回 NULL")

    # 作废时间戳。NULL = 未作废。
    #
    # 2026-10-07 新增。语义是"**我决定不做了**"，与"完成"是**两件事**：
    #   完成 = 做到了；作废 = 主动放弃（不做了，别再提醒我）。
    # 用户把它定位成废纸篓/回收站：可查看、可恢复，不是删除。
    #
    # 为什么不能省掉这个字段、直接用删除：
    #   删掉之后"这条曾经存在过"这个事实就没了，回收站也无从谈起。
    #
    # ⚠️ **所有"未完成"的查询都必须同时排除已作废**：
    #   `completed_at IS NULL AND archived_at IS NULL`
    # 为此查询已集中在 `crud/calendar.pending_events()` 一处，
    # 不要在别处另写 `completed_at.is_(None)`，否则会漏掉作废过滤。
    archived_at = Column(DateTime, nullable=True, default=None,
                         comment="作废时间；NULL 表示未作废。作废=主动放弃，可恢复")

    created_at = Column(DateTime, server_default=func.now(), nullable=False,
                        comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
                        comment="更新时间；通过后端 ORM 更新时刷新")

    __table_args__ = {
        "comment": "Dashboard 首页日历事项表：存储待做事项（todo）与安排（meeting）",
    }
