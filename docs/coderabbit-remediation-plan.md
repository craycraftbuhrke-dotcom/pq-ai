# PQ-AI CodeRabbit 候选问题优化与修复计划

## 1. 目的与基线

本计划用于跟踪 2026-07-16 对 GitHub 最新 `main` 分段审查产生的 226 个候选问题。候选问题不等于 226 个已确认缺陷；重复项、历史差异和不适用于当前业务规则的提示必须经过代码与业务场景复核后再处理，禁止为了清数字盲目修改。

所有候选必须满足以下闭环之一，不能静默遗漏：

- `FIXED`：问题有效，已修复并有测试或验证证据。
- `INVALID`：当前代码不存在该问题，记录复核依据。
- `DUPLICATE`：与另一问题同根因，记录归并目标。
- `ACCEPTED_RISK`：暂不处理，记录业务理由、责任人和复核日期。
- `PENDING`：尚未完成复核，不得宣称本轮审查已关闭。

## 2. 226 项候选批次台账

| 批次 | 编号范围 | 原始数 | FIXED | INVALID | DUPLICATE | ACCEPTED_RISK | PENDING | 增量复审累计 | 对账证据/状态 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| API/后端 | `CR-API-001..113` | 113 | 0 | 0 | 0 | 0 | 113 | 23 | 原始逐项 NDJSON 未留存，不能伪造分类，保持 PENDING |
| 前端路由 | `CR-WEB-APP-001..035` | 35 | 0 | 0 | 0 | 0 | 35 | 16 | 原始逐项 NDJSON 未留存，不能伪造分类，保持 PENDING |
| 前端组件 | `CR-WEB-CMP-001..048` | 48 | 0 | 0 | 0 | 0 | 48 | 4 | 原始逐项 NDJSON 未留存，不能伪造分类，保持 PENDING |
| 前端公共库 | `CR-WEB-LIB-001..024` | 24 | 0 | 0 | 0 | 0 | 24 | 24 | 原始逐项 NDJSON 未留存，不能伪造分类，保持 PENDING |
| 脚本 | `CR-SCRIPT-001..006` | 6 | 0 | 0 | 0 | 0 | 6 | 7 | 原始逐项 NDJSON 未留存，不能伪造分类，保持 PENDING |
| 跨批次文档 | `CR-RR-DOC` | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 三项文档口径已修复；一项 DDL 字段建议经核实为 INVALID |
| **合计** |  | **226** | **0** | **0** | **0** | **0** | **226** | **78** | **原 226 项尚未完成逐项对账，不得宣称关闭** |

原始 CLI 审查缓存未保留逐条文本，因此不伪造 226 个标题，也不把当前确认的根因反推成 226 条分类。本台账以原始批次数量守恒；只有取得原始逐项清单并为每条记录分类和证据后，才可减少 `PENDING`。新审查发现的问题进入下方复审台账，不用“旧编号已用完”为理由忽略。

## 3. 已验证的优先修复项

