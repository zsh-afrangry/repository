"""门户三个模块（bills / tags / calendar_events）的 CRUD 回归用例。

与 `tradesim_grid_strategy_cases.py` 一样，这是一个**纯 Python 运行器**，不是 pytest：

    cd backend
    python tests/portal_crud_cases.py        # 期望全部 PASS

为什么用内存 SQLite 而不是直接连 MySQL：这些用例会建表、插数据、删数据，而开发机上那份
MySQL 里是**真实账单数据**。内存库让每条用例都在干净的环境里跑，且**完全不碰 MySQL**。

代价是两处方言差异，已在下面显式处理：

1. `crud.monthly_summary` 用的是 MySQL 的 `YEAR()` / `MONTH()`（见其 docstring），SQLite
   没有这两个函数。测试通过 `create_function` 注册了等价替身，好让**同一条 CRUD 代码路径**
   被真实执行到。**这只是测试替身，不代表那条查询可移植**——生产就是 MySQL。
2. SQLAlchemy 在 SQLite 上对 `Numeric` 只能以浮点中转，会发一条 SAWarning。金额断言一律
   先用 `float()` 归一，避免 Decimal 标度差异导致的假失败。
"""

import sys
import warnings
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crud import bill as crud_bill
from app.models.bill import Base, Bill, RecordType, ReimbursementStatus, Tag, TagType
from app.schemas.bill import BillCreate, BillUpdate, MonthlySummaryOut

# SQLite 用浮点存放 Numeric，SQLAlchemy 会提示精度可能丢失；这是已知且可接受的中转。
warnings.filterwarnings("ignore", category=Warning, message=".*support Decimal objects.*")


def make_db():
    """返回一个干净的 (engine, session) —— 每条用例各自一份内存库。"""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _register_mysql_date_functions(dbapi_connection, _record):
        # 见模块 docstring 第 1 条：仅为让 monthly_summary 在同一条代码路径上可跑。
        dbapi_connection.create_function(
            "YEAR", 1, lambda value: int(str(value)[:4]) if value else None
        )
        dbapi_connection.create_function(
            "MONTH", 1, lambda value: int(str(value)[5:7]) if value else None
        )

    Base.metadata.create_all(engine)
    return engine, Session(engine)


def seed_category(db, name="餐饮"):
    tag = Tag(name=name, type=TagType.category, sort_order=1)
    db.add(tag)
    db.commit()
    return tag


def make_bill(db, *, amount="12.00", when=date(2026, 6, 21), kind=RecordType.expense, **overrides):
    payload = {
        "record_type": kind,
        "expense_date": when,
        "amount": Decimal(amount),
    }
    payload.update(overrides)
    return crud_bill.create_bill(db, BillCreate(**payload))


def assert_equal(actual, expected, name):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


def assert_money(actual, expected, name):
    if float(actual) != float(expected):
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


def test_create_bill_persists_and_returns_row_with_id():
    """钉住 crud.create_bill 里那句多余 db.refresh 被删掉后的行为。

    删 refresh 之后唯一的风险点就是 `bill.id` 取不回来（commit 后属性已过期）。这条用例
    专门盯住它：id 必须拿到，且返回对象要是同一条已落库的行。
    """
    engine, db = make_db()
    with db:
        bill = make_bill(db, amount="12.34", note="京东闪送")
        if bill is None:
            raise AssertionError("create_bill 返回了 None")
        if bill.id is None or bill.id <= 0:
            raise AssertionError(f"create_bill 未取回 id（删掉 db.refresh 后的主要风险）: {bill.id!r}")
        assert_money(bill.amount, "12.34", "amount")
        assert_equal(bill.note, "京东闪送", "note")
        assert_equal(bill.record_type, RecordType.expense, "record_type")
        assert_equal(db.scalar(select(func.count()).select_from(Bill)), 1, "落库行数")
    engine.dispose()


def test_create_bill_eager_loads_tag_relationships():
    """返回的对象必须已经把 5 个标签关系载入（否则路由序列化时才懒加载会炸）。"""
    engine, db = make_db()
    with db:
        category = seed_category(db, "餐饮")
        bill = make_bill(db, category_id=category.id)
        if bill.category is None:
            raise AssertionError("category 关系未载入")
        assert_equal(bill.category.name, "餐饮", "category.name")
        for name in ("subcategory", "payment_platform", "payment_channel", "fund_type"):
            assert_equal(getattr(bill, name), None, name)
    engine.dispose()


def test_get_bill_returns_none_when_missing():
    engine, db = make_db()
    with db:
        assert_equal(crud_bill.get_bill(db, 999), None, "不存在的 id")
        created = make_bill(db)
        assert_equal(crud_bill.get_bill(db, created.id).id, created.id, "存在的 id")
    engine.dispose()


