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
4. An Ingress/Gateway maintained by the platform team. Route browser traffic to
   `pq-ai-frontend:80`; the frontend BFF accesses `pq-ai-backend:8000` internally.

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
