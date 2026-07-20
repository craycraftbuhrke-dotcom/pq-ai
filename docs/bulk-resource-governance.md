# 批量导入导出资源治理

PQ-AI 当前 92 张业务表中，63 张受治理资源已提供统一 Excel/CSV 模板和导出，其中 62 张允许按模板导入。
模板目录由 `GET /api/v1/bulk/resources` 返回，前端“批量导入”页面不维护第二份静态清单。

`file_import_job` 只允许通过“文件预览 -> 用户确认 -> 后端写入 -> 失败重放”专用流程创建和流转；它保留任务清单导出能力，但 `importable=false`，禁止用通用模板伪造状态、行数、错误报告、规范化数据或写入时间。

其余 29 张表禁止通用批量覆写，并由自动测试锁定以下排除理由：

| 类别 | 数据表 | 处理方式 |
| --- | --- | --- |
| 认证、权限、审计 | `api_key`, `app_user`, `audit_log`, `permission`, `role_code`, `role_permission`, `user_role`, `user_session` | 只能走安全管理、登录和审计工作流。 |
| AI 与闭环工作流 | `closed_loop_evaluation`, `controlled_trial`, `dataset_snapshot`, `dataset_split_member`, `diagnosis_result`, `model_acceptance_decision`, `model_acceptance_policy`, `model_applicability_scope`, `model_artifact`, `model_ood_policy`, `model_validation_fold`, `model_version`, `point_feature_snapshot`, `prediction_result`, `program_rollback_execution`, `recommendation`, `recommendation_action` | 由数据集构建、训练、验收、预测、诊断、推荐、试验和回滚服务生成，禁止人工伪造血缘。 |
| 受控子明细/系统目录 | `measurement_repeat_reading`, `path_segment_execution`, `quality_metric_definition`, `quality_metric_value` | 随质量测量、设备执行或批准目录的父工作流写入，不能脱离父记录单独导入。 |

`services/api/tests/test_bulk_io.py` 会比较 ORM 全表集合、批量资源集合和上述排除集合。
新增表时必须同时选择“开放统一批量能力”或“记录专用工作流理由”，否则 CI 失败。
