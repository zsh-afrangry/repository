"""Opt-in real MySQL recovery/migration/concurrency test in a unique disposable DB.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
Requires --backup-dir and --env-file; never writes the source schema.
Restores the private dump only into km_bridge_test_<random>, then drops exactly that DB.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup-dir', required=True)
    parser.add_argument('--env-file', required=True)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    from sqlalchemy import create_engine, text, select, func
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.orm.exc import StaleDataError
    from app.database import engine as source
    from app.assistant.service import write_once
    from app.assistant.models import AssistantRequest
    from app.models.bill import CalendarEvent, Bill
    from app.schemas.bill import BillCreate
    from app.crud.bill import create_bill
    from app.crud.calendar import create_calendar_event
    from app.schemas.calendar import CalendarEventCreate
    assert source.dialect.name == 'mysql'
    root = Path(args.backup_dir) / 'private-state'
    manifest = json.loads((root / 'manifest.json').read_text())
    compressed = (root / 'database.sql.gz').read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == manifest['mysqlDumpSha256']
    dump = gzip.decompress(compressed)
    assert not re.search(rb'(?im)^\s*(USE |CREATE DATABASE|DROP DATABASE)', dump), 'dump must not select another database'
    name = 'km_bridge_test_' + uuid.uuid4().hex[:16]
    assert re.fullmatch('km_bridge_test_[a-f0-9]{16}', name)
    admin = create_engine(source.url.set(database=None))
    target = None
    checks = []
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4'))
        with tempfile.TemporaryDirectory(prefix='km-mysql-auth-') as temporary:
            config = Path(temporary) / 'mysql.cnf'
            def quote(value): return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
            config.write_text('[client]\n' + '\n'.join(f'{k}={quote(v)}' for k, v in {
                'host': source.url.host, 'port': source.url.port or 3306, 'user': source.url.username,
                'password': source.url.password, 'default-character-set': 'utf8mb4'}.items()))
            config.chmod(0o600)
            result = subprocess.run(['mysql', '--defaults-extra-file=' + str(config), name], input=dump, capture_output=True, timeout=60)
            assert result.returncode == 0, 'private dump restore failed; no raw dump/stderr emitted'
        target = create_engine(source.url.set(database=name))
        with target.connect() as connection:
            counts = {table: connection.scalar(text(f'SELECT COUNT(*) FROM `{table}`')) for table in ['bills', 'calendar_events', 'tags']}
            checks.append('consistent dump SHA256 + full isolated MySQL restore')
        spec = importlib.util.spec_from_file_location('bridge_migration', Path(__file__).resolve().parents[1] / 'scripts/migrate_assistant.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with target.begin() as connection:
            statements, tables = module.plan(connection)
            for statement in statements: connection.execute(text(statement))
            for table in tables: table.create(connection, checkfirst=True)
        with target.connect() as connection:
            assert not any(module.plan(connection)), 'migration not idempotent'
            assert counts == {table: connection.scalar(text(f'SELECT COUNT(*) FROM `{table}`')) for table in counts}
        checks.append('additive migration + second-run no-op + original row counts preserved')
        Session = sessionmaker(bind=target)
        with Session() as db:
            row = create_calendar_event(db, CalendarEventCreate(title='[bridge-test]并发事项', note='无DDL'))
            identity = row.id
        with Session() as first, Session() as second:
            a = first.get(CalendarEvent, identity); b = second.get(CalendarEvent, identity)
            a.note = 'first writer'; first.commit()
            b.note = 'second writer'
            try: second.commit()
            except StaleDataError: second.rollback()
            else: raise AssertionError('lost-update conflict not caught')
        checks.append('actual MySQL optimistic concurrency across two sessions')
        def one_write(_):
            with Session() as db:
                def work():
                    item = create_bill(db, BillCreate(amount='14.00', expense_date='2026-10-17', note='[bridge-test]'), commit=False)
                    return {'ok': True, 'item': {'id': item.id}}
                return write_once(db, 'real-mysql-concurrent-request-001', 'bills', {'amount': '14.00'}, work)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(one_write, [1, 2]))
        assert results[0] == results[1]
        with Session() as db:
            assert db.scalar(select(func.count()).select_from(Bill).where(Bill.note == '[bridge-test]')) == 1
            assert db.get(AssistantRequest, 'real-mysql-concurrent-request-001') is not None
        checks.append('actual concurrent duplicate request commits exactly one bill and receipt')
        print(json.dumps({'ok': True, 'boundary': 'real MySQL temporary clone; no source DB writes, QQ or model',
                          'restoredCounts': counts, 'checks': checks, 'temporaryDatabaseRemovedOnExit': True}, ensure_ascii=False))
    finally:
        if target: target.dispose()
        with admin.connect() as connection: connection.execute(text(f'DROP DATABASE IF EXISTS `{name}`'))
        admin.dispose()


if __name__ == '__main__': main()
