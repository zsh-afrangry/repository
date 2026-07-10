/*
 Navicat Premium Data Transfer

 Source Server         : local_mysql
 Source Server Type    : MySQL
 Source Server Version : 80044 (8.0.44)
 Source Host           : localhost:3306
 Source Schema         : knowledgemap

 Target Server Type    : MySQL
 Target Server Version : 80044
 File Encoding         : 65001

 Date: 05/07/2026
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- KnowledgeMap 数据库说明
-- ============================================================
-- 当前数据库服务于 KnowledgeMap 本地门户，核心包含三类数据：
-- 1. tags：统一标签字典。用于维护账单分类、子分类、支付平台、支付渠道、资金账户等可复用选项。
-- 2. bills：记账模块主表。记录每一笔收入/支出，并通过多个外键引用 tags 中的标签。
-- 3. calendar_events：Dashboard 首页日历事项表。记录某一天的待办、计划、会议或账单提醒。
--
-- 主要关系：
-- - tags.parent_id 自关联 tags.id，用于“大类 -> 小类”的层级关系。
-- - bills.category_id / subcategory_id / payment_platform_id / payment_channel_id / fund_type_id 均引用 tags.id。
-- - calendar_events 当前独立存储首页日程，后续可按需要增加 bill_id 或 project_id 与其他模块关联。

-- ----------------------------
-- Table structure for tags
-- ----------------------------
DROP TABLE IF EXISTS `tags`;
CREATE TABLE `tags`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '标签主键，自增 ID',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标签名称，如餐饮、午饭、支付宝、现金等',
  `type` enum('category','subcategory','payment_platform','payment_channel','fund_type') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标签类型：category=账单大类，subcategory=账单小类，payment_platform=支付平台，payment_channel=支付渠道，fund_type=资金账户/资金类型',
  `parent_id` int NULL DEFAULT NULL COMMENT '父级标签 ID；主要用于 subcategory 指向所属 category',
  `sort_order` int NOT NULL COMMENT '排序权重，数值越小越靠前',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `parent_id`(`parent_id` ASC) USING BTREE,
  CONSTRAINT `tags_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 72 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic COMMENT = '统一标签字典表：维护账单分类、支付方式、资金账户等可复用选项';

-- ----------------------------
-- Table structure for bills
-- ----------------------------
DROP TABLE IF EXISTS `bills`;
CREATE TABLE `bills`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '账单主键，自增 ID',
  `record_type` enum('expense','income') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '记录类型：expense=支出，income=收入',
  `expense_date` date NOT NULL COMMENT '发生日期，按天统计和筛选的主日期字段',
  `expense_time` time NULL DEFAULT NULL COMMENT '发生时间，可为空；用于同一天内排序或记录精确时间',
  `amount` decimal(12, 2) NOT NULL COMMENT '金额，保留 2 位小数',
  `category_id` int NULL DEFAULT NULL COMMENT '账单大类标签 ID，引用 tags.id',
  `subcategory_id` int NULL DEFAULT NULL COMMENT '账单小类标签 ID，引用 tags.id',
  `payment_platform_id` int NULL DEFAULT NULL COMMENT '支付平台标签 ID，如支付宝、微信、银行等，引用 tags.id',
  `payment_channel_id` int NULL DEFAULT NULL COMMENT '支付渠道标签 ID，如花呗、银行卡、余额等，引用 tags.id',
  `fund_type_id` int NULL DEFAULT NULL COMMENT '资金账户/资金类型标签 ID，引用 tags.id',
  `reimbursement_status` enum('na','pending','done') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '报销状态：na=无需报销，pending=待报销，done=已报销',
  `reimbursement_amount` decimal(12, 2) NULL DEFAULT NULL COMMENT '报销金额；无需报销时通常为空',
  `transaction_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '外部交易流水号或导入来源唯一标识，用于避免重复导入',
  `note` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '备注信息',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT (now()) COMMENT '更新时间；通过后端 ORM 更新时刷新',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `transaction_id`(`transaction_id` ASC) USING BTREE,
  INDEX `category_id`(`category_id` ASC) USING BTREE,
  INDEX `subcategory_id`(`subcategory_id` ASC) USING BTREE,
  INDEX `payment_platform_id`(`payment_platform_id` ASC) USING BTREE,
  INDEX `payment_channel_id`(`payment_channel_id` ASC) USING BTREE,
  INDEX `fund_type_id`(`fund_type_id` ASC) USING BTREE,
  CONSTRAINT `bills_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `bills_ibfk_2` FOREIGN KEY (`subcategory_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `bills_ibfk_3` FOREIGN KEY (`payment_platform_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `bills_ibfk_4` FOREIGN KEY (`payment_channel_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `bills_ibfk_5` FOREIGN KEY (`fund_type_id`) REFERENCES `tags` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 31 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic COMMENT = '记账模块主表：记录收入、支出、报销状态和标签维度';

-- ----------------------------
-- Table structure for calendar_events
-- ----------------------------
DROP TABLE IF EXISTS `calendar_events`;
CREATE TABLE `calendar_events`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '日历事项主键，自增 ID',
  `event_date` date NOT NULL COMMENT '事项日期；Dashboard 日历按此字段加载和标记',
  `event_time` time NULL DEFAULT NULL COMMENT '事项时间；为空表示全天或暂未指定具体时间',
  `title` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '事项标题，显示在日期详情弹窗中',
  `detail` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '事项说明，如待办内容、会议地点、计划上下文等',
  `tone` enum('todo','plan','meeting','bill') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '事项类型/视觉语义：todo=待办，plan=计划，meeting=会议，bill=账单提醒',
  `created_at` datetime NOT NULL DEFAULT (now()) COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT (now()) COMMENT '更新时间；通过后端 ORM 更新时刷新',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_calendar_events_event_date`(`event_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic COMMENT = 'Dashboard 首页日历事项表：存储某天的待办、计划、会议和账单提醒';

SET FOREIGN_KEY_CHECKS = 1;
