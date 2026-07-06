# PQ-AI 喷涂工艺与质量智能化闭环系统

PQ-AI 将汽车涂装工艺参数、材料实绩与漆膜质量统一聚合到生产事件和测量点，并提供质量预测、问题诊断、参数推荐、审批执行和复测评价。

## 业务边界

- 三个涂层体系：中涂、色漆、清漆。
- 五个喷涂执行阶段：中涂外喷、色漆一/二遍、清漆一/二遍。分遍不是独立涂层体系。
- 质量目标：膜厚、色差/效应、橘皮。
- 设备与数据：Dürr 静电旋杯机器人及轨迹/参数、相关材料批次特性、BYK 色差/橘皮和 Fischer 膜厚测量。
- 明确排除：预处理、电泳、涂胶、喷房温湿度、烘房温度、调漆间和光泽度。

领域知识、项目目标、强制规则和成熟度审计见：

- [3C2B 领域知识基线](docs/domain-knowledge-3c2b.md)
- [开发目标与项目规则](docs/project-goals-and-rules.md)
- [系统成熟度评估](docs/system-maturity-assessment.md)
- [公司 MySQL 数据库规范](docs/mysql-company-standards.md)
- [MySQL 数据库变更控制](docs/database-change-control.md)
- [MySQL Schema 审查报告](docs/mysql-schema-audit.md)
- [DBA 审批建表 SQL](docs/sql/pq_ai_mysql_schema.sql)
- [3C3B 工程闭环 DBA Delta SQL](docs/sql/pq_ai_3c3b_engineering_delta.sql)
- [环境变量与认证输入清单](docs/environment-variables.md)
- [项目级领域 skill](.codex/skills/automotive-paint-process-quality/SKILL.md)

## 技术栈

- 前端：Next.js 16、React 19、TypeScript，面向 Vercel 部署
- 后端：Python 3.11、FastAPI、SQLAlchemy 2（DDL 通过 DBA 工单审批执行）
- 数据库：MySQL 8.4
- 数据库变更：禁止自动迁移；建库、建表、改表、索引、约束等结构变更必须走审批工单并由人工执行 SQL
- 数据库约束：不使用物理外键；引用完整性由应用层 `logical_fk`、存在性校验和引用检查实现
- 删除策略：正式 API 拒绝 HTTP `DELETE`；业务删除必须改为停用、归档、状态流转或版本替换
- 本地编排：Docker Compose

## 目录

```text
apps/web/       Next.js 管理端
services/api/   FastAPI 业务 API
docs/           架构与开发说明
```

完整实施路线见 [docs/development-plan.md](docs/development-plan.md)。

使用本机 MySQL 的当前开发环境启动与维护方式见
[docs/local-mysql-runbook.md](docs/local-mysql-runbook.md)。

## 本地启动

安装 Docker Desktop 并启用 WSL 集成后：

```bash
cp .env.example .env
docker compose up --build
```

- 管理端：http://localhost（默认 80 端口）
- API：http://localhost:8000
- OpenAPI：http://localhost:8000/docs

不使用 Docker 时：

