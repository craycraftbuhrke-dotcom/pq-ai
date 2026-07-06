-- PQ-AI MySQL 建表总表审批 SQL
-- 生成日期：2026-07-05
-- 用途：提交数据库审批工单后由授权 DBA 人工执行。
-- 范围：仅包含数据表定义；不包含建库语句、物理外键、视图、触发器、存储过程或事件。
-- 规则：应用、Docker、CI、测试和种子脚本不得自动执行本文件。
-- 统计：数据表 90 张；应用层逻辑引用 156 个。


CREATE TABLE `actual_parameter` (
  `production_stage_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产阶段实绩ID；应用层逻辑引用 production_stage_run.id',
  `brush_id` VARCHAR(36) NULL COMMENT '刷子ID；应用层逻辑引用 brush.id',
  `parameter_definition_id` VARCHAR(36) NULL COMMENT '业务字段：parameter_definition_id；应用层逻辑引用 parameter_definition.id',
  `parameter_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '工艺参数编码',
  `actual_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '实际值',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `sampled_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采样时间',
  `source_system` VARCHAR(64) NULL COMMENT '来源系统',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_actual_parameter_stage_code` (`production_stage_run_id`, `parameter_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产阶段实际工艺参数';

CREATE TABLE `api_key` (
  `user_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '用户ID；应用层逻辑引用 app_user.id',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `key_prefix` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '密钥前缀',
  `key_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '密钥哈希',
  `expires_at` TIMESTAMP NULL COMMENT '过期时间',
  `last_used_at` TIMESTAMP NULL COMMENT '最后使用时间',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key_hash` (`key_hash`),
  KEY `idx_api_key_prefix` (`key_prefix`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统集成 API 密钥';

CREATE TABLE `app_user` (
  `username` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '用户名',
  `display_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '显示名称',
  `email` VARCHAR(200) NULL COMMENT '邮箱',
  `department` VARCHAR(120) NULL COMMENT '部门',
  `password_hash` VARCHAR(255) NULL COMMENT '密码哈希',
  `password_changed_at` TIMESTAMP NULL COMMENT '密码修改时间',
  `failed_login_count` INT NOT NULL DEFAULT 0 COMMENT '登录失败次数',
  `locked_until` TIMESTAMP NULL COMMENT '锁定到期时间',
  `last_login_at` TIMESTAMP NULL COMMENT '最后登录时间',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统用户账号';

CREATE TABLE `audit_log` (
  `request_id` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '请求ID',
  `actor_user_id` VARCHAR(36) NULL COMMENT '操作用户ID；应用层逻辑引用 app_user.id',
  `actor_username` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '操作用户名',
  `action_type` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '操作动作',
  `http_method` VARCHAR(12) NOT NULL DEFAULT '' COMMENT 'HTTP方法',
  `path` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '请求路径',
  `resource_type` VARCHAR(100) NULL COMMENT '资源类型',
  `resource_id` VARCHAR(100) NULL COMMENT '资源ID',
  `status_code` INT NOT NULL DEFAULT 0 COMMENT '状态码',
  `client_ip` VARCHAR(64) NULL COMMENT '客户端IP',
  `detail` JSON NULL COMMENT '明细JSON',
  `occurred_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发生时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  PRIMARY KEY (`id`),
  KEY `idx_audit_actor_time` (`actor_user_id`, `occurred_at`),
  KEY `idx_audit_resource` (`resource_type`, `resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='业务写操作审计日志';

CREATE TABLE `brush` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `brush_no` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '刷子号',
  `brush_table_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '刷子表号',
  `spray_position` VARCHAR(120) NULL COMMENT '喷涂位置',
  `part_id` VARCHAR(36) NULL COMMENT '零件ID；应用层逻辑引用 part.id',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_brush_no` (`program_version_id`, `brush_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喷涂刷子号与刷子表行';

CREATE TABLE `brush_parameter` (
  `brush_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '刷子ID；应用层逻辑引用 brush.id',
  `parameter_definition_id` VARCHAR(36) NULL COMMENT '业务字段：parameter_definition_id；应用层逻辑引用 parameter_definition.id',
  `parameter_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '工艺参数编码',
  `parameter_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '工艺参数名称',
  `configured_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '配置值',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `soft_min` DECIMAL(18,6) NULL COMMENT '软下限',
  `soft_max` DECIMAL(18,6) NULL COMMENT '软上限',
  `hard_min` DECIMAL(18,6) NULL COMMENT '硬下限',
  `hard_max` DECIMAL(18,6) NULL COMMENT '硬上限',
  `is_recommendable` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '业务字段：is_recommendable',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brush_parameter` (`brush_id`, `parameter_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='刷子配置工艺参数';

CREATE TABLE `brush_point_contribution` (
  `brush_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '刷子ID；应用层逻辑引用 brush.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `overlap_ratio` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：overlap_ratio',
  `contribution_weight` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：contribution_weight',
  `source` VARCHAR(32) NOT NULL DEFAULT 'EXPERT' COMMENT '来源',
  `version` VARCHAR(32) NOT NULL DEFAULT '1.0' COMMENT '版本号',
  `is_approved` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_approved',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brush_point` (`brush_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='刷子到测量点贡献权重';

CREATE TABLE `closed_loop_evaluation` (
  `recommendation_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '推荐ID；应用层逻辑引用 recommendation.id',
  `baseline_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：baseline_value',
  `verified_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：verified_value',
  `actual_improvement` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：actual_improvement',
  `is_effective` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_effective',
  `verified_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：verified_at',
  `verified_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：verified_by',
  `conclusion` TEXT NULL COMMENT '业务字段：conclusion',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_evaluation` (`recommendation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 闭环复测评价';

CREATE TABLE `color` (
  `code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `color_type` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '颜色类型',
  `feature_values` JSON NULL COMMENT '特征值JSON',
  `supplier` VARCHAR(120) NULL COMMENT '供应商',
  `tds_uri` VARCHAR(500) NULL COMMENT 'TDS文件URI',
  `msds_uri` VARCHAR(500) NULL COMMENT 'MSDS文件URI',
  `coa_uri` VARCHAR(500) NULL COMMENT 'COA文件URI',
  `doe_uri` VARCHAR(500) NULL COMMENT 'DOE文件URI',
  `digital_standard` JSON NULL COMMENT '数字化标准JSON',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='色漆和中涂颜色主数据';

CREATE TABLE `contribution_validation` (
  `contribution_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：contribution_version_id；应用层逻辑引用 point_contribution_version.id',
  `study_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：study_no',
  `target_family` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：target_family',
  `method_code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '方法',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `sample_count` INT NULL COMMENT '业务字段：sample_count',
  `validation_score` DECIMAL(18,6) NULL COMMENT '业务字段：validation_score',
  `evidence_uri` VARCHAR(500) NULL COMMENT '证据URI',
  `evidence_payload` JSON NULL COMMENT '证据载荷',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_contrib_val_study` (`contribution_version_id`, `study_no`),
  KEY `idx_contrib_val_status` (`contribution_version_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='点位贡献验证研究';

CREATE TABLE `controlled_trial` (
  `recommendation_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '推荐ID；应用层逻辑引用 recommendation.id',
  `trial_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '试验编号',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `evidence_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '证据类型',
  `plan_document` JSON NULL COMMENT '计划阶段文档JSON：hypothesis/expected_outcome/risk_assessment/rollback_plan/sustained_observation_plan',
  `constraint_evidence` JSON NULL COMMENT '业务字段：constraint_evidence',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PLANNED' COMMENT '状态',
  `requested_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '申请人',
  `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `execution_document` JSON NULL COMMENT '执行阶段文档JSON：approval_comment/completion_summary',
  `started_at` TIMESTAMP NULL COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL COMMENT '完成时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_controlled_trial_no` (`trial_no`),
  UNIQUE KEY `uk_trial_recommendation` (`recommendation_id`),
  KEY `idx_controlled_trial_status` (`row_status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='受控试验计划与审批';

CREATE TABLE `dataset_snapshot` (
  `dataset_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：dataset_code',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `feature_set_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：feature_set_version',
  `split_strategy` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：split_strategy',
  `group_key` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：group_key',
  `holdout_ratio` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：holdout_ratio',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'BUILT' COMMENT '状态',
  `sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：sample_count',
  `group_count` INT NOT NULL DEFAULT 0 COMMENT '编组数量',
  `train_sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：train_sample_count',
  `validation_sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：validation_sample_count',
  `train_group_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：train_group_count',
  `validation_group_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：validation_group_count',
  `cutoff_at` TIMESTAMP NULL COMMENT '业务字段：cutoff_at',
  `feature_names` JSON NULL COMMENT '业务字段：feature_names',
  `lineage` JSON NULL COMMENT '血缘JSON',
  `leakage_check` JSON NULL COMMENT '业务字段：leakage_check',
  `built_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：built_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_snapshot_version` (`dataset_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 训练数据集快照';

CREATE TABLE `dataset_split_member` (
  `dataset_snapshot_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '数据集快照ID；应用层逻辑引用 dataset_snapshot.id',
  `point_feature_snapshot_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：point_feature_snapshot_id；应用层逻辑引用 point_feature_snapshot.id',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `target_measurement_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '目标测量ID；应用层逻辑引用 quality_measurement.id',
  `group_value` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '编组值',
  `split` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '业务字段：split',
  `target_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '目标值',
  `feature_values` JSON NULL COMMENT '特征值JSON',
  `occurred_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发生时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_feature_snapshot` (`dataset_snapshot_id`, `point_feature_snapshot_id`),
  KEY `idx_dataset_split_group` (`dataset_snapshot_id`, `split`, `group_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='数据集训练验证成员';

CREATE TABLE `diagnosis_result` (
  `prediction_result_id` VARCHAR(36) NULL COMMENT '预测结果ID；应用层逻辑引用 prediction_result.id',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `summary` TEXT NULL COMMENT '业务字段：summary',
  `factor_contributions` JSON NULL COMMENT '业务字段：factor_contributions',
  `confidence` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：confidence',
  `causality_status` VARCHAR(24) NOT NULL DEFAULT 'CORRELATION_ONLY' COMMENT '业务字段：causality_status',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 质量诊断结果';

CREATE TABLE `durr_application_controller` (
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `model` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '模型',
  `serial_no` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '业务字段：serial_no',
  `software_version` VARCHAR(80) NULL COMMENT '业务字段：software_version',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_serial_no` (`serial_no`),
  UNIQUE KEY `uk_factory_durr_controller` (`factory_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dürr 应用控制器主数据';

CREATE TABLE `durr_robot` (
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `model` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '模型',
  `serial_no` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '业务字段：serial_no',
  `controller_software_version` VARCHAR(80) NULL COMMENT '业务字段：controller_software_version',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_serial_no` (`serial_no`),
  UNIQUE KEY `uk_factory_durr_robot` (`factory_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dürr 机器人主数据';

CREATE TABLE `durr_rotary_atomizer` (
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `controller_id` VARCHAR(36) NULL COMMENT '业务字段：controller_id；应用层逻辑引用 durr_application_controller.id',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `model` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '模型',
  `serial_no` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '业务字段：serial_no',
  `bell_cup_type` VARCHAR(120) NULL COMMENT '业务字段：bell_cup_type',
  `bell_cup_code` VARCHAR(120) NULL COMMENT '业务字段：bell_cup_code',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_serial_no` (`serial_no`),
  UNIQUE KEY `uk_factory_durr_atomizer` (`factory_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dürr 高压静电旋杯主数据';

CREATE TABLE `eng_knowledge_entry` (
  `entry_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：entry_code',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `title` VARCHAR(180) NOT NULL DEFAULT '' COMMENT '业务字段：title',
  `category` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：category',
  `target_quality_type` VARCHAR(32) NULL COMMENT '目标质量类型',
  `metric_code` VARCHAR(64) NULL COMMENT '质量指标编码',
  `symptom_pattern` TEXT NULL COMMENT '业务字段：symptom_pattern',
  `diagnosis_rule` TEXT NULL COMMENT '业务字段：diagnosis_rule',
  `recommended_checks` JSON NULL COMMENT '业务字段：recommended_checks',
  `related_parameters` JSON NULL COMMENT '业务字段：related_parameters',
  `evidence_level` VARCHAR(32) NOT NULL DEFAULT 'RULE' COMMENT '业务字段：evidence_level',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `created_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '创建人',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_eng_knowledge_entry` (`entry_code`, `version`),
  KEY `idx_eng_knowledge_target` (`target_quality_type`, `metric_code`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工程诊断经验知识库';

CREATE TABLE `factory` (
  `code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `site_owner` VARCHAR(80) NULL COMMENT '业务字段：site_owner',
  `remark` TEXT NULL COMMENT '备注',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工厂主数据';

CREATE TABLE `factory_vehicle_model` (
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_vehicle_model` (`factory_id`, `vehicle_model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工厂车型适用关系';

CREATE TABLE `file_import_job` (
  `import_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：import_no',
  `profile_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：profile_id；应用层逻辑引用 file_import_profile.id',
  `domain_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：domain_type',
  `source_filename` VARCHAR(240) NOT NULL DEFAULT '' COMMENT '业务字段：source_filename',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `source_checksum` VARCHAR(128) NULL COMMENT '业务字段：source_checksum',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PREVIEWED' COMMENT '状态',
  `row_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：row_count',
  `valid_row_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：valid_row_count',
  `failed_row_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：failed_row_count',
  `preview_payload` JSON NULL COMMENT '业务字段：preview_payload',
  `error_report` JSON NULL COMMENT '业务字段：error_report',
  `submitted_by` VARCHAR(80) NOT NULL DEFAULT 'system' COMMENT '提交人',
  `submitted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `imported_at` TIMESTAMP NULL COMMENT '业务字段：imported_at',
  `replay_of_job_id` VARCHAR(36) NULL COMMENT '业务字段：replay_of_job_id；应用层逻辑引用 file_import_job.id',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_import_job_no` (`import_no`),
  KEY `idx_file_import_job_status` (`domain_type`, `row_status`, `submitted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='外部文件导入任务';

CREATE TABLE `file_import_profile` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `domain_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：domain_type',
  `parser_type` VARCHAR(32) NOT NULL DEFAULT 'CSV' COMMENT '业务字段：parser_type',
  `target_resource` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：target_resource',
  `field_mapping` JSON NULL COMMENT '业务字段：field_mapping',
  `required_fields` JSON NULL COMMENT '业务字段：required_fields',
  `validation_rules` JSON NULL COMMENT '业务字段：validation_rules',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_import_profile` (`code`, `version`),
  KEY `idx_file_import_profile_domain` (`domain_type`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='外部文件导入映射模板';

CREATE TABLE `integration_endpoint` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `system_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：system_type',
  `direction` VARCHAR(24) NOT NULL DEFAULT 'INBOUND' COMMENT '业务字段：direction',
  `base_url` VARCHAR(500) NULL COMMENT '业务字段：base_url',
  `auth_type` VARCHAR(32) NOT NULL DEFAULT 'API_KEY' COMMENT '业务字段：auth_type',
  `config` JSON NULL COMMENT '业务字段：config',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `last_success_at` TIMESTAMP NULL COMMENT '业务字段：last_success_at',
  `last_failure_at` TIMESTAMP NULL COMMENT '业务字段：last_failure_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='外部系统集成端点';

CREATE TABLE `integration_event` (
  `event_no` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '事件编号',
  `endpoint_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '集成端点ID；应用层逻辑引用 integration_endpoint.id',
  `source_event_id` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '来源事件ID',
  `event_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '事件类型',
  `direction` VARCHAR(24) NOT NULL DEFAULT 'INBOUND' COMMENT '业务字段：direction',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  `payload` JSON NULL COMMENT '载荷',
  `mapped_payload` JSON NULL COMMENT '业务字段：mapped_payload',
  `attempt_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：attempt_count',
  `max_attempts` INT NOT NULL DEFAULT 3 COMMENT '业务字段：max_attempts',
  `next_retry_at` TIMESTAMP NULL COMMENT '业务字段：next_retry_at',
  `last_error` TEXT NULL COMMENT '业务字段：last_error',
  `processed_at` TIMESTAMP NULL COMMENT '业务字段：processed_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_event_no` (`event_no`),
  UNIQUE KEY `uk_endpoint_source_event` (`endpoint_id`, `source_event_id`),
  KEY `idx_integration_status_time` (`row_status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='集成事件收件箱';

CREATE TABLE `mat_char_applicability` (
  `characteristic_definition_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：characteristic_definition_id；应用层逻辑引用 mat_char_definition.id',
  `material_type` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '材料类型',
  `process_stage` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '喷涂执行阶段',
  `target_family` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：target_family',
  `is_required` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_required',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mat_char_applicability` (`characteristic_definition_id`, `material_type`, `process_stage`, `target_family`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料特性适用工艺与质量目标';

CREATE TABLE `mat_char_definition` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `category` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：category',
  `canonical_unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '业务字段：canonical_unit',
  `target_families` JSON NULL COMMENT '业务字段：target_families',
  `is_model_feature` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '业务字段：is_model_feature',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `description` TEXT NULL COMMENT '描述',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料特性定义';

CREATE TABLE `material_batch` (
  `batch_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '批次号',
  `material_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '材料编码',
  `material_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '材料名称',
  `material_type` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '材料类型',
  `supplier` VARCHAR(120) NULL COMMENT '供应商',
  `viscosity` DECIMAL(18,6) NULL COMMENT '粘度',
  `solid_ratio` DECIMAL(18,6) NULL COMMENT '固含比',
  `coa_values` JSON NULL COMMENT '业务字段：coa_values',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_batch_no` (`batch_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料批次主数据';

CREATE TABLE `material_batch_test_result` (
  `result_no` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '结果编号',
  `material_batch_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '材料批次ID；应用层逻辑引用 material_batch.id',
  `characteristic_definition_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：characteristic_definition_id；应用层逻辑引用 mat_char_definition.id',
  `method_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '方法ID；应用层逻辑引用 material_test_method.id',
  `specification_id` VARCHAR(36) NULL COMMENT '业务字段：specification_id；应用层逻辑引用 material_specification.id',
  `result_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '结果值',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `tested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：tested_at',
  `tested_by` VARCHAR(80) NULL COMMENT '业务字段：tested_by',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `raw_values` JSON NULL COMMENT '业务字段：raw_values',
  `reliability_status` VARCHAR(24) NOT NULL DEFAULT 'UNVERIFIED' COMMENT '业务字段：reliability_status',
  `reliability_issues` JSON NULL COMMENT '业务字段：reliability_issues',
  `is_within_spec` INT UNSIGNED NULL COMMENT '业务字段：is_within_spec',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_result_no` (`result_no`),
  KEY `idx_mat_result_batch_char_time` (`material_batch_id`, `characteristic_definition_id`, `tested_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料批次检测结果';

CREATE TABLE `material_specification` (
  `material_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '材料编码',
  `characteristic_definition_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：characteristic_definition_id；应用层逻辑引用 mat_char_definition.id',
  `method_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '方法ID；应用层逻辑引用 material_test_method.id',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `lower_limit` DECIMAL(18,6) NULL COMMENT '下限',
  `upper_limit` DECIMAL(18,6) NULL COMMENT '上限',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `effective_from` TIMESTAMP NULL COMMENT '业务字段：effective_from',
  `effective_to` TIMESTAMP NULL COMMENT '业务字段：effective_to',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mat_spec_ver` (`material_code`, `characteristic_definition_id`, `method_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料规格上下限';

CREATE TABLE `material_test_method` (
  `characteristic_definition_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：characteristic_definition_id；应用层逻辑引用 mat_char_definition.id',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `method_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '方法类型',
  `result_unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '业务字段：result_unit',
  `procedure_uri` VARCHAR(500) NULL COMMENT '业务字段：procedure_uri',
  `conditions` JSON NULL COMMENT '业务字段：conditions',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_material_test_method_version` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='材料检测方法版本';

CREATE TABLE `measurement_calibration_record` (
  `calibration_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '校准编号',
  `instrument_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量仪器ID；应用层逻辑引用 measurement_instrument.id',
  `method_id` VARCHAR(36) NULL COMMENT '方法ID；应用层逻辑引用 measurement_method.id',
  `reference_standard_id` VARCHAR(36) NULL COMMENT '参考标准件ID；应用层逻辑引用 measurement_reference_standard.id',
  `calibrated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：calibrated_at',
  `valid_until` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：valid_until',
  `result` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '结果',
  `performed_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：performed_by',
  `certificate_uri` VARCHAR(500) NULL COMMENT '业务字段：certificate_uri',
  `check_values` JSON NULL COMMENT '业务字段：check_values',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_calibration_no` (`calibration_no`),
  KEY `idx_calibration_instrument_time` (`instrument_id`, `calibrated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量仪器校准记录';

CREATE TABLE `measurement_group` (
  `code` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `expected_point_count` INT NULL COMMENT '业务字段：expected_point_count',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_model_code` (`vehicle_model_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量编组';

CREATE TABLE `measurement_group_point` (
  `measurement_group_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量编组ID；应用层逻辑引用 measurement_group.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `sequence_no` INT NOT NULL DEFAULT 0 COMMENT '顺序号',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_point` (`measurement_group_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量编组点位关系';

CREATE TABLE `measurement_import_profile` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `instrument_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '仪器类型',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `schema_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：schema_version',
  `field_mapping` JSON NULL COMMENT '业务字段：field_mapping',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_meas_import_profile_ver` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量文件导入模板';

CREATE TABLE `measurement_instrument` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `manufacturer` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：manufacturer',
  `model` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '模型',
  `instrument_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '仪器类型',
  `serial_no` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '业务字段：serial_no',
  `firmware_version` VARCHAR(64) NULL COMMENT '业务字段：firmware_version',
  `supported_quality_types` JSON NULL COMMENT '业务字段：supported_quality_types',
  `calibration_required` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '业务字段：calibration_required',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_serial_no` (`serial_no`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量仪器主数据';

CREATE TABLE `measurement_method` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `instrument_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '仪器类型',
  `method_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '方法类型',
  `probe_code` VARCHAR(64) NULL COMMENT '探头编码',
  `substrate_type` VARCHAR(80) NULL COMMENT '业务字段：substrate_type',
  `geometry_class` VARCHAR(80) NULL COMMENT '业务字段：geometry_class',
  `layer_scope` VARCHAR(80) NULL COMMENT '业务字段：layer_scope',
  `requires_reference` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：requires_reference',
  `requires_direction` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：requires_direction',
  `minimum_repeats` INT NOT NULL DEFAULT 1 COMMENT '业务字段：minimum_repeats',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `instructions` TEXT NULL COMMENT '业务字段：instructions',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_method_version` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量方法版本';

CREATE TABLE `measurement_msa_study` (
  `study_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：study_no',
  `instrument_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量仪器ID；应用层逻辑引用 measurement_instrument.id',
  `probe_id` VARCHAR(36) NULL COMMENT '探头ID；应用层逻辑引用 measurement_probe.id',
  `method_id` VARCHAR(36) NULL COMMENT '方法ID；应用层逻辑引用 measurement_method.id',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `study_type` VARCHAR(32) NOT NULL DEFAULT 'GRR' COMMENT '业务字段：study_type',
  `sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：sample_count',
  `operator_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：operator_count',
  `repeat_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：repeat_count',
  `grr_percent` DECIMAL(18,6) NULL COMMENT '业务字段：grr_percent',
  `ndc` DECIMAL(18,6) NULL COMMENT '业务字段：ndc',
  `result` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '结果',
  `study_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：study_at',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `raw_results` JSON NULL COMMENT '业务字段：raw_results',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_msa_study` (`study_no`),
  KEY `idx_measurement_msa_status` (`instrument_id`, `result`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量系统分析研究';

CREATE TABLE `measurement_point` (
  `code` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `part_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '零件ID；应用层逻辑引用 part.id',
  `point_type` VARCHAR(32) NOT NULL DEFAULT 'QUALITY' COMMENT '点位类型',
  `region` VARCHAR(80) NULL COMMENT '业务字段：region',
  `quality_types` JSON NULL COMMENT '业务字段：quality_types',
  `is_match_point` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_match_point',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_point_model_code` (`vehicle_model_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量点主数据';

CREATE TABLE `measurement_probe` (
  `instrument_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量仪器ID；应用层逻辑引用 measurement_instrument.id',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `probe_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '探头类型',
  `serial_no` VARCHAR(120) NULL COMMENT '业务字段：serial_no',
  `substrate_type` VARCHAR(80) NULL COMMENT '业务字段：substrate_type',
  `geometry_class` VARCHAR(80) NULL COMMENT '业务字段：geometry_class',
  `layer_scope` VARCHAR(80) NULL COMMENT '业务字段：layer_scope',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `valid_from` TIMESTAMP NULL COMMENT '业务字段：valid_from',
  `valid_until` TIMESTAMP NULL COMMENT '业务字段：valid_until',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_instrument_probe_code` (`instrument_id`, `code`),
  KEY `idx_measurement_probe_status` (`instrument_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量探头主数据';

CREATE TABLE `measurement_reference_standard` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `serial_no` VARCHAR(120) NULL COMMENT '业务字段：serial_no',
  `certificate_no` VARCHAR(120) NULL COMMENT '业务字段：certificate_no',
  `valid_from` TIMESTAMP NULL COMMENT '业务字段：valid_from',
  `valid_until` TIMESTAMP NULL COMMENT '业务字段：valid_until',
  `reference_values` JSON NULL COMMENT '业务字段：reference_values',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量参考标准件';

CREATE TABLE `measurement_repeat_reading` (
  `measurement_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量ID；应用层逻辑引用 quality_measurement.id',
  `repeat_no` INT NOT NULL DEFAULT 0 COMMENT '业务字段：repeat_no',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `raw_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '原始值',
  `corrected_value` DECIMAL(18,6) NULL COMMENT '修正值',
  `unit` VARCHAR(24) NULL COMMENT '单位',
  `is_valid` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否有效',
  `invalid_reason` VARCHAR(240) NULL COMMENT '业务字段：invalid_reason',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_repeat_metric` (`measurement_id`, `repeat_no`, `metric_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量重复读数';

CREATE TABLE `model_acceptance_decision` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `dataset_snapshot_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '数据集快照ID；应用层逻辑引用 dataset_snapshot.id',
  `decision` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '业务字段：decision',
  `criteria` JSON NULL COMMENT '业务字段：criteria',
  `checks` JSON NULL COMMENT '业务字段：checks',
  `decided_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：decided_by',
  `decided_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：decided_at',
  `comment` TEXT NULL COMMENT '协作记录',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_model_accept_decision_time` (`model_version_id`, `decided_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型人工验收决策';

CREATE TABLE `model_acceptance_policy` (
  `policy_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：policy_code',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `policy_type` VARCHAR(24) NOT NULL DEFAULT 'FACTORY_APPROVED' COMMENT '业务字段：policy_type',
  `max_validation_rmse` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：max_validation_rmse',
  `min_validation_r2` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：min_validation_r2',
  `min_train_groups` INT NOT NULL DEFAULT 0 COMMENT '业务字段：min_train_groups',
  `min_validation_groups` INT NOT NULL DEFAULT 0 COMMENT '业务字段：min_validation_groups',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '来源文件URI',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_accept_policy_ver` (`policy_code`, `version`),
  KEY `idx_model_accept_policy_match` (`factory_id`, `target_metric`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工厂模型验收策略';

CREATE TABLE `model_applicability_scope` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '颜色ID；应用层逻辑引用 color.id',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  `source` VARCHAR(32) NOT NULL DEFAULT 'DATASET_DERIVED' COMMENT '来源',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_applicability_context` (`model_version_id`, `factory_id`, `vehicle_model_id`, `color_id`),
  KEY `idx_model_applicability_status` (`model_version_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型适用范围';

CREATE TABLE `model_artifact` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `artifact_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：artifact_type',
  `artifact_uri` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '业务字段：artifact_uri',
  `storage_backend` VARCHAR(32) NOT NULL DEFAULT 'MYSQL' COMMENT '业务字段：storage_backend',
  `payload_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：payload_hash',
  `metadata_payload` JSON NULL COMMENT '业务字段：metadata_payload',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'REGISTERED' COMMENT '状态',
  `created_by` VARCHAR(80) NOT NULL DEFAULT 'system' COMMENT '创建人',
  `registered_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：registered_at',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_artifact_type` (`model_version_id`, `artifact_type`),
  KEY `idx_model_artifact_status` (`model_version_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型制品登记';

CREATE TABLE `model_explanation` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `prediction_result_id` VARCHAR(36) NULL COMMENT '预测结果ID；应用层逻辑引用 prediction_result.id',
  `explanation_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：explanation_type',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `feature_impacts` JSON NULL COMMENT '业务字段：feature_impacts',
  `sensitivity_grid` JSON NULL COMMENT '业务字段：sensitivity_grid',
  `uncertainty` JSON NULL COMMENT '业务字段：uncertainty',
  `generated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：generated_at',
  `generated_by` VARCHAR(80) NOT NULL DEFAULT 'system' COMMENT '业务字段：generated_by',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_model_explanation_target` (`model_version_id`, `explanation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型解释与敏感性分析';

CREATE TABLE `model_ood_policy` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `max_abs_standardized_shift` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：max_abs_standardized_shift',
  `max_outlier_feature_ratio` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：max_outlier_feature_ratio',
  `min_feature_completeness` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：min_feature_completeness',
  `action_type` VARCHAR(24) NOT NULL DEFAULT 'BLOCK' COMMENT '操作动作',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_ood_policy_version` (`model_version_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型分布外检测策略';

CREATE TABLE `model_validation_fold` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `dataset_snapshot_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '数据集快照ID；应用层逻辑引用 dataset_snapshot.id',
  `validation_axis` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '业务字段：validation_axis',
  `fold_key` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '业务字段：fold_key',
  `train_sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：train_sample_count',
  `validation_sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：validation_sample_count',
  `train_group_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：train_group_count',
  `validation_group_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：validation_group_count',
  `metrics` JSON NULL COMMENT '业务字段：metrics',
  `row_status` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '状态',
  `evaluated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：evaluated_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_validation_fold` (`model_version_id`, `validation_axis`, `fold_key`),
  KEY `idx_model_validation_axis` (`model_version_id`, `validation_axis`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模型验证折与指标';

CREATE TABLE `model_version` (
  `model_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '模型编码',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `model_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '模型类型',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `feature_set_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：feature_set_version',
  `artifact_uri` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '业务字段：artifact_uri',
  `dataset_snapshot_id` VARCHAR(36) NULL COMMENT '数据集快照ID；应用层逻辑引用 dataset_snapshot.id',
  `model_payload` JSON NULL COMMENT '模型载荷',
  `evaluation_metrics` JSON NULL COMMENT '业务字段：evaluation_metrics',
  `training_sample_count` INT NOT NULL DEFAULT 0 COMMENT '业务字段：training_sample_count',
  `trained_at` TIMESTAMP NULL COMMENT '业务字段：trained_at',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_version` (`model_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 模型版本';

CREATE TABLE `parameter_constraint_source` (
  `parameter_definition_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：parameter_definition_id；应用层逻辑引用 parameter_definition.id',
  `factory_id` VARCHAR(36) NULL COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `process_stage` VARCHAR(32) NULL COMMENT '喷涂执行阶段',
  `constraint_code` VARCHAR(96) NOT NULL DEFAULT '' COMMENT '业务字段：constraint_code',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `source_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '来源类型',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `lower_limit` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '下限',
  `upper_limit` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '上限',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `effective_from` TIMESTAMP NULL COMMENT '业务字段：effective_from',
  `effective_to` TIMESTAMP NULL COMMENT '业务字段：effective_to',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_param_constraint_code` (`constraint_code`),
  KEY `idx_param_constraint_lookup` (`parameter_definition_id`, `factory_id`, `process_stage`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='参数推荐约束来源';

CREATE TABLE `parameter_definition` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `category` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：category',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `aggregation_method` VARCHAR(32) NOT NULL DEFAULT 'WEIGHTED_AVERAGE' COMMENT '业务字段：aggregation_method',
  `hard_min` DECIMAL(18,6) NULL COMMENT '硬下限',
  `hard_max` DECIMAL(18,6) NULL COMMENT '硬上限',
  `is_recommendable` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '业务字段：is_recommendable',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喷涂参数定义';

CREATE TABLE `part` (
  `code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `material` VARCHAR(80) NULL COMMENT '材料',
  `region` VARCHAR(80) NULL COMMENT '业务字段：region',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='车身零件主数据';

CREATE TABLE `path_segment_execution` (
  `device_execution_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '设备执行ID；应用层逻辑引用 production_device_execution.id',
  `path_segment_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：path_segment_id；应用层逻辑引用 trajectory_path_segment.id',
  `actual_speed` DECIMAL(18,6) NULL COMMENT '业务字段：actual_speed',
  `speed_unit` VARCHAR(24) NULL COMMENT '业务字段：speed_unit',
  `trigger_state` VARCHAR(24) NULL COMMENT '业务字段：trigger_state',
  `actual_values` JSON NULL COMMENT '业务字段：actual_values',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_path_segment_execution` (`device_execution_id`, `path_segment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='路径段实际执行记录';

CREATE TABLE `permission` (
  `code` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `description` TEXT NULL COMMENT '描述',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统权限定义';

CREATE TABLE `point_contribution_entry` (
  `contribution_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：contribution_version_id；应用层逻辑引用 point_contribution_version.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `brush_id` VARCHAR(36) NULL COMMENT '刷子ID；应用层逻辑引用 brush.id',
  `path_segment_id` VARCHAR(36) NULL COMMENT '业务字段：path_segment_id；应用层逻辑引用 trajectory_path_segment.id',
  `source_key` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '业务字段：source_key',
  `overlap_ratio` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：overlap_ratio',
  `contribution_weight` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：contribution_weight',
  `validation_score` DECIMAL(18,6) NULL COMMENT '业务字段：validation_score',
  `evidence` JSON NULL COMMENT '证据',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ver_point_contrib_src` (`contribution_version_id`, `measurement_point_id`, `source_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='点位贡献版本明细';

CREATE TABLE `point_contribution_version` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `target_family` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：target_family',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `method_code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '方法',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `evidence_uri` VARCHAR(500) NULL COMMENT '证据URI',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prog_target_contrib_ver` (`program_version_id`, `target_family`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='点位贡献版本';

CREATE TABLE `point_feature_snapshot` (
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `feature_set_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：feature_set_version',
  `target_family` VARCHAR(32) NOT NULL DEFAULT 'ORANGE_PEEL' COMMENT '业务字段：target_family',
  `feature_values` JSON NULL COMMENT '特征值JSON',
  `lineage` JSON NULL COMMENT '血缘JSON',
  `completeness_score` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：completeness_score',
  `generated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：generated_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_point_feature_ver` (`production_run_id`, `measurement_point_id`, `feature_set_version`, `target_family`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量点特征快照';

CREATE TABLE `prediction_result` (
  `model_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '模型版本ID；应用层逻辑引用 model_version.id',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `predicted_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：predicted_value',
  `lower_bound` DECIMAL(18,6) NULL COMMENT '业务字段：lower_bound',
  `upper_bound` DECIMAL(18,6) NULL COMMENT '业务字段：upper_bound',
  `confidence` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：confidence',
  `applicability_status` VARCHAR(24) NOT NULL DEFAULT 'LEGACY_UNGOVERNED' COMMENT '业务字段：applicability_status',
  `ood_status` VARCHAR(24) NOT NULL DEFAULT 'LEGACY_UNGOVERNED' COMMENT '业务字段：ood_status',
  `governance_evidence` JSON NULL COMMENT '业务字段：governance_evidence',
  `predicted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：predicted_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_prediction_run_point` (`production_run_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 质量预测结果';

CREATE TABLE `process_route` (
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `route_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '路线编码',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `route_type` VARCHAR(24) NOT NULL DEFAULT '3C3B' COMMENT '路线类型',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `bake_strategy` VARCHAR(120) NULL COMMENT '业务字段：bake_strategy',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `effective_from` TIMESTAMP NULL COMMENT '业务字段：effective_from',
  `effective_to` TIMESTAMP NULL COMMENT '业务字段：effective_to',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_process_route_ver` (`factory_id`, `route_code`, `version`),
  KEY `idx_process_route_status` (`factory_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='3C3B 工艺路线版本';

CREATE TABLE `process_route_applicability` (
  `process_route_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：process_route_id；应用层逻辑引用 process_route.id',
  `vehicle_model_id` VARCHAR(36) NULL COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NULL COMMENT '颜色ID；应用层逻辑引用 color.id',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_route_model_color` (`process_route_id`, `vehicle_model_id`, `color_id`),
  KEY `idx_route_applicability_status` (`process_route_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工艺路线适用车型颜色';

CREATE TABLE `process_route_step` (
  `process_route_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：process_route_id；应用层逻辑引用 process_route.id',
  `sequence_no` INT NOT NULL DEFAULT 0 COMMENT '顺序号',
  `step_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '步骤编码',
  `step_name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '步骤名称',
  `step_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '步骤类型',
  `coating_system` VARCHAR(32) NULL COMMENT '业务字段：coating_system',
  `process_stage` VARCHAR(32) NULL COMMENT '喷涂执行阶段',
  `station_code` VARCHAR(64) NULL COMMENT '站点编号',
  `upstream_step_code` VARCHAR(64) NULL COMMENT '业务字段：upstream_step_code',
  `downstream_step_code` VARCHAR(64) NULL COMMENT '业务字段：downstream_step_code',
  `is_ai_feature_source` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_ai_feature_source',
  `control_requirements` JSON NULL COMMENT '业务字段：control_requirements',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_route_step_code` (`process_route_id`, `step_code`),
  UNIQUE KEY `uk_route_step_seq` (`process_route_id`, `sequence_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工艺路线步骤';

CREATE TABLE `production_device_execution` (
  `production_stage_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产阶段实绩ID；应用层逻辑引用 production_stage_run.id',
  `device_configuration_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：device_configuration_id；应用层逻辑引用 program_device_configuration.id',
  `trajectory_program_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '轨迹程序ID；应用层逻辑引用 trajectory_program.id',
  `executed_checksum` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '业务字段：executed_checksum',
  `started_at` TIMESTAMP NULL COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL COMMENT '完成时间',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'COMPLETED' COMMENT '状态',
  `source_system` VARCHAR(80) NULL COMMENT '来源系统',
  `deviation_details` JSON NULL COMMENT '业务字段：deviation_details',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_stage_device_execution` (`production_stage_run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产设备执行记录';

CREATE TABLE `production_run` (
  `run_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '生产事件编号',
  `body_no` VARCHAR(64) NULL COMMENT '车身号',
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '颜色ID；应用层逻辑引用 color.id',
  `shift` VARCHAR(24) NULL COMMENT '班次',
  `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL COMMENT '完成时间',
  `context_values` JSON NULL COMMENT '业务字段：context_values',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_no` (`run_no`),
  KEY `idx_production_body_no` (`body_no`),
  KEY `idx_production_run_context` (`factory_id`, `vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产事件';

CREATE TABLE `production_stage_run` (
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `process_stage` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '喷涂执行阶段',
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `material_batch_id` VARCHAR(36) NULL COMMENT '材料批次ID；应用层逻辑引用 material_batch.id',
  `actual_parameters` JSON NULL COMMENT '业务字段：actual_parameters',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'COMPLETED' COMMENT '状态',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_stage` (`production_run_id`, `process_stage`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产工艺阶段实绩';

CREATE TABLE `program_color` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `color_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '颜色ID；应用层逻辑引用 color.id',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_color` (`program_version_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='程序版本适用颜色';

CREATE TABLE `program_device_configuration` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `robot_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '机器人ID；应用层逻辑引用 durr_robot.id',
  `atomizer_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：atomizer_id；应用层逻辑引用 durr_rotary_atomizer.id',
  `controller_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：controller_id；应用层逻辑引用 durr_application_controller.id',
  `configuration_version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：configuration_version',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `effective_from` TIMESTAMP NULL COMMENT '业务字段：effective_from',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prog_device_config_ver` (`program_version_id`, `configuration_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='程序设备组合配置';

CREATE TABLE `program_rollback_execution` (
  `rollback_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务字段：rollback_no',
  `recommendation_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '推荐ID；应用层逻辑引用 recommendation.id',
  `controlled_trial_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '受控试验ID；应用层逻辑引用 controlled_trial.id',
  `rollback_to_program_version_id` VARCHAR(36) NULL COMMENT '业务字段：rollback_to_program_version_id；应用层逻辑引用 spray_program_version.id',
  `rollback_reason` TEXT NULL COMMENT '业务字段：rollback_reason',
  `execution_note` TEXT NULL COMMENT '业务字段：execution_note',
  `executed_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：executed_by',
  `executed_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '业务字段：executed_at',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'EXECUTED' COMMENT '状态',
  `action_snapshot` JSON NULL COMMENT '业务字段：action_snapshot',
  `verified_by` VARCHAR(80) NULL COMMENT '业务字段：verified_by',
  `verified_at` TIMESTAMP NULL COMMENT '业务字段：verified_at',
  `verification_comment` TEXT NULL COMMENT '业务字段：verification_comment',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_rollback_no` (`rollback_no`),
  UNIQUE KEY `uk_rollback_controlled_trial` (`controlled_trial_id`),
  KEY `idx_program_rollback_status` (`row_status`, `executed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='程序回滚执行记录';

CREATE TABLE `program_vehicle_model` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_model` (`program_version_id`, `vehicle_model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='程序版本适用车型';

CREATE TABLE `quality_issue_comment` (
  `task_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工单ID；应用层逻辑引用 quality_issue_task.id',
  `author` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '业务字段：author',
  `role_code` VARCHAR(64) NULL COMMENT '业务字段：role',
  `comment_type` VARCHAR(32) NOT NULL DEFAULT 'COMMENT' COMMENT '协作记录类型',
  `body` TEXT NULL COMMENT '业务字段：body',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_quality_issue_comment` (`task_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量问题协作记录';

CREATE TABLE `quality_issue_evidence` (
  `task_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工单ID；应用层逻辑引用 quality_issue_task.id',
  `evidence_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '证据类型',
  `source_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '来源类型',
  `source_id` VARCHAR(36) NULL COMMENT '来源ID',
  `summary` TEXT NULL COMMENT '业务字段：summary',
  `evidence_payload` JSON NULL COMMENT '证据载荷',
  `confidence` DECIMAL(18,6) NULL COMMENT '业务字段：confidence',
  `causality_status` VARCHAR(32) NOT NULL DEFAULT 'CORRELATION_ONLY' COMMENT '业务字段：causality_status',
  `created_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '创建人',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_quality_issue_evidence` (`task_id`, `evidence_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量问题证据';

CREATE TABLE `quality_issue_task` (
  `task_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '工单编号',
  `title` VARCHAR(180) NOT NULL DEFAULT '' COMMENT '业务字段：title',
  `task_type` VARCHAR(32) NOT NULL DEFAULT 'QUALITY_ISSUE' COMMENT '工单类型',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'OPEN' COMMENT '状态',
  `severity` VARCHAR(24) NOT NULL DEFAULT 'MEDIUM' COMMENT '严重度',
  `factory_id` VARCHAR(36) NULL COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `vehicle_model_id` VARCHAR(36) NULL COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NULL COMMENT '颜色ID；应用层逻辑引用 color.id',
  `production_run_id` VARCHAR(36) NULL COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NULL COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `quality_measurement_id` VARCHAR(36) NULL COMMENT '质量测量ID；应用层逻辑引用 quality_measurement.id',
  `material_batch_id` VARCHAR(36) NULL COMMENT '材料批次ID；应用层逻辑引用 material_batch.id',
  `recommendation_id` VARCHAR(36) NULL COMMENT '推荐ID；应用层逻辑引用 recommendation.id',
  `controlled_trial_id` VARCHAR(36) NULL COMMENT '受控试验ID；应用层逻辑引用 controlled_trial.id',
  `process_stage` VARCHAR(32) NULL COMMENT '喷涂执行阶段',
  `target_quality_type` VARCHAR(32) NULL COMMENT '目标质量类型',
  `target_metric` VARCHAR(64) NULL COMMENT '目标质量指标',
  `owner_role` VARCHAR(64) NULL COMMENT '业务字段：owner_role',
  `owner_user_id` VARCHAR(36) NULL COMMENT '负责人用户ID；应用层逻辑引用 app_user.id',
  `created_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '创建人',
  `due_at` TIMESTAMP NULL COMMENT '业务字段：due_at',
  `closed_at` TIMESTAMP NULL COMMENT '业务字段：closed_at',
  `problem_statement` TEXT NULL COMMENT '业务字段：problem_statement',
  `hypothesis` TEXT NULL COMMENT '业务字段：hypothesis',
  `suspected_cause` TEXT NULL COMMENT '业务字段：suspected_cause',
  `conclusion` TEXT NULL COMMENT '业务字段：conclusion',
  `causality_status` VARCHAR(32) NOT NULL DEFAULT 'CORRELATION_ONLY' COMMENT '业务字段：causality_status',
  `data_quality_status` VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT '业务字段：data_quality_status',
  `material_status` VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT '材料状态',
  `durr_execution_status` VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT '业务字段：durr_execution_status',
  `ai_summary` TEXT NULL COMMENT '业务字段：ai_summary',
  `tags` JSON NULL COMMENT '业务字段：tags',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_quality_issue_task_no` (`task_no`),
  KEY `idx_quality_issue_context` (`factory_id`, `vehicle_model_id`, `color_id`),
  KEY `idx_quality_issue_status` (`row_status`, `severity`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量问题和调试工单';

CREATE TABLE `quality_measurement` (
  `data_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量数据编号',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_group_id` VARCHAR(36) NULL COMMENT '测量编组ID；应用层逻辑引用 measurement_group.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `data_type` VARCHAR(24) NOT NULL DEFAULT 'TEST' COMMENT '数据类型',
  `measured_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '测量时间',
  `measured_by` VARCHAR(80) NULL COMMENT '测量人',
  `device_code` VARCHAR(64) NULL COMMENT '设备编码',
  `instrument_id` VARCHAR(36) NULL COMMENT '测量仪器ID；应用层逻辑引用 measurement_instrument.id',
  `measurement_probe_id` VARCHAR(36) NULL COMMENT '测量探头ID；应用层逻辑引用 measurement_probe.id',
  `measurement_method_id` VARCHAR(36) NULL COMMENT '测量方法ID；应用层逻辑引用 measurement_method.id',
  `calibration_record_id` VARCHAR(36) NULL COMMENT '校准记录ID；应用层逻辑引用 measurement_calibration_record.id',
  `reference_standard_id` VARCHAR(36) NULL COMMENT '参考标准件ID；应用层逻辑引用 measurement_reference_standard.id',
  `import_profile_id` VARCHAR(36) NULL COMMENT '导入模板ID；应用层逻辑引用 measurement_import_profile.id',
  `measurement_direction` VARCHAR(32) NULL COMMENT '业务字段：measurement_direction',
  `raw_file_uri` VARCHAR(500) NULL COMMENT '业务字段：raw_file_uri',
  `reliability_status` VARCHAR(24) NOT NULL DEFAULT 'UNVERIFIED' COMMENT '业务字段：reliability_status',
  `reliability_issues` JSON NULL COMMENT '业务字段：reliability_issues',
  `status_score` DECIMAL(18,6) NULL COMMENT '状态评分',
  `is_valid` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否有效',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_data_no` (`data_no`),
  KEY `idx_quality_point_time` (`measurement_point_id`, `measured_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量测量记录';

CREATE TABLE `quality_metric_definition` (
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `unit` VARCHAR(24) NULL COMMENT '单位',
  `display_order` INT NOT NULL DEFAULT 0 COMMENT '业务字段：display_order',
  `is_primary` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_primary',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_quality_type_metric_code` (`quality_type`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量指标定义';

CREATE TABLE `quality_metric_value` (
  `measurement_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量ID；应用层逻辑引用 quality_measurement.id',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `metric_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '质量指标名称',
  `raw_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '原始值',
  `corrected_value` DECIMAL(18,6) NULL COMMENT '修正值',
  `unit` VARCHAR(24) NULL COMMENT '单位',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_metric` (`measurement_id`, `metric_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量指标测量值';

CREATE TABLE `quality_standard` (
  `standard_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '标准编号',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `standard_type` VARCHAR(24) NOT NULL DEFAULT 'PRODUCTION' COMMENT '标准类型',
  `quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '质量指标类型',
  `metric_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '质量指标编码',
  `vehicle_model_id` VARCHAR(36) NULL COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NULL COMMENT '颜色ID；应用层逻辑引用 color.id',
  `part_id` VARCHAR(36) NULL COMMENT '零件ID；应用层逻辑引用 part.id',
  `measurement_point_id` VARCHAR(36) NULL COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `min_value` DECIMAL(18,6) NULL COMMENT '标准下限',
  `max_value` DECIMAL(18,6) NULL COMMENT '标准上限',
  `unit` VARCHAR(24) NULL COMMENT '单位',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_standard_match` (`quality_type`, `metric_code`, `vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量标准上下限';

CREATE TABLE `recommendation` (
  `recommendation_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '推荐编号',
  `production_run_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '生产事件ID；应用层逻辑引用 production_run.id',
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '测量点ID；应用层逻辑引用 measurement_point.id',
  `target_quality_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '目标质量类型',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `diagnosis_summary` TEXT NULL COMMENT '业务字段：diagnosis_summary',
  `predicted_improvement` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：predicted_improvement',
  `confidence` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：confidence',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  `model_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '模型版本',
  `constraints_checked` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：constraints_checked',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `executed_by` VARCHAR(80) NULL COMMENT '业务字段：executed_by',
  `executed_at` TIMESTAMP NULL COMMENT '业务字段：executed_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_no` (`recommendation_no`),
  KEY `idx_recommendation_status` (`row_status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI 参数推荐';

CREATE TABLE `recommendation_action` (
  `recommendation_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '推荐ID；应用层逻辑引用 recommendation.id',
  `process_stage` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '喷涂执行阶段',
  `brush_no` VARCHAR(32) NULL COMMENT '刷子号',
  `parameter_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '工艺参数编码',
  `parameter_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '工艺参数名称',
  `current_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：current_value',
  `recommended_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '业务字段：recommended_value',
  `executed_value` DECIMAL(18,6) NULL COMMENT '业务字段：executed_value',
  `unit` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '单位',
  `hard_min` DECIMAL(18,6) NULL COMMENT '硬下限',
  `hard_max` DECIMAL(18,6) NULL COMMENT '硬上限',
  `constraint_source_id` VARCHAR(36) NULL COMMENT '业务字段：constraint_source_id；应用层逻辑引用 parameter_constraint_source.id',
  `constraint_source_code` VARCHAR(96) NULL COMMENT '业务字段：constraint_source_code',
  `constraint_source_version` VARCHAR(32) NULL COMMENT '业务字段：constraint_source_version',
  `constraint_source_type` VARCHAR(32) NULL COMMENT '业务字段：constraint_source_type',
  `constraint_source_uri` VARCHAR(500) NULL COMMENT '业务字段：constraint_source_uri',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='推荐参数动作';

CREATE TABLE `role_code` (
  `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `description` TEXT NULL COMMENT '描述',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统角色定义';

CREATE TABLE `role_permission` (
  `role_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '角色ID；应用层逻辑引用 role.id',
  `permission_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '权限ID；应用层逻辑引用 permission.id',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='角色权限关系';

CREATE TABLE `spray_program` (
  `program_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '喷涂程序编号',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `process_stage` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '喷涂执行阶段',
  `station_code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '站点编号',
  `station_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '站点名称',
  `robot_model` VARCHAR(120) NULL COMMENT '机器人型号',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_program_code` (`factory_id`, `program_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喷涂程序主数据';

CREATE TABLE `spray_program_version` (
  `spray_program_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '喷涂程序ID；应用层逻辑引用 spray_program.id',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_type` VARCHAR(24) NOT NULL DEFAULT 'MANUAL' COMMENT '来源类型',
  `is_master_sample` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '业务字段：is_master_sample',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `effective_from` TIMESTAMP NULL COMMENT '业务字段：effective_from',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_version` (`spray_program_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喷涂程序版本';

CREATE TABLE `supplier_mat_issue` (
  `issue_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '问题编号',
  `submission_id` VARCHAR(36) NULL COMMENT '提交ID；应用层逻辑引用 supplier_mat_submission.id',
  `material_batch_id` VARCHAR(36) NULL COMMENT '材料批次ID；应用层逻辑引用 material_batch.id',
  `issue_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '问题类型',
  `severity` VARCHAR(24) NOT NULL DEFAULT 'MEDIUM' COMMENT '严重度',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'OPEN' COMMENT '状态',
  `description` TEXT NULL COMMENT '描述',
  `containment_action` TEXT NULL COMMENT '业务字段：containment_action',
  `supplier_response` TEXT NULL COMMENT '业务字段：supplier_response',
  `resolution` TEXT NULL COMMENT '业务字段：resolution',
  `owner` VARCHAR(80) NULL COMMENT '业务字段：owner',
  `due_at` TIMESTAMP NULL COMMENT '业务字段：due_at',
  `closed_at` TIMESTAMP NULL COMMENT '业务字段：closed_at',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_supplier_mat_issue` (`issue_no`),
  KEY `idx_supplier_issue_status` (`row_status`, `due_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='供应商材料问题反馈';

CREATE TABLE `supplier_mat_submission` (
  `submission_no` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '提交编号',
  `supplier` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '供应商',
  `material_batch_id` VARCHAR(36) NULL COMMENT '材料批次ID；应用层逻辑引用 material_batch.id',
  `material_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '材料编码',
  `material_name` VARCHAR(120) NULL COMMENT '材料名称',
  `document_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：document_type',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `profile_id` VARCHAR(36) NULL COMMENT '业务字段：profile_id；应用层逻辑引用 file_import_profile.id',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'SUBMITTED' COMMENT '状态',
  `submitted_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '提交人',
  `submitted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `reviewed_by` VARCHAR(80) NULL COMMENT '业务字段：reviewed_by',
  `reviewed_at` TIMESTAMP NULL COMMENT '业务字段：reviewed_at',
  `field_values` JSON NULL COMMENT '业务字段：field_values',
  `validation_result` JSON NULL COMMENT '业务字段：validation_result',
  `deviation_decision` VARCHAR(32) NULL COMMENT '业务字段：deviation_decision',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_supplier_mat_submission` (`submission_no`),
  KEY `idx_supplier_mat_status` (`supplier`, `row_status`, `submitted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='供应商材料资料提交';

CREATE TABLE `trajectory_path_segment` (
  `trajectory_program_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '轨迹程序ID；应用层逻辑引用 trajectory_program.id',
  `segment_no` INT NOT NULL DEFAULT 0 COMMENT '路径段编号',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `brush_id` VARCHAR(36) NULL COMMENT '刷子ID；应用层逻辑引用 brush.id',
  `part_id` VARCHAR(36) NULL COMMENT '零件ID；应用层逻辑引用 part.id',
  `tcp_name` VARCHAR(120) NULL COMMENT '业务字段：tcp_name',
  `configured_speed` DECIMAL(18,6) NULL COMMENT '业务字段：configured_speed',
  `speed_unit` VARCHAR(24) NULL COMMENT '业务字段：speed_unit',
  `start_position` JSON NULL COMMENT '业务字段：start_position',
  `end_position` JSON NULL COMMENT '业务字段：end_position',
  `orientation` JSON NULL COMMENT '业务字段：orientation',
  `trigger_state` VARCHAR(24) NOT NULL DEFAULT 'ON' COMMENT '业务字段：trigger_state',
  `trigger_start_ms` DECIMAL(18,6) NULL COMMENT '业务字段：trigger_start_ms',
  `trigger_end_ms` DECIMAL(18,6) NULL COMMENT '业务字段：trigger_end_ms',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trajectory_path_segment_no` (`trajectory_program_id`, `segment_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dürr 轨迹路径段';

CREATE TABLE `trajectory_program` (
  `program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '程序版本ID；应用层逻辑引用 spray_program_version.id',
  `trajectory_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '轨迹编码',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '名称',
  `version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '版本号',
  `checksum` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '业务字段：checksum',
  `coordinate_system` VARCHAR(80) NULL COMMENT '业务字段：coordinate_system',
  `tcp_name` VARCHAR(120) NULL COMMENT '业务字段：tcp_name',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `source_uri` VARCHAR(500) NULL COMMENT '来源文件URI',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_trajectory_version` (`program_version_id`, `trajectory_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Dürr 轨迹程序';

CREATE TABLE `trajectory_segment_geometry` (
  `path_segment_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '业务字段：path_segment_id；应用层逻辑引用 trajectory_path_segment.id',
  `geometry_version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业务字段：geometry_version',
  `source_import_job_id` VARCHAR(36) NULL COMMENT '业务字段：source_import_job_id；应用层逻辑引用 file_import_job.id',
  `start_position` JSON NULL COMMENT '业务字段：start_position',
  `end_position` JSON NULL COMMENT '业务字段：end_position',
  `orientation` JSON NULL COMMENT '业务字段：orientation',
  `normal_vector` JSON NULL COMMENT '业务字段：normal_vector',
  `gun_distance` DECIMAL(18,6) NULL COMMENT '业务字段：gun_distance',
  `path_spacing` DECIMAL(18,6) NULL COMMENT '业务字段：path_spacing',
  `overlap_ratio` DECIMAL(18,6) NULL COMMENT '业务字段：overlap_ratio',
  `collision_risk_score` DECIMAL(18,6) NULL COMMENT '业务字段：collision_risk_score',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  `evidence_uri` VARCHAR(500) NULL COMMENT '证据URI',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_path_segment_geometry` (`path_segment_id`, `geometry_version`),
  KEY `idx_path_geometry_status` (`path_segment_id`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='路径段几何姿态事实';

CREATE TABLE `user_role` (
  `user_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '用户ID；应用层逻辑引用 app_user.id',
  `role_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '角色ID；应用层逻辑引用 role.id',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户角色关系';

CREATE TABLE `user_session` (
  `user_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '用户ID；应用层逻辑引用 app_user.id',
  `token_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '会话令牌哈希',
  `issued_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '签发时间',
  `expires_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '过期时间',
  `revoked_at` TIMESTAMP NULL COMMENT '吊销时间',
  `last_seen_at` TIMESTAMP NULL COMMENT '最后访问时间',
  `user_agent` VARCHAR(500) NULL COMMENT '用户代理',
  `client_ip` VARCHAR(64) NULL COMMENT '客户端IP',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_token_hash` (`token_hash`),
  KEY `idx_user_session_user` (`user_id`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户登录会话';

CREATE TABLE `vehicle_model` (
  `code` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '编码',
  `name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '名称',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='车型主数据';

CREATE TABLE `vehicle_model_color` (
  `vehicle_model_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '车型ID；应用层逻辑引用 vehicle_model.id',
  `color_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '颜色ID；应用层逻辑引用 color.id',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_vehicle_model_color` (`vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='车型颜色关系';

-- 应用层逻辑引用清单，仅供 DBA 和应用审查；不会生成物理外键。
-- actual_parameter.production_stage_run_id -> production_stage_run.id
-- actual_parameter.brush_id -> brush.id
-- actual_parameter.parameter_definition_id -> parameter_definition.id
-- api_key.user_id -> app_user.id
-- audit_log.actor_user_id -> app_user.id
-- brush.program_version_id -> spray_program_version.id
-- brush.part_id -> part.id
-- brush_parameter.brush_id -> brush.id
-- brush_parameter.parameter_definition_id -> parameter_definition.id
-- brush_point_contribution.brush_id -> brush.id
-- brush_point_contribution.measurement_point_id -> measurement_point.id
-- closed_loop_evaluation.recommendation_id -> recommendation.id
-- contribution_validation.contribution_version_id -> point_contribution_version.id
-- controlled_trial.recommendation_id -> recommendation.id
-- controlled_trial.production_run_id -> production_run.id
-- controlled_trial.measurement_point_id -> measurement_point.id
-- dataset_split_member.dataset_snapshot_id -> dataset_snapshot.id
-- dataset_split_member.point_feature_snapshot_id -> point_feature_snapshot.id
-- dataset_split_member.production_run_id -> production_run.id
-- dataset_split_member.measurement_point_id -> measurement_point.id
-- dataset_split_member.target_measurement_id -> quality_measurement.id
-- diagnosis_result.prediction_result_id -> prediction_result.id
-- diagnosis_result.production_run_id -> production_run.id
-- diagnosis_result.measurement_point_id -> measurement_point.id
-- durr_application_controller.factory_id -> factory.id
-- durr_robot.factory_id -> factory.id
-- durr_rotary_atomizer.factory_id -> factory.id
-- durr_rotary_atomizer.controller_id -> durr_application_controller.id
-- factory_vehicle_model.factory_id -> factory.id
-- factory_vehicle_model.vehicle_model_id -> vehicle_model.id
-- file_import_job.profile_id -> file_import_profile.id
-- file_import_job.replay_of_job_id -> file_import_job.id
-- integration_event.endpoint_id -> integration_endpoint.id
-- mat_char_applicability.characteristic_definition_id -> mat_char_definition.id
-- material_batch_test_result.material_batch_id -> material_batch.id
-- material_batch_test_result.characteristic_definition_id -> mat_char_definition.id
-- material_batch_test_result.method_id -> material_test_method.id
-- material_batch_test_result.specification_id -> material_specification.id
-- material_specification.characteristic_definition_id -> mat_char_definition.id
-- material_specification.method_id -> material_test_method.id
-- material_test_method.characteristic_definition_id -> mat_char_definition.id
-- measurement_calibration_record.instrument_id -> measurement_instrument.id
-- measurement_calibration_record.method_id -> measurement_method.id
-- measurement_calibration_record.reference_standard_id -> measurement_reference_standard.id
-- measurement_group.vehicle_model_id -> vehicle_model.id
-- measurement_group_point.measurement_group_id -> measurement_group.id
-- measurement_group_point.measurement_point_id -> measurement_point.id
-- measurement_msa_study.instrument_id -> measurement_instrument.id
-- measurement_msa_study.probe_id -> measurement_probe.id
-- measurement_msa_study.method_id -> measurement_method.id
-- measurement_point.vehicle_model_id -> vehicle_model.id
-- measurement_point.part_id -> part.id
-- measurement_probe.instrument_id -> measurement_instrument.id
-- measurement_repeat_reading.measurement_id -> quality_measurement.id
-- model_acceptance_decision.model_version_id -> model_version.id
-- model_acceptance_decision.dataset_snapshot_id -> dataset_snapshot.id
-- model_acceptance_policy.factory_id -> factory.id
-- model_applicability_scope.model_version_id -> model_version.id
-- model_applicability_scope.factory_id -> factory.id
-- model_applicability_scope.vehicle_model_id -> vehicle_model.id
-- model_applicability_scope.color_id -> color.id
-- model_artifact.model_version_id -> model_version.id
-- model_explanation.model_version_id -> model_version.id
-- model_explanation.prediction_result_id -> prediction_result.id
-- model_ood_policy.model_version_id -> model_version.id
-- model_validation_fold.model_version_id -> model_version.id
-- model_validation_fold.dataset_snapshot_id -> dataset_snapshot.id
-- model_version.dataset_snapshot_id -> dataset_snapshot.id
-- parameter_constraint_source.parameter_definition_id -> parameter_definition.id
-- parameter_constraint_source.factory_id -> factory.id
-- path_segment_execution.device_execution_id -> production_device_execution.id
-- path_segment_execution.path_segment_id -> trajectory_path_segment.id
-- point_contribution_entry.contribution_version_id -> point_contribution_version.id
-- point_contribution_entry.measurement_point_id -> measurement_point.id
-- point_contribution_entry.brush_id -> brush.id
-- point_contribution_entry.path_segment_id -> trajectory_path_segment.id
-- point_contribution_version.program_version_id -> spray_program_version.id
-- point_feature_snapshot.production_run_id -> production_run.id
-- point_feature_snapshot.measurement_point_id -> measurement_point.id
-- prediction_result.model_version_id -> model_version.id
-- prediction_result.production_run_id -> production_run.id
-- prediction_result.measurement_point_id -> measurement_point.id
-- process_route.factory_id -> factory.id
-- process_route_applicability.process_route_id -> process_route.id
-- process_route_applicability.vehicle_model_id -> vehicle_model.id
-- process_route_applicability.color_id -> color.id
-- process_route_step.process_route_id -> process_route.id
-- production_device_execution.production_stage_run_id -> production_stage_run.id
-- production_device_execution.device_configuration_id -> program_device_configuration.id
-- production_device_execution.trajectory_program_id -> trajectory_program.id
-- production_run.factory_id -> factory.id
-- production_run.vehicle_model_id -> vehicle_model.id
-- production_run.color_id -> color.id
-- production_stage_run.production_run_id -> production_run.id
-- production_stage_run.program_version_id -> spray_program_version.id
-- production_stage_run.material_batch_id -> material_batch.id
-- program_color.program_version_id -> spray_program_version.id
-- program_color.color_id -> color.id
-- program_device_configuration.program_version_id -> spray_program_version.id
-- program_device_configuration.robot_id -> durr_robot.id
-- program_device_configuration.atomizer_id -> durr_rotary_atomizer.id
-- program_device_configuration.controller_id -> durr_application_controller.id
-- program_rollback_execution.recommendation_id -> recommendation.id
-- program_rollback_execution.controlled_trial_id -> controlled_trial.id
-- program_rollback_execution.rollback_to_program_version_id -> spray_program_version.id
-- program_vehicle_model.program_version_id -> spray_program_version.id
-- program_vehicle_model.vehicle_model_id -> vehicle_model.id
-- quality_issue_comment.task_id -> quality_issue_task.id
-- quality_issue_evidence.task_id -> quality_issue_task.id
-- quality_issue_task.factory_id -> factory.id
-- quality_issue_task.vehicle_model_id -> vehicle_model.id
-- quality_issue_task.color_id -> color.id
-- quality_issue_task.production_run_id -> production_run.id
-- quality_issue_task.measurement_point_id -> measurement_point.id
-- quality_issue_task.quality_measurement_id -> quality_measurement.id
-- quality_issue_task.material_batch_id -> material_batch.id
-- quality_issue_task.recommendation_id -> recommendation.id
-- quality_issue_task.controlled_trial_id -> controlled_trial.id
-- quality_issue_task.owner_user_id -> app_user.id
-- quality_measurement.production_run_id -> production_run.id
-- quality_measurement.measurement_group_id -> measurement_group.id
-- quality_measurement.measurement_point_id -> measurement_point.id
-- quality_measurement.instrument_id -> measurement_instrument.id
-- quality_measurement.measurement_probe_id -> measurement_probe.id
-- quality_measurement.measurement_method_id -> measurement_method.id
-- quality_measurement.calibration_record_id -> measurement_calibration_record.id
-- quality_measurement.reference_standard_id -> measurement_reference_standard.id
-- quality_measurement.import_profile_id -> measurement_import_profile.id
-- quality_metric_value.measurement_id -> quality_measurement.id
-- quality_standard.vehicle_model_id -> vehicle_model.id
-- quality_standard.color_id -> color.id
-- quality_standard.part_id -> part.id
-- quality_standard.measurement_point_id -> measurement_point.id
-- recommendation.production_run_id -> production_run.id
-- recommendation.measurement_point_id -> measurement_point.id
-- recommendation_action.recommendation_id -> recommendation.id
-- recommendation_action.constraint_source_id -> parameter_constraint_source.id
-- role_permission.role_id -> role.id
-- role_permission.permission_id -> permission.id
-- spray_program.factory_id -> factory.id
-- spray_program_version.spray_program_id -> spray_program.id
-- supplier_mat_issue.submission_id -> supplier_mat_submission.id
-- supplier_mat_issue.material_batch_id -> material_batch.id
-- supplier_mat_submission.material_batch_id -> material_batch.id
-- supplier_mat_submission.profile_id -> file_import_profile.id
-- trajectory_path_segment.trajectory_program_id -> trajectory_program.id
-- trajectory_path_segment.brush_id -> brush.id
-- trajectory_path_segment.part_id -> part.id
-- trajectory_program.program_version_id -> spray_program_version.id
-- trajectory_segment_geometry.path_segment_id -> trajectory_path_segment.id
-- trajectory_segment_geometry.source_import_job_id -> file_import_job.id
-- user_role.user_id -> app_user.id
-- user_role.role_id -> role.id
-- user_session.user_id -> app_user.id
-- vehicle_model_color.vehicle_model_id -> vehicle_model.id
-- vehicle_model_color.color_id -> color.id
