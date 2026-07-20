-- PQ-AI 新增 7 张表独立建表审批 SQL
-- 生成日期：2026-07-19
-- 用途：由授权 DBA 按审批工单人工执行，仅补建训练宽表和机器人远程工作站相关表。
-- 范围：只包含 7 个 CREATE TABLE；不建数据库，不包含物理外键、ALTER、DROP、DELETE、SET、视图、触发器、存储过程或事件。
-- 前提：factory、spray_program_version 等被逻辑引用的既有表已经存在；引用完整性由应用层校验。
-- 重要：混合使用生产样本和人工训练宽表还要求 dataset_split_member 采用总 DDL 中的最新来源字段结构；该既有表变更不在本文件内。
-- 执行顺序：连接配置 -> 参数快照 -> 发布单 -> 发布事件 -> 三方对账 -> 训练上传 -> 训练样本。
-- 统计：数据表 7 张；物理外键 0 个。


CREATE TABLE `remote_station_connection` (
  `connection_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '连接编号',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '连接名称',
  `factory_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '工厂ID；应用层逻辑引用 factory.id',
  `station_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '工作站编号',
  `station_name` VARCHAR(120) NOT NULL DEFAULT '' COMMENT '工作站名称',
  `process_stage` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '喷涂执行阶段',
  `host` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '目标上位机地址',
  `port` INT UNSIGNED NOT NULL DEFAULT 9443 COMMENT '双向TLS通信端口',
  `transport` VARCHAR(24) NOT NULL DEFAULT 'TLS_TCP' COMMENT '传输方式',
  `adapter_mode` VARCHAR(32) NOT NULL DEFAULT 'SIMULATOR' COMMENT '目标机适配方式',
  `agent_id` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '目标通讯程序编号',
  `server_name` VARCHAR(255) NULL COMMENT '服务端证书名称',
  `client_certificate_ref` VARCHAR(160) NULL COMMENT '客户端证书运行时配置引用名',
  `client_private_key_ref` VARCHAR(160) NULL COMMENT '客户端私钥运行时配置引用名',
  `trusted_ca_ref` VARCHAR(160) NULL COMMENT '受信任根证书运行时配置引用名',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '连接审批状态',
  `operating_mode` VARCHAR(24) NOT NULL DEFAULT 'READ_ONLY' COMMENT '只读或仅已审批发布',
  `local_confirmation_required` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否要求上位机现场确认',
  `connect_timeout_seconds` INT UNSIGNED NOT NULL DEFAULT 5 COMMENT '连接超时秒数',
  `max_package_bytes` INT UNSIGNED NOT NULL DEFAULT 5242880 COMMENT '最大参数包字节数',
  `last_seen_at` TIMESTAMP NULL COMMENT '最后连通时间',
  `last_inventory_hash` VARCHAR(64) NULL COMMENT '最后回读完整刷子表SHA-256',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `remark` TEXT NULL COMMENT '备注',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_remote_station_connection` (`connection_code`),
  KEY `idx_remote_station_factory` (`factory_id`, `process_stage`, `row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='目标机器人上位机受控连接配置';


CREATE TABLE `remote_parameter_snapshot` (
  `connection_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '远程工作站连接ID；应用层逻辑引用 remote_station_connection.id',
  `source_type` VARCHAR(24) NOT NULL DEFAULT '' COMMENT '来源：云端、虚拟线或上位机',
  `program_version_id` VARCHAR(36) NULL COMMENT '喷涂程序版本ID；应用层逻辑引用 spray_program_version.id',
  `version_label` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '来源侧版本标识',
  `payload_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '完整刷子表SHA-256',
  `parameter_payload` JSON NULL COMMENT '完整刷子表快照',
  `collection_ref` VARCHAR(160) NULL COMMENT '采集来源标识',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'VERIFIED' COMMENT '状态',
  `collected_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '采集人',
  `collected_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_remote_snapshot_source` (`connection_id`, `source_type`, `collected_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='云端虚拟线与上位机完整参数快照';


CREATE TABLE `remote_program_release` (
  `release_no` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '远程发布单号',
  `connection_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '远程工作站连接ID；应用层逻辑引用 remote_station_connection.id',
  `base_program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '原喷涂程序版本ID；应用层逻辑引用 spray_program_version.id',
  `candidate_program_version_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '候选喷涂程序版本ID；应用层逻辑引用 spray_program_version.id',
  `row_status` VARCHAR(32) NOT NULL DEFAULT 'DRAFT' COMMENT '发布状态',
  `package_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '完整发布包SHA-256',
  `package_payload` JSON NULL COMMENT '完整刷子表发布包',
  `risk_summary` TEXT NULL COMMENT '调整原因、风险与回退条件',
  `requested_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '申请人',
  `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `approved_by` VARCHAR(80) NULL COMMENT '审批人',
  `approved_at` TIMESTAMP NULL COMMENT '审批时间',
  `staged_at` TIMESTAMP NULL COMMENT '远程暂存时间',
  `local_confirmed_at` TIMESTAMP NULL COMMENT '上位机现场确认时间',
  `applied_at` TIMESTAMP NULL COMMENT '正式提交时间',
  `verified_at` TIMESTAMP NULL COMMENT '回读核验时间',
  `readback_hash` VARCHAR(64) NULL COMMENT '回读完整刷子表SHA-256',
  `rollback_program_version_id` VARCHAR(36) NULL COMMENT '回退程序版本ID；应用层逻辑引用 spray_program_version.id',
  `last_error` TEXT NULL COMMENT '最后错误',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_remote_program_release` (`release_no`),
  KEY `idx_remote_release_status` (`connection_id`, `row_status`, `requested_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='上位机完整喷涂程序受控发布单';


CREATE TABLE `remote_release_event` (
  `release_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '远程发布单ID；应用层逻辑引用 remote_program_release.id',
  `event_type` VARCHAR(48) NOT NULL DEFAULT '' COMMENT '发布事件类型',
  `status` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '事件发生后状态',
  `message` TEXT NULL COMMENT '通俗事件说明',
  `event_payload` JSON NULL COMMENT '非敏感事件证据',
  `actor` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '操作人',
  `occurred_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发生时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_remote_release_event` (`release_id`, `occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='远程程序发布审计事件';


CREATE TABLE `remote_station_reconciliation` (
  `connection_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '远程工作站连接ID；应用层逻辑引用 remote_station_connection.id',
  `cloud_snapshot_id` VARCHAR(36) NULL COMMENT '云端快照ID；应用层逻辑引用 remote_parameter_snapshot.id',
  `virtual_snapshot_id` VARCHAR(36) NULL COMMENT '虚拟生产线快照ID；应用层逻辑引用 remote_parameter_snapshot.id',
  `upper_snapshot_id` VARCHAR(36) NULL COMMENT '上位机快照ID；应用层逻辑引用 remote_parameter_snapshot.id',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'GENERATED' COMMENT '对账状态',
  `diff_payload` JSON NULL COMMENT '按刷子号和参数生成的三方差异',
  `generated_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '生成人',
  `generated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_remote_reconcile_time` (`connection_id`, `generated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='云端虚拟线与上位机参数三方对账';


CREATE TABLE `training_data_upload` (
  `upload_no` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '人工训练数据上传编号',
  `name` VARCHAR(160) NOT NULL DEFAULT '' COMMENT '人工训练数据名称',
  `target_metric` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '目标质量指标',
  `feature_set_version` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '特征集合版本',
  `source_type` VARCHAR(24) NOT NULL DEFAULT 'MANUAL_UPLOAD' COMMENT '数据来源类型',
  `file_name` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '原始文件名',
  `file_hash` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '原始文件SHA-256',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'VALIDATED' COMMENT '校验状态',
  `sample_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '样本数量',
  `feature_names` JSON NULL COMMENT '统一训练特征名称',
  `validation_report` JSON NULL COMMENT '导入校验结果',
  `uploaded_by` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '上传人',
  `uploaded_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_training_data_upload_no` (`upload_no`),
  KEY `idx_training_upload_target` (`target_metric`, `row_status`, `uploaded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='人工上传训练宽表治理记录';


CREATE TABLE `training_wide_sample` (
  `upload_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '人工训练数据上传ID；应用层逻辑引用 training_data_upload.id',
  `sample_no` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '样本编号',
  `group_value` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '独立车身批次或试验分组',
  `occurred_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '样本实际发生时间',
  `target_value` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '目标质量实测值',
  `feature_values` JSON NULL COMMENT '经中文列名转换后的统一特征值',
  `lineage` JSON NULL COMMENT '原始文件哈希和行号血缘',
  `is_valid` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否通过校验',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_training_upload_sample` (`upload_id`, `sample_no`),
  KEY `idx_training_sample_group` (`upload_id`, `group_value`, `occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='人工训练数据宽表样本';
