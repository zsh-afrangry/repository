"""开发启动前的环境自检：确保 MySQL 数据库存在，并报告 MongoDB 状态。

对应文档：docs/15_开发启动脚本方案.md「§3.4 `ensure_database.py` 的边界」。

**为什么需要它**

启动脚本在 Win11（PowerShell）和 Ubuntu（Bash）上各有一份，但"检查什么、怎么算通过"
必须**只有一份实现**——两处各写一遍迟早不一致（本项目已经吃过"同一规则两处实现"的亏，
见 docs/14 §12.3）。

**它补的那个唯一硬缺口：数据库不存在**

`backend/main.py` 的 lifespan 已经做了这些事：

    Base.metadata.create_all(bind=engine)   # 建表（表不存在才建）
    seed_default_tags(db)                   # 39 个标签（表非空就跳过）
    seed_notes(db)                          # 7 个笔记主题（版本标记判定）

但 `create_all()` **只能建表，不能建库**。库不存在时 SQLAlchemy 直接抛
`Unknown database 'knowledgemap'`，而且这个错发生在 lifespan 里，**服务根本起不来**。
所以启动脚本必须先保证库存在。

**它刻意不做什么**（每一条都是"越界会造成伤害"的动作）：

| 不做 | 原因 |
|---|---|
| 不建表、不灌种子数据 | 那是 `main.py` 的职责。重叠会让人搞不清"谁负责"，出问题也无从定位 |
| 不执行 `backend/sql/knowledgemap.sql` | 该文件含 `DROP TABLE IF EXISTS`，对已有数据的库执行会**清空真实数据** |
| 不改已有库的字符集 | 改字符集可能损坏已有数据，必须由人决定 |
| 不包含任何 `DROP` / `--recreate` | 见 docs/14 §12.4：一次"清空表"式的清理丢过真实数据 |
| 不启动/停止 MongoDB | 用户的 Mongo 是 Windows 服务（`Automatic` 自启）／systemd 用户服务。脚本擅自启停会掩盖"为什么它本来是停的" |

**用法**

    python backend/scripts/ensure_database.py            # 检查 + 按需建库
    python backend/scripts/ensure_database.py --check    # 只检查，**不创建**
    python backend/scripts/ensure_database.py --json     # 机器可读输出（给启动脚本用）

**退出码**：0 = 可以启动；1 = 环境不满足（原因已打印）。

⚠️ 本脚本**只读业务数据**，唯一的写操作是"创建不存在的数据库"。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

OK_MARK = "[OK]"
WARN_MARK = "[--]"
FAIL_MARK = "[!!]"

# 建库时使用的字符集。与 models 里各表的 utf8mb4_0900_ai_ci 一致，
# 否则新库默认可能是 utf8mb4_0900_ai_ci 之外的排序规则，导致跨库比较行为不同。
MYSQL_CHARSET = "utf8mb4"
MYSQL_COLLATION = "utf8mb4_0900_ai_ci"

# 脚本要检查存在的关键表（只报告，不创建）。
# `tags` 是字典表、`notes_topics` 是种子数据——缺了它们页面能开但功能不可用。
KEY_TABLES = ("bills", "tags", "calendar_events", "notes_topics", "simulation_records")

# 字典/种子数据的最低期望条数。低于这个数只**警告**：
# 可能只是用户自己删过标签，不该由脚本擅自补回去。
EXPECTED_SEED_ROWS = {"tags": 30, "notes_topics": 5}


class CheckError(RuntimeError):
    """环境不满足，且不是脚本能自动修复的。"""


def _database_url() -> tuple[str, str, str]:
    """返回 (完整连接串, 库名, 服务器地址(不含库))。

    复用 `app.database` 的解析逻辑，**不在这里重复实现**——
    否则 `.env` 的键名规则会变成两份（docs/14 §12.3 的教训）。
    """
    from app.database import DATABASE_URL

    # 形如 mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4
    head, _, tail = DATABASE_URL.partition("://")
    _, _, tail = tail.partition("/")
    db_name, _, _ = tail.partition("?")
    server = DATABASE_URL.split("@", 1)[1].split("/", 1)[0] if "@" in DATABASE_URL else "?"
    return DATABASE_URL, db_name, server


def _split_url(url: str) -> tuple[str, str]:
    """把连接串拆成 (服务器部分, 库名)。"""
    head, _, tail = url.partition("://")
    credentials_host, _, rest = tail.partition("/")
    db_name, _, _ = rest.partition("?")
    return f"{head}://{credentials_host}", db_name


def check_mysql_server() -> str:
    """MySQL 服务连得上吗？返回服务器版本字符串；连不上抛 CheckError。"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError, SQLAlchemyError

    url, _, server = _database_url()
    server_url = _split_url(url)[0]  # 不带库名，因为库可能还不存在
    try:
        engine = create_engine(server_url, pool_pre_ping=True)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
        engine.dispose()
        return str(version)
    except OperationalError as exc:
        raise CheckError(
            f"连不上 MySQL 服务（{server}）。\n"
            f"     原始错误：{exc.orig if hasattr(exc, 'orig') else exc}\n"
            f"     排查方向：服务起了吗？（Windows：服务面板看 MySQL80；"
            f"Ubuntu：systemctl status mysql）端口对吗？账号密码在 backend/.env 里。"
        ) from exc
    except SQLAlchemyError as exc:
        raise CheckError(f"MySQL 连接串有问题：{exc}") from exc


