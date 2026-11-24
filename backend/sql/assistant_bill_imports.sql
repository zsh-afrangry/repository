-- Additive DDL archive for assistant bill batch import (see docs/18_助手业务接口与共享数据.md).
-- Apply via `python backend/scripts/migrate_assistant.py --apply --backup-dir ...`, never raw DROP scripts.

CREATE TABLE IF NOT EXISTS `assistant_bill_import_batches` (
  `batch_id` varchar(64) NOT NULL,
  `source_type` varchar(32) NOT NULL,
  `file_sha256` varchar(64) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `total_rows` int NOT NULL,
  `inserted_count` int NOT NULL,
  `skipped_count` int NOT NULL,
  `created_tags_json` text NOT NULL,
  `request_key` varchar(128) NOT NULL,
  `run_id` varchar(96) NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`batch_id`),
  UNIQUE KEY `request_key` (`request_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `assistant_bill_origins` (
  `source_key` varchar(96) NOT NULL,
  `batch_id` varchar(64) NOT NULL,
  `bill_id` int DEFAULT NULL,
  `row_hash` varchar(64) NOT NULL,
  `source_json` text NOT NULL,
  `imported_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`source_key`),
  KEY `batch_id` (`batch_id`),
  KEY `ix_assistant_bill_origins_bill_id` (`bill_id`),
  CONSTRAINT `assistant_bill_origins_ibfk_1` FOREIGN KEY (`batch_id`) REFERENCES `assistant_bill_import_batches` (`batch_id`) ON DELETE RESTRICT,
  CONSTRAINT `assistant_bill_origins_ibfk_2` FOREIGN KEY (`bill_id`) REFERENCES `bills` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
