-- PQ-AI training_wide_sample 生产上下文对齐升级审批 SQL
-- 生成日期：2026-07-21
-- 用途：人工训练宽表样本补齐与 ProductionRun 同语义的工厂/车型/颜色字段，
--       使 FACTORY / VEHICLE_MODEL / COLOR 多维验证轴与适用范围派生与生产样本一致。
-- 执行方式：必须由授权 DBA 审批后人工执行；应用、容器、CI 和启动脚本不得运行本文件。
-- 约束：不删除数据、不使用物理外键；旧样本三列为 NULL，需用新模板重新导入后才参与三轴验证。


ALTER TABLE `training_wide_sample`
  ADD COLUMN `factory_id` VARCHAR(36) NULL COMMENT '工厂ID；应用层逻辑引用 factory.id；语义同生产事件' AFTER `group_value`,
  ADD COLUMN `vehicle_model_id` VARCHAR(36) NULL COMMENT '车型ID；应用层逻辑引用 vehicle_model.id；语义同生产事件' AFTER `factory_id`,
  ADD COLUMN `color_id` VARCHAR(36) NULL COMMENT '颜色ID；应用层逻辑引用 color.id；语义同生产事件' AFTER `vehicle_model_id`,
  ADD KEY `idx_training_sample_context` (`factory_id`, `vehicle_model_id`, `color_id`);