def database_exists(db_name: str) -> bool:
    from sqlalchemy import create_engine, text

    url, _, _ = _database_url()
    engine = create_engine(_split_url(url)[0], pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                     "WHERE SCHEMA_NAME = :name"),
                {"name": db_name},
            ).first()
        return row is not None
    finally:
        engine.dispose()


def create_database(db_name: str) -> None:
    """创建数据库。**唯一的写操作**，且只在库不存在时调用。

    ⚠️ 库名来自 `.env`，会被拼进 SQL（标识符无法用参数占位）。
    因此这里做**白名单校验**：只允许字母数字下划线。
    否则一个含反引号的库名就能注入任意 SQL。
    """
    from sqlalchemy import create_engine, text

    if not db_name.replace("_", "").isalnum():
        raise CheckError(f"库名 {db_name!r} 含非法字符（只允许字母、数字、下划线）。")

    url, _, _ = _database_url()
    engine = create_engine(_split_url(url)[0], pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET {MYSQL_CHARSET} COLLATE {MYSQL_COLLATION}"
            ))
    finally:
        engine.dispose()


def inspect_tables(db_name: str) -> dict:
    """报告关键表与种子数据的现状。**只读**。"""
    from sqlalchemy import create_engine, inspect, text

    url, _, _ = _database_url()
    engine = create_engine(url, pool_pre_ping=True)
    result: dict = {"tables": {}, "seed_rows": {}}
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        for table in KEY_TABLES:
            result["tables"][table] = table in existing
        with engine.connect() as conn:
            for table in EXPECTED_SEED_ROWS:
                if table not in existing:
                    continue
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                    result["seed_rows"][table] = int(count or 0)
                except Exception:  # noqa: BLE001 - 计数失败不该让整个自检崩
                    result["seed_rows"][table] = None
    finally:
        engine.dispose()
    return result


def check_mongodb(url: str | None = None) -> dict:
    """检查 MongoDB 连通性。**只读、只报告，不启停服务**。

    ⚠️ `pymongo` 默认**懒连接**：不显式 ping 的话，连不上也不报错。
    必须 ping，并设**短超时**——否则默认 30 秒会让启动脚本卡住。
    """
    from app.tradesim.core.config import settings

    # ⚠️ 字段名是 `MONGO_URL`（不带 TRADESIM_ 前缀）——`TRADESIM_MONGO_URL`
    # 是它读取的**环境变量**名，不是属性名。写错会 AttributeError。
    mongo_url = url or settings.MONGO_URL
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
    except ImportError:
        return {"ok": None, "url": mongo_url,
                "detail": "未安装 pymongo（不影响门户功能，只影响 TradeSim 回测）"}

    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        version = client.server_info().get("version")
        client.close()
        return {"ok": True, "url": mongo_url, "version": version}
    except PyMongoError as exc:
        return {
            "ok": False,
            "url": mongo_url,
            "detail": str(exc)[:200],
            "hint": (
                "MongoDB 未启动。它不是门户的必需依赖（首页/账单/待做都不用它），"
                "只有 TradeSim 回测需要。\n"
                "     Windows：它是服务 `MongoDB`（通常开机自启）→ "
                "`Start-Service MongoDB`（需管理员）或服务面板启动\n"
                "     Ubuntu：`systemctl --user start knowledgemap-mongodb`"
            ),
        }


