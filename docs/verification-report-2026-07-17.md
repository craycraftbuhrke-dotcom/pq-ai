# PQ-AI 修复验证记录（2026-07-17）

## 自动化门禁

| 范围 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `cd services/api && ./.venv/Scripts/python.exe -m pytest -q` | `131 passed, 1 skipped` |
| 前端规范 | `npm run lint:web` | 通过，0 error / 0 warning |
| 前端类型 | `cd apps/web && npx tsc --noEmit` | 通过 |
| 前端生产构建 | `NEXT_PUBLIC_AUTH_ENABLED=true npm run build:web` | 通过，34 个页面/路由生成完成，无 NFT 路径追踪警告 |
| Node 依赖 | `npm audit --omit=dev --audit-level=moderate` | 无未豁免高中风险 |
| Python 依赖 | `cd services/api && python -m pip_audit --strict .` | 无未豁免高中风险 |
| 差异格式 | `git diff --check` | 通过 |

## 数据库与 DDL

- SQLAlchemy ORM 表：92。
- `docs/sql/pq_ai_mysql_schema.sql` 建表：92。
- 缺失表：0；额外表：0；逐表列差异：0；`measurement_point_3d_layout` 已包含。
- 物理外键：0。
- 总 DDL 不包含建库，也不包含运行时禁止的 `DROP/DELETE/ALTER/SET` 语句。
- `services/api/tests/test_models.py` 只读解析总 DDL，逐表核对 ORM 列名并检查无物理外键。
- `services/api/tests/test_database_operation_policy.py` 的 30 项用例覆盖普通语句、可执行注释、CTE、多语句、`RENAME TABLE`、`PREPARE`、`CALL`、反斜杠失败关闭和 MySQL `--` 注释边界。
- `project_to_2d` 是接口/批量导入的一次性执行指令，只控制同步二维投影，不是 `measurement_point_3d_layout` 持久化字段。

## 浏览器回归

使用 agent-browser 在隔离 SQLite 测试库上模拟登录用户完成 21 个入口回归：工作台、主数据、程序/工艺、生产、质量、仪器、材料、工程/AI、受控试验、集成、导入、审计、安全、个人资料和设置均返回 200 或按设计跳转到对应任务页。

- 浏览器控制台错误：0。
- 页面运行错误：0。
- 会话 Cookie：HttpOnly，浏览器 JavaScript 不可读。
- 匿名模型资源访问：307 到登录页。
- 已认证运行时模型 Range 请求：206，GLB 文件头校验为 `glTF`。
- 文件导入入口显示“检查文件 -> 确认写入”两步流程。

## CodeRabbit 增量复审

复审候选按轮次为 8、7、3、3、2、11、20、13、6、1；最新一项指出陈旧锁接管缺少发布阶段 fencing。应用已删除自动接管逻辑，改为锁占用时失败关闭和运维人工清理，避免旧、新所有者并发发布。全部问题已归并进入 `docs/coderabbit-remediation-plan.md` 的 `CR-RR-*` 台账。原始 226 条候选因逐项 NDJSON 未留存，仍按五个批次全部保留为 PENDING，不宣称已逐项关闭。
