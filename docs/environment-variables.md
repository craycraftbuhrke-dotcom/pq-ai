# PQ-AI 环境变量与认证输入清单

本文列出 PQ-AI 的构建时、运行时、认证和 CI/CD 输入。生产部署不得把真实密钥、数据库密码、API Key 或内部地址硬编码到代码、Dockerfile、Compose 或前端包中；必须通过 GitLab CI/CD Variables、Kubernetes Secret、容器平台 Secret、`.env` 本地文件或运行时环境变量注入。

## 1. 后端运行时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `APP_NAME` | 是 | 否 | FastAPI 应用名称。 |
| `API_PREFIX` | 是 | 否 | API 路由前缀，例如 `/api/v1`。 |
| `DATABASE_URL` | 是 | 是 | SQLAlchemy 数据库连接串，包含数据库用户名和密码。 |
| `API_CORS_ORIGINS` | 是 | 否 | 允许访问 API 的前端源，多个值用逗号分隔。 |
| `API_AUTH_ENABLED` | 是 | 否 | 是否启用会话/API Key 鉴权；部署必须为 `true`。 |
| `ALLOW_SELF_REGISTRATION` | 否 | 否 | 是否允许公开自助注册；生产默认且建议保持 `false`，账号由管理员创建。 |
| `SEED_ON_STARTUP` | 否 | 否 | 仅受控目录初始化任务可设为 `true`；部署默认且必须保持 `false`。 |
| `API_HOST` | 是 | 否 | Uvicorn 监听地址，由容器运行时注入。 |
| `API_PORT` | 是 | 否 | Uvicorn 监听端口，由容器运行时注入。 |

说明：生产镜像启动时不会执行任何自动数据库迁移、建库、建表、改表或内置业务数据加载动作。所有 DDL、建库、建表和表结构变更必须按公司工单审批流程手动执行；如果数据库不可连接、权限不足或表结构不匹配，后端会继续启动，并在对应 API 返回明确的数据库错误，前端会展示告警。

## 2. 前端运行时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `NODE_ENV` | 是 | 否 | Node.js 运行模式，生产镜像应注入 `production`。 |
| `LISTEN_HOST` | 否 | 否 | 前端容器监听地址，默认 `0.0.0.0`；启动时会映射为 Next.js standalone 读取的 `HOSTNAME`，避免容器平台自动 `HOSTNAME` 被解析成 Pod/容器名。 |
| `PORT` | 是 | 否 | Next.js standalone server 监听端口，默认 `80`（nginx 惯例）；如与宿主机 80 冲突可设 `8080`。Compose 中由 `FRONTEND_PORT` 映射。 |
| `API_URL` | 是 | 否 | 前端服务端访问 FastAPI 的内网地址，例如容器网络内的 API 地址。 |
| `NEXT_PUBLIC_API_URL` | 是 | 否 | 浏览器可见的 API 地址；也会作为前端构建参数注入。不得包含密钥。 |
| `AUTH_ENABLED` | 是 | 否 | Next.js 服务端代理认证开关；部署必须为 `true`，只有 `NODE_ENV=test` 的隔离测试可关闭。 |
| `NEXT_PUBLIC_AUTH_ENABLED` | 是 | 否 | 构建时嵌入浏览器包的认证开关；生产构建必须为 `true`，仅修改 Pod 运行时变量无效。 |
| `NEXT_PUBLIC_ALLOW_SELF_REGISTRATION` | 否 | 否 | 构建时嵌入的自助注册入口开关；必须与后端开关一致，生产默认 `false`。 |
| `WEB_PUBLIC_DIR` | 否 | 否 | 前端服务端底图/数模运行时目录；容器镜像已设置为应用 `public` 目录。 |
| `WEB_RUNTIME_ASSET_DIR` | 否 | 否 | 用户上传模型、底图、覆盖清单和上传会话目录；K8s 挂载 RWX PVC，本地默认与 `WEB_PUBLIC_DIR` 共用。 |
| `BODY_MODEL_MAX_UPLOAD_BYTES` | 否 | 否 | 三维车身模型上传大小上限，默认 256 MiB；更大文件需接入对象存储和流式转换服务后另行放开。 |
| `BODY_MODEL_UPLOAD_SESSION_TTL_MS` | 否 | 否 | 三维数模分片上传会话有效期，默认 24 小时、最小 60 秒；过期会话在访问时及后续上传任务中清理。 |
| `BULK_IMPORT_MAX_BYTES` | 否 | 否 | 通用 Excel/CSV 批量导入大小上限，默认 50 MiB。 |
| `FILE_IMPORT_MAX_BYTES` | 否 | 否 | Dürr/BYK/Fischer/材料文件预览大小上限，默认 50 MiB。 |

