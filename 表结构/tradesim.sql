/*
  TradeSim integrated storage schema.

  This database remains separate from KnowledgeMap's knowledgemap schema.
  Large arrays are stored in MongoDB tradesim.simulation_logs and linked by
  simulation_records.mongo_log_id.

  Run against a MySQL 8.x instance after reviewing the existing database.
  Do not use this file to drop or overwrite an existing database.
*/

CREATE DATABASE IF NOT EXISTS `tradesim`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `tradesim`;

CREATE TABLE IF NOT EXISTS `simulation_records` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录唯一标识',
  `mongo_log_id` varchar(50) DEFAULT NULL COMMENT 'MongoDB 大对象文档 ID',
  `user_id` bigint NOT NULL DEFAULT 0 COMMENT '当前单用户模式',
  `strategy_name` varchar(50) NOT NULL COMMENT '策略标识',
  `symbol` varchar(20) NOT NULL COMMENT '交易标的代码',
  `start_date` date NOT NULL COMMENT '回测起始日期',
  `end_date` date NOT NULL COMMENT '回测结束日期',
  `data_frequency` varchar(20) NOT NULL DEFAULT 'daily' COMMENT '数据频率',
  `strategy_params` json DEFAULT NULL COMMENT '策略配置快照',
  `total_return` decimal(10,4) NOT NULL COMMENT '总收益率',
  `annualized_return` decimal(10,4) NOT NULL DEFAULT 0.0000 COMMENT '年化收益率',
  `max_drawdown` decimal(10,4) NOT NULL COMMENT '最大回撤率',
  `win_rate` decimal(10,4) NOT NULL COMMENT '胜率',
  `total_trades` int NOT NULL COMMENT '交易总笔数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '保存时间',
  PRIMARY KEY (`id`),
  KEY `idx_simulation_records_mongo_log_id` (`mongo_log_id`),
  KEY `idx_simulation_records_symbol` (`symbol`),
  KEY `idx_simulation_records_total_return` (`total_return`),
  KEY `idx_simulation_records_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='TradeSim 回测记录索引表';
