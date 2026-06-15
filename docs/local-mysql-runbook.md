# 本机 MySQL 运行手册

当前本机环境使用：

- MySQL：`127.0.0.1:3306`
- 数据库：`pq_ai`
- API：`http://localhost:8012`
- 管理端：`http://localhost:3012`

数据库密码与 API Key 保存在被 Git 忽略的 `.env.local`，不会进入版本库。

## 首次初始化或升级数据库

```bash
cd /mnt/d/codex/brush-param/pq-ai
./scripts/init-local-mysql.sh
```

## 启动系统

```bash
cd /mnt/d/codex/brush-param/pq-ai
./scripts/start-local.sh
```

保持终端窗口运行，然后打开：

- 管理端：<http://localhost:3012>
- API 文档：<http://localhost:8012/docs>

停止系统时在启动终端按 `Ctrl+C`。

`start-local.sh` 默认会先执行最新数据库迁移、幂等初始化和前端生产构建，避免数据库结构或页面版本滞后。仅在确认已完成构建时可设置 `SKIP_WEB_BUILD=true` 跳过构建。

## 当前可实际操作范围

- 驾驶舱、程序、质量、AI、审计页面读取真实 API 数据。
- 主数据中心支持工厂、车型、颜色、零件、测量编组、测量点完整 CRUD，支持工厂-车型、车型-颜色、编组-点位关系和颜色 TDS/MSDS/COA/DOE 元数据。
- 喷涂程序中心支持程序、版本、适用车型颜色、刷子、参数、点位贡献权重和版本审批。
- 生产实绩中心支持生产事件、五个喷涂执行阶段实绩、材料批次和实际参数完整 CRUD。
- 生产实绩中心的“材料特性治理”支持定义、方法、规格、适用关系和批次检测结果 CRUD；只有生产前 `VERIFIED` 结果进入 AI。
- 质量中心支持质量测量、质量标准、自动判定、JSON 批量导入和 CSV 导出。
- AI 工作台支持不可变数据集快照、分组时间留出、泄漏检查、候选模型训练、独立验证、人工验收/激活，以及预测、诊断、约束推荐、审批、执行和复测评价。
- 集成与任务中心支持 MES/QMS/机器人/材料端点、幂等事件、失败重试、死信和重放。

每次代码升级后先执行 `./scripts/init-local-mysql.sh`，确保最新 Alembic 迁移和幂等初始化数据已写入 MySQL。