| 编号 | 级别 | 问题 | 验收条件 | 状态 | 证据 |
|---|---|---|---|---|---|
| `SEC-001` | P0 | 后端、前端和 CI 认证默认关闭 | 缺少认证变量时启动/构建失败；生产不能静默开放 | FIXED | `services/api/tests/test_api.py`、`dockerfile.frontend`、生产构建记录 |
| `SEC-002` | P0 | 浏览器可读 `pq_api_key`，服务端请求回退共享 `API_KEY` | 人员只使用 HttpOnly 会话；匿名请求不能借用共享身份 | FIXED | `apps/web/src/lib/auth-data.ts`、浏览器 HttpOnly/匿名访问回归 |
| `SEC-003` | P0 | 三维模型上传 `uploadId` 路径穿越 | 上传标识白名单校验；解析后路径必须位于上传根目录 | FIXED | `apps/web/src/lib/body-map-model-store.ts`、生产类型检查 |
| `DATA-001` | P1 | 启动默认写入领域演示数据 | 生产默认不 seed；领域演示数据入口从运行时代码移除 | FIXED | `services/api/app/services/startup_seed.py`、敏感/演示数据文本扫描 |
| `DATA-002` | P1 | MySQL 运行时禁令漏掉 `SET` | MySQL 应用 SQL 阻断禁用操作及注释、CTE、多语句、PREPARE/CALL 绕过 | FIXED | `services/api/tests/test_database_operation_policy.py`（29 项） |
| `DDL-001` | P1 | 总 DDL 缺三维点位布局表 | ORM 与总 DDL 表名、字段、索引一致，共 92 张表 | FIXED | `services/api/tests/test_models.py`、DDL/ORM 92/92 比对记录 |
| `OPS-001` | P1 | 健康接口不检查数据库，前端固定显示可用 | liveness/readiness 分离；UI 根据真实状态显示 | FIXED | `services/api/tests/test_api.py`、21 页面浏览器健康状态回归 |
| `IMP-001` | P1 | Dürr/BYK/Fischer 文件任务停留在预览，重放不重新解析 | 预览、校验、确认入库、失败重放形成真实数据链，并发确认只能成功一次 | FIXED | `services/api/tests/test_engineering_workflow.py` |
| `AI-001` | P1 | 当前仅岭回归，解释记录依赖人工录入 | 增加经验证的模型族与自动解释/区间，保留基线回退 | ACCEPTED_RISK：不冒充生产 AI；责任人为项目模型负责人，阶段 6 启动前复核，模型发布继续受人工门禁 | `services/api/app/services/modeling.py`，发布仍受模型验收门禁 |
| `DEP-001` | P1 | Python/Node 生产依赖存在已知漏洞 | `pip-audit --strict .`、`npm audit --omit=dev --audit-level=moderate` 无未豁免高中风险 | FIXED | `docs/security-audit-report-2026-07-17.md` |
| `BE-TEST-001` | P2 | ORM 表名测试仍断言 `role` | 测试与 `role_code` 一致 | FIXED | `services/api/tests/test_models.py` |
| `BE-TEST-002` | P2 | STEP 缺文件时先报可选依赖缺失 | 先校验输入文件，再加载可选转换依赖 | FIXED | `services/api/tests/test_api.py`、`services/api/app/services/stp_convert.py` |
| `WEB-001` | P1 | 前端 lint 25 error/8 warning | lint 零 error，warning 必须有明确豁免 | FIXED | `npm run lint:web`：0 error / 0 warning |
| `WEB-002` | P1 | 数据库失败时页面仍显示“系统可用” | 全局状态与 readiness 一致，错误文案给出用户下一步 | FIXED | `apps/web/src/components/system-status.tsx`、浏览器回归 |
| `BULK-001` | P2 | 统一批量能力覆盖 59/92 张表 | 63 个用户可维护资源具备模板/导入/导出；29 个治理排除项逐表记录理由 | FIXED | `services/api/tests/test_bulk_io.py`、`docs/bulk-resource-governance.md` |

## 4. CodeRabbit 复审闭环

