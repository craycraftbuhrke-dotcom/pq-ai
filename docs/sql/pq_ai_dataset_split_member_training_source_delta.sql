-- PQ-AI dataset_split_member 双训练来源兼容升级审批 SQL
-- 生成日期：2026-07-19
-- 用途：已有数据库从“仅生产样本”升级为“生产样本与人工训练宽表同等有效”。
-- 执行方式：必须由授权 DBA 审批后人工执行；应用、容器、CI 和启动脚本不得运行本文件。
-- 前提：先执行 pq_ai_training_remote_7_tables.sql，确保 training_wide_sample 已存在。
-- 约束：不删除数据、不删除旧索引、不使用物理外键；旧索引可保留用于生产样本快速核对。


ALTER TABLE `dataset_split_member`
  ADD COLUMN `source_type` VARCHAR(24) NULL COMMENT '样本来源：PRODUCTION或MANUAL_UPLOAD' AFTER `dataset_snapshot_id`,
  ADD COLUMN `source_ref` VARCHAR(100) NULL COMMENT '来源内唯一标识' AFTER `source_type`,
  ADD COLUMN `manual_sample_id` VARCHAR(36) NULL COMMENT '人工训练宽表样本ID；应用层逻辑引用 training_wide_sample.id' AFTER `point_feature_snapshot_id`,
  MODIFY COLUMN `point_feature_snapshot_id` VARCHAR(36) NULL COMMENT '生产点位特征快照ID；应用层逻辑引用 point_feature_snapshot.id',
  MODIFY COLUMN `production_run_id` VARCHAR(36) NULL COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  MODIFY COLUMN `measurement_point_id` VARCHAR(36) NULL COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  MODIFY COLUMN `target_measurement_id` VARCHAR(36) NULL COMMENT '目标测量ID；应用层逻辑引用 quality_measurement.id';


UPDATE `dataset_split_member`
SET
  `source_type` = 'PRODUCTION',
  `source_ref` = `point_feature_snapshot_id`
WHERE `source_type` IS NULL OR `source_type` = '';


ALTER TABLE `dataset_split_member`
  MODIFY COLUMN `source_type` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '样本来源：PRODUCTION或MANUAL_UPLOAD',
  MODIFY COLUMN `source_ref` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '来源内唯一标识',
  ADD UNIQUE KEY `uk_dataset_source_member` (`dataset_snapshot_id`, `source_type`, `source_ref`);
