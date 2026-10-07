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
DROP TABLE IF EXISTS `bills`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bills` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '账单主键，自增 ID',
  `record_type` enum('expense','income') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '记录类型：expense=支出，income=收入',
  `expense_date` date NOT NULL COMMENT '发生日期，按天统计和筛选的主日期字段',
  `expense_time` time DEFAULT NULL COMMENT '发生时间，可为空；用于同一天内排序或记录精确时间',
  `amount` decimal(12,2) NOT NULL COMMENT '金额，保留 2 位小数',
  `category_id` int DEFAULT NULL COMMENT '账单大类标签 ID，引用 tags.id',
  `subcategory_id` int DEFAULT NULL COMMENT '账单小类标签 ID，引用 tags.id',
  `payment_platform_id` int DEFAULT NULL COMMENT '支付平台标签 ID，如支付宝、微信、银行等，引用 tags.id',
  `payment_channel_id` int DEFAULT NULL COMMENT '支付渠道标签 ID，如花呗、银行卡、余额等，引用 tags.id',
  `fund_type_id` int DEFAULT NULL COMMENT '资金账户/资金类型标签 ID，引用 tags.id',
  `reimbursement_status` enum('na','pending','done') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '报销状态：na=无需报销，pending=待报销，done=已报销',
  `reimbursement_amount` decimal(12,2) DEFAULT NULL COMMENT '报销金额；无需报销时通常为空',
  `transaction_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '外部交易流水号或导入来源唯一标识，用于避免重复导入',
  `note` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '备注信息',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT (now()) COMMENT '更新时间；通过后端 ORM 更新时刷新',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='记账模块主表：记录收入、支出、报销状态和标签维度';

DROP TABLE IF EXISTS `calendar_events`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `calendar_events` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '日历事项主键，自增 ID',
  `event_date` date NOT NULL COMMENT '事项日期；Dashboard 日历按此字段加载和标记',
  `event_time` time DEFAULT NULL COMMENT '事项时间；为空表示当天但未指定具体时刻，判定过期时兜底为 23:59:59',
  `title` varchar(128) NOT NULL COMMENT '事项标题，显示在日期详情弹窗中',
  `detail` text COMMENT '事项说明，如待办内容、会议地点等上下文',
  `tone` enum('todo','meeting') NOT NULL COMMENT '事项类型：todo=待做事项，meeting=安排（会议/日程）',
  `completed_at` datetime DEFAULT NULL COMMENT '完成时间；NULL 表示未完成。撤销完成即置回 NULL',
  `archived_at` datetime DEFAULT NULL COMMENT '作废时间；NULL 表示未作废。作废=主动放弃，可恢复',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT (now()) COMMENT '更新时间；通过后端 ORM 更新时刷新',
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
  `mongo_log_id` varchar(50) DEFAULT NULL COMMENT 'MongoDB 大对象文档 ID',
  `user_id` bigint NOT NULL DEFAULT '0' COMMENT '当前单用户模式',
  `strategy_name` varchar(50) NOT NULL COMMENT '策略标识',
  `symbol` varchar(20) NOT NULL COMMENT '交易标的代码',
  `start_date` date NOT NULL COMMENT '回测起始日期',
  `end_date` date NOT NULL COMMENT '回测结束日期',
  `data_frequency` varchar(20) NOT NULL DEFAULT 'daily' COMMENT '数据频率',
  `strategy_params` json DEFAULT NULL COMMENT '策略配置快照',
  `total_return` decimal(10,4) NOT NULL COMMENT '总收益率',
  `annualized_return` decimal(10,4) NOT NULL DEFAULT '0.0000' COMMENT '年化收益率',
  `max_drawdown` decimal(10,4) NOT NULL COMMENT '最大回撤率',
  `win_rate` decimal(10,4) NOT NULL COMMENT '胜率',
  `total_trades` int NOT NULL COMMENT '交易总笔数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '保存时间',
  PRIMARY KEY (`id`),
  KEY `idx_simulation_records_mongo_log_id` (`mongo_log_id`),
  KEY `idx_simulation_records_symbol` (`symbol`),
  KEY `idx_simulation_records_total_return` (`total_return`),
  KEY `idx_simulation_records_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='TradeSim 回测记录索引表';

DROP TABLE IF EXISTS `tags`;

/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tags` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '标签主键，自增 ID',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标签名称，如餐饮、午饭、支付宝、现金等',
  `type` enum('category','subcategory','payment_platform','payment_channel','fund_type') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标签类型：category=账单大类，subcategory=账单小类，payment_platform=支付平台，payment_channel=支付渠道，fund_type=资金账户/资金类型',
  `parent_id` int DEFAULT NULL COMMENT '父级标签 ID；主要用于 subcategory 指向所属 category',
  `sort_order` int NOT NULL COMMENT '排序权重，数值越小越靠前',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`),
  CONSTRAINT `tags_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='统一标签字典表：维护账单分类、支付方式、资金账户等可复用选项';

/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
