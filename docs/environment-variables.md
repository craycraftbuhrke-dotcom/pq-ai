# PQ-AI 环境变量与认证输入清单

本文列出 PQ-AI 的构建时、运行时、认证和 CI/CD 输入。生产部署不得把真实密钥、数据库密码、API Key 或内部地址硬编码到代码、Dockerfile、Compose 或前端包中；必须通过 GitLab CI/CD Variables、Kubernetes Secret、容器平台 Secret、`.env` 本地文件或运行时环境变量注入。

## 1. 后端运行时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `APP_NAME` | 是 | 否 | FastAPI 应用名称。 |
| `API_PREFIX` | 是 | 否 | API 路由前缀，例如 `/api/v1`。 |
| `DATABASE_URL` | 是 | 是 | SQLAlchemy 数据库连接串，包含数据库用户名和密码。 |
| `API_CORS_ORIGINS` | 是 | 否 | 允许访问 API 的前端源，多个值用逗号分隔。 |
| `API_AUTH_ENABLED` | 是 | 否 | 是否启用 API Key 鉴权；生产必须为 `true`。 |
| `API_HOST` | 是 | 否 | Uvicorn 监听地址，由容器运行时注入。 |
| `API_PORT` | 是 | 否 | Uvicorn 监听端口，由容器运行时注入。 |

说明：生产镜像启动时不会执行任何自动数据库迁移、建库、建表、改表或内置业务数据加载动作。所有 DDL、建库、建表和表结构变更必须按公司工单审批流程手动执行；如果数据库不可连接、权限不足或表结构不匹配，后端会继续启动，并在对应 API 返回明确的数据库错误，前端会展示告警。

## 2. 前端运行时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `NODE_ENV` | 是 | 否 | Node.js 运行模式，生产镜像应注入 `production`。 |
| `LISTEN_HOST` | 否 | 否 | 前端容器监听地址，默认 `0.0.0.0`；启动时会映射为 Next.js standalone 读取的 `HOSTNAME`，避免容器平台自动 `HOSTNAME` 被解析成 Pod/容器名。 |
| `PORT` | 是 | 否 | Next.js standalone server 监听端口。Compose 中由 `FRONTEND_PORT` 映射。 |
| `API_URL` | 是 | 否 | 前端服务端访问 FastAPI 的内网地址，例如容器网络内的 API 地址。 |
| `NEXT_PUBLIC_API_URL` | 是 | 否 | 浏览器可见的 API 地址；也会作为前端构建参数注入。不得包含密钥。 |
| `API_KEY` | 是 | 是 | Next.js 服务端代理调用 FastAPI 的 API Key，不得使用 `NEXT_PUBLIC_` 前缀，不得下发到浏览器。 |

## 3. 构建时变量

| 变量 | 必填 | 敏感 | 用途 |
| --- | --- | --- | --- |
| `NODE_IMAGE` | 否 | 否 | GitLab 前端扫描/构建 Job 使用的 Node.js 执行镜像，默认 `node:22-alpine`；根目录 `dockerfile.frontend` 已固定基础镜像，避免平台未传 build-arg 时失败。 |
| `PYTHON_IMAGE` | 否 | 否 | GitLab 后端扫描/构建 Job 使用的 Python 执行镜像，默认 `python:3.11-slim`；根目录 `dockerfile.backend` 已固定基础镜像，避免平台未传 build-arg 时失败。 |
| `NEXT_PUBLIC_API_URL` | 是 | 否 | 前端构建时注入的浏览器可见 API 地址。 |

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
| `PROJECT_GIT_REPOSITORY` | 是 | 否 | 由 CI/CD 注入的项目仓库地址，用于标识扫描与构建来源仓库。 |
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

## 6. 注入规则

- 本地开发：复制 `.env.example` 为 `.env`，把所有 `<replace-with-...>` 占位符替换为本地值。
- GitLab CI：在 CI/CD Variables 中配置 `NEXT_PUBLIC_API_URL` 和镜像仓库登录变量；如需替换 CI 执行镜像，可覆盖 `NODE_IMAGE`、`PYTHON_IMAGE`，密钥类变量必须 masked/protected。
- 容器运行：用容器平台环境变量或 Secret 注入 `DATABASE_URL`、`API_KEY`、数据库密码等敏感信息。
- 前端安全：只有 `NEXT_PUBLIC_` 前缀变量会暴露给浏览器；`API_KEY` 必须只存在于 Next.js 服务端运行环境。
- 生产安全：`API_AUTH_ENABLED` 必须为 `true`，不得使用测试密钥；生产环境不得在服务启动时自动执行 Alembic、任何 DDL 或内置业务数据加载。
