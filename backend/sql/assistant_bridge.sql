-- Targeted, non-destructive MySQL upgrade for document 18 / Fusion document 23.
-- Applied conditionally by backend/scripts/migrate_assistant.py after backup verification.
-- Do not execute the full schema snapshot against an existing database.
ALTER TABLE calendar_events MODIFY COLUMN event_date DATE NULL COMMENT '事项日期；NULL 表示未安排/无DDL，不归入日历日期格';
ALTER TABLE calendar_events ADD COLUMN note TEXT NULL COMMENT '事项备注或无日期条件；不自动解释为事件触发器';
ALTER TABLE calendar_events ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT '网页与助手共享的乐观并发版本';
CREATE TABLE IF NOT EXISTS assistant_requests (
  request_key VARCHAR(128) NOT NULL PRIMARY KEY,
  payload_hash VARCHAR(64) NOT NULL,
  result_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS assistant_task_origins (
  source_id VARCHAR(96) NOT NULL PRIMARY KEY,
  event_id INT NOT NULL UNIQUE,
  source_json TEXT NOT NULL,
  imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES calendar_events(id) ON DELETE RESTRICT
);
