-- PQ-AI MySQL schema for DBA approval.
-- Generated from services/api/app/models/domain.py metadata.
-- Review material only. Application code, Docker, CI, tests, and seed scripts must never run this file automatically.
-- The file emits table definitions only and omits physical reference constraints; references are enforced by the application layer.

CREATE TABLE `actual_parameter` (
  `production_stage_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_stage_run_id',
  `brush_id` VARCHAR(36) NULL COMMENT '字段 brush_id',
  `parameter_definition_id` VARCHAR(36) NULL COMMENT '字段 parameter_definition_id',
  `parameter_code` VARCHAR(64) NOT NULL COMMENT '字段 parameter_code',
  `actual_value` DECIMAL(18,6) NOT NULL COMMENT '字段 actual_value',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `sampled_at` TIMESTAMP NOT NULL COMMENT '字段 sampled_at',
  `source_system` VARCHAR(64) NULL COMMENT '字段 source_system',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  KEY `idx_actual_parameter_stage_code` (`production_stage_run_id`, `parameter_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI actual_parameter';

CREATE TABLE `api_key` (
  `user_id` VARCHAR(36) NOT NULL COMMENT '字段 user_id',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `key_prefix` VARCHAR(16) NOT NULL COMMENT '字段 key_prefix',
  `key_hash` VARCHAR(64) NOT NULL COMMENT '字段 key_hash',
  `expires_at` TIMESTAMP NULL COMMENT '字段 expires_at',
  `last_used_at` TIMESTAMP NULL COMMENT '字段 last_used_at',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key_hash` (`key_hash`),
  KEY `idx_api_key_prefix` (`key_prefix`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI api_key';

CREATE TABLE `app_user` (
  `username` VARCHAR(80) NOT NULL COMMENT '字段 username',
  `display_name` VARCHAR(120) NOT NULL COMMENT '字段 display_name',
  `email` VARCHAR(200) NULL COMMENT '字段 email',
  `department` VARCHAR(120) NULL COMMENT '字段 department',
  `password_hash` VARCHAR(255) NULL COMMENT '字段 password_hash',
  `password_changed_at` TIMESTAMP NULL COMMENT '字段 password_changed_at',
  `failed_login_count` INT NOT NULL DEFAULT 0 COMMENT '字段 failed_login_count',
  `locked_until` TIMESTAMP NULL COMMENT '字段 locked_until',
  `last_login_at` TIMESTAMP NULL COMMENT '字段 last_login_at',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI app_user';

CREATE TABLE `audit_log` (
  `request_id` VARCHAR(64) NOT NULL COMMENT '字段 request_id',
  `actor_user_id` VARCHAR(36) NULL COMMENT '字段 actor_user_id',
  `actor_username` VARCHAR(80) NOT NULL COMMENT '字段 actor_username',
  `action` VARCHAR(100) NOT NULL COMMENT '字段 action',
  `http_method` VARCHAR(12) NOT NULL COMMENT '字段 http_method',
  `path` VARCHAR(500) NOT NULL COMMENT '字段 path',
  `resource_type` VARCHAR(100) NULL COMMENT '字段 resource_type',
  `resource_id` VARCHAR(100) NULL COMMENT '字段 resource_id',
  `status_code` INT NOT NULL COMMENT '字段 status_code',
  `client_ip` VARCHAR(64) NULL COMMENT '字段 client_ip',
  `detail` JSON NULL COMMENT '字段 detail',
  `occurred_at` TIMESTAMP NOT NULL COMMENT '字段 occurred_at',
  `id` VARCHAR(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_audit_actor_time` (`actor_user_id`, `occurred_at`),
  KEY `idx_audit_resource` (`resource_type`, `resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI audit_log';

CREATE TABLE `brush` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `brush_no` VARCHAR(32) NOT NULL COMMENT '字段 brush_no',
  `brush_table_no` VARCHAR(64) NOT NULL COMMENT '字段 brush_table_no',
  `spray_position` VARCHAR(120) NULL COMMENT '字段 spray_position',
  `part_id` VARCHAR(36) NULL COMMENT '字段 part_id',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_brush_no` (`program_version_id`, `brush_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI brush';

CREATE TABLE `brush_parameter` (
  `brush_id` VARCHAR(36) NOT NULL COMMENT '字段 brush_id',
  `parameter_definition_id` VARCHAR(36) NULL COMMENT '字段 parameter_definition_id',
  `parameter_code` VARCHAR(64) NOT NULL COMMENT '字段 parameter_code',
  `parameter_name` VARCHAR(120) NOT NULL COMMENT '字段 parameter_name',
  `configured_value` DECIMAL(18,6) NOT NULL COMMENT '字段 configured_value',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `soft_min` DECIMAL(18,6) NULL COMMENT '字段 soft_min',
  `soft_max` DECIMAL(18,6) NULL COMMENT '字段 soft_max',
  `hard_min` DECIMAL(18,6) NULL COMMENT '字段 hard_min',
  `hard_max` DECIMAL(18,6) NULL COMMENT '字段 hard_max',
  `is_recommendable` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_recommendable',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brush_parameter` (`brush_id`, `parameter_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI brush_parameter';

CREATE TABLE `brush_point_contribution` (
  `brush_id` VARCHAR(36) NOT NULL COMMENT '字段 brush_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `overlap_ratio` DECIMAL(18,6) NOT NULL COMMENT '字段 overlap_ratio',
  `contribution_weight` DECIMAL(18,6) NOT NULL COMMENT '字段 contribution_weight',
  `source` VARCHAR(32) NOT NULL DEFAULT 'EXPERT' COMMENT '字段 source',
  `version` VARCHAR(32) NOT NULL DEFAULT '1.0' COMMENT '字段 version',
  `is_approved` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 is_approved',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brush_point` (`brush_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI brush_point_contribution';

CREATE TABLE `closed_loop_evaluation` (
  `recommendation_id` VARCHAR(36) NOT NULL COMMENT '字段 recommendation_id',
  `baseline_value` DECIMAL(18,6) NOT NULL COMMENT '字段 baseline_value',
  `verified_value` DECIMAL(18,6) NOT NULL COMMENT '字段 verified_value',
  `actual_improvement` DECIMAL(18,6) NOT NULL COMMENT '字段 actual_improvement',
  `is_effective` INT UNSIGNED NOT NULL COMMENT '字段 is_effective',
  `verified_at` TIMESTAMP NOT NULL COMMENT '字段 verified_at',
  `verified_by` VARCHAR(80) NOT NULL COMMENT '字段 verified_by',
  `conclusion` VARCHAR(2000) NULL COMMENT '字段 conclusion',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_evaluation` (`recommendation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI closed_loop_evaluation';

CREATE TABLE `color` (
  `code` VARCHAR(32) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `color_type` VARCHAR(24) NOT NULL COMMENT '字段 color_type',
  `feature_values` JSON NULL COMMENT '字段 feature_values',
  `supplier` VARCHAR(120) NULL COMMENT '字段 supplier',
  `tds_uri` VARCHAR(500) NULL COMMENT '字段 tds_uri',
  `msds_uri` VARCHAR(500) NULL COMMENT '字段 msds_uri',
  `coa_uri` VARCHAR(500) NULL COMMENT '字段 coa_uri',
  `doe_uri` VARCHAR(500) NULL COMMENT '字段 doe_uri',
  `digital_standard` JSON NULL COMMENT '字段 digital_standard',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI color';

CREATE TABLE `controlled_trial` (
  `recommendation_id` VARCHAR(36) NOT NULL COMMENT '字段 recommendation_id',
  `trial_no` VARCHAR(64) NOT NULL COMMENT '字段 trial_no',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `target_metric` VARCHAR(64) NOT NULL COMMENT '字段 target_metric',
  `hypothesis` VARCHAR(2000) NOT NULL COMMENT '字段 hypothesis',
  `evidence_type` VARCHAR(32) NOT NULL COMMENT '字段 evidence_type',
  `expected_outcome` VARCHAR(2000) NOT NULL COMMENT '字段 expected_outcome',
  `risk_assessment` VARCHAR(2000) NOT NULL COMMENT '字段 risk_assessment',
  `rollback_plan` VARCHAR(2000) NOT NULL COMMENT '字段 rollback_plan',
  `sustained_observation_plan` VARCHAR(2000) NOT NULL COMMENT '字段 sustained_observation_plan',
  `constraint_evidence` JSON NOT NULL COMMENT '字段 constraint_evidence',
  `status` VARCHAR(24) NOT NULL DEFAULT 'PLANNED' COMMENT '字段 status',
  `requested_by` VARCHAR(80) NOT NULL COMMENT '字段 requested_by',
  `requested_at` TIMESTAMP NOT NULL COMMENT '字段 requested_at',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `approval_comment` VARCHAR(2000) NULL COMMENT '字段 approval_comment',
  `started_at` TIMESTAMP NULL COMMENT '字段 started_at',
  `completed_at` TIMESTAMP NULL COMMENT '字段 completed_at',
  `completion_summary` VARCHAR(2000) NULL COMMENT '字段 completion_summary',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_controlled_trial_no` (`trial_no`),
  UNIQUE KEY `uk_trial_recommendation` (`recommendation_id`),
  KEY `idx_controlled_trial_status` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI controlled_trial';

CREATE TABLE `dataset_snapshot` (
  `dataset_code` VARCHAR(64) NOT NULL COMMENT '字段 dataset_code',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `target_metric` VARCHAR(64) NOT NULL COMMENT '字段 target_metric',
  `feature_set_version` VARCHAR(64) NOT NULL COMMENT '字段 feature_set_version',
  `split_strategy` VARCHAR(48) NOT NULL COMMENT '字段 split_strategy',
  `group_key` VARCHAR(32) NOT NULL COMMENT '字段 group_key',
  `holdout_ratio` DECIMAL(18,6) NOT NULL COMMENT '字段 holdout_ratio',
  `status` VARCHAR(24) NOT NULL DEFAULT 'BUILT' COMMENT '字段 status',
  `sample_count` INT NOT NULL COMMENT '字段 sample_count',
  `group_count` INT NOT NULL COMMENT '字段 group_count',
  `train_sample_count` INT NOT NULL COMMENT '字段 train_sample_count',
  `validation_sample_count` INT NOT NULL COMMENT '字段 validation_sample_count',
  `train_group_count` INT NOT NULL COMMENT '字段 train_group_count',
  `validation_group_count` INT NOT NULL COMMENT '字段 validation_group_count',
  `cutoff_at` TIMESTAMP NULL COMMENT '字段 cutoff_at',
  `feature_names` JSON NOT NULL COMMENT '字段 feature_names',
  `lineage` JSON NOT NULL COMMENT '字段 lineage',
  `leakage_check` JSON NOT NULL COMMENT '字段 leakage_check',
  `built_at` TIMESTAMP NOT NULL COMMENT '字段 built_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_snapshot_version` (`dataset_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI dataset_snapshot';

CREATE TABLE `dataset_split_member` (
  `dataset_snapshot_id` VARCHAR(36) NOT NULL COMMENT '字段 dataset_snapshot_id',
  `point_feature_snapshot_id` VARCHAR(36) NOT NULL COMMENT '字段 point_feature_snapshot_id',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `target_measurement_id` VARCHAR(36) NOT NULL COMMENT '字段 target_measurement_id',
  `group_value` VARCHAR(100) NOT NULL COMMENT '字段 group_value',
  `split` VARCHAR(24) NOT NULL COMMENT '字段 split',
  `target_value` DECIMAL(18,6) NOT NULL COMMENT '字段 target_value',
  `feature_values` JSON NOT NULL COMMENT '字段 feature_values',
  `occurred_at` TIMESTAMP NOT NULL COMMENT '字段 occurred_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_feature_snapshot` (`dataset_snapshot_id`, `point_feature_snapshot_id`),
  KEY `idx_dataset_split_group` (`dataset_snapshot_id`, `split`, `group_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI dataset_split_member';

CREATE TABLE `diagnosis_result` (
  `prediction_result_id` VARCHAR(36) NULL COMMENT '字段 prediction_result_id',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `metric_code` VARCHAR(64) NOT NULL COMMENT '字段 metric_code',
  `summary` VARCHAR(2000) NOT NULL COMMENT '字段 summary',
  `factor_contributions` JSON NOT NULL COMMENT '字段 factor_contributions',
  `confidence` DECIMAL(18,6) NOT NULL COMMENT '字段 confidence',
  `causality_status` VARCHAR(24) NOT NULL DEFAULT 'CORRELATION_ONLY' COMMENT '字段 causality_status',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI diagnosis_result';

CREATE TABLE `durr_application_controller` (
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `model` VARCHAR(120) NOT NULL COMMENT '字段 model',
  `serial_no` VARCHAR(120) NOT NULL COMMENT '字段 serial_no',
  `software_version` VARCHAR(80) NULL COMMENT '字段 software_version',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_durr_controller` (`factory_id`, `code`),
  UNIQUE KEY `uk_serial_no` (`serial_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI durr_application_controller';

CREATE TABLE `durr_robot` (
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `model` VARCHAR(120) NOT NULL COMMENT '字段 model',
  `serial_no` VARCHAR(120) NOT NULL COMMENT '字段 serial_no',
  `controller_software_version` VARCHAR(80) NULL COMMENT '字段 controller_software_version',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_durr_robot` (`factory_id`, `code`),
  UNIQUE KEY `uk_serial_no` (`serial_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI durr_robot';

CREATE TABLE `durr_rotary_atomizer` (
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `controller_id` VARCHAR(36) NULL COMMENT '字段 controller_id',
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `model` VARCHAR(120) NOT NULL COMMENT '字段 model',
  `serial_no` VARCHAR(120) NOT NULL COMMENT '字段 serial_no',
  `bell_cup_type` VARCHAR(120) NULL COMMENT '字段 bell_cup_type',
  `bell_cup_code` VARCHAR(120) NULL COMMENT '字段 bell_cup_code',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_durr_atomizer` (`factory_id`, `code`),
  UNIQUE KEY `uk_serial_no` (`serial_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI durr_rotary_atomizer';

CREATE TABLE `factory` (
  `code` VARCHAR(32) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `site_owner` VARCHAR(80) NULL COMMENT '字段 site_owner',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI factory';

CREATE TABLE `factory_vehicle_model` (
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_vehicle_model` (`factory_id`, `vehicle_model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI factory_vehicle_model';

CREATE TABLE `integration_endpoint` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(160) NOT NULL COMMENT '字段 name',
  `system_type` VARCHAR(32) NOT NULL COMMENT '字段 system_type',
  `direction` VARCHAR(24) NOT NULL DEFAULT 'INBOUND' COMMENT '字段 direction',
  `base_url` VARCHAR(500) NULL COMMENT '字段 base_url',
  `auth_type` VARCHAR(32) NOT NULL DEFAULT 'API_KEY' COMMENT '字段 auth_type',
  `config` JSON NULL COMMENT '字段 config',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `last_success_at` TIMESTAMP NULL COMMENT '字段 last_success_at',
  `last_failure_at` TIMESTAMP NULL COMMENT '字段 last_failure_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI integration_endpoint';

CREATE TABLE `integration_event` (
  `event_no` VARCHAR(80) NOT NULL COMMENT '字段 event_no',
  `endpoint_id` VARCHAR(36) NOT NULL COMMENT '字段 endpoint_id',
  `source_event_id` VARCHAR(160) NOT NULL COMMENT '字段 source_event_id',
  `event_type` VARCHAR(64) NOT NULL COMMENT '字段 event_type',
  `direction` VARCHAR(24) NOT NULL DEFAULT 'INBOUND' COMMENT '字段 direction',
  `status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '字段 status',
  `payload` JSON NOT NULL COMMENT '字段 payload',
  `mapped_payload` JSON NULL COMMENT '字段 mapped_payload',
  `attempt_count` INT NOT NULL DEFAULT 0 COMMENT '字段 attempt_count',
  `max_attempts` INT NOT NULL DEFAULT 3 COMMENT '字段 max_attempts',
  `next_retry_at` TIMESTAMP NULL COMMENT '字段 next_retry_at',
  `last_error` VARCHAR(2000) NULL COMMENT '字段 last_error',
  `processed_at` TIMESTAMP NULL COMMENT '字段 processed_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_endpoint_source_event` (`endpoint_id`, `source_event_id`),
  UNIQUE KEY `uk_event_no` (`event_no`),
  KEY `idx_integration_status_time` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI integration_event';

CREATE TABLE `mat_char_applicability` (
  `characteristic_definition_id` VARCHAR(36) NOT NULL COMMENT '字段 characteristic_definition_id',
  `material_type` VARCHAR(24) NOT NULL COMMENT '字段 material_type',
  `process_stage` VARCHAR(32) NOT NULL COMMENT '字段 process_stage',
  `target_family` VARCHAR(32) NOT NULL COMMENT '字段 target_family',
  `is_required` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 is_required',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mat_char_applicability` (`characteristic_definition_id`, `material_type`, `process_stage`, `target_family`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI mat_char_applicability';

CREATE TABLE `mat_char_definition` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `category` VARCHAR(32) NOT NULL COMMENT '字段 category',
  `canonical_unit` VARCHAR(24) NOT NULL COMMENT '字段 canonical_unit',
  `target_families` JSON NOT NULL COMMENT '字段 target_families',
  `is_model_feature` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_model_feature',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `description` VARCHAR(2000) NULL COMMENT '字段 description',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI mat_char_definition';

CREATE TABLE `material_batch` (
  `batch_no` VARCHAR(64) NOT NULL COMMENT '字段 batch_no',
  `material_code` VARCHAR(64) NOT NULL COMMENT '字段 material_code',
  `material_name` VARCHAR(120) NOT NULL COMMENT '字段 material_name',
  `material_type` VARCHAR(24) NOT NULL COMMENT '字段 material_type',
  `supplier` VARCHAR(120) NULL COMMENT '字段 supplier',
  `viscosity` DECIMAL(18,6) NULL COMMENT '字段 viscosity',
  `solid_ratio` DECIMAL(18,6) NULL COMMENT '字段 solid_ratio',
  `coa_values` JSON NULL COMMENT '字段 coa_values',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_batch_no` (`batch_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI material_batch';

CREATE TABLE `material_batch_test_result` (
  `result_no` VARCHAR(80) NOT NULL COMMENT '字段 result_no',
  `material_batch_id` VARCHAR(36) NOT NULL COMMENT '字段 material_batch_id',
  `characteristic_definition_id` VARCHAR(36) NOT NULL COMMENT '字段 characteristic_definition_id',
  `method_id` VARCHAR(36) NOT NULL COMMENT '字段 method_id',
  `specification_id` VARCHAR(36) NULL COMMENT '字段 specification_id',
  `result_value` DECIMAL(18,6) NOT NULL COMMENT '字段 result_value',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `tested_at` TIMESTAMP NOT NULL COMMENT '字段 tested_at',
  `tested_by` VARCHAR(80) NULL COMMENT '字段 tested_by',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `raw_values` JSON NULL COMMENT '字段 raw_values',
  `reliability_status` VARCHAR(24) NOT NULL DEFAULT 'UNVERIFIED' COMMENT '字段 reliability_status',
  `reliability_issues` JSON NULL COMMENT '字段 reliability_issues',
  `is_within_spec` INT UNSIGNED NULL COMMENT '字段 is_within_spec',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_result_no` (`result_no`),
  KEY `idx_mat_result_batch_char_time` (`material_batch_id`, `characteristic_definition_id`, `tested_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI material_batch_test_result';

CREATE TABLE `material_specification` (
  `material_code` VARCHAR(64) NOT NULL COMMENT '字段 material_code',
  `characteristic_definition_id` VARCHAR(36) NOT NULL COMMENT '字段 characteristic_definition_id',
  `method_id` VARCHAR(36) NOT NULL COMMENT '字段 method_id',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `lower_limit` DECIMAL(18,6) NULL COMMENT '字段 lower_limit',
  `upper_limit` DECIMAL(18,6) NULL COMMENT '字段 upper_limit',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `effective_from` TIMESTAMP NULL COMMENT '字段 effective_from',
  `effective_to` TIMESTAMP NULL COMMENT '字段 effective_to',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mat_spec_ver` (`material_code`, `characteristic_definition_id`, `method_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI material_specification';

CREATE TABLE `material_test_method` (
  `characteristic_definition_id` VARCHAR(36) NOT NULL COMMENT '字段 characteristic_definition_id',
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `method_type` VARCHAR(64) NOT NULL COMMENT '字段 method_type',
  `result_unit` VARCHAR(24) NOT NULL COMMENT '字段 result_unit',
  `procedure_uri` VARCHAR(500) NULL COMMENT '字段 procedure_uri',
  `conditions` JSON NULL COMMENT '字段 conditions',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_material_test_method_version` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI material_test_method';

CREATE TABLE `measurement_calibration_record` (
  `calibration_no` VARCHAR(64) NOT NULL COMMENT '字段 calibration_no',
  `instrument_id` VARCHAR(36) NOT NULL COMMENT '字段 instrument_id',
  `method_id` VARCHAR(36) NULL COMMENT '字段 method_id',
  `reference_standard_id` VARCHAR(36) NULL COMMENT '字段 reference_standard_id',
  `calibrated_at` TIMESTAMP NOT NULL COMMENT '字段 calibrated_at',
  `valid_until` TIMESTAMP NOT NULL COMMENT '字段 valid_until',
  `result` VARCHAR(24) NOT NULL COMMENT '字段 result',
  `performed_by` VARCHAR(80) NOT NULL COMMENT '字段 performed_by',
  `certificate_uri` VARCHAR(500) NULL COMMENT '字段 certificate_uri',
  `check_values` JSON NULL COMMENT '字段 check_values',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_calibration_no` (`calibration_no`),
  KEY `idx_calibration_instrument_time` (`instrument_id`, `calibrated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_calibration_record';

CREATE TABLE `measurement_group` (
  `code` VARCHAR(48) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `expected_point_count` INT NULL COMMENT '字段 expected_point_count',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_model_code` (`vehicle_model_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_group';

CREATE TABLE `measurement_group_point` (
  `measurement_group_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_group_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `sequence_no` INT NOT NULL DEFAULT 0 COMMENT '字段 sequence_no',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_point` (`measurement_group_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_group_point';

CREATE TABLE `measurement_import_profile` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `instrument_type` VARCHAR(32) NOT NULL COMMENT '字段 instrument_type',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `schema_version` VARCHAR(64) NOT NULL COMMENT '字段 schema_version',
  `field_mapping` JSON NOT NULL COMMENT '字段 field_mapping',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_meas_import_profile_ver` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_import_profile';

CREATE TABLE `measurement_instrument` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `manufacturer` VARCHAR(80) NOT NULL COMMENT '字段 manufacturer',
  `model` VARCHAR(120) NOT NULL COMMENT '字段 model',
  `instrument_type` VARCHAR(32) NOT NULL COMMENT '字段 instrument_type',
  `serial_no` VARCHAR(120) NOT NULL COMMENT '字段 serial_no',
  `firmware_version` VARCHAR(64) NULL COMMENT '字段 firmware_version',
  `supported_quality_types` JSON NOT NULL COMMENT '字段 supported_quality_types',
  `calibration_required` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 calibration_required',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  UNIQUE KEY `uk_serial_no` (`serial_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_instrument';

CREATE TABLE `measurement_method` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `instrument_type` VARCHAR(32) NOT NULL COMMENT '字段 instrument_type',
  `method_type` VARCHAR(64) NOT NULL COMMENT '字段 method_type',
  `probe_code` VARCHAR(64) NULL COMMENT '字段 probe_code',
  `substrate_type` VARCHAR(80) NULL COMMENT '字段 substrate_type',
  `geometry_class` VARCHAR(80) NULL COMMENT '字段 geometry_class',
  `layer_scope` VARCHAR(80) NULL COMMENT '字段 layer_scope',
  `requires_reference` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 requires_reference',
  `requires_direction` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 requires_direction',
  `minimum_repeats` INT NOT NULL DEFAULT 1 COMMENT '字段 minimum_repeats',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `instructions` VARCHAR(2000) NULL COMMENT '字段 instructions',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_method_version` (`code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_method';

CREATE TABLE `measurement_point` (
  `code` VARCHAR(48) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `part_id` VARCHAR(36) NOT NULL COMMENT '字段 part_id',
  `point_type` VARCHAR(32) NOT NULL DEFAULT 'QUALITY' COMMENT '字段 point_type',
  `region` VARCHAR(80) NULL COMMENT '字段 region',
  `quality_types` JSON NOT NULL COMMENT '字段 quality_types',
  `is_match_point` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 is_match_point',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_point_model_code` (`vehicle_model_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_point';

CREATE TABLE `measurement_reference_standard` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `serial_no` VARCHAR(120) NULL COMMENT '字段 serial_no',
  `certificate_no` VARCHAR(120) NULL COMMENT '字段 certificate_no',
  `valid_from` TIMESTAMP NULL COMMENT '字段 valid_from',
  `valid_until` TIMESTAMP NULL COMMENT '字段 valid_until',
  `reference_values` JSON NULL COMMENT '字段 reference_values',
  `status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT '字段 status',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_reference_standard';

CREATE TABLE `measurement_repeat_reading` (
  `measurement_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_id',
  `repeat_no` INT NOT NULL COMMENT '字段 repeat_no',
  `metric_code` VARCHAR(64) NOT NULL COMMENT '字段 metric_code',
  `raw_value` DECIMAL(18,6) NOT NULL COMMENT '字段 raw_value',
  `corrected_value` DECIMAL(18,6) NULL COMMENT '字段 corrected_value',
  `unit` VARCHAR(24) NULL COMMENT '字段 unit',
  `is_valid` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_valid',
  `invalid_reason` VARCHAR(240) NULL COMMENT '字段 invalid_reason',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_repeat_metric` (`measurement_id`, `repeat_no`, `metric_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI measurement_repeat_reading';

CREATE TABLE `model_acceptance_decision` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `dataset_snapshot_id` VARCHAR(36) NOT NULL COMMENT '字段 dataset_snapshot_id',
  `decision` VARCHAR(24) NOT NULL COMMENT '字段 decision',
  `criteria` JSON NOT NULL COMMENT '字段 criteria',
  `checks` JSON NOT NULL COMMENT '字段 checks',
  `decided_by` VARCHAR(80) NOT NULL COMMENT '字段 decided_by',
  `decided_at` TIMESTAMP NOT NULL COMMENT '字段 decided_at',
  `comment` VARCHAR(2000) NULL COMMENT '字段 comment',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  KEY `idx_model_accept_decision_time` (`model_version_id`, `decided_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_acceptance_decision';

CREATE TABLE `model_acceptance_policy` (
  `policy_code` VARCHAR(64) NOT NULL COMMENT '字段 policy_code',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `target_metric` VARCHAR(64) NOT NULL COMMENT '字段 target_metric',
  `policy_type` VARCHAR(24) NOT NULL DEFAULT 'FACTORY_APPROVED' COMMENT '字段 policy_type',
  `max_validation_rmse` DECIMAL(18,6) NOT NULL COMMENT '字段 max_validation_rmse',
  `min_validation_r2` DECIMAL(18,6) NOT NULL COMMENT '字段 min_validation_r2',
  `min_train_groups` INT NOT NULL COMMENT '字段 min_train_groups',
  `min_validation_groups` INT NOT NULL COMMENT '字段 min_validation_groups',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NOT NULL COMMENT '字段 source_uri',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_accept_policy_ver` (`policy_code`, `version`),
  KEY `idx_model_accept_policy_match` (`factory_id`, `target_metric`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_acceptance_policy';

CREATE TABLE `model_applicability_scope` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `color_id` VARCHAR(36) NOT NULL COMMENT '字段 color_id',
  `status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '字段 status',
  `source` VARCHAR(32) NOT NULL DEFAULT 'DATASET_DERIVED' COMMENT '字段 source',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_applicability_context` (`model_version_id`, `factory_id`, `vehicle_model_id`, `color_id`),
  KEY `idx_model_applicability_status` (`model_version_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_applicability_scope';

CREATE TABLE `model_artifact` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `artifact_type` VARCHAR(48) NOT NULL COMMENT '字段 artifact_type',
  `artifact_uri` VARCHAR(500) NOT NULL COMMENT '字段 artifact_uri',
  `storage_backend` VARCHAR(32) NOT NULL DEFAULT 'MYSQL' COMMENT '字段 storage_backend',
  `payload_hash` VARCHAR(64) NOT NULL COMMENT '字段 payload_hash',
  `metadata_payload` JSON NOT NULL COMMENT '字段 metadata_payload',
  `status` VARCHAR(24) NOT NULL DEFAULT 'REGISTERED' COMMENT '字段 status',
  `created_by` VARCHAR(80) NOT NULL DEFAULT 'system' COMMENT '字段 created_by',
  `registered_at` TIMESTAMP NOT NULL COMMENT '字段 registered_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_artifact_type` (`model_version_id`, `artifact_type`),
  KEY `idx_model_artifact_status` (`model_version_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_artifact';

CREATE TABLE `model_ood_policy` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `max_abs_standardized_shift` DECIMAL(18,6) NOT NULL COMMENT '字段 max_abs_standardized_shift',
  `max_outlier_feature_ratio` DECIMAL(18,6) NOT NULL COMMENT '字段 max_outlier_feature_ratio',
  `min_feature_completeness` DECIMAL(18,6) NOT NULL COMMENT '字段 min_feature_completeness',
  `action` VARCHAR(24) NOT NULL DEFAULT 'BLOCK' COMMENT '字段 action',
  `status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '字段 status',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_ood_policy_version` (`model_version_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_ood_policy';

CREATE TABLE `model_validation_fold` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `dataset_snapshot_id` VARCHAR(36) NOT NULL COMMENT '字段 dataset_snapshot_id',
  `validation_axis` VARCHAR(48) NOT NULL COMMENT '字段 validation_axis',
  `fold_key` VARCHAR(120) NOT NULL COMMENT '字段 fold_key',
  `train_sample_count` INT NOT NULL COMMENT '字段 train_sample_count',
  `validation_sample_count` INT NOT NULL COMMENT '字段 validation_sample_count',
  `train_group_count` INT NOT NULL COMMENT '字段 train_group_count',
  `validation_group_count` INT NOT NULL COMMENT '字段 validation_group_count',
  `metrics` JSON NOT NULL COMMENT '字段 metrics',
  `status` VARCHAR(32) NOT NULL COMMENT '字段 status',
  `evaluated_at` TIMESTAMP NOT NULL COMMENT '字段 evaluated_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_validation_fold` (`model_version_id`, `validation_axis`, `fold_key`),
  KEY `idx_model_validation_axis` (`model_version_id`, `validation_axis`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_validation_fold';

CREATE TABLE `model_version` (
  `model_code` VARCHAR(64) NOT NULL COMMENT '字段 model_code',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `model_type` VARCHAR(32) NOT NULL COMMENT '字段 model_type',
  `target_metric` VARCHAR(64) NOT NULL COMMENT '字段 target_metric',
  `feature_set_version` VARCHAR(64) NOT NULL COMMENT '字段 feature_set_version',
  `artifact_uri` VARCHAR(500) NOT NULL COMMENT '字段 artifact_uri',
  `dataset_snapshot_id` VARCHAR(36) NULL COMMENT '字段 dataset_snapshot_id',
  `model_payload` JSON NOT NULL COMMENT '字段 model_payload',
  `evaluation_metrics` JSON NOT NULL COMMENT '字段 evaluation_metrics',
  `training_sample_count` INT NOT NULL DEFAULT 0 COMMENT '字段 training_sample_count',
  `trained_at` TIMESTAMP NULL COMMENT '字段 trained_at',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_version` (`model_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI model_version';

CREATE TABLE `parameter_constraint_source` (
  `parameter_definition_id` VARCHAR(36) NOT NULL COMMENT '字段 parameter_definition_id',
  `factory_id` VARCHAR(36) NULL COMMENT '字段 factory_id',
  `process_stage` VARCHAR(32) NULL COMMENT '字段 process_stage',
  `constraint_code` VARCHAR(96) NOT NULL COMMENT '字段 constraint_code',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `source_type` VARCHAR(32) NOT NULL COMMENT '字段 source_type',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `lower_limit` DECIMAL(18,6) NOT NULL COMMENT '字段 lower_limit',
  `upper_limit` DECIMAL(18,6) NOT NULL COMMENT '字段 upper_limit',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `effective_from` TIMESTAMP NULL COMMENT '字段 effective_from',
  `effective_to` TIMESTAMP NULL COMMENT '字段 effective_to',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_param_constraint_code` (`constraint_code`),
  KEY `idx_param_constraint_lookup` (`parameter_definition_id`, `factory_id`, `process_stage`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI parameter_constraint_source';

CREATE TABLE `parameter_definition` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `category` VARCHAR(32) NOT NULL COMMENT '字段 category',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `aggregation_method` VARCHAR(32) NOT NULL DEFAULT 'WEIGHTED_AVERAGE' COMMENT '字段 aggregation_method',
  `hard_min` DECIMAL(18,6) NULL COMMENT '字段 hard_min',
  `hard_max` DECIMAL(18,6) NULL COMMENT '字段 hard_max',
  `is_recommendable` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_recommendable',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI parameter_definition';

CREATE TABLE `part` (
  `code` VARCHAR(32) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `material` VARCHAR(80) NULL COMMENT '字段 material',
  `region` VARCHAR(80) NULL COMMENT '字段 region',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI part';

CREATE TABLE `path_segment_execution` (
  `device_execution_id` VARCHAR(36) NOT NULL COMMENT '字段 device_execution_id',
  `path_segment_id` VARCHAR(36) NOT NULL COMMENT '字段 path_segment_id',
  `actual_speed` DECIMAL(18,6) NULL COMMENT '字段 actual_speed',
  `speed_unit` VARCHAR(24) NULL COMMENT '字段 speed_unit',
  `trigger_state` VARCHAR(24) NULL COMMENT '字段 trigger_state',
  `actual_values` JSON NULL COMMENT '字段 actual_values',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_path_segment_execution` (`device_execution_id`, `path_segment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI path_segment_execution';

CREATE TABLE `permission` (
  `code` VARCHAR(100) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(160) NOT NULL COMMENT '字段 name',
  `description` VARCHAR(2000) NULL COMMENT '字段 description',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI permission';

CREATE TABLE `point_contribution_entry` (
  `contribution_version_id` VARCHAR(36) NOT NULL COMMENT '字段 contribution_version_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `brush_id` VARCHAR(36) NULL COMMENT '字段 brush_id',
  `path_segment_id` VARCHAR(36) NULL COMMENT '字段 path_segment_id',
  `source_key` VARCHAR(100) NOT NULL COMMENT '字段 source_key',
  `overlap_ratio` DECIMAL(18,6) NOT NULL COMMENT '字段 overlap_ratio',
  `contribution_weight` DECIMAL(18,6) NOT NULL COMMENT '字段 contribution_weight',
  `validation_score` DECIMAL(18,6) NULL COMMENT '字段 validation_score',
  `evidence` JSON NULL COMMENT '字段 evidence',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ver_point_contrib_src` (`contribution_version_id`, `measurement_point_id`, `source_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI point_contribution_entry';

CREATE TABLE `point_contribution_version` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `target_family` VARCHAR(32) NOT NULL COMMENT '字段 target_family',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `method` VARCHAR(32) NOT NULL COMMENT '字段 method',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `evidence_uri` VARCHAR(500) NULL COMMENT '字段 evidence_uri',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prog_target_contrib_ver` (`program_version_id`, `target_family`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI point_contribution_version';

CREATE TABLE `point_feature_snapshot` (
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `feature_set_version` VARCHAR(64) NOT NULL COMMENT '字段 feature_set_version',
  `target_family` VARCHAR(32) NOT NULL DEFAULT 'ORANGE_PEEL' COMMENT '字段 target_family',
  `feature_values` JSON NOT NULL COMMENT '字段 feature_values',
  `lineage` JSON NOT NULL COMMENT '字段 lineage',
  `completeness_score` DECIMAL(18,6) NOT NULL COMMENT '字段 completeness_score',
  `generated_at` TIMESTAMP NOT NULL COMMENT '字段 generated_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_point_feature_ver` (`production_run_id`, `measurement_point_id`, `feature_set_version`, `target_family`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI point_feature_snapshot';

CREATE TABLE `prediction_result` (
  `model_version_id` VARCHAR(36) NOT NULL COMMENT '字段 model_version_id',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `metric_code` VARCHAR(64) NOT NULL COMMENT '字段 metric_code',
  `predicted_value` DECIMAL(18,6) NOT NULL COMMENT '字段 predicted_value',
  `lower_bound` DECIMAL(18,6) NULL COMMENT '字段 lower_bound',
  `upper_bound` DECIMAL(18,6) NULL COMMENT '字段 upper_bound',
  `confidence` DECIMAL(18,6) NOT NULL COMMENT '字段 confidence',
  `applicability_status` VARCHAR(24) NOT NULL DEFAULT 'LEGACY_UNGOVERNED' COMMENT '字段 applicability_status',
  `ood_status` VARCHAR(24) NOT NULL DEFAULT 'LEGACY_UNGOVERNED' COMMENT '字段 ood_status',
  `governance_evidence` JSON NULL COMMENT '字段 governance_evidence',
  `predicted_at` TIMESTAMP NOT NULL COMMENT '字段 predicted_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  KEY `idx_prediction_run_point` (`production_run_id`, `measurement_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI prediction_result';

CREATE TABLE `production_device_execution` (
  `production_stage_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_stage_run_id',
  `device_configuration_id` VARCHAR(36) NOT NULL COMMENT '字段 device_configuration_id',
  `trajectory_program_id` VARCHAR(36) NOT NULL COMMENT '字段 trajectory_program_id',
  `executed_checksum` VARCHAR(128) NOT NULL COMMENT '字段 executed_checksum',
  `started_at` TIMESTAMP NULL COMMENT '字段 started_at',
  `completed_at` TIMESTAMP NULL COMMENT '字段 completed_at',
  `status` VARCHAR(24) NOT NULL DEFAULT 'COMPLETED' COMMENT '字段 status',
  `source_system` VARCHAR(80) NULL COMMENT '字段 source_system',
  `deviation_details` JSON NULL COMMENT '字段 deviation_details',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_stage_device_execution` (`production_stage_run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI production_device_execution';

CREATE TABLE `production_run` (
  `run_no` VARCHAR(64) NOT NULL COMMENT '字段 run_no',
  `body_no` VARCHAR(64) NULL COMMENT '字段 body_no',
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `color_id` VARCHAR(36) NOT NULL COMMENT '字段 color_id',
  `shift` VARCHAR(24) NULL COMMENT '字段 shift',
  `started_at` TIMESTAMP NOT NULL COMMENT '字段 started_at',
  `completed_at` TIMESTAMP NULL COMMENT '字段 completed_at',
  `context_values` JSON NULL COMMENT '字段 context_values',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_no` (`run_no`),
  KEY `idx_production_body_no` (`body_no`),
  KEY `idx_production_run_context` (`factory_id`, `vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI production_run';

CREATE TABLE `production_stage_run` (
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `process_stage` VARCHAR(32) NOT NULL COMMENT '字段 process_stage',
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `material_batch_id` VARCHAR(36) NULL COMMENT '字段 material_batch_id',
  `actual_parameters` JSON NULL COMMENT '字段 actual_parameters',
  `status` VARCHAR(24) NOT NULL DEFAULT 'COMPLETED' COMMENT '字段 status',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_stage` (`production_run_id`, `process_stage`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI production_stage_run';

CREATE TABLE `program_color` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `color_id` VARCHAR(36) NOT NULL COMMENT '字段 color_id',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_color` (`program_version_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI program_color';

CREATE TABLE `program_device_configuration` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `robot_id` VARCHAR(36) NOT NULL COMMENT '字段 robot_id',
  `atomizer_id` VARCHAR(36) NOT NULL COMMENT '字段 atomizer_id',
  `controller_id` VARCHAR(36) NOT NULL COMMENT '字段 controller_id',
  `configuration_version` VARCHAR(32) NOT NULL COMMENT '字段 configuration_version',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `effective_from` TIMESTAMP NULL COMMENT '字段 effective_from',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prog_device_config_ver` (`program_version_id`, `configuration_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI program_device_configuration';

CREATE TABLE `program_rollback_execution` (
  `rollback_no` VARCHAR(64) NOT NULL COMMENT '字段 rollback_no',
  `recommendation_id` VARCHAR(36) NOT NULL COMMENT '字段 recommendation_id',
  `controlled_trial_id` VARCHAR(36) NOT NULL COMMENT '字段 controlled_trial_id',
  `rollback_to_program_version_id` VARCHAR(36) NULL COMMENT '字段 rollback_to_program_version_id',
  `rollback_reason` VARCHAR(2000) NOT NULL COMMENT '字段 rollback_reason',
  `execution_note` VARCHAR(2000) NULL COMMENT '字段 execution_note',
  `executed_by` VARCHAR(80) NOT NULL COMMENT '字段 executed_by',
  `executed_at` TIMESTAMP NOT NULL COMMENT '字段 executed_at',
  `status` VARCHAR(24) NOT NULL DEFAULT 'EXECUTED' COMMENT '字段 status',
  `action_snapshot` JSON NOT NULL COMMENT '字段 action_snapshot',
  `verified_by` VARCHAR(80) NULL COMMENT '字段 verified_by',
  `verified_at` TIMESTAMP NULL COMMENT '字段 verified_at',
  `verification_comment` VARCHAR(2000) NULL COMMENT '字段 verification_comment',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_rollback_no` (`rollback_no`),
  UNIQUE KEY `uk_rollback_controlled_trial` (`controlled_trial_id`),
  KEY `idx_program_rollback_status` (`status`, `executed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI program_rollback_execution';

CREATE TABLE `program_vehicle_model` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_model` (`program_version_id`, `vehicle_model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI program_vehicle_model';

CREATE TABLE `quality_measurement` (
  `data_no` VARCHAR(64) NOT NULL COMMENT '字段 data_no',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_group_id` VARCHAR(36) NULL COMMENT '字段 measurement_group_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `data_type` VARCHAR(24) NOT NULL DEFAULT 'TEST' COMMENT '字段 data_type',
  `measured_at` TIMESTAMP NOT NULL COMMENT '字段 measured_at',
  `measured_by` VARCHAR(80) NULL COMMENT '字段 measured_by',
  `device_code` VARCHAR(64) NULL COMMENT '字段 device_code',
  `instrument_id` VARCHAR(36) NULL COMMENT '字段 instrument_id',
  `measurement_method_id` VARCHAR(36) NULL COMMENT '字段 measurement_method_id',
  `calibration_record_id` VARCHAR(36) NULL COMMENT '字段 calibration_record_id',
  `reference_standard_id` VARCHAR(36) NULL COMMENT '字段 reference_standard_id',
  `import_profile_id` VARCHAR(36) NULL COMMENT '字段 import_profile_id',
  `measurement_direction` VARCHAR(32) NULL COMMENT '字段 measurement_direction',
  `raw_file_uri` VARCHAR(500) NULL COMMENT '字段 raw_file_uri',
  `reliability_status` VARCHAR(24) NOT NULL DEFAULT 'UNVERIFIED' COMMENT '字段 reliability_status',
  `reliability_issues` JSON NULL COMMENT '字段 reliability_issues',
  `status_score` DECIMAL(18,6) NULL COMMENT '字段 status_score',
  `is_valid` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_valid',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_data_no` (`data_no`),
  KEY `idx_quality_point_time` (`measurement_point_id`, `measured_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI quality_measurement';

CREATE TABLE `quality_metric_definition` (
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `unit` VARCHAR(24) NULL COMMENT '字段 unit',
  `display_order` INT NOT NULL DEFAULT 0 COMMENT '字段 display_order',
  `is_primary` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 is_primary',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_quality_type_metric_code` (`quality_type`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI quality_metric_definition';

CREATE TABLE `quality_metric_value` (
  `measurement_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_id',
  `metric_code` VARCHAR(64) NOT NULL COMMENT '字段 metric_code',
  `metric_name` VARCHAR(120) NOT NULL COMMENT '字段 metric_name',
  `raw_value` DECIMAL(18,6) NOT NULL COMMENT '字段 raw_value',
  `corrected_value` DECIMAL(18,6) NULL COMMENT '字段 corrected_value',
  `unit` VARCHAR(24) NULL COMMENT '字段 unit',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_measurement_metric` (`measurement_id`, `metric_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI quality_metric_value';

CREATE TABLE `quality_standard` (
  `standard_no` VARCHAR(64) NOT NULL COMMENT '字段 standard_no',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `standard_type` VARCHAR(24) NOT NULL DEFAULT 'PRODUCTION' COMMENT '字段 standard_type',
  `quality_type` VARCHAR(32) NOT NULL COMMENT '字段 quality_type',
  `metric_code` VARCHAR(64) NOT NULL COMMENT '字段 metric_code',
  `vehicle_model_id` VARCHAR(36) NULL COMMENT '字段 vehicle_model_id',
  `color_id` VARCHAR(36) NULL COMMENT '字段 color_id',
  `part_id` VARCHAR(36) NULL COMMENT '字段 part_id',
  `measurement_point_id` VARCHAR(36) NULL COMMENT '字段 measurement_point_id',
  `min_value` DECIMAL(18,6) NULL COMMENT '字段 min_value',
  `max_value` DECIMAL(18,6) NULL COMMENT '字段 max_value',
  `unit` VARCHAR(24) NULL COMMENT '字段 unit',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  KEY `idx_standard_match` (`quality_type`, `metric_code`, `vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI quality_standard';

CREATE TABLE `recommendation` (
  `recommendation_no` VARCHAR(64) NOT NULL COMMENT '字段 recommendation_no',
  `production_run_id` VARCHAR(36) NOT NULL COMMENT '字段 production_run_id',
  `measurement_point_id` VARCHAR(36) NOT NULL COMMENT '字段 measurement_point_id',
  `target_quality_type` VARCHAR(32) NOT NULL COMMENT '字段 target_quality_type',
  `target_metric` VARCHAR(64) NOT NULL COMMENT '字段 target_metric',
  `diagnosis_summary` VARCHAR(2000) NOT NULL COMMENT '字段 diagnosis_summary',
  `predicted_improvement` DECIMAL(18,6) NOT NULL COMMENT '字段 predicted_improvement',
  `confidence` DECIMAL(18,6) NOT NULL COMMENT '字段 confidence',
  `status` VARCHAR(24) NOT NULL DEFAULT 'PENDING' COMMENT '字段 status',
  `model_version` VARCHAR(64) NOT NULL COMMENT '字段 model_version',
  `constraints_checked` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 constraints_checked',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `executed_by` VARCHAR(80) NULL COMMENT '字段 executed_by',
  `executed_at` TIMESTAMP NULL COMMENT '字段 executed_at',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recommendation_no` (`recommendation_no`),
  KEY `idx_recommendation_status` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI recommendation';

CREATE TABLE `recommendation_action` (
  `recommendation_id` VARCHAR(36) NOT NULL COMMENT '字段 recommendation_id',
  `process_stage` VARCHAR(32) NOT NULL COMMENT '字段 process_stage',
  `brush_no` VARCHAR(32) NULL COMMENT '字段 brush_no',
  `parameter_code` VARCHAR(64) NOT NULL COMMENT '字段 parameter_code',
  `parameter_name` VARCHAR(120) NOT NULL COMMENT '字段 parameter_name',
  `current_value` DECIMAL(18,6) NOT NULL COMMENT '字段 current_value',
  `recommended_value` DECIMAL(18,6) NOT NULL COMMENT '字段 recommended_value',
  `executed_value` DECIMAL(18,6) NULL COMMENT '字段 executed_value',
  `unit` VARCHAR(24) NOT NULL COMMENT '字段 unit',
  `hard_min` DECIMAL(18,6) NULL COMMENT '字段 hard_min',
  `hard_max` DECIMAL(18,6) NULL COMMENT '字段 hard_max',
  `constraint_source_id` VARCHAR(36) NULL COMMENT '字段 constraint_source_id',
  `constraint_source_code` VARCHAR(96) NULL COMMENT '字段 constraint_source_code',
  `constraint_source_version` VARCHAR(32) NULL COMMENT '字段 constraint_source_version',
  `constraint_source_type` VARCHAR(32) NULL COMMENT '字段 constraint_source_type',
  `constraint_source_uri` VARCHAR(500) NULL COMMENT '字段 constraint_source_uri',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI recommendation_action';

CREATE TABLE `role` (
  `code` VARCHAR(64) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `description` VARCHAR(2000) NULL COMMENT '字段 description',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI role';

CREATE TABLE `role_permission` (
  `role_id` VARCHAR(36) NOT NULL COMMENT '字段 role_id',
  `permission_id` VARCHAR(36) NOT NULL COMMENT '字段 permission_id',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI role_permission';

CREATE TABLE `spray_program` (
  `program_code` VARCHAR(64) NOT NULL COMMENT '字段 program_code',
  `name` VARCHAR(160) NOT NULL COMMENT '字段 name',
  `factory_id` VARCHAR(36) NOT NULL COMMENT '字段 factory_id',
  `process_stage` VARCHAR(32) NOT NULL COMMENT '字段 process_stage',
  `station_code` VARCHAR(32) NOT NULL COMMENT '字段 station_code',
  `station_name` VARCHAR(120) NOT NULL COMMENT '字段 station_name',
  `robot_model` VARCHAR(120) NULL COMMENT '字段 robot_model',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_factory_program_code` (`factory_id`, `program_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI spray_program';

CREATE TABLE `spray_program_version` (
  `spray_program_id` VARCHAR(36) NOT NULL COMMENT '字段 spray_program_id',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `source_type` VARCHAR(24) NOT NULL DEFAULT 'MANUAL' COMMENT '字段 source_type',
  `is_master_sample` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '字段 is_master_sample',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `effective_from` TIMESTAMP NULL COMMENT '字段 effective_from',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_version` (`spray_program_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI spray_program_version';

CREATE TABLE `trajectory_path_segment` (
  `trajectory_program_id` VARCHAR(36) NOT NULL COMMENT '字段 trajectory_program_id',
  `segment_no` INT NOT NULL COMMENT '字段 segment_no',
  `name` VARCHAR(160) NOT NULL COMMENT '字段 name',
  `brush_id` VARCHAR(36) NULL COMMENT '字段 brush_id',
  `part_id` VARCHAR(36) NULL COMMENT '字段 part_id',
  `tcp_name` VARCHAR(120) NULL COMMENT '字段 tcp_name',
  `configured_speed` DECIMAL(18,6) NULL COMMENT '字段 configured_speed',
  `speed_unit` VARCHAR(24) NULL COMMENT '字段 speed_unit',
  `start_position` JSON NULL COMMENT '字段 start_position',
  `end_position` JSON NULL COMMENT '字段 end_position',
  `orientation` JSON NULL COMMENT '字段 orientation',
  `trigger_state` VARCHAR(24) NOT NULL DEFAULT 'ON' COMMENT '字段 trigger_state',
  `trigger_start_ms` DECIMAL(18,6) NULL COMMENT '字段 trigger_start_ms',
  `trigger_end_ms` DECIMAL(18,6) NULL COMMENT '字段 trigger_end_ms',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trajectory_path_segment_no` (`trajectory_program_id`, `segment_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI trajectory_path_segment';

CREATE TABLE `trajectory_program` (
  `program_version_id` VARCHAR(36) NOT NULL COMMENT '字段 program_version_id',
  `trajectory_code` VARCHAR(64) NOT NULL COMMENT '字段 trajectory_code',
  `name` VARCHAR(160) NOT NULL COMMENT '字段 name',
  `version` VARCHAR(32) NOT NULL COMMENT '字段 version',
  `checksum` VARCHAR(128) NOT NULL COMMENT '字段 checksum',
  `coordinate_system` VARCHAR(80) NULL COMMENT '字段 coordinate_system',
  `tcp_name` VARCHAR(120) NULL COMMENT '字段 tcp_name',
  `status` VARCHAR(24) NOT NULL DEFAULT 'DRAFT' COMMENT '字段 status',
  `source_uri` VARCHAR(500) NULL COMMENT '字段 source_uri',
  `approved_by` VARCHAR(80) NULL COMMENT '字段 approved_by',
  `approved_at` TIMESTAMP NULL COMMENT '字段 approved_at',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_program_trajectory_version` (`program_version_id`, `trajectory_code`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI trajectory_program';

CREATE TABLE `user_role` (
  `user_id` VARCHAR(36) NOT NULL COMMENT '字段 user_id',
  `role_id` VARCHAR(36) NOT NULL COMMENT '字段 role_id',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI user_role';

CREATE TABLE `user_session` (
  `user_id` VARCHAR(36) NOT NULL COMMENT '字段 user_id',
  `token_hash` VARCHAR(64) NOT NULL COMMENT '字段 token_hash',
  `issued_at` TIMESTAMP NOT NULL COMMENT '字段 issued_at',
  `expires_at` TIMESTAMP NOT NULL COMMENT '字段 expires_at',
  `revoked_at` TIMESTAMP NULL COMMENT '字段 revoked_at',
  `last_seen_at` TIMESTAMP NULL COMMENT '字段 last_seen_at',
  `user_agent` VARCHAR(500) NULL COMMENT '字段 user_agent',
  `client_ip` VARCHAR(64) NULL COMMENT '字段 client_ip',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_token_hash` (`token_hash`),
  KEY `idx_user_session_user` (`user_id`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI user_session';

CREATE TABLE `vehicle_model` (
  `code` VARCHAR(32) NOT NULL COMMENT '字段 code',
  `name` VARCHAR(120) NOT NULL COMMENT '字段 name',
  `remark` VARCHAR(2000) NULL COMMENT '字段 remark',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI vehicle_model';

CREATE TABLE `vehicle_model_color` (
  `vehicle_model_id` VARCHAR(36) NOT NULL COMMENT '字段 vehicle_model_id',
  `color_id` VARCHAR(36) NOT NULL COMMENT '字段 color_id',
  `is_active` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '字段 is_active',
  `id` VARCHAR(36) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '字段 created_at',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '字段 updated_at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_vehicle_model_color` (`vehicle_model_id`, `color_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='PQ-AI vehicle_model_color';

-- Logical references for application-layer enforcement; no physical reference constraints are emitted.
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
-- measurement_point.vehicle_model_id -> vehicle_model.id
-- measurement_point.part_id -> part.id
-- measurement_repeat_reading.measurement_id -> quality_measurement.id
-- model_acceptance_decision.model_version_id -> model_version.id
-- model_acceptance_decision.dataset_snapshot_id -> dataset_snapshot.id
-- model_acceptance_policy.factory_id -> factory.id
-- model_applicability_scope.model_version_id -> model_version.id
-- model_applicability_scope.factory_id -> factory.id
-- model_applicability_scope.vehicle_model_id -> vehicle_model.id
-- model_applicability_scope.color_id -> color.id
-- model_artifact.model_version_id -> model_version.id
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
-- quality_measurement.production_run_id -> production_run.id
-- quality_measurement.measurement_group_id -> measurement_group.id
-- quality_measurement.measurement_point_id -> measurement_point.id
-- quality_measurement.instrument_id -> measurement_instrument.id
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
-- trajectory_path_segment.trajectory_program_id -> trajectory_program.id
-- trajectory_path_segment.brush_id -> brush.id
-- trajectory_path_segment.part_id -> part.id
-- trajectory_program.program_version_id -> spray_program_version.id
-- user_role.user_id -> app_user.id
-- user_role.role_id -> role.id
-- user_session.user_id -> app_user.id
-- vehicle_model_color.vehicle_model_id -> vehicle_model.id
-- vehicle_model_color.color_id -> color.id