```bash
npm install
npm run dev:web

cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API 默认要求 MySQL。单元测试使用 SQLite 内存库验证模型和服务行为。

数据库结构不由代码自动管理。首次部署或任何结构变更必须按
[MySQL 数据库变更控制](docs/database-change-control.md) 走审批工单并由人工执行 SQL。
当前建表审批材料见 [docs/sql/pq_ai_mysql_schema.sql](docs/sql/pq_ai_mysql_schema.sql)，不得由应用、
Docker、CI 或种子脚本执行。本轮 3C3B 工程闭环新增表/字段的审批材料见
[docs/sql/pq_ai_3c3b_engineering_delta.sql](docs/sql/pq_ai_3c3b_engineering_delta.sql)。
内置业务数据加载已禁用；业务数据必须通过受治理导入流程或 DBA 审批 SQL 写入。

## 当前实现

- 工业驾驶舱与五个喷涂执行阶段流程视图
- 主数据、关系维护、颜色技术资料、程序、刷子参数、生产、质量和 AI 闭环真实操作界面
- 生产事件、五个喷涂执行阶段实绩、材料批次与实际参数完整 CRUD
- 主数据、程序/刷子、生产实绩、质量、仪器治理、材料治理、Dürr 轨迹治理和集成事件支持 Excel/CSV 模板、批量导入和批量导出；导入采用字段类型校验和业务 upsert，不执行自动建表或结构变更
- 工程闭环中心：3C3B 工艺路线、质量问题/调试工单、工单证据与协作记录、真实文件导入任务、测量探头/MSA、供应商材料提交、贡献验证、轨迹几何和模型解释 API/前端/批量模板已接入
- 材料特性定义、检测方法、材料规格、工序/质量目标族适用关系和批次检测结果治理
- 材料可靠性自动判定；只有生产前 `VERIFIED` 的受控批次结果可进入 AI，旧自由字段仅保留追溯
- BYK/Fischer 仪器、测量方法、参考件、校准记录、导入模板与重复读数治理
- 质量测量可靠性自动判定；仅 `VERIFIED` 数据可进入 SPC、AI 训练和闭环验证
- 质量 SPC 控制图、趋势斜率、Cp/Cpk、点位风险热力图、数据质量健康评分与校准告警
- AI 模型训练、对比、预测、诊断、约束推荐、受控试验、审批、执行、复测评价和回滚记录工作台
- 受控试验全生命周期管理、程序版本差异对比、材料批次质量趋势分析
- MES、QMS、机器人/PLC、材料系统端点与幂等集成事件任务中心
- 失败重试、死信、人工重放、业务映射结果追踪与集成健康监控
- 受批准范围约束的喷涂/材料与质量指标目录；历史越界模型保留血缘并退役
- Dashboard、主数据、程序、质量、点位特征、预测、诊断、推荐和审批 API
- 基于刷子/路径贡献权重、实际参数和受治理材料批次结果的点位特征聚合
- Dürr 机器人、应用控制器、静电旋杯、程序设备组合、轨迹程序校验和、路径段和生产执行治理
- 按膜厚、色差/效应、橘皮目标族分别版本化并审批刷子/路径段到测量点贡献
- `point-features-v4-material-governed` 保存完整血缘；校验和异常或材料缺失阻断 AI
- 可持久化岭回归基础模型训练、真实点位预测和相关性贡献诊断
- 模型人工验收、激活门禁、版本激活/退役、在线特征与预测效果漂移监控
- 模型工厂/车型/颜色适用范围、统计 OOD 策略、推理前门禁和预测治理证据
- 不可变训练数据集快照、按车身/生产运行分组的时间留出、独立验证指标和泄漏检查
- 模型人工验收、激活门禁、版本激活/退役、基于独立验证基线的在线特征与预测效果漂移监控
- 模型工厂/车型/颜色适用范围、统计 OOD 策略、推理前门禁和预测治理证据；范围外、缺失或分布外输入会同时阻断预测与推荐
- 工厂模型验收策略版本；模型必须满足全部适用工厂针对目标指标批准的验证 RMSE、验证 R² 和独立分组数阈值
- 受已批准约束来源版本保护的参数推荐，以及受控试验、审批、执行、复测、效果评价和失败回滚记录闭环
- 用户名/密码登录、HttpOnly 会话 Cookie、API Key 系统集成认证、角色权限目录、关键写操作审计与审计中心
- 完整的认证系统：密码登录、注册、个人中心、角色管理和安全管理
- MySQL Docker 环境、人工审批 SQL 变更流程和受治理数据导入
- 公司 MySQL 规范基线、无物理外键模型、运行时禁用危险 SQL、HTTP DELETE 拦截和 DBA 审批建表 SQL

基础模型用于验证数据和闭环链路，不代表生产模型精度。当前版本是现场数据接入准备基础，不是生产验收状态。批准范围、旧模型隔离、测量可靠性门禁、Dürr 设备/轨迹血缘、材料治理、无泄漏模型验收、适用范围/OOD 阻断、工厂验收策略版本、受控试验门禁、约束来源版本和回滚记录基线已完成；生产上线前仍必须接入工厂批准的材料方法/单位/TDS/COA、工艺标准和模型验收阈值，并完成 BYK/Fischer 与 Dürr DXQ/PLC 文件适配、测量不确定度、真实轨迹坐标/姿态/触发和沉积贡献验证、自动程序回滚发布和灰度评估。

## 部署

`apps/web` 可作为独立 Vercel 项目部署，Root Directory 设置为 `apps/web`，并配置：

```text
API_URL=由运行时注入的后端内网 API 地址
NEXT_PUBLIC_API_URL=由构建时和运行时注入的浏览器可见 API 地址
API_KEY=由运行时 Secret 注入的服务端调用密钥
API_AUTH_ENABLED=true
```

FastAPI 与 AI Worker 建议部署在可访问工厂 MySQL/MES/QMS 的容器平台或企业内网。
所有认证、数据库、镜像和前后端运行参数必须通过构建时或运行时环境变量注入，完整清单见
[docs/environment-variables.md](docs/environment-variables.md) 和
[docs/sensitive-config-inventory.md](docs/sensitive-config-inventory.md)。

K8s 流水线可在仓库根目录分别构建前后端镜像：

```bash
docker build -f dockerfile.frontend -t your-registry/pq-ai-frontend:TAG .
docker build -f dockerfile.backend -t your-registry/pq-ai-backend:TAG .
```

前端容器监听 `80`（nginx 惯例，如与宿主机冲突可通过 `FRONTEND_PORT=8080` 覆盖），后端容器监听 `8000`。两个镜像启动时不会执行建库、建表、迁移或 seed；
MySQL schema 仍必须按 DBA 审批 SQL 人工执行。

生产环境必须启用 `API_AUTH_ENABLED=true`。网页登录使用用户名/密码换取后端会话令牌，
Next.js 只把令牌保存为 HttpOnly Cookie；MES、QMS、机器人/PLC 和脚本集成继续使用
API Key。Next.js 服务端 `API_KEY` 必须由运行时 Secret 注入，并由安全管理页面或企业密钥系统签发和轮换。
`API_KEY` 不得使用 `NEXT_PUBLIC_` 前缀，也不得下发到浏览器。
