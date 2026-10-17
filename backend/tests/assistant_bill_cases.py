"""Second-iteration bill CRUD/version/receipt tests; disposable SQLite only.

对应文档：docs/18_助手业务接口与共享数据.md「第二轮账单维护与验证」。
"""
import json
import unittest
from sqlalchemy import select, func
from sqlalchemy.orm.exc import StaleDataError
import assistant_cases as fixtures
from app.models.bill import Bill
from app.assistant.models import AssistantRequest
from app.schemas.bill import BillUpdate
from app.crud.bill import update_bill, delete_bill


class BillCases(unittest.TestCase):
    setUp = fixtures.AssistantCases.setUp
    tearDown = fixtures.AssistantCases.tearDown
    post = fixtures.AssistantCases.post
    bill = fixtures.AssistantCases.bill

    def create(self, **fields):
        r = self.post('bills', {**self.bill(), **fields})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()['item']

    def manage(self, row, action='update', fields=None, key=None, **overrides):
        body = {'action': action, 'id': row['id'], 'expected_version': row['version'], **overrides}
        if fields is not None: body['fields'] = fields
        return self.post('bills/manage', body, key)

    def test_new_bill_exposes_shared_version(self):
        row = self.create()
        self.assertEqual(row['version'], 1)
        self.assertEqual(self.client.get(f"/api/bills/{row['id']}").json()['version'], 1)

    def test_update_keeps_unmentioned_fields_and_replays(self):
        row = self.create(payment_platform_id=None)
        result = self.manage(row, fields={'amount': '36.80'}, key='bill-update-replay-001')
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertEqual(body['item']['amount'], '36.80')
        self.assertEqual(body['item']['note'], row['note'])
        self.assertEqual(body['item']['version'], 2)
        self.assertEqual(body['before']['amount'], '14.00')
        self.assertEqual(self.manage(row, fields={'amount': '36.80'}, key='bill-update-replay-001').json(), body)
        self.assertEqual(self.manage(row, fields={'amount': '37'}, key='bill-update-replay-001').status_code, 409)

    def test_delete_is_actual_and_replay_returns_original_receipt(self):
        row = self.create()
        first = self.manage(row, 'delete', key='bill-delete-replay-001')
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()['item']['deleted'])
        self.assertEqual(first.json()['before']['id'], row['id'])
        self.assertEqual(self.client.get(f"/api/bills/{row['id']}").status_code, 404)
        self.assertEqual(self.manage(row, 'delete', key='bill-delete-replay-001').json(), first.json())
        self.assertEqual(self.manage(row, 'delete').status_code, 404)
        with self.Session() as db:
            receipt = json.loads(db.get(AssistantRequest, 'bill-delete-replay-001').result_json)
            self.assertEqual(receipt['before']['note'], row['note'])

    def test_delete_does_not_touch_other_records_or_summary(self):
        one, two = self.create(), self.create(amount='6.90', note='另一笔')
        self.assertEqual(self.manage(one, 'delete').status_code, 200)
        page = self.client.get('/api/assistant/bills', headers=self.headers).json()
        self.assertEqual([x['id'] for x in page['items']], [two['id']])
        summary = self.client.get('/api/assistant/bills/monthly?year=2026&month=10', headers=self.headers).json()
        self.assertEqual(summary['expense'], '6.90')

    def test_website_edit_invalidates_assistant_update_and_delete(self):
        row = self.create()
        web = self.client.patch(f"/api/bills/{row['id']}", json={'amount': '15.00', 'expected_version': 1})
        self.assertEqual(web.status_code, 200, web.text)
        self.assertEqual(web.json()['version'], 2)
        for action, fields in [('update', {'note': '过时'}), ('delete', None)]:
            r = self.manage(row, action, fields)
            self.assertEqual(r.status_code, 409)
            self.assertEqual(r.json()['detail']['code'], 'version_conflict')

    def test_assistant_edit_invalidates_website_form_and_delete(self):
        row = self.create()
        self.assertEqual(self.manage(row, fields={'amount': '15.00'}).status_code, 200)
        patch = self.client.patch(f"/api/bills/{row['id']}", json={'note': '过时表单', 'expected_version': 1})
        self.assertEqual(patch.status_code, 409)
        deleted = self.client.delete(f"/api/bills/{row['id']}?expected_version=1")
        self.assertEqual(deleted.status_code, 409)
        self.assertEqual(self.client.delete(f"/api/bills/{row['id']}?expected_version=2").status_code, 204)

    def test_requires_id_version_and_one_action(self):
        row = self.create()
        for body in [{'action': 'delete', 'id': row['id']}, {'action': 'delete', 'expected_version': 1},
                     {'action': 'delete', 'id': [row['id']], 'expected_version': 1},
                     {'action': 'delete-all', 'id': row['id'], 'expected_version': 1}]:
            self.assertEqual(self.post('bills/manage', body).status_code, 422)
        self.assertEqual(self.client.patch(f"/api/bills/{row['id']}", json={'amount': '15'}).status_code, 422)
        self.assertEqual(self.client.delete(f"/api/bills/{row['id']}").status_code, 422)

    def test_fields_are_strict_and_failed_write_does_not_consume_key(self):
        row = self.create()
        for fields in [{}, {'date': '2026-10-18'}, {'amount': None}, {'amount': '0'}, {'amount': '14.001'},
                       {'category_id': 3}, {'subcategory_id': 999}, {'id': 2}, {'version': 99}]:
            self.assertEqual(self.manage(row, fields=fields, key='bill-invalid-fields-001').status_code, 422, fields)
        self.assertEqual(self.manage(row, fields={'note': '合法'}, key='bill-invalid-fields-001').status_code, 200)

    def test_null_clears_nullable_fields_only(self):
        row = self.create()
        r = self.manage(row, fields={'note': None, 'subcategory_id': None})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()['item']['note'])
        self.assertIsNone(r.json()['item']['subcategory_id'])
        self.assertEqual(r.json()['item']['category_id'], row['category_id'])

    def test_delete_cannot_include_update_or_override_version(self):
        row = self.create()
        self.assertEqual(self.manage(row, 'delete', {'amount': '2'}).status_code, 422)
        self.assertEqual(self.manage(row, fields={'expected_version': 9}).status_code, 422)

    def test_query_by_id_and_literal_note_text(self):
        one, two = self.create(note='午饭 29.9+6.9 100%'), self.create(note='午饭普通')
        for query, ids in [(f"id={one['id']}", [one['id']]), ('query=29.9%2B6.9', [one['id']]),
                           ('query=100%25', [one['id']]), ('query=_', []), ('id=99999', [])]:
            r = self.client.get('/api/assistant/bills?' + query, headers=self.headers)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual([x['id'] for x in r.json()['items']], ids)
        self.assertEqual(self.client.get('/api/assistant/bills?query=午饭&limit=1', headers=self.headers).json()['total'], 2)

    def test_actual_orm_update_and_delete_conflict_between_sessions(self):
        row = self.create()
        for operation in ['update', 'delete']:
            with self.Session() as a, self.Session() as b:
                first, stale = a.get(Bill, row['id']), b.get(Bill, row['id'])
                first.amount += 1
                a.commit()
                with self.assertRaises(StaleDataError):
                    if operation == 'update': update_bill(b, stale, BillUpdate(note='stale'))
                    else: delete_bill(b, stale)
                b.rollback()

    def test_update_and_delete_transaction_can_rollback_with_receipt_failure(self):
        row = self.create()
        for operation in ['update', 'delete']:
            with self.Session() as db:
                bill = db.get(Bill, row['id'])
                if operation == 'update': update_bill(db, bill, BillUpdate(note='回滚'), commit=False)
                else: delete_bill(db, bill, commit=False)
                db.rollback()
            self.assertEqual(self.client.get(f"/api/bills/{row['id']}").json()['note'], row['note'])


if __name__ == '__main__': unittest.main(verbosity=2)
