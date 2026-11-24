"""Additive MySQL migration; never recreates a table or alters business rows.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
Default checks only. --apply requires --backup-dir containing a verified private-state dump.
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, text
from app.database import engine
from app.assistant.models import (
    AssistantBillImportBatch,
    AssistantBillOrigin,
    AssistantRequest,
    AssistantTaskOrigin,
)


def plan(connection):
    inspector = inspect(connection)
    columns = {c['name']: c for c in inspector.get_columns('calendar_events')}
    statements = []
    if not columns['event_date']['nullable']:
        statements.append("ALTER TABLE calendar_events MODIFY COLUMN event_date DATE NULL COMMENT '事项日期；NULL 表示未安排/无DDL，不归入日历日期格'")
    if 'note' not in columns:
        statements.append("ALTER TABLE calendar_events ADD COLUMN note TEXT NULL COMMENT '事项备注或无日期条件；不自动解释为事件触发器'")
    if 'version' not in columns:
        statements.append("ALTER TABLE calendar_events ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT '网页与助手共享的乐观并发版本'")
    if 'version' not in {c['name'] for c in inspector.get_columns('bills')}:
        statements.append("ALTER TABLE bills ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT '网页与助手共享的账单乐观并发版本'")
    tables = [
        model.__table__
        for model in (AssistantRequest, AssistantTaskOrigin, AssistantBillImportBatch, AssistantBillOrigin)
        if not inspector.has_table(model.__tablename__)
    ]
    return statements, tables


def verify_backup(directory):
    root = Path(directory).resolve()
    if (root / 'private-state').is_dir(): root /= 'private-state'
    manifest = json.loads((root / 'manifest.json').read_text())
    payload = (root / 'database.sql.gz').read_bytes()
    gzip.decompress(payload)  # Also verify gzip integrity before any DDL.
    if manifest['mysqlDumpSha256'] != hashlib.sha256(payload).hexdigest():
        raise ValueError('备份校验失败，未执行迁移')
    if manifest['mysqlDatabase'] != engine.url.database:
        raise ValueError('备份数据库与目标不一致，未执行迁移')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-dir')
    args = parser.parse_args()
    if engine.dialect.name != 'mysql': raise SystemExit('此脚本仅用于MySQL定向升级')
    if args.apply:
        if not args.backup_dir: raise SystemExit('--apply必须提供--backup-dir')
        verify_backup(args.backup_dir)
    with engine.begin() as connection:
        statements, tables = plan(connection)
        print(json.dumps({'apply': args.apply, 'alterCount': len(statements), 'createTables': [t.name for t in tables]}, ensure_ascii=False))
        if args.apply:
            # MySQL DDL autocommits; each step is additive and may be rerun after interruption.
            for statement in statements: connection.execute(text(statement))
            for table in tables: table.create(connection, checkfirst=True)
    if args.apply:
        with engine.connect() as connection:
            remaining = plan(connection)
            if any(remaining): raise SystemExit('迁移后仍有结构漂移')
        print('schema aligned; business rows untouched')


if __name__ == '__main__': main()
