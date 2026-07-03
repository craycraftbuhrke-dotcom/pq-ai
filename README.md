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
- [MySQL 数据库变更控制](docs/database-change-control.md)
- [项目级领域 skill](.codex/skills/automotive-paint-process-quality/SKILL.md)

## 技术栈

- 前端：Next.js 16、React 19、TypeScript，面向 Vercel 部署
- 后端：Python 3.12、FastAPI、SQLAlchemy 2
- 数据库：MySQL 8.4
- 数据库变更：禁止自动迁移；建库、建表、改表、索引、约束等结构变更必须走审批工单并由人工执行 SQL
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

数据库结构不由代码自动管理。首次部署或任何结构变更必须按
[MySQL 数据库变更控制](docs/database-change-control.md) 走审批工单并由人工执行 SQL。
在已存在且结构正确的 MySQL 数据库上，可手工加载幂等演示数据：

```bash
cd services/api
python -m app.db.seed_demo
```

## 当前实现

- 工业驾驶舱与五个喷涂执行阶段流程视图
- 主数据、关系维护、颜色技术资料、程序、刷子参数、生产、质量和 AI 闭环真实操作界面
- 生产事件、五个喷涂执行阶段实绩、材料批次与实际参数完整 CRUD
- 材料特性定义、检测方法、材料规格、工序/质量目标族适用关系和批次检测结果治理
- 材料可靠性自动判定；只有生产前 `VERIFIED` 的受控批次结果可进入 AI，旧自由字段仅保留追溯
- BYK/Fischer 仪器、测量方法、参考件、校准记录、导入模板与重复读数治理
- 质量测量可靠性自动判定；仅 `VERIFIED` 数据可进入 SPC、AI 训练和闭环验证
- 质量 SPC 控制图、趋势斜率、Cp/Cpk、点位风险热力图与数据质量监控
- AI 模型训练、预测、诊断、约束推荐、受控试验、审批、执行、复测评价和回滚记录工作台
- MES、QMS、机器人/PLC、材料系统端点与幂等集成事件任务中心
- 失败重试、死信、人工重放和业务映射结果追踪
- 受批准范围约束的喷涂/材料与质量指标目录；历史越界模型保留血缘并退役
- Dashboard、主数据、程序、质量、点位特征、预测、诊断、推荐和审批 API
- 基于刷子/路径贡献权重、实际参数和受治理材料批次结果的点位特征聚合
- Dürr 机器人、应用控制器、静电旋杯、程序设备组合、轨迹程序校验和、路径段和生产执行治理
- 按膜厚、色差/效应、橘皮目标族分别版本化并审批刷子/路径段到测量点贡献
- `point-features-v4-material-governed` 保存程序、贡献版本、轨迹、设备执行、材料结果和材料规格血缘；轨迹校验和异常或必需材料结果缺失会阻断 AI
- 可持久化岭回归基础模型训练、真实点位预测和相关性贡献诊断
- 不可变训练数据集快照、按车身/生产运行分组的时间留出、独立验证指标和泄漏检查
- 模型人工验收、激活门禁、版本激活/退役、基于独立验证基线的在线特征与预测效果漂移监控
- 模型工厂/车型/颜色适用范围、统计 OOD 策略、推理前门禁和预测治理证据；范围外、缺失或分布外输入会同时阻断预测与推荐
- 工厂模型验收策略版本；普通模型必须满足全部适用工厂针对目标指标批准的验证 RMSE、验证 R² 和独立分组数阈值，演示策略只能用于演示模型
- 受已批准约束来源版本保护的参数推荐，以及受控试验、审批、执行、复测、效果评价和失败回滚记录闭环
- API Key 身份认证、角色权限目录、关键写操作审计与审计中心
- MySQL Docker 环境、人工审批 SQL 变更流程和幂等演示数据初始化

基础模型用于验证数据和闭环链路，不代表生产模型精度。当前版本是可演示原型和现场数据接入准备基础，不是生产验收状态。批准范围、旧模型隔离、测量可靠性门禁、Dürr 设备/轨迹血缘、材料治理、无泄漏模型验收、适用范围/OOD 阻断、工厂验收策略版本、受控试验门禁、约束来源版本和回滚记录基线已完成；生产上线前仍必须用工厂批准的真实材料方法/单位/TDS/COA、工艺标准和模型验收阈值替换演示占位资料，并完成真实 BYK/Fischer 与 Dürr DXQ/PLC 文件适配、测量不确定度、真实轨迹坐标/姿态/触发和沉积贡献验证、自动程序回滚发布和灰度评估。

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
