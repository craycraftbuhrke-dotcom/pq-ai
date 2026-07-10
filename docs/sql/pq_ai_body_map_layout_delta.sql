-- PQ-AI body-map measurement point layout delta SQL for DBA approval.
-- Review material only. Application code, Docker, CI, tests, and seed scripts must never run this file automatically.
-- No physical foreign keys are declared; all references are logical *_id fields enforced by application services.
-- Runtime MySQL policy still forbids automatic DELETE/CREATE/DROP/ALTER/TRUNCATE/REPLACE/SET.

CREATE TABLE `measurement_point_layout` (
  `measurement_point_id` VARCHAR(36) NOT NULL DEFAULT '' COMMENT '逻辑引用 measurement_point.id',
  `body_view` VARCHAR(16) NOT NULL DEFAULT '' COMMENT 'TOP/SIDE 白车身视图',
  `layout_x` DOUBLE NOT NULL COMMENT '相对底图归一化 X，范围 0~1',
  `layout_y` DOUBLE NOT NULL COMMENT '相对底图归一化 Y，范围 0~1',
  `grid_col` INT NULL COMMENT '可选网格列索引',
  `grid_row` INT NULL COMMENT '可选网格行索引',
  `row_status` VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/INACTIVE；图上移除仅停用布局',
  `id` VARCHAR(36) NOT NULL COMMENT '主键ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_point_layout_view` (`measurement_point_id`, `body_view`),
  KEY `idx_point_layout_view_status` (`body_view`, `row_status`),
  CONSTRAINT `ck_point_layout_x` CHECK (`layout_x` >= 0 AND `layout_x` <= 1),
  CONSTRAINT `ck_point_layout_y` CHECK (`layout_y` >= 0 AND `layout_y` <= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测量点白车身布局坐标';
