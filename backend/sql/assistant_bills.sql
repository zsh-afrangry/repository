-- Document18 / Fusion document23 second iteration. Additive, no row deletion.
-- Apply through scripts/migrate_assistant.py with verified backup, not by rerunning this file.
ALTER TABLE bills ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT '网页与助手共享的账单乐观并发版本';
