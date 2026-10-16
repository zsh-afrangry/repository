-- KnowledgeMap 表结构（自动生成，请勿手工编辑）
--
-- 生成方式：python backend/scripts/export_schema.py
-- 来源库：  127.0.0.1:3306/knowledgemap
--
-- ⚠️ 本文件由脚本覆盖，手工修改会在下次导出时丢失。
-- ⚠️ 含 DROP TABLE IF EXISTS，**不要**直接对生产库执行；它用于重建空库或核对结构漂移。
--
-- 表结构的权威来源是 `backend/app/models/` 下的 SQLAlchemy 模型
-- （项目刻意不使用 Alembic，决定见 docs/3 §13）。本文件是它的导出快照。
--
-- 已抹平 AUTO_INCREMENT 计数等噪声，使 git diff 只反映真实结构变化。

/*!50503 SET NAMES utf8mb4 */;

/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `assistant_requests`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assistant_requests` (
  `request_key` varchar(128) NOT NULL,
  `payload_hash` varchar(64) NOT NULL,
  `result_json` longtext NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`request_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `assistant_task_origins`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assistant_task_origins` (
  `source_id` varchar(96) NOT NULL,
  `event_id` int NOT NULL,
  `source_json` text NOT NULL,
  `imported_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`source_id`),
  UNIQUE KEY `event_id` (`event_id`),
  CONSTRAINT `assistant_task_origins_ibfk_1` FOREIGN KEY (`event_id`) REFERENCES `calendar_events` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `bills`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bills` (
  `id` int NOT NULL AUTO_INCREMENT,
  `record_type` enum('expense','income') NOT NULL,
  `expense_date` date NOT NULL,
  `expense_time` time DEFAULT NULL,
  `amount` decimal(12,2) NOT NULL,
  `category_id` int DEFAULT NULL,
  `subcategory_id` int DEFAULT NULL,
  `payment_platform_id` int DEFAULT NULL,
  `payment_channel_id` int DEFAULT NULL,
  `fund_type_id` int DEFAULT NULL,
  `reimbursement_status` enum('na','pending','done') NOT NULL,
  `reimbursement_amount` decimal(12,2) DEFAULT NULL,
  `transaction_id` varchar(128) DEFAULT NULL,
  `note` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `transaction_id` (`transaction_id`),
  KEY `category_id` (`category_id`),
  KEY `subcategory_id` (`subcategory_id`),
  KEY `payment_platform_id` (`payment_platform_id`),
  KEY `payment_channel_id` (`payment_channel_id`),
  KEY `fund_type_id` (`fund_type_id`),
  CONSTRAINT `bills_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL,
  CONSTRAINT `bills_ibfk_2` FOREIGN KEY (`subcategory_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL,
  CONSTRAINT `bills_ibfk_3` FOREIGN KEY (`payment_platform_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL,
  CONSTRAINT `bills_ibfk_4` FOREIGN KEY (`payment_channel_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL,
  CONSTRAINT `bills_ibfk_5` FOREIGN KEY (`fund_type_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `calendar_events`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `calendar_events` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '日历事项主键，自增 ID',
  `event_date` date DEFAULT NULL COMMENT '事项日期；NULL 表示未安排/无DDL，不归入日历日期格',
  `event_time` time DEFAULT NULL COMMENT '事项时间；为空表示当天但未指定具体时刻，判定过期时兜底为 23:59:59',
  `title` varchar(128) NOT NULL COMMENT '事项标题，显示在日期详情弹窗中',
  `detail` text COMMENT '事项说明，如待办内容、会议地点等上下文',
  `tone` enum('todo','meeting') NOT NULL COMMENT '事项类型：todo=待做事项，meeting=安排（会议/日程）',
  `completed_at` datetime DEFAULT NULL COMMENT '完成时间；NULL 表示未完成。撤销完成即置回 NULL',
  `archived_at` datetime DEFAULT NULL COMMENT '作废时间；NULL 表示未作废。作废=主动放弃，可恢复',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT (now()) COMMENT '更新时间；通过后端 ORM 更新时刷新',
  `note` text COMMENT '事项备注或无日期条件；不自动解释为事件触发器',
  `version` int NOT NULL DEFAULT '1' COMMENT '网页与助手共享的乐观并发版本',
  PRIMARY KEY (`id`),
  KEY `ix_calendar_events_event_date` (`event_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dashboard 首页日历事项表：存储待做事项（todo）与安排（meeting）';

DROP TABLE IF EXISTS `notes_seed_versions`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notes_seed_versions` (
  `id` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `notes_topics`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notes_topics` (
  `id` varchar(64) NOT NULL,
  `version` int NOT NULL,
  `data` json NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `simulation_records`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `simulation_records` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录唯一标识',
  `mongo_log_id` varchar(50) DEFAULT NULL COMMENT '绑定的 MongoDB 文档主键 ID',
  `user_id` bigint NOT NULL DEFAULT '0' COMMENT '目前暂无多用户,留空或置0',
  `strategy_name` varchar(50) NOT NULL COMMENT '策略标识',
  `symbol` varchar(20) NOT NULL COMMENT '交易标的代码',
  `start_date` date NOT NULL COMMENT '回测起始日',
  `end_date` date NOT NULL COMMENT '回测结束日',
  `data_frequency` varchar(20) NOT NULL DEFAULT 'daily' COMMENT '数据粒度',
  `strategy_params` json DEFAULT NULL COMMENT '动态策略配置参数字典',
  `total_return` decimal(10,4) NOT NULL COMMENT '总收益率',
  `annualized_return` decimal(10,4) NOT NULL DEFAULT (0.0000) COMMENT '年化收益率',
  `max_drawdown` decimal(10,4) NOT NULL COMMENT '最大回撤率',
  `win_rate` decimal(10,4) NOT NULL COMMENT '胜率',
  `total_trades` int NOT NULL COMMENT '交易总笔数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录存储时间',
  PRIMARY KEY (`id`),
  KEY `ix_simulation_records_total_return` (`total_return`),
  KEY `ix_simulation_records_mongo_log_id` (`mongo_log_id`),
  KEY `ix_simulation_records_symbol` (`symbol`),
  KEY `ix_simulation_records_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `tags`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tags` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `type` enum('category','subcategory','payment_platform','payment_channel','fund_type') NOT NULL,
  `parent_id` int DEFAULT NULL,
  `sort_order` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`),
  CONSTRAINT `tags_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
