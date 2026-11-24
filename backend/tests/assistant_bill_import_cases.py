"""Bill batch import preview, dynamic tag creation, idempotency, and overlap hint tests.

对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
"""
import hashlib
import json
import unittest
from sqlalchemy import func, select
import assistant_cases as fixtures
from app.assistant.models import AssistantBillImportBatch, AssistantBillOrigin
from app.models.bill import Bill, Tag, TagType


def make_row(
    *,
    expense_date='2026-11-10',
    expense_time='12:30:00',
    record_type='支出',
    amount='25.50',
    category_name='餐饮',
    subcategory_name='午饭',
    note='套餐',
    dup_seq=0,
):
    tuple_base = '|'.join([
        expense_date,
        expense_time or '00:00:00',
        record_type,
        amount,
        category_name,
        subcategory_name or '',
        note or '',
    ])
    source_key = 'xlsx-v1:' + hashlib.sha256(f'{tuple_base}|{dup_seq}'.encode()).hexdigest()
    row_hash = hashlib.sha256(json.dumps({
        'expense_date': expense_date,
        'expense_time': expense_time,
        'record_type': record_type,
        'amount': amount,
        'category_name': category_name,
        'subcategory_name': subcategory_name,
        'note': note,
    }, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {
        'source_key': source_key,
        'row_hash': row_hash,
        'expense_date': expense_date,
        'expense_time': expense_time,
        'record_type': record_type,
        'amount': amount,
        'category_name': category_name,
        'subcategory_name': subcategory_name,
        'note': note,
    }


class BillImportCases(unittest.TestCase):
    def setUp(self):
        fixtures.AssistantCases.setUp(self)
        with self.engine.begin() as conn:
            conn.exec_driver_sql('PRAGMA foreign_keys=ON')

    tearDown = fixtures.AssistantCases.tearDown
    post = fixtures.AssistantCases.post

    def test_preview_is_read_only_and_discovers_new_tags_and_manual_overlaps(self):
        # Create one manual bill that overlaps by (expense_date, record_type, amount).
        manual = self.client.post('/api/bills/', json={
            'expense_date': '2026-11-10',
            'record_type': '支出',
            'amount': '25.50',
            'category_id': 1,
            'note': '手工先记了一笔',
        })
        self.assertEqual(manual.status_code, 201)

        rows = [
            make_row(amount='25.50', category_name='餐饮', subcategory_name='午饭'),
            make_row(expense_date='2026-11-11', amount='42.00', category_name='消费', subcategory_name=None, note='便利店'),
            make_row(expense_date='2026-11-12', amount='88.00', category_name='交通', subcategory_name='打车租车', note='机场'),
            make_row(expense_date='2026-11-13', record_type='收入', amount='100.00', category_name='收转账', subcategory_name=None, note='报销款'),
        ]
        payload = {
            'file_name': '2026-11.xlsx',
            'file_sha256': 'a' * 64,
            'rows': rows,
        }
        r = self.post('bills/import/preview', payload)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body['insert_count'], 4)
        self.assertEqual(body['skipped_count'], 0)
        self.assertEqual(body['total_expense'], '155.50')
        self.assertEqual(body['total_income'], '100.00')
        self.assertEqual(body['date_from'], '2026-11-10')
        self.assertEqual(body['date_to'], '2026-11-13')
        self.assertEqual(body['planned_new_tags'], [
            {'type': 'category', 'name': '消费', 'parent_name': None},
            {'type': 'subcategory', 'name': '打车租车', 'parent_name': '交通'},
            {'type': 'category', 'name': '收转账', 'parent_name': None},
        ])
        self.assertEqual(len(body['manual_overlap_hints']), 1)
        self.assertEqual(body['manual_overlap_hints'][0]['amount'], '25.50')

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Bill)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(AssistantBillImportBatch)), 0)
            self.assertIsNone(db.scalar(select(Tag).where(Tag.name == '消费')))

    def test_commit_creates_tags_bills_origins_and_replays_idempotently(self):
        rows = [
            make_row(expense_date='2026-11-01', amount='19.90', category_name='餐饮', subcategory_name='早午晚餐', note='早餐'),
            make_row(expense_date='2026-11-02', amount='50.00', category_name='服饰美妆', subcategory_name='穿搭', note='围巾'),
        ]
        preview_req = {'file_name': 'nov.xlsx', 'file_sha256': 'b' * 64, 'rows': rows}
        preview = self.post('bills/import/preview', preview_req).json()

        commit_req = {**preview_req, 'expected_preview_hash': preview['preview_hash']}
        c1 = self.post('bills/import/commit', commit_req, key='import-batch-request-0001')
        self.assertEqual(c1.status_code, 200, c1.text)
        b1 = c1.json()
        self.assertEqual(b1['inserted_count'], 2)
        self.assertEqual(b1['skipped_count'], 0)
        self.assertEqual(len(b1['created_tags']), 3)

        # Idempotent replay with same key & same payload returns exact stored receipt.
        c2 = self.post('bills/import/commit', commit_req, key='import-batch-request-0001')
        self.assertEqual(c2.status_code, 200)
        self.assertEqual(c2.json(), b1)

        # Same key with different payload fails 409 idempotency_conflict.
        c_conflict = self.post('bills/import/commit', {**commit_req, 'file_name': 'other.xlsx'}, key='import-batch-request-0001')
        self.assertEqual(c_conflict.status_code, 409)
        self.assertEqual(c_conflict.json()['detail']['code'], 'idempotency_conflict')

        # Even if user edits bill note/category on website later, overlapping re-import skips already imported rows!
        listed = self.client.get('/api/bills/').json()['items']
        self.assertEqual(len(listed), 2)
        target = listed[0]
        patched = self.client.patch(f"/api/bills/{target['id']}", json={'note': '网页手工改过备注', 'expected_version': target['version']})
        self.assertEqual(patched.status_code, 200)

        new_row = make_row(expense_date='2026-11-03', amount='9.90', category_name='餐饮', subcategory_name='早午晚餐', note='豆浆')
        overlap_req = {'file_name': 'nov-full.xlsx', 'file_sha256': 'c' * 64, 'rows': [*rows, new_row]}
        p2 = self.post('bills/import/preview', overlap_req).json()
        self.assertEqual(p2['insert_count'], 1)
        self.assertEqual(p2['skipped_count'], 2)
        self.assertEqual(p2['planned_new_tags'], [])
        c3 = self.post('bills/import/commit', {**overlap_req, 'expected_preview_hash': p2['preview_hash']}, key='import-batch-request-0002')
        self.assertEqual(c3.status_code, 200)
        self.assertEqual(c3.json()['inserted_count'], 1)
        self.assertEqual(c3.json()['skipped_count'], 2)

        batches = self.client.get('/api/assistant/bills/import/batches', headers=self.headers).json()
        self.assertEqual(len(batches['items']), 2)
        self.assertEqual({b['batch_id'] for b in batches['items']}, {b1['batch_id'], c3.json()['batch_id']})
        by_key = self.client.get('/api/assistant/bills/import/batches?request_key=import-batch-request-0002', headers=self.headers).json()
        self.assertEqual(len(by_key['items']), 1)
        self.assertEqual(by_key['items'][0]['batch_id'], c3.json()['batch_id'])

    def test_stale_tag_drift_rejects_commit_and_delete_preserves_origin(self):
        rows = [make_row(expense_date='2026-11-05', amount='33.00', category_name='新分类X', subcategory_name=None, note='测试')]
        req = {'file_name': 'drift.xlsx', 'file_sha256': 'd' * 64, 'rows': rows}
        preview = self.post('bills/import/preview', req).json()

        # Simulate website adding tag 新分类X between preview and commit.
        with self.Session() as db:
            db.add(Tag(name='新分类X', type=TagType.category, sort_order=99))
            db.commit()

        stale = self.post('bills/import/commit', {**req, 'expected_preview_hash': preview['preview_hash']}, key='import-batch-request-0003')
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['detail']['code'], 'import_preview_stale')

        # Re-preview picks up existing tag, commits, and deleting bill keeps origin provenance.
        fresh = self.post('bills/import/preview', req).json()
        self.assertEqual(fresh['planned_new_tags'], [])
        done = self.post('bills/import/commit', {**req, 'expected_preview_hash': fresh['preview_hash']}, key='import-batch-request-0004')
        self.assertEqual(done.status_code, 200)

        bill = self.client.get('/api/bills/').json()['items'][0]
        del_res = self.client.delete(f"/api/bills/{bill['id']}?expected_version={bill['version']}")
        self.assertEqual(del_res.status_code, 204)
        with self.Session() as db:
            origin = db.get(AssistantBillOrigin, rows[0]['source_key'])
            self.assertIsNotNone(origin)
            self.assertIsNone(origin.bill_id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