| 复审编号 | 级别 | 根因 | 状态与验证 |
|---|---|---|---|
| `CR-RR-001` | Major | K8s 多 Pod init container 并发写共享静态资源 | FIXED：镜像内置资源只读，PVC 仅挂载运行时资源目录 |
| `CR-RR-002` | Major | STEP 转换占用全局清单锁 | FIXED：转换/复制在锁外，锁内仅原子换文件和写清单 |
| `CR-RR-003` | Major | 文件导入确认存在并发重复写入 | FIXED：`VALIDATED -> IMPORTING` 条件更新原子占用 |
| `CR-RR-004` | Major | 分片/批量导入先完整缓冲再检查大小 | FIXED：请求流逐块计数，超限立即取消 |
| `CR-RR-005` | Major | 模型键可碰撞 JavaScript 原型属性 | FIXED：危险键加稳定后缀，读取使用 own-property 判断 |
| `CR-RR-006` | Major | 模型上传上限与全局代理上限导致内存风险 | FIXED：模型 256 MiB、分片 512 KiB、代理 64 MiB |
| `CR-RR-007` | Major | 密码更新请求无小型请求体上限 | FIXED：16 KiB 流式上限，超限返回 413 |
| `CR-RR-008` | Major | MySQL 禁令可被可执行注释、CTE、RENAME、多语句绕过 | FIXED：结构化扫描并新增回归用例 |
| `CR-RR-009` | Major | 模型最终文件切换失败时回滚不完整 | FIXED：两次 rename 与清单写入使用同一回滚块 |
| `CR-RR-010` | Minor | 运行时资源路径不统一且泄漏文件系统错误 | FIXED：复用统一 resolver、realpath containment、错误脱敏 |
| `CR-RR-011` | Minor | 上传总大小接受小数，错误 JSON 返回 500 | FIXED：要求安全正整数，错误 JSON 返回 400 |
| `CR-RR-012` | Critical | MySQL `--` 注释边界错误可隐藏后续禁用语句 | FIXED：仅空白/控制字符后识别注释，并覆盖算术表达式后多语句用例 |
| `CR-RR-013` | Major | 认证上游 404/5xx 被统一改写为 401 | FIXED：仅 401/403 映射登录/权限，其他状态原样向上游传播 |
| `CR-RR-014` | Major | 二维点位图切换车型时旧筛选和旧请求可覆盖新范围 | FIXED：车型与依赖筛选同批重置，请求使用 AbortController 与递增序号双重防陈旧写入 |
| `CR-RR-015` | Major | 二维点位详情请求在切换车型后仍可回写旧数据 | FIXED：详情请求增加独立递增序号，车型切换立即使旧请求失效 |
| `CR-RR-016` | Major | 前端代理只依赖 64 MiB 缓冲阈值，未执行 50 MiB 业务上限 | FIXED：批量和配方宽表前后端入口均逐块计数，超限返回 413 |
| `CR-RR-017` | Major | 原 226 项缺少逐项证据却被标记为已完成 | FIXED：恢复五批次全部 PENDING，明确分类数量、最新新增和证据缺口 |
| `CR-RR-018` | Major | 优先修复表的 FIXED 状态缺少逐项可追溯证据 | FIXED：增加证据列并建立独立验证记录 |
| `CR-RR-019` | Minor | 依赖审计结论与风险阈值、命令和输入版本不一致 | FIXED：统一为无未豁免高中风险并记录命令、版本和 SHA-256 |
| `CR-RR-020` | Major | 建议把 `project_to_2d` 加入已审批三维布局表 | INVALID：该字段是一次性投影执行指令，不在 ORM 中持久化；总 DDL 与已审批表保持一致，并补充边界注释 |
| `CR-RR-021` | Major | `PREPARE` 动态 SQL 与 `CALL` 可绕过 MySQL 运行时策略 | FIXED：拒绝 CALL、非字面量 PREPARE，并递归检查 PREPARE 字面量 SQL；增加 6 个策略用例 |
| `CR-RR-022` | Major | 注册请求无边界且错误 JSON 被默认为空对象 | FIXED：16 KiB 流式上限，超限/错误 JSON 分别返回 413/400；同类登录和审批入口同步治理 |
| `CR-RR-023` | Minor | 工程闭环代理把上游超时返回为 502 | FIXED：上游超时返回 504，连接失败保留 502；同类业务代理统一映射 |
| `CR-RR-024` | Minor | 质量代理把上游超时返回为 502 | FIXED：上游超时返回 504，连接失败保留 502 |
| `CR-RR-025` | Major | 注册上游 2xx 空响应沿用成功状态 | FIXED：非 2xx 保留上游状态，2xx 缺令牌或到期时间返回 502；登录入口同步治理 |
| `CR-RR-026` | Major | 数模版本覆盖后旧修订文件长期泄漏 | FIXED：清单原子提交后仅清理 CUSTOM_DIR 内符合系统 UUID 命名的旧模型和 STEP 源文件，内置模型受保护 |
| `CR-RR-027` | Major | 上传已提交后清理失败可能改写成功结果 | FIXED：会话目录清理显式按尽力而为处理，不影响已提交响应 |
| `CR-RR-028` | Major | STEP 转换响应完整 `arrayBuffer()` 后才校验大小 | FIXED：先验证 Content-Length，再逐块读取并在超限时立即取消；源 STEP 使用文件 Blob，避免额外完整读入 |
| `CR-RR-029` | Major | GLB/GLTF 仅校验文件开头且转换结果未复验 | FIXED：GLB 校验 magic、版本和声明长度，GLTF 完整解析并校验 glTF 2.x，转换和直传产物提交前统一复验 |
| `CR-RR-030` | Major | 分片组装失败遗留半成品 | FIXED：大小不符、缺片或写入失败时销毁流并删除 assembled 文件 |
| `CR-RR-031` | Major | 体验镜像 standalone 复制路径与启动路径疑似不一致 | INVALID：构建产物实测为 `/app/apps/web/server.js`，原路径可运行；另新增构建期文件断言和绝对启动路径消除歧义 |
| `CR-RR-032` | Minor | 配方宽表代理超时返回 502 | FIXED：超时返回 504，连接失败保留 502 |
| `CR-RR-033` | Minor | 批量代理超时返回 502 | FIXED：超时返回 504，连接失败保留 502 |
| `CR-RR-034` | Minor | 注册响应到期时间未验证 | FIXED：令牌要求非空字符串，到期时间要求有效且晚于当前时间；登录同步治理 |
| `CR-RR-035` | Major | 安全管理代理无小型请求体上限 | FIXED：64 KiB 流式上限，400/413 与上游 502/504 分开映射 |
| `CR-RR-036` | Major | Proxy 仅凭非空 Cookie 放行 | FIXED：每次受保护入口通过后端 `/auth/me` 验证会话；失效、伪造或过期 Cookie 清除并拒绝 |
| `CR-RR-037` | Major | 轨迹两段请求可被旧程序响应覆盖 | FIXED：程序版本变化时 AbortController 同时取消轨迹程序和路径段请求，旧响应不再写状态 |
| `CR-RR-038` | Major | Experience Compose 仅检查认证变量非空 | FIXED：前后端认证标志固定为 `true` |
| `CR-RR-039` | Major | pip 私有索引凭据通过 build-arg 进入镜像历史 | FIXED：改用可选 BuildKit `pip.conf` secret；GitLab 使用 masked/protected File 变量 |
| `CR-RR-040` | Major | 车型切换未立即清空二维画布 | FIXED：切换时递增画布请求代次、清空画布并显示新范围加载状态 |
| `CR-RR-041` | Major | 标准 Compose 可用 `false` 绕过认证 | FIXED：构建期和运行时认证标志固定为 `true` |
| `CR-RR-042` | Major | 预览后 profile 目标资源漂移可改变实际写入表 | FIXED：预览冻结解析后的目标，确认/重放时校验漂移并只使用冻结目标 |
| `CR-RR-043` | Major | 通用导入任务 CRUD 可伪造工作流字段 | FIXED：移除直接创建路由，通用批量导入禁用，PATCH 只允许来源说明和备注且拒绝额外字段 |
| `CR-RR-044` | Minor | 自定义数模通过 legacy/fallback 命中时误标为内置 | FIXED：解析和来源分类复用同一 normalized/legacy/fallback 查找函数 |
| `CR-RR-045` | Major | 陈旧锁恢复和释放可能删除其他请求的新锁 | FIXED：锁记录唯一 token；恢复锁串行复核陈旧状态；持有者只释放自己的 token |
| `CR-RR-046` | Major | 底图覆盖先写固定服务文件再提交清单 | FIXED：镜像和上传均写 UUID 修订，清单成功后再删旧图，失败保留旧清单和旧图 |
| `CR-RR-047` | Major | 数模上传会话无 TTL 和孤儿回收 | FIXED：默认 24 小时 TTL，访问时过期并在新会话创建时扫描回收无后续请求的旧目录 |
| `CR-RR-048` | Major | STEP 转换结果仍在 Node 内存中完整聚合 | FIXED：响应逐块写入 pending 文件，累计计数超限即取消并删除半成品 |
| `CR-RR-049` | Major | 完成上传清理后重试会重复发布模型 | FIXED：上传 ID、来源格式和转换引擎随模型清单原子持久化；重试先返回已提交结果再尽力清理 |
| `CR-RR-050` | Major | 单文件 GLTF 可引用未上传的外部资源 | FIXED：只接受 data URI buffer/image 或内嵌 bufferView 图片，提交前拒绝外部路径和 URL |
| `CR-RR-051` | Major | 文件导入进程中断后任务永久停留在 `IMPORTING` | FIXED：复用 `updated_at` 作为两小时租约；活动租约保持独占，过期租约可原子重新认领并刷新时间，不新增 DDL |
| `CR-RR-052` | Major | 带静态扩展名的 `/api/*` 路径可被代理当成公开资源 | FIXED：扩展名白名单只适用于非 API 路径，API 请求始终进入会话验证 |
| `CR-RR-053` | Major | 生产可通过关闭环境变量取得 SYSTEM 通配权限 | FIXED：只有 `NODE_ENV=test` 且服务端与后端认证开关同时关闭的隔离测试允许旁路，其他环境失败关闭 |
| `CR-RR-054` | Minor | 会话撤销后刷新身份仍保留旧角色 | FIXED：`/api/auth/me` 返回 401 时先清空前端 actor，再向调用方报告会话失效 |
| `CR-RR-055` | Minor | 认证上游 2.5 秒超时被误报为连接失败 502 | FIXED：TimeoutError 映射 504，其他连接失败保持 502 |
| `CR-RR-056` | Major | Proxy 使用浏览器构建变量控制服务端认证 | FIXED：改用服务端运行时 `AUTH_ENABLED`，Compose/K8s/Docker 强制为 true，默认仍启用 |
| `CR-RR-057` | Major | 退出请求失败时前端仍清空身份并显示已退出 | FIXED：仅服务端确认清理 Cookie 后切换匿名身份和跳转；失败保留当前身份并记录错误 |
| `CR-RR-058` | Major | 文件锁先比较 token 再删除仍有替换竞态 | FIXED：改为锁目录和 UUID 所有者文件；释放者只删除自己的文件，旧持有者不能删除新锁目录 |
| `CR-RR-059` | Major | 上传会话 GC 可与分片写入或完成提交并发删除目录 | FIXED：GC 使用同一会话锁零等待尝试，锁内重新读取时间并判断过期，忙碌会话跳过 |
| `CR-RR-060` | Major | 旧版孤儿 `.recovery` 文件导致锁循环忙等 | FIXED：统一截止时间和随机退避；应用不再自动删除 recovery，超时后返回 409 并要求运维确认无活动副本后清理 |
| `CR-RR-061` | Major | 大型 GLTF JSON 完整读入导致额外内存峰值 | FIXED：读入前检查文件大小，GLTF JSON 上限 32 MiB，超限提示改用 GLB |
| `CR-RR-062` | Major | PREPARE 字面量反斜杠转义可能被错误解码 | FIXED：动态 SQL 字面量遇到反斜杠一律失败关闭为 PREPARE 禁令，并补回归用例 |
| `CR-RR-063` | Major | STEP 转换落盘失败后未取消上游响应流 | FIXED：输出打开、写入、校验任一失败都主动 cancel reader，关闭文件并删除半成品 |
| `CR-RR-064` | Minor | 流式请求超限测试未证明停止读取后续块 | FIXED：增加第三块和 receive 调用计数，断言第二块超限后调用次数严格为 2 |
| `CR-RR-065` | Minor | `CR-RR-031` 使用组合状态 `INVALID/HARDENED` | FIXED：状态统一为 canonical `INVALID`，加固措施保留在处置说明中 |
| `CR-RR-066` | Minor | 三维点位恢复测试只断言 X 坐标 | FIXED：同步断言 pos_y=2.5、pos_z=3.5，覆盖完整三维位置回写 |
| `CR-RR-067` | Major | 导入任务只有时间租约，旧 worker 可在重领后覆盖结果 | FIXED：claim token 持久化到既有 JSON；逐行处理触发节流续租，续租和最终更新均条件校验当前 token |
| `CR-RR-068` | Major | 运行时文件锁只按获取时间回收仍可能清理活动锁 | FIXED：所有者文件句柄每 5 秒续租 mtime 用于活跃性诊断；应用层取消所有过期锁自动接管，避免错误清理活动锁 |
| `CR-RR-069` | Major | 程序版本适用车型并发绑定可能返回 500 | FIXED：ORM 与总 DDL 原本已有 `uk_program_model` 组合唯一约束；车型和颜色绑定提交均补 `IntegrityError` 回滚并返回 409 |
| `CR-RR-070` | Major | 陈旧锁接管仍缺少发布阶段 fencing，旧所有者恢复后可与新所有者同时写入 | FIXED：删除应用自动接管与隔离逻辑；锁存在时失败关闭为 409，只有当前 UUID 所有者可释放；孤儿锁必须按 K8s 运维规程人工清理，长期生产方案改用具备 fencing token 的外部协调服务 |
| `CR-RR-071` | Major | 远程连接修改可能绕过工厂和连接编号校验 | INVALID：修改模型不允许变更 `factory_id` 或 `connection_code`，两个字段只能创建时校验，当前路由不存在该绕过路径 |
| `CR-RR-072` | Major | 连接测试可能暴露未处理的通讯异常 | FIXED：协议层统一转换证书、TLS、网络和响应异常，路由再对非预期适配器异常做 502 脱敏兜底 |
| `CR-RR-073` | Major | 批量导入每个未解析引用都重新读取并计算全部候选 | FIXED：单次导入按引用模型和字段组合缓存候选及预计算检索词，保留上下文字段缩小范围和最终解析缓存 |
| `CR-RR-074` | Major | 字典和列表渲染后的首字符未做 Excel 公式防护 | FIXED：所有最终单元格文本统一检查 `= + - @` 并加前导单引号，新增分项内容导出回归 |
| `CR-RR-075` | Minor | 带页面默认值的空行可能被误建为只有父级引用的记录 | FIXED：默认值合并前先判断原始行是否为空，新增默认父级空行回归 |
| `CR-RR-076` | Major | 人工训练宽表导出可能触发电子表格公式 | FIXED：CSV/XLSX 每个上传来源单元格写出前统一公式转义并验证两种格式 |
| `CR-RR-077` | Major | 损坏的训练 Excel 可能冒泡为 500 | FIXED：捕获 ZIP、OpenXML、文件和解析错误并返回可操作的 422 提示 |
| `CR-RR-078` | Minor | 训练宽表重复列可在字典解析时静默覆盖 | FIXED：解析后先检查重复中文列和重复参数映射，再进行逐行赋值 |
| `CR-RR-079` | Major | 历史训练特征缺少当前中文标签时导出抛出 KeyError | FIXED：导出前检查标签覆盖；缺失时返回说明恢复参数中文名称的 422，不输出不可重导的伪列名 |
| `CR-RR-080` | Minor | Excel 数字样本编号 `100.0` 被保存为不稳定文本 | FIXED：整数型浮点编号规范为 `100`，非整数仍保留有效小数 |
| `CR-RR-081` | Major | 暂存、现场状态查询和正式提交的通讯失败缺少可审计状态 | FIXED：分别记录 `STAGE_FAILED`、`STATUS_PENDING`、`COMMIT_UNCERTAIN`；提交结果未知时进入待回读且明确禁止重复提交 |
| `CR-RR-082` | Major | 远程协议向前端暴露底层 TLS、文件和网络异常文本 | FIXED：完整异常只写服务端日志，客户端仅收到稳定的 502/503 业务提示；远端拒绝原因同步脱敏 |
| `CR-RR-083` | Major | 上位机数值和云端十进制字符串导致三方对账误报 | FIXED：先按原始负载校验线端哈希，再把刷子参数规范成十进制字符串后存储、对账和发布回读核对 |
| `CR-RR-084` | Major | TLS 证书上下文加载失败可能冒泡为 500 | FIXED：证书引用缺失保留治理提示，证书文件或私钥加载失败统一记录日志并返回 503 |
| `CR-RR-085` | Major | 切换质量类型时旧模板定义和旧文件读取可覆盖新类型 | FIXED：切换事件立即清空旧预览，AbortController 取消旧元数据请求，文件读取校验类型代次，定义就绪前禁用模板、选文件和导入 |
| `CR-RR-086` | Major | 前端测试认证开关与入口代理不一致 | FIXED：拒绝放宽身份服务；入口代理同步要求 `NODE_ENV=test` 且前后端认证开关同时关闭才允许测试旁路 |
| `CR-RR-087` | Minor | 后端认证成功状态返回错误 JSON 时异常未治理 | FIXED：统一解析并验证账号字段和权限数组，错误 JSON 或不完整身份明确映射为 502 |
| `CR-RR-088` | Major | 远程工作站前端代理无请求体大小限制 | FIXED：JSON 请求按流读取并限制 64 KiB，错误格式和超限分别返回 400/413 |
| `CR-RR-089` | Minor | 会话失效后刷新身份仍继续读取 401 响应 | FIXED：收到 401 后清空身份并立即返回，不再二次覆盖状态 |
| `CR-RR-090` | Major | 清空参数输入框会被 `Number("")` 转换为 0 | FIXED：空白值跳过，非空值才进行有限数字和变更判断 |
| `CR-RR-091` | Major | 自定义三维数模使用包含匹配可能误选相似车型 | FIXED：保留直接和旧键兼容，清单遍历只允许规范化后的精确相等 |
| `CR-RR-092` | Major | 文件操作提交完成后的心跳失败可能改写成功结果 | FIXED：标记操作完成并停止定时器；仅操作期间已确认的续租失败阻断结果，提交后失败不覆盖已完成结果 |
| `CR-RR-093` | Minor | Windows 上位机配置文件带 BOM 时首个键无法识别 | FIXED：INI 解析前只移除开头 UTF-8 BOM |
| `CR-RR-094` | Major | 上位机端口、包大小和适配模式路径缺少启动前校验 | FIXED：端口、端口冲突和包大小均执行范围校验；文件投递、批准适配器和非模拟回读路径按模式强制必填 |
| `CR-RR-095` | Minor | 单文件构建完成提示遗漏真实 Dürr 适配器部署条件 | FIXED：提示明确仅模拟/文件投递无需额外程序，批准适配模式还必须部署工厂批准的适配器程序 |