## 3. 构建时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `NODE_IMAGE` | 否 | 否 | GitLab 前端扫描/构建 Job 使用的 Node.js 执行镜像，默认 `node:22-alpine`；根目录 `dockerfile.frontend` 已固定基础镜像，避免平台未传 build-arg 时失败。 |
| `PYTHON_IMAGE` | 否 | 否 | GitLab 后端扫描/构建 Job 使用的 Python 执行镜像，默认 `python:3.11-slim`；根目录 `dockerfile.backend` 已固定基础镜像，避免平台未传 build-arg 时失败。 |
| `PIP_CONFIG_SECRET_FILE` | 否 | 是 | GitLab File 类型、masked/protected 变量，内容为企业 `pip.conf`；仅通过 BuildKit secret 挂载到构建步骤，不进入 build-arg、镜像层或历史。未配置时使用 pip 默认公开索引。 |
| `NEXT_PUBLIC_API_URL` | 是 | 否 | 前端构建时注入的浏览器可见 API 地址。 |
| `NEXT_PUBLIC_AUTH_ENABLED` | 是 | 否 | 前端构建时认证开关，生产镜像必须为 `true`；不能依赖 K8s 运行时覆盖。 |
| `NEXT_PUBLIC_ALLOW_SELF_REGISTRATION` | 否 | 否 | 前端构建时注册入口开关，默认 `false`。 |

## 4. MySQL / Compose 本地变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `MYSQL_IMAGE` | 是 | 否 | MySQL Docker 镜像。 |
| `MYSQL_DATABASE` | 是 | 否 | MySQL 数据库名。 |
| `MYSQL_USER` | 是 | 否 | MySQL 应用用户。 |
| `MYSQL_PASSWORD` | 是 | 是 | MySQL 应用用户密码。 |
| `MYSQL_ROOT_PASSWORD` | 是 | 是 | MySQL root 密码。 |
| `MYSQL_PORT` | 是 | 否 | 本机映射 MySQL 端口。 |
| `API_PUBLISH_PORT` | 是 | 否 | 本机映射 API 端口。 |
| `FRONTEND_HOSTNAME` | 是 | 否 | Compose 注入到前端容器的 `LISTEN_HOST`。 |
| `FRONTEND_PORT` | 是 | 否 | Compose 注入到前端容器的 `PORT`。 |
| `FRONTEND_PUBLISH_PORT` | 是 | 否 | 本机映射前端端口。 |
| `API_IMAGE` | 仅 experience | 否 | `docker-compose.experience.yml` 使用的后端镜像名。 |
| `FRONTEND_IMAGE` | 仅 experience | 否 | `docker-compose.experience.yml` 使用的前端镜像名。 |

## 5. GitLab CI/CD 变量

