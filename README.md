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
- [项目级领域 skill](.codex/skills/automotive-paint-process-quality/SKILL.md)

## 技术栈

- 前端：Next.js 16、React 19、TypeScript，面向 Vercel 部署
- 后端：Python 3.12、FastAPI、SQLAlchemy 2、Alembic
- 数据库：MySQL 8.4
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

- 管理端：http://localhost:3000
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

数据库结构由 Alembic 管理。手工初始化与演示数据命令：

```bash
cd services/api
alembic upgrade head
python -m app.db.seed_demo
```

## 当前实现

- 工业驾驶舱与五个喷涂执行阶段流程视图
- 主数据、关系维护、颜色技术资料、程序、刷子参数、生产、质量和 AI 闭环真实操作界面
- 生产事件、五个喷涂执行阶段实绩、材料批次与实际参数完整 CRUD
- 质量 SPC 控制图、趋势斜率、Cp/Cpk、点位风险热力图与数据质量监控
- AI 模型训练、预测、诊断、约束推荐、审批、执行和复测评价工作台
- MES、QMS、机器人/PLC、材料系统端点与幂等集成事件任务中心
- 失败重试、死信、人工重放和业务映射结果追踪
- 现有喷涂/材料与质量指标目录；其中历史演示目录仍含越界字段，已列入最高优先级整改
- Dashboard、主数据、程序、质量、点位特征、预测、诊断、推荐和审批 API
- 基于刷子贡献权重、实际参数和材料批次的点位特征聚合
- 可持久化岭回归基础模型训练、真实点位预测和相关性贡献诊断
- 模型版本激活/退役、在线特征漂移与预测效果监控
- 受硬边界约束的参数推荐，以及审批、执行、复测、效果评价闭环
- API Key 身份认证、角色权限目录、关键写操作审计与审计中心
- MySQL Docker 环境、Alembic 迁移和幂等演示数据初始化

基础模型用于验证数据和闭环链路，不代表生产模型精度。当前版本是可演示原型和现场数据接入准备基础，不是生产验收状态。批准范围基线与旧模型隔离已完成；生产上线前仍必须完成仪器与轨迹追溯、真实历史数据的按生产事件/时间分组验证、工厂约束配置、灰度评估和模型治理。

## 部署

`apps/web` 可作为独立 Vercel 项目部署，Root Directory 设置为 `apps/web`，并配置：

```text
API_URL=https://your-api.example.com/api/v1
NEXT_PUBLIC_API_URL=https://your-api.example.com/api/v1
API_KEY=服务端调用密钥
```

FastAPI 与 AI Worker 建议部署在可访问工厂 MySQL/MES/QMS 的容器平台或企业内网。

生产环境必须启用 `API_AUTH_ENABLED=true`，分别配置高熵的
`BOOTSTRAP_API_KEY` 与 Next.js 服务端 `API_KEY`，并在首次创建正式管理员密钥后轮换
引导密钥。`API_KEY` 不得使用 `NEXT_PUBLIC_` 前缀，也不得下发到浏览器。