当前验证基线（2026-07-19）：后端全量 `274 passed, 1 skipped`；前端 ESLint、TypeScript 和 34 页面生产构建通过；npm 生产依赖与 Python 依赖均无已知漏洞；敏感信息拆分扫描无命中；上位机代理语法、缺失配置失败关闭和此前双向 TLS 完整发布回读联调通过；浏览器验证质量模板切换、64 KiB 远程请求边界、生产/人工训练数据并列选择和中文模板入口均通过且无页面错误。原始 226 项因逐条文本未留存仍保持 `PENDING`，不得用本轮新增 25 项替代原始对账。

数据库脚本分段复审在 2026-07-19 首次因免费 CodeRabbit CLI 额度触发 14 分钟限流；等待后已完成重试，审查总 DDL、三维布局增量、训练来源增量和独立 7 表 SQL 共 4 个文件，CodeRabbit 提出 0 项问题。独立 7 表 SQL 同时继续由 ORM/DDL 自动比对测试和禁用语句扫描约束。

## 5. 实施顺序

### 阶段 A：安全与数据库治理

修复 `SEC-001..003`、`DATA-001..002`、`DDL-001`、`OPS-001`。这一阶段未通过前，禁止把系统标记为可部署。

### 阶段 B：后端正确性与数据入口