def run(*, create: bool, as_json: bool) -> int:
    url, db_name, server = _database_url()
    report: dict = {"database": db_name, "server": server, "steps": []}

    def emit(text: str) -> None:
        if not as_json:
            print(text)

    # ---- 1. MySQL 服务 ----
    try:
        version = check_mysql_server()
    except CheckError as exc:
        if as_json:
            report["ok"] = False
            report["error"] = str(exc)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"{FAIL_MARK} {exc}")
        return 1
    emit(f"{OK_MARK} MySQL 服务可连接：{server}（版本 {version}）")
    report["steps"].append({"step": "mysql_server", "ok": True, "version": version})

    # ---- 2. 数据库存在吗（唯一的写操作）----
    exists = database_exists(db_name)
    if exists:
        emit(f"{OK_MARK} 数据库 `{db_name}` 已存在")
        report["steps"].append({"step": "database", "ok": True, "created": False})
    elif create:
        try:
            create_database(db_name)
        except CheckError as exc:
            if as_json:
                report["ok"] = False
                report["error"] = str(exc)
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"{FAIL_MARK} {exc}")
            return 1
        emit(f"{OK_MARK} 已创建数据库 `{db_name}`"
             f"（{MYSQL_CHARSET} / {MYSQL_COLLATION}）")
        report["steps"].append({"step": "database", "ok": True, "created": True})
    else:
        emit(f"{FAIL_MARK} 数据库 `{db_name}` 不存在"
             f"（当前是 --check，未创建；去掉 --check 即会创建）")
        report["steps"].append({"step": "database", "ok": False, "created": False})
        report["ok"] = False
        if as_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    # ---- 3. 表与种子数据（只报告）----
    info = inspect_tables(db_name)
    missing = [t for t, present in info["tables"].items() if not present]
    if missing:
        emit(f"{WARN_MARK} 缺少表：{', '.join(missing)}"
             f"—— 启动后端时 main.py 会自动建（create_all 只建缺失的表）")
    else:
        emit(f"{OK_MARK} {len(KEY_TABLES)} 张关键表都在")
    report["steps"].append({"step": "tables", "missing": missing})

    for table, expected in EXPECTED_SEED_ROWS.items():
        count = info["seed_rows"].get(table)
        if count is None:
            continue
        if count < expected:
            emit(f"{WARN_MARK} `{table}` 只有 {count} 行（预期约 {expected}），"
                 f"字典/种子数据可能不全 —— 启动后端时会按需补齐")
        else:
            emit(f"{OK_MARK} `{table}`：{count} 行")
    report["steps"].append({"step": "seed_rows", "rows": info["seed_rows"]})

    # ---- 4. MongoDB（只报告，不影响退出码）----
    mongo = check_mongodb()
    report["mongodb"] = mongo
    if mongo["ok"] is True:
        emit(f"{OK_MARK} MongoDB 可连接：{mongo['url']}（版本 {mongo.get('version')}）")
    elif mongo["ok"] is None:
        emit(f"{WARN_MARK} MongoDB：{mongo['detail']}")
    else:
        # 不返回非零：门户不依赖 Mongo，不该因此拦住开发启动。
        emit(f"{WARN_MARK} MongoDB 不可用（不影响门户，只影响 TradeSim 回测）")
        emit(f"     {mongo.get('hint', mongo.get('detail', ''))}")

    report["ok"] = True
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print()
        print(f"{OK_MARK} 环境自检通过，可以启动后端。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="开发启动前的环境自检（建库 + 报告表/种子/Mongo）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true",
                        help="只检查，**不创建**数据库（供排障与 CI 用）")
    parser.add_argument("--json", action="store_true",
                        help="输出机器可读的 JSON（供启动脚本判断）")
    args = parser.parse_args()
    try:
        return run(create=not args.check, as_json=args.json)
    except CheckError as exc:
        print(f"{FAIL_MARK} {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
