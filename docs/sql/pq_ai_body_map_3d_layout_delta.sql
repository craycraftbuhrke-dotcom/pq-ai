-- PQ-AI body-map 3D measurement point layout delta SQL for DBA approval.
-- Review material only. Application code, Docker, CI, tests, and seed scripts must never run this file automatically.
-- No physical foreign keys are declared; all references are logical *_id fields enforced by application services.
-- Runtime MySQL policy still forbids automatic DELETE/CREATE/DROP/ALTER/TRUNCATE/REPLACE/SET.
-- One ACTIVE 3D layout per measurement_point; soft-retire via row_status=INACTIVE.
-- Coordinate frame: vehicle local space matching the GLB (default Y-up); bounds/unitScale live in view-models.json.

CREATE TABLE `measurement_point_3d_layout` (
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '逻辑引用 measurement_point.id',
  `pos_x` DOUBLE NOT NULL COMMENT '车身局部坐标 X',
  `pos_y` DOUBLE NOT NULL COMMENT '车身局部坐标 Y',
  `pos_z` DOUBLE NOT NULL COMMENT '车身局部坐标 Z',
  `normal_x` DOUBLE NULL COMMENT '表面法向 X（可选）',
  `normal_y` DOUBLE NULL COMMENT '表面法向 Y（可选）',
  `normal_z` DOUBLE NULL COMMENT '表面法向 Z（可选）',
  `model_asset_key` VARCHAR(120) NULL COMMENT '绑定数模版本/路径键，换模后提示重标定',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/INACTIVE；移除仅停用',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_point_3d_layout_point` (`measurement_point_id`),
  KEY `idx_point_3d_layout_status` (`row_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量点白车身三维布局坐标';