修复测试失败、事务边界、逻辑引用校验、导入大小限制、CSV/Excel 公式注入、错误信息泄露和真实设备文件入库。复杂规则全部在后端服务执行，前端不复制一套规则。

### 阶段 C：前端任务流与人本化交互

页面按用户任务组织，而不是按数据表堆叠：

1. 每页只保留一个主目标和一个主操作。
2. 高风险操作采用“选择对象 -> 系统检查 -> 用户确认 -> 后端执行 -> 结果说明”的向导。
3. 默认展示业务名称，代码、ID、JSON、版本哈希放在“追溯详情”。
4. 标签使用现场语言，如“生产车号”“喷涂工序”“检测点”“采用的程序版本”，不直接暴露字段名。
5. 不自动选择第一条高风险业务记录；系统可以推荐，但必须让用户确认。
6. 空状态说明为什么为空和下一步做什么；错误信息说明影响、原因和处理动作。
7. 简化只发生在表达层，领域模型、审批、血缘、可靠性和约束不能删减。

### 阶段 D：AI、依赖与生产质量门禁

升级依赖，补齐模型族、解释与不确定度；执行全量后端测试、前端 lint/build、依赖/密钥扫描、桌面和移动端浏览器回归。

### 阶段 E：CodeRabbit 对账关闭

按五个原始目录重新分段审查。每个批次记录 `原始候选数 -> FIXED/INVALID/DUPLICATE/ACCEPTED_RISK/PENDING -> 新增候选数`，最终 `PENDING=0` 才能关闭本计划。

## 6. 完成定义

- 安全默认值必须失败关闭，人员凭据不进入浏览器 JavaScript。
- ORM 与总 DDL 自动比对通过；无物理外键、无自动 DDL、无运行时禁止语句。
- 后端全量测试、前端 lint 和生产构建通过。
- 核心用户流完成真实浏览器操作，不以“页面能打开”代替业务验证。
- 关键数据链可从车号、测量点追溯到五工序实际参数、材料、质量结果和 AI 样本。
- 计划、代码、测试证据和剩余风险同步更新，禁止只改代码不回写台账。