def test_list_bills_filters_by_type_and_date_range():
    engine, db = make_db()
    with db:
        make_bill(db, when=date(2026, 6, 1), kind=RecordType.expense)
        make_bill(db, when=date(2026, 6, 15), kind=RecordType.expense)
        make_bill(db, when=date(2026, 6, 20), kind=RecordType.income, amount="500.00")
        make_bill(db, when=date(2026, 7, 1), kind=RecordType.expense)

        total, items = crud_bill.list_bills(db, record_type=RecordType.expense)
        assert_equal(total, 3, "仅按类型过滤的 total")

        total, items = crud_bill.list_bills(
            db, date_from=date(2026, 6, 2), date_to=date(2026, 6, 30)
        )
        assert_equal(total, 2, "按日期区间过滤的 total")
        # 排序是 expense_date 倒序，最近的应排在最前
        assert_equal(items[0].expense_date, date(2026, 6, 20), "排序首条")
    engine.dispose()


def test_list_bills_paginates_and_reports_total():
    engine, db = make_db()
    with db:
        for day in range(1, 8):
            make_bill(db, when=date(2026, 6, day))

        total, items = crud_bill.list_bills(db, skip=0, limit=3)
        assert_equal(total, 7, "total 应为过滤后的总数而非本页条数")
        assert_equal(len(items), 3, "第一页条数")

        total, items = crud_bill.list_bills(db, skip=6, limit=3)
        assert_equal(total, 7, "翻页后 total 不变")
        assert_equal(len(items), 1, "最后一页条数")
    engine.dispose()


def test_update_bill_persists_changes():
    engine, db = make_db()
    with db:
        bill = make_bill(db, amount="10.00")
        updated = crud_bill.update_bill(
            db,
            bill,
            BillUpdate(
                amount=Decimal("20.00"),
                reimbursement_status=ReimbursementStatus.pending,
                note="改过了",
            ),
        )
        assert_money(updated.amount, "20.00", "amount")
        assert_equal(updated.reimbursement_status, ReimbursementStatus.pending, "报销状态")
        assert_equal(updated.note, "改过了", "note")
        # 重新查一遍，确认是真的落库而不是只改了内存对象
        assert_money(crud_bill.get_bill(db, bill.id).amount, "20.00", "落库后的 amount")
    engine.dispose()


def test_delete_bill_removes_row():
    engine, db = make_db()
    with db:
        bill = make_bill(db)
        crud_bill.delete_bill(db, bill)
        assert_equal(db.scalar(select(func.count()).select_from(Bill)), 0, "删后行数")
        assert_equal(crud_bill.get_bill(db, bill.id), None, "删后按 id 查")
    engine.dispose()


def test_monthly_summary_splits_income_expense_and_net():
    engine, db = make_db()
    with db:
        make_bill(db, when=date(2026, 6, 3), amount="644.71", kind=RecordType.expense)
        make_bill(db, when=date(2026, 6, 5), amount="100.29", kind=RecordType.expense)
        make_bill(db, when=date(2026, 6, 10), amount="5000.00", kind=RecordType.income)
        # 落在别的月份，不能被算进来
        make_bill(db, when=date(2026, 7, 1), amount="999.99", kind=RecordType.expense)

        summary = crud_bill.monthly_summary(db, 2026, 6)
        assert_equal(summary["year"], 2026, "year")
        assert_equal(summary["month"], 6, "month")
        assert_money(summary["income"], "5000.00", "income")
        assert_money(summary["expense"], "745.00", "expense")
        assert_money(summary["net"], "4255.00", "net")

        empty = crud_bill.monthly_summary(db, 2026, 8)
        assert_money(empty["income"], 0, "空月份 income")
        assert_money(empty["net"], 0, "空月份 net")
    engine.dispose()


def test_monthly_summary_response_model_pins_float_types():
    """钉住 2026-09-20 补上的契约。

    这个路由此前没有 response_model，走 FastAPI 的 jsonable_encoder，而它把"整数值的
    Decimal"转成 int、带小数的转成 float —— 同一个字段类型会摇摆。改用 MonthlySummaryOut
    后类型恒定；这条用例同时保证 `Decimal` 输入仍能被模型接受（否则路由会 500）。
    """
    engine, db = make_db()
    with db:
        make_bill(db, when=date(2026, 6, 3), amount="644.71", kind=RecordType.expense)
        raw = crud_bill.monthly_summary(db, 2026, 6)

        typed = MonthlySummaryOut(**raw)
        # Decimal 进、float 出：类型恒定，且不会变成字符串（那会打断前端的金额运算）
        for name in ("income", "expense", "net"):
            value = getattr(typed, name)
            if not isinstance(value, float):
                raise AssertionError(f"{name} 应为 float，实际是 {type(value).__name__}")
        assert_money(typed.expense, "644.71", "expense")
        assert_equal(typed.income, 0.0, "零值 income 应为 float 0.0")
    engine.dispose()


def main():
    tests = [
        test_create_bill_persists_and_returns_row_with_id,
        test_create_bill_eager_loads_tag_relationships,
        test_get_bill_returns_none_when_missing,
        test_list_bills_filters_by_type_and_date_range,
        test_list_bills_paginates_and_reports_total,
        test_update_bill_persists_changes,
        test_delete_bill_removes_row,
        test_monthly_summary_splits_income_expense_and_net,
        test_monthly_summary_response_model_pins_float_types,
    ]
    failed = 0

    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