| 变量 | 必填 | 敏感 | 来源/用途 |
| --- | --- | --- | --- |
| `CI_PROJECT_PATH` | 自动 | 否 | GitLab 自动提供的项目标识，仅用于无凭据的构建日志。 |
| `CI_REGISTRY` | 构建镜像必填 | 否 | GitLab 容器镜像仓库地址，GitLab 自动提供。 |
| `CI_REGISTRY_IMAGE` | 构建镜像必填 | 否 | 当前项目镜像命名空间，GitLab 自动提供。 |
| `CI_REGISTRY_USER` | 构建镜像必填 | 是 | 镜像仓库登录用户名，GitLab 自动提供或由 CI 注入。 |
| `CI_REGISTRY_PASSWORD` | 构建镜像必填 | 是 | 镜像仓库登录密码/令牌，GitLab 自动提供或由 CI 注入。 |
| `CI_COMMIT_SHORT_SHA` | 构建镜像必填 | 否 | 镜像 tag 的提交短 SHA，GitLab 自动提供。 |
| `DOCKER_IMAGE_TAG` | 否 | 否 | 镜像 tag，默认使用 `${CI_COMMIT_SHORT_SHA}`。 |
| `FRONTEND_IMAGE` | 否 | 否 | 前端镜像 tag，默认 `${CI_REGISTRY_IMAGE}/frontend:${DOCKER_IMAGE_TAG}`。 |
| `BACKEND_IMAGE` | 否 | 否 | 后端镜像 tag，默认 `${CI_REGISTRY_IMAGE}/backend:${DOCKER_IMAGE_TAG}`。 |
| `FRONTEND_LATEST_IMAGE` | 否 | 否 | 前端 latest tag。 |
| `BACKEND_LATEST_IMAGE` | 否 | 否 | 后端 latest tag。 |
| `SECRET_DETECTION_ENABLED` | 否 | 否 | GitLab Secret Detection 开关。 |
| `PIP_CONFIG_SECRET_FILE` | 企业私有索引时必填 | 是 | GitLab File 类型变量，构建时以 BuildKit secret 挂载；禁止把带凭据 URL 放进普通 CI 变量或命令行。 |
| `KUBECTL_IMAGE` | 否 | 否 | 包含 shell 与 kubectl 的流水线部署镜像，可由企业镜像仓库覆盖。 |
| `KUBE_CONTEXT` | 部署必填 | 敏感配置 | GitLab Kubernetes Agent 或注入 kubeconfig 中的目标 context，必须 protected。 |
| `K8S_NAMESPACE` | 部署必填 | 否 | 已由平台创建并授权给流水线的目标 namespace。 |

## 6. Kubernetes 运行时对象

Kubernetes 模板只引用以下预创建对象，不在代码中生成 Secret、数据库或 DDL：

| 对象 | 必填键/能力 | 用途 |
| --- | --- | --- |
| ConfigMap `pq-ai-runtime-config` | `api-cors-origins` | 后端允许的浏览器来源。 |
| Secret `pq-ai-runtime-secrets` | `database-url` | MySQL SQLAlchemy 连接串；由平台密钥系统注入。 |
| PVC `pq-ai-frontend-assets` | `ReadWriteMany` | 多前端 Pod 仅共享用户上传模型、底图、上传会话和覆盖清单；镜像内置资源不写入 PVC。 |

Ingress/Gateway 由平台维护，只暴露 `pq-ai-frontend:80`。浏览器通过同源 BFF 访问业务 API，
前端 Pod 通过集群内地址 `pq-ai-backend:8000` 访问后端，后端 Service 不要求公网暴露。

## 7. 注入规则

- 本地开发：复制 `.env.example` 为 `.env`，把所有 `<replace-with-...>` 占位符替换为本地值。
- GitLab CI：在 CI/CD Variables 中配置 `NEXT_PUBLIC_API_URL` 和镜像仓库登录变量；部署时还需配置受保护的 `KUBE_CONTEXT`、`K8S_NAMESPACE`。如需替换 CI 执行镜像可覆盖 `NODE_IMAGE`、`PYTHON_IMAGE`、`KUBECTL_IMAGE`；企业 pip 配置只能使用 masked/protected 的 File 类型 `PIP_CONFIG_SECRET_FILE`，不得通过 build-arg 或带凭据 URL 注入。
- 容器运行：用容器平台环境变量或 Secret 注入 `DATABASE_URL`、数据库密码等敏感信息。
- 前端安全：人员请求只使用 HttpOnly 会话 Cookie；Next.js 代理不得配置或回退到共享 API Key。
- 生产安全：`API_AUTH_ENABLED` 必须为 `true`，不得使用测试密钥；生产环境不得在服务启动时自动执行 Alembic、任何 DDL 或内置业务数据加载。
