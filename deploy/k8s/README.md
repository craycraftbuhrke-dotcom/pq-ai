# PQ-AI Kubernetes deployment

The manifests deploy the frontend and backend independently. They never create a
database, run DDL, seed business data, or store credentials in Git.

Platform prerequisites in the target namespace:

1. `pq-ai-runtime-config` ConfigMap with key `api-cors-origins`.
2. `pq-ai-runtime-secrets` Secret with key `database-url`.
3. `pq-ai-frontend-assets` ReadWriteMany PVC. It stores only runtime uploads,
   upload sessions, and override manifests across restarts and frontend replicas.
   Built-in models and body-map images remain immutable inside each release image;
   no init container copies release files into the shared volume.
4. `deploy/k8s/redis.yaml` (`pq-ai-redis`) for shared actor/summary cache across
   backend replicas. Backend sets `REDIS_URL=redis://pq-ai-redis:6379/0`; if Redis
   is unavailable the API falls back to in-process TTL cache automatically.
5. An Ingress/Gateway maintained by the platform team. Route browser traffic to
   `pq-ai-frontend:80`; the frontend BFF accesses `pq-ai-backend:8000` internally.

### 小米云 / 平台发布：三维数模上传必备配置

分片上传会话写在 `WEB_RUNTIME_ASSET_DIR` 下。若只改环境变量、不挂共享盘，
或多副本各自写本地盘，会出现 `meta.json` ENOENT、chunk 404。

平台侧请同时完成（缺一不可）：

1. 创建 **ReadWriteMany** PVC（示例名 `pq-ai-frontend-assets`）。
2. 所有前端 Pod 挂载到同一路径，例如 `/data/runtime-assets`。
3. 运行时环境变量：`WEB_RUNTIME_ASSET_DIR=/data/runtime-assets`。
4. 目录对容器用户可写（清单默认 `runAsUser/fsGroup: 1000`）。
5. 发布后在任意两个前端 Pod 验证：
   - `ls -ld /data/runtime-assets` 存在且可写
   - 在 Pod A `touch /data/runtime-assets/.pvc-check`，Pod B 能看到同一文件

临时排障可把前端缩成 1 副本，但不能替代共享 PVC。

The CI deploy jobs require protected variables `KUBE_CONTEXT` and `K8S_NAMESPACE`.
The GitLab Kubernetes agent or injected kubeconfig supplies cluster credentials.
Database schema changes still use `docs/sql/pq_ai_mysql_schema.sql` through the
manual DBA approval process.

`NEXT_PUBLIC_AUTH_ENABLED` and other `NEXT_PUBLIC_*` values are compiled into the
frontend image. Prefer passing `--build-arg NEXT_PUBLIC_AUTH_ENABLED=true` in the
image build job (Xiaomi Kaniko / GitLab). The root `dockerfile.frontend` defaults
the ARG to `true` when the platform omits it. Changing a Deployment environment
variable alone does not change browser-side behavior.
The server-only `AUTH_ENABLED` guard is injected at frontend runtime and must remain
`true` in every deployed environment.

## Runtime asset lock recovery

Runtime model and body-map manifest updates use filesystem owner locks on the
shared PVC. The application deliberately does not take over a lock based only on
age: an old Pod can resume after a pause, so automatic takeover without a fencing
token could allow two writers to publish concurrently.

When an operation repeatedly returns HTTP 409 with an orphan-lock message:

1. Stop or scale the frontend Deployment to zero and confirm that no frontend Pod
   is still running or terminating.
2. Back up the affected runtime asset directory and inspect the UUID owner file in
   the matching `*.lock` directory.
3. Remove only the confirmed orphan `*.lock` directory and any legacy
   `*.lock.recovery` marker.
4. Restore the Deployment and retry the operation.

Never delete a runtime lock while any frontend Pod can still execute. A future
multi-replica production hardening step should move coordination to Redis, MySQL,
or another platform lock that issues monotonic fencing tokens.
