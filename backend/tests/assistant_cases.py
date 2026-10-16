"""Shared-data assistant contract regression. SQLite and stubbed weather only.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
Run: python backend/tests/assistant_cases.py. No real DB, QQ, model or weather.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.assistant.router import router
from app.assistant.errors import install_errors
from app.assistant.models import AssistantRequest, AssistantTaskOrigin
from app.assistant.service import write_once
from app.business_errors import BusinessError
from app.database import get_db
from app.models.bill import Base, Bill, CalendarEvent, Tag, TagType
from app.routers.bill import router as bill_router
from app.routers.calendar import router as calendar_router
from app.routers import weather
from app.crud.calendar import is_overdue, counts_as_progress, pending_bucket


class AssistantCases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token = Path(self.temp.name) / 'token'
        self.token.write_text('a' * 64)
        self.token.chmod(0o600)
        self.previous = os.environ.get('KM_ASSISTANT_TOKEN_FILE')
        os.environ['KM_ASSISTANT_TOKEN_FILE'] = str(self.token)
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(self.engine, 'connect')
        def functions(connection, _record):
            connection.create_function('year', 1, lambda s: int(s[:4]))
            connection.create_function('month', 1, lambda s: int(s[5:7]))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add_all([Tag(id=1, name='餐饮', type=TagType.category),
                        Tag(id=2, name='午饭', type=TagType.subcategory, parent_id=1),
                        Tag(id=3, name='交通', type=TagType.category)])
            db.commit()
        app = FastAPI()
        install_errors(app)
        app.include_router(router, prefix='/api')
        app.include_router(bill_router, prefix='/api')
        app.include_router(calendar_router, prefix='/api')
        def db_override():
            with self.Session() as db: yield db
        app.dependency_overrides[get_db] = db_override
        self.client = TestClient(app)
        self.headers = {'Authorization': 'Bearer ' + 'a' * 64}
        self.seq = 0

    def tearDown(self):
        self.client.close()
        self.engine.dispose()
        if self.previous is None: os.environ.pop('KM_ASSISTANT_TOKEN_FILE', None)
        else: os.environ['KM_ASSISTANT_TOKEN_FILE'] = self.previous
        self.temp.cleanup()

    def post(self, path, data, key=None):
        self.seq += 1
        return self.client.post('/api/assistant/' + path, json=data,
                                headers={**self.headers, 'Idempotency-Key': key or f'request-test-key-{self.seq:04}'})

    def task(self, **fields):
        response = self.post('tasks', {'action': 'add', 'fields': {'title': '共享事项', **fields}})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['item']

    def bill(self):
        return {'expense_date': '2026-10-17', 'amount': '14.00', 'category_id': 1, 'subcategory_id': 2, 'note': '午饭'}

    def test_auth_missing_and_invalid(self):
        self.assertEqual(self.client.get('/api/assistant/tasks').status_code, 401)
        self.assertEqual(self.client.get('/api/assistant/status', headers={'Authorization': 'Bearer bad'}).status_code, 401)

    def test_auth_unconfigured_and_permissions(self):
        self.token.chmod(0o644)
        self.assertEqual(self.client.get('/api/assistant/status', headers=self.headers).status_code, 503)
        self.token.unlink()
        self.assertEqual(self.client.get('/api/assistant/status', headers=self.headers).status_code, 503)

    def test_status_and_tag_catalog(self):
        self.assertEqual(self.client.get('/api/assistant/status', headers=self.headers).json()['billWrites'], ['create'])
        self.assertEqual(len(self.client.get('/api/assistant/tags', headers=self.headers).json()['items']), 3)

    def test_task_create_visible_in_website(self):
        row = self.task(note='活动结束后，越快越好')
        website = self.client.get('/api/calendar-events/').json()
        self.assertEqual(website[0]['id'], row['id'])
        self.assertIsNone(website[0]['event_date'])
        self.assertEqual(website[0]['note'], '活动结束后，越快越好')

    def test_website_create_visible_in_assistant(self):
        row = self.client.post('/api/calendar-events/', json={'title': '网站事项', 'event_date': None}).json()
        result = self.client.get('/api/assistant/tasks', headers=self.headers).json()
        self.assertEqual(result['items'][0]['id'], row['id'])

    def test_no_deadline_never_overdue_or_automatic_progress(self):
        row = self.task(tone='meeting')
        with self.Session() as db:
            record = db.get(CalendarEvent, row['id'])
            self.assertFalse(is_overdue(record, now=datetime(2099, 1, 1)))
            self.assertFalse(counts_as_progress(record, now=datetime(2099, 1, 1)))
            self.assertEqual(pending_bucket(record), 'unscheduled')

    def test_past_deadline_stays_pending(self):
        row = self.task(event_date='2020-01-01', event_time='10:30:00')
        self.assertEqual(self.client.get('/api/assistant/tasks', headers=self.headers).json()['items'][0]['id'], row['id'])
        with self.Session() as db: self.assertTrue(is_overdue(db.get(CalendarEvent, row['id'])))

    def test_invalid_time_without_date(self):
        self.assertEqual(self.post('tasks', {'action': 'add', 'fields': {'title': '错误', 'event_time': '10:30:00'}}).status_code, 422)

    def test_web_update_then_assistant_stale_write_rejected(self):
        row = self.task()
        result = self.client.patch(f"/api/calendar-events/{row['id']}", json={'title': '网站改过', 'expected_version': row['version']})
        self.assertEqual(result.status_code, 200, result.text)
        stale = self.post('tasks', {'action': 'void', 'id': row['id'], 'expected_version': row['version']})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['detail']['code'], 'version_conflict')

    def test_assistant_update_then_website_stale_write_rejected(self):
        row = self.task()
        self.assertEqual(self.post('tasks', {'action': 'update', 'id': row['id'], 'expected_version': row['version'], 'fields': {'note': '改过'}}).status_code, 200)
        response = self.client.patch(f"/api/calendar-events/{row['id']}/archive", json={'archived': True, 'expected_version': row['version']})
        self.assertEqual(response.status_code, 409)

    def test_complete_void_and_reopen(self):
        row = self.task()
        for action in ['complete', 'void', 'reopen']:
            result = self.post('tasks', {'action': action, 'id': row['id'], 'expected_version': row['version']})
            self.assertEqual(result.status_code, 200, result.text)
            row = result.json()['item']
            shown = self.client.get('/api/assistant/tasks', headers=self.headers).json()['total']
            self.assertEqual(shown, 1 if action == 'reopen' else 0)
        self.assertIsNone(row['completed_at'])
        self.assertIsNone(row['archived_at'])

    def test_clear_date_and_preserve_note(self):
        row = self.task(event_date='2026-10-20', note='条件')
        result = self.post('tasks', {'action': 'update', 'id': row['id'], 'expected_version': row['version'], 'fields': {'event_date': None, 'event_time': None}})
        self.assertIsNone(result.json()['item']['event_date'])
        self.assertEqual(result.json()['item']['note'], '条件')

    def test_task_requires_version_and_forbids_status_fields(self):
        row = self.task()
        self.assertEqual(self.post('tasks', {'action': 'void', 'id': row['id']}).status_code, 422)
        self.assertEqual(self.post('tasks', {'action': 'add', 'fields': {'title': '越权', 'completed_at': '2026-10-17'}}).status_code, 422)

    def test_same_request_retries_once(self):
        body = {'action': 'add', 'fields': {'title': '唯一'}}
        a = self.post('tasks', body, 'same-request-key-0001')
        b = self.post('tasks', body, 'same-request-key-0001')
        self.assertEqual(a.json(), b.json())
        self.assertEqual(self.client.get('/api/assistant/tasks', headers=self.headers).json()['total'], 1)
        self.assertEqual(self.post('tasks', {'action': 'add', 'fields': {'title': '另一条'}}, 'same-request-key-0001').status_code, 409)

    def test_missing_request_key(self):
        r = self.client.post('/api/assistant/bills', headers=self.headers, json=self.bill())
        self.assertEqual(r.status_code, 422)

    def test_bill_assistant_to_web_and_exact_amount(self):
        created = self.post('bills', self.bill())
        self.assertEqual(created.status_code, 201, created.text)
        web = self.client.get('/api/bills/').json()
        self.assertEqual(web['items'][0]['id'], created.json()['item']['id'])
        self.assertEqual(web['items'][0]['amount'], '14.00')
        self.assertIsNone(web['items'][0]['payment_channel_id'])

    def test_bill_web_to_assistant_and_summary(self):
        self.assertEqual(self.client.post('/api/bills/', json=self.bill()).status_code, 201)
        result = self.client.get('/api/assistant/bills', headers=self.headers).json()
        self.assertEqual(result['total'], 1)
        summary = self.client.get('/api/assistant/bills/monthly?year=2026&month=10', headers=self.headers).json()
        self.assertEqual(summary['expense'], '14.00')

    def test_bill_duplicate_retry_and_changed_amount(self):
        a = self.post('bills', self.bill(), 'bill-retry-key-0001')
        b = self.post('bills', self.bill(), 'bill-retry-key-0001')
        self.assertEqual(a.json(), b.json())
        self.assertEqual(self.post('bills', {**self.bill(), 'amount': '15'}, 'bill-retry-key-0001').status_code, 409)
        self.assertEqual(self.client.get('/api/bills/').json()['total'], 1)

    def test_bill_invalid_amount_and_tags(self):
        for changed in [{'amount': '0'}, {'amount': '14.001'}, {'amount': '10000000000'},
                        {'category_id': 999}, {'category_id': 2}, {'category_id': 3}]:
            self.assertEqual(self.post('bills', {**self.bill(), **changed}).status_code, 422, changed)
        self.assertEqual(self.client.get('/api/bills/').json()['total'], 0)

    def test_bill_no_delete_or_patch(self):
        self.assertEqual(self.client.delete('/api/assistant/bills/1', headers=self.headers).status_code, 404)
        self.assertEqual(self.client.patch('/api/assistant/bills', headers=self.headers, json={'amount': 1}).status_code, 405)

    def test_pagination_and_search(self):
        self.task(title='第一项')
        self.task(title='第二项')
        result = self.client.get('/api/assistant/tasks?limit=1', headers=self.headers).json()
        self.assertTrue(result['truncated'])
        self.assertEqual(result['total'], 2)
        result = self.client.get('/api/assistant/tasks?query=第二', headers=self.headers).json()
        self.assertEqual(result['total'], 1)

    def test_atomic_write_failure_rolls_back_receipt_and_item(self):
        with self.Session() as db:
            def fail():
                db.add(CalendarEvent(title='必须回滚'))
                db.flush()
                raise RuntimeError('injected transaction failure')
            with self.assertRaises(RuntimeError): write_once(db, 'rollback-request-1', 'tasks', {}, fail)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(CalendarEvent)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(AssistantRequest)), 0)

    def legacy(self, **changes):
        return {'id': '123456abcdef', 'title': '旧事项', 'status': 'active', 'ddl': None,
                'content': '说明', 'note': '越快越好', 'deadline_ms': None, 'version': 2,
                'created_ms': 1791000000000, 'updated_ms': 1791000000000, **changes}

    def test_import_preview_nonwriting_and_repeat_safe(self):
        body = {'items': [self.legacy()]}
        preview = self.post('tasks/import', body).json()
        self.assertEqual(preview['mapping'][0]['result'], 'would_import')
        self.assertEqual(self.client.get('/api/assistant/tasks', headers=self.headers).json()['total'], 0)
        first = self.post('tasks/import', {**body, 'apply': True}).json()
        second = self.post('tasks/import', {**body, 'apply': True}).json()
        self.assertEqual(first['mapping'][0]['eventId'], second['mapping'][0]['eventId'])
        self.assertEqual(self.client.get('/api/assistant/tasks', headers=self.headers).json()['total'], 1)

    def test_import_expired_stays_archived_and_keeps_provenance(self):
        r = self.post('tasks/import', {'apply': True, 'items': [self.legacy(status='expired', ddl='2026-01-01')]}).json()
        self.assertTrue(r['ok'])
        self.assertEqual(self.client.get('/api/assistant/tasks', headers=self.headers).json()['total'], 0)
        with self.Session() as db:
            origin = db.get(AssistantTaskOrigin, 'kurumi-list-v1:123456abcdef')
            self.assertIn('expired', origin.source_json)
            self.assertIsNotNone(db.get(CalendarEvent, origin.event_id).archived_at)

    def test_import_conflict_rolls_back_entire_batch(self):
        self.task(title='网站已有')
        r = self.post('tasks/import', {'apply': True, 'items': [self.legacy(), self.legacy(id='abcdef123456', title='网站已有')]})
        self.assertEqual(r.status_code, 409)
        with self.Session() as db: self.assertEqual(db.scalar(select(func.count()).select_from(CalendarEvent)), 1)

    def test_weather_closed_components_and_coordinates(self):
        original = weather._request_qweather
        calls = []
        weather._request_qweather = lambda path: calls.append(path) or {'code': '200', 'value': 'stub'}
        try:
            for component in ['current', 'daily', 'hourly', 'alerts']:
                r = self.client.get('/api/assistant/weather/' + component + '?latitude=23.14&longitude=113.34', headers=self.headers)
                self.assertEqual(r.status_code, 200)
            self.assertEqual(self.client.get('/api/assistant/weather/lookup?location=天河&adm=广州', headers=self.headers).status_code, 200)
            self.assertIn('hours=24', calls[2])
            self.assertIn('/weatheralert/v1/current/23.14/113.34', calls[3])
            self.assertEqual(self.client.get('/api/assistant/weather/anything', headers=self.headers).status_code, 422)
            self.assertEqual(self.client.get('/api/assistant/weather/current?latitude=999', headers=self.headers).status_code, 422)
        finally: weather._request_qweather = original

    def test_pagination_snapshot_rejects_interleaved_edit(self):
        row = self.task()
        self.task(title='下一页')
        first = self.client.get('/api/assistant/tasks?limit=1', headers=self.headers).json()
        self.client.patch(f"/api/calendar-events/{row['id']}", json={'title': '期间变更'})
        stale = self.client.get('/api/assistant/tasks', params={'skip': 1, 'limit': 1, 'snapshot': first['snapshot']}, headers=self.headers)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['detail']['code'], 'list_changed')

    def test_reopen_can_change_fields_atomically(self):
        row = self.task()
        row = self.post('tasks', {'action': 'void', 'id': row['id'], 'expected_version': row['version']}).json()['item']
        result = self.post('tasks', {'action': 'reopen', 'id': row['id'], 'expected_version': row['version'], 'fields': {'note': '先联系'}})
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.json()['item']['archived_at'])
        self.assertEqual(result.json()['item']['note'], '先联系')

    def test_weather_coordinates_required(self):
        self.assertEqual(self.client.get('/api/assistant/weather/current', headers=self.headers).status_code, 422)

    def test_import_same_title_sources_stay_distinct(self):
        rows = [{'id': f'{i:012x}', 'title': '同名历史', 'status': 'completed', 'version': 1,
                 'created_ms': 0, 'updated_ms': 0} for i in range(2)]
        result = self.post('tasks/import', {'apply': True, 'items': rows})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(len(set(x['eventId'] for x in result.json()['mapping'])), 2)
        with self.Session() as db:
            self.assertEqual(db.scalars(select(CalendarEvent)).first().created_at, datetime(1970, 1, 1, 8))


if __name__ == '__main__': unittest.main(verbosity=2)
