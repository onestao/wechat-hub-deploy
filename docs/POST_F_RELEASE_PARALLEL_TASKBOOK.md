# WeChat Hub Post-F Release / CI / GHCR 并行任务书

版本：2026-09-02

适用目录：

```text
G:\LLM\WeChat_Hub
```

本任务书是一个**完全自包含的后续执行手册**。新的会话/Agent 不需要读取之前的聊天记录，但开始工作前必须读取本文件以及文中指定的项目文件。

---

# 1. 当前项目状态

截至 2026-09-02，F-Live 双账号真实 Gate 已完成，详细证据位于：

```text
F_COMPLETION_REPORT.md
docs/SESSION_F_RUNTIME_SENDER_DRIVERS.md
```

当前已经有真实 NAS/微信证据证明：

- A/B 均可运行独立 `agent_wechat` Runtime。
- Container/Data/Desktop/Token/PID namespace 隔离通过。
- 双账号真实并行发送通过。
- post-fix Core 正式 write Gate：52/52 DB-confirmed sent。
- wrong-chat = 0。
- duplicate = 0。
- missing = 0（post-fix required Core Gate）。
- uncertain = 0（post-fix required Core Gate）。
- B SIGSTOP 时 `/v1/accounts` 约 1.83 s 返回并正确 degraded。
- Desktop Gateway HTTP/WebSocket/鼠标/键盘真实 Edge 验证通过。
- Runtime/Core/Console/A/B child token-value 日志扫描无命中。
- AgentWechat upstream false-success 已由 Core `submitted -> DB echo -> sent` 门禁收敛。
- message identity 已改为稳定 source identity，并完成旧库 dedupe migration。
- media `_image_aes/_image_xor` 与真实 XOR derive 修复已通过真实图片验证。
- AgentWechat 首次 ChatOpen 时序问题已由 Core-side official chat-open preflight 修复并 live 验证。

当前仍未闭环：

1. **Runtime reproducible source build = BLOCKED**：NAS source build 曾因外网 APT/下载失败而中断。
2. **最新 Core chat-preopen 修复尚未重新进入正式 source-built image**；真实 Gate 使用了工作树 + live hot-patch。
3. **EFB = PARTIAL**：text 有成功与 uncertain；image/file 尚缺可靠媒体 echo reconciliation。file 内容本身真实发送成功，但 outbox 不能从 DB media echo 转为 sent。
4. **remote filename preservation = PARTIAL**：上游仍使用 `send_file_<timestamp>_<safe_name>`。
5. 双 AgentWechat 无发送瞬时资源样本约 2.59 GiB，Docker CPU 瞬时约 85%；尚缺真正长期 idle 平均 CPU 采样。
6. Native Bridge 仍为 `NOT TESTED / RESERVED`，本阶段不要展开逆向实现。
7. **Post-F Desktop UX = source complete / live pending**：AgentWechat 账号已新增 Selkies Attach desktop provider，复用同一账号已有 `Xvfb :99` 与唯一 WeChat 进程，补齐本地中文 IME、clipboard、文件 upload/download、resize/DPI 等能力；noVNC 保留 fallback。该增量尚未在正式 GHCR Runtime/Core/Console RC 上完成真实浏览器 Gate。
8. **Manual Desktop / Sender GUI exclusion = source complete / live pending**：人工 Desktop 控制 WebSocket 与同账号自动 Sender 使用跨进程账号级 GUI lease；人工操作 A 时 A 的 outbox 必须 defer 且不增加 `attempt_count`，账号 B 仍可发送。该增量需要 H3 用正式镜像真实验证。

因此当前总状态：

```text
F Functional / Live Acceptance       PASS
Dual-account isolation               PASS
Dual-account concurrent sending      PASS
F-Live noVNC Desktop                PASS
Token isolation                      PASS
Core DB-confirmed text send          PASS
EFB                                  PARTIAL
Remote filename preservation         PARTIAL
Runtime reproducible image           BLOCKED
Current Core image reproducibility   PARTIAL
Selkies Attach desktop               PARTIAL (source complete / live pending)
Production Ready                     PARTIAL
```

---

# 2. 后续发布方向（已确定，不再重新设计）

正式生产构建采用：

```text
Git source
   ↓
GitHub Actions
   ↓
tests + clean Docker build
   ↓
GHCR immutable image
   ↓
Release Manifest（固定 digest）
   ↓
Unraid docker pull
   ↓
deploy / rollback
```

原则：

1. **Unraid/NAS 是 Runtime Host，不是正式 Build Server。**
2. NAS 本地 `docker build` 只作为开发/诊断/断网应急，不作为 Production Ready 的必要条件。
3. 正式 reproducible build 的定义是：干净 GitHub runner 从固定源码成功构建、测试并产生可追踪 image digest。
4. Production Compose/Manifest 不使用 `latest`。
5. Production 最终按 `image@sha256:...` 固定镜像。
6. tag 用于人类识别；digest 才是正式部署身份。
7. `agent-wechat` 尽量继续直接使用 upstream 固定版本/固定 digest，不复制/Fork其源代码。
8. 当前阶段只验证 `linux/amd64`。没有真实 arm64 Gate 前不得宣称 arm64 Production support。
9. 当前镜像/仓库默认设为 **PRIVATE**。在完成全部 upstream license / redistribution audit 前，不公开发布包含官方 WeChat 客户端或其衍生运行环境的镜像。

GitHub 官方资料确认：GitHub Actions 可使用 `GITHUB_TOKEN` 将镜像发布到 GHCR；GitHub 建议第三方 Actions 固定到 commit SHA；GHCR 支持按 immutable digest 拉取；外部机器拉 private package 可使用只含 `read:packages` 的 PAT classic。

参考：

- https://docs.github.com/actions/tutorials/publish-packages/publish-docker-images
- https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- https://docs.github.com/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

---

# 3. Git 仓库策略

**不要在本阶段强行改造成 Monorepo。**

当前 `work/*` 已经是独立 Git Repository，并保留各自 upstream/source-cache 历史：

```text
work/runtime
work/core
work/console
work/agent
work/efb-linux-wechat-slave
```

本阶段继续保留这种结构，避免在已经通过真实 Gate 后再做大规模目录迁移。

建议用户自己的 GitHub canonical repositories：

```text
wechat-hub-runtime
wechat-hub-core
wechat-hub-console
wechat-hub-agent
wechat-hub-efb-linux-wechat-slave
wechat-hub-deploy
```

其中：

- 每个 `work/*` repo 新增用户自己的 `origin`。
- 原 `upstream` remote 保留，禁止覆盖。
- 原 `source-cache` local remote 保留即可。
- `wechat-hub-deploy` 用于 root 的 `stack/`、`docs/`、Release Manifest、部署脚本和发布文档。
- `wechat-hub-deploy` 不提交 `work/`、`upstream/`、`.tmp/`、真实 DB、token、二维码、Live Gate marker 等运行数据。

如果用户明确要求未来再合并 Monorepo，应另开任务；当前 Release 不因此阻塞。

---

# 4. 并行执行拓扑

不要一上来让多个 Agent 同时修改当前未提交工作树。

执行分三波。

## Wave 0：只开一个会话

```text
Session 0 — Release Coordinator / Source Freeze
```

目标：把当前已经通过 F-Live 的未提交工作树固化成可追踪、无 secret 的 Git baseline。

**只有 Session 0 输出 `RELEASE_BASELINE_READY` 后，才开始 Wave 1。**

重要：如果 GitHub push 已经开始，但 push 的 commit 早于 Post-F Selkies Attach / Desktop-Sender lease 增量，**不得**把那个较早 commit 当成最终 Release baseline。允许正常追加 commit 并再次 push，但禁止 force-push 改写历史。Session 0 必须以包含当前全部 Post-F source changes 的最终 SHA 输出 `RELEASE_BASELINE_READY`。

## Wave 1：可以同时开 5 个会话

```text
Session G1 — Runtime reproducible CI/GHCR
Session G2 — Core reproducible CI/GHCR
Session G3 — Console CI/GHCR + Desktop packaging
Session G4 — Deploy/Release Manifest/GHCR rollout
Session G5 — Agent + EFB test/package CI
```

这些会话的代码所有权互不重叠，允许同时执行。

## Wave 2

当 G1/G2/G3/G4 已提供 RC image digest 后：

```text
Session H1 — EFB media echo reconciliation
Session H2 — Idle CPU / resource profiling
Session H3 — GHCR RC real NAS acceptance
```

H1 与 H2 可以并行。

H3 必须等 G1/G2/G3/G4 的 RC 镜像和 Release Manifest 可用后再执行。

如果 H1 要修改 `work/core`，必须以 **G2 完成后的 baseline** 开始，不能和 G2 同时修改同一个 Core working tree。

## Final

最后回到 Session 0：

```text
Session 0 — Final Release Sign-off
```

汇总所有 digest、测试和 live evidence，决定是否发布 `v0.1.0` 或继续 `rc`。

---

# 5. Session 0 — Release Coordinator / Source Freeze

## 5.1 所有权

Session 0 可以读取全部项目。

在 Freeze 阶段不要修改功能逻辑。

主要负责：

- Git hygiene
- secret/runtime data scan
- 当前测试基线复核
- canonical origin 准备
- baseline commits
- root deploy repo
- release status coordination

## 5.2 开始前必读

```text
F_COMPLETION_REPORT.md
docs/SESSION_F_RUNTIME_SENDER_DRIVERS.md
docs/INTERFACE_CONTRACT_V1.md
docs/WORK_PACKAGE_HANDOFFS.md
docs/UPSTREAM_LOCK.md
docs/SOURCE_MAP.md
```

并分别检查：

```text
work/runtime
work/core
work/console
work/agent
work/efb-linux-wechat-slave
```

的：

```text
git status
git diff
git diff --check
git remote -v
```

遇到 Windows dubious ownership 只允许命令级：

```text
git -c safe.directory=<repo> ...
```

不要修改 global git config。

## 5.3 Freeze 前 secret / artifact Gate

不得把以下内容推 GitHub：

- auth token
- DB key
- WeChat credential
- QR snapshot
- 用户聊天数据库
- `.tmp/f-live`
- NAS `/tmp` 测试文件
- appdata
- cookie/session
- SSH private key
- generated SQLite DB
-真实日志（如包含个人数据）

建立或补充 `.gitignore`。

对 staged files 和完整待提交 diff 做 secret scan。

不得把 token-value 本身打印到 completion report。

## 5.4 Freeze 回归

重新运行当前可运行的：

```text
Runtime
Core
EFB
Console
Agent
Mock Core
Stack
Python compile
JS syntax
YAML/OpenAPI
git diff --check
```

测试数允许随当前代码自然增长，不要为了匹配历史数字删测试。

## 5.5 Baseline commit

本阶段**允许并要求建立本地 baseline commit**，因为后续 CI 必须基于可追踪源码。

但必须遵守：

- 不 squash/rebase upstream history。
- 不 force push。
- 不自动改写以前 commit。
- 不把所有 work repo 合并成一个 repo。
- 每个 repo 的 commit message 明确类似 `release: freeze post-f-live baseline`。
- 在 commit 前记录旧 HEAD、新 HEAD、diff stat、测试结果。

如果用户自己的 GitHub `origin` 已经配置并有权限，可以 push baseline branch。

如果没有 GitHub auth：

- 仍然完成本地 baseline commit；
- 输出 `GITHUB_AUTH_REQUIRED`；
- 不要用不明 PAT 或把 credential 写入文件。

## 5.6 Deploy repo

Root 当前不是 canonical Git repo。

建立 `wechat-hub-deploy` 时只纳入：

```text
docs/
stack/
F_COMPLETION_REPORT.md
release/        # 新建，用于 manifest
.github/        # deploy/release workflow
.gitignore
README.md       # 如需要
```

明确忽略：

```text
/work/
/upstream/
/.tmp/
/.playwright-mcp/
```

不要移动现有 work repo。

## 5.7 Session 0 完成标志

输出：

```text
RELEASE_BASELINE_READY

runtime baseline commit: <sha>
core baseline commit: <sha>
console baseline commit: <sha>
agent baseline commit: <sha>
efb baseline commit: <sha>
deploy baseline commit: <sha or local-only>

GitHub auth: READY / USER ACTION REQUIRED
secret scan: PASS / FAIL
full regression: PASS / PARTIAL / FAIL
```

并写：

```text
docs/POST_F_RELEASE_STATUS.md
```

只有 `RELEASE_BASELINE_READY` 才允许启动 G1–G5。

---

# 6. Session G1 — Runtime reproducible CI / GHCR

## 6.1 所有权

只修改：

```text
work/runtime
```

必要时可给 Session 0 提交 deploy/stack 建议，但不要直接并发修改 root deploy files。

## 6.2 目标

把当前：

```text
Reproducible Runtime image = BLOCKED
```

提升为：

```text
GitHub clean-runner build = PASS
GHCR RC image = PASS
```

NAS 本地 build 失败不再等价于 Production build FAIL。

## 6.3 Dockerfile hardening

审查当前 Runtime Dockerfile 所有网络依赖：

- base image
- apt repositories
- Tencent/WeChat download
- GitHub download
- pip/npm/cargo（如有）

要求：

1. 优先 HTTPS。
2. 合理 timeout/retry。
3. 不因为某个历史 HTTP mirror 不可用而永久失败。
4. 固定关键版本。
5. 能校验下载的文件尽量使用 checksum。
6. 不把 secret 写进 image layer。
7. OCI label 至少包含：
   - `org.opencontainers.image.source`
   - `org.opencontainers.image.revision`
   - `org.opencontainers.image.version`
8. 审核 Runtime image 中官方 WeChat 客户端的 redistribution/license 风险；在完成法律/许可证确认前 GHCR package 保持 PRIVATE。

不要为了 build 稳定性上传或公开镜像一个来源不明的 WeChat `.deb`。

如需要 cache，优先 GitHub Actions cache/BuildKit cache，而不是把 proprietary installer 提交到 Git。

## 6.4 GitHub Actions

新增：

```text
.github/workflows/ci.yml
.github/workflows/publish-image.yml
```

或职责等价文件。

CI：

- pull_request
- push to release/development branch（根据 repo 当前 branch policy）
- 运行 Runtime tests
- clean Docker build
- 不 push production image

Publish：

- tag/release 或手动 workflow_dispatch
- `permissions` 最小化
- `contents: read`
- `packages: write`
- 如启用 attestation：`id-token: write`, `attestations: write`
- GHCR 使用 GitHub Actions 的 `GITHUB_TOKEN`
- 第三方 actions 固定到完整 commit SHA，不使用浮动 branch
- Actions 的当前 SHA 必须实现时从官方仓库/官方 GitHub 文档重新确认，不能照抄历史 taskbook 中可能过期的 SHA

建议 image：

```text
ghcr.io/<namespace>/wechat-hub-runtime
```

tag 至少：

```text
0.1.0-rc.N
sha-<git-short-sha>
```

不要让 Production Compose 使用 `latest`。

## 6.5 Target platform

第一阶段：

```text
linux/amd64
```

如果没有 arm64 真机和官方 WeChat arm64 upstream Gate，不做 multi-arch 宣称。

## 6.6 验收

必须证明：

```text
clean GitHub runner
→ checkout fixed commit
→ tests PASS
→ Docker build PASS
→ GHCR private RC push PASS
→ digest captured
```

同时检查 image 内包含：

- Desktop Gateway
- AgentWechat Runtime Manager
- interactive x11vnc reconcile
- parallel health probe / no global network probe lock
- current F-Live Runtime fixes
- Post-F Selkies Attach companion：只附着目标 AgentWechat child 的现有 `DISPLAY=:99`，不得启动第二个 Xvfb/WeChat。
- account-private X11/browser-files volumes 与独立 desktop auth secret。
- Selkies internal proxy 的 `X-WeChat-Hub-Desktop-Token` 认证与 health probe 使用一致。
- Desktop Gateway 对 Selkies HTTP/WebSocket/binary/large-upload 的代理路径。
- `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME/HOST/PORT` public endpoint 配置。
- manual Desktop GUI lease：Browser control WebSocket 与 Core Sender 通过同一 account-scoped lock file 互斥。

输出：

```text
G1_RUNTIME_RELEASE_REPORT.md
```

完成标志：

```text
RUNTIME_RC_READY
image=<fqdn>@sha256:<digest>
```

---

# 7. Session G2 — Core reproducible CI / GHCR

## 7.1 所有权

只修改：

```text
work/core
```

## 7.2 目标

确保所有 F-Live hot-patch 已进入 source tree，并由 clean build 生成正式 Core image。

必须特别核对：

- AgentWechat chat-open preflight + target validation
- submitted -> DB-confirmed sent
- false-success containment
- uncertain / no auto retry
- stable message identity
- duplicate migration
- `_image_aes/_image_xor`
- `derive_xor_byte()`
- per-account capabilities
- health degraded semantics
- account-scoped concurrency
- manual Desktop / automatic Sender account-scoped GUI lease：同账号人工控制时自动 Sender defer，不调用 upstream、不增加 `attempt_count`；不同账号不互锁

不得只因为 live container 里存在补丁就认为 source tree 已包含。

## 7.3 CI / Publish

建立与 Runtime 一致原则的 GitHub Actions：

- tests
- compile
- OpenAPI
- clean image build
- GHCR private RC
- fixed action SHAs
- `GITHUB_TOKEN`
- OCI source/revision/version labels
- digest output

建议 image：

```text
ghcr.io/<namespace>/wechat-hub-core
```

第一阶段只声明 `linux/amd64`。

## 7.4 本阶段不要做的事情

不要在 G2 同时实现大型 image/file echo reconciliation。

G2 的职责是：

> 把已经通过真实 F-Live 的 Core 精确、可重复地装进 image。

媒体 reconciliation 留给 H1，避免 CI 固化和新功能开发互相污染。

## 7.5 验收

在 clean runner：

- Core full tests PASS
- agent routing专项 PASS
- submitted reconciliation PASS
- migration tests PASS
- OpenAPI PASS
- Docker build PASS
- GHCR RC image push PASS

输出：

```text
G2_CORE_RELEASE_REPORT.md
```

完成标志：

```text
CORE_RC_READY
image=<fqdn>@sha256:<digest>
```

---

# 8. Session G3 — Console CI/GHCR + Desktop packaging

## 8.1 所有权

只修改：

```text
work/console
```

## 8.2 目标

- 将当前 Console/Desktop UI 从 source clean build 成正式 image。
- 确认增强模式 Beta、Desktop Gateway client URL、submitted/uncertain 状态文案都来自 source tree。
- 确认 Desktop API 返回 public `host/scheme/port` 时 Console 使用该 HTTPS/反代入口，而不是强制拼接当前页面 hostname。
- 确认 `desktop_provider=selkies|novnc`、`features`、`fallback_reason` 能正确透传；fallback noVNC 时给用户清晰提示。
- 建 GitHub CI + GHCR RC。

建议 image：

```text
ghcr.io/<namespace>/wechat-hub-console
```

## 8.3 CI

至少：

- Python tests
- Python compile
- JS syntax
- template/static consistency
- Docker build

如果能运行 headless browser：

- Home/account pages load
- Desktop link 使用 opaque gateway session
- browser-facing URL 不含 upstream token

不要要求 GitHub runner 连接真实微信。

## 8.4 发布

同样：

- private GHCR
- fixed action commit SHAs
- `GITHUB_TOKEN`
- digest capture
- linux/amd64 first

输出：

```text
G3_CONSOLE_RELEASE_REPORT.md
```

完成标志：

```text
CONSOLE_RC_READY
image=<fqdn>@sha256:<digest>
```

---

# 9. Session G4 — Deploy / Release Manifest / Rollback

## 9.1 所有权

只修改 canonical `wechat-hub-deploy` 内容：

```text
stack/
docs/
release/
.github/
```

不要修改 `work/*`。

## 9.2 目标

建立生产部署唯一来源：Release Manifest。

例如：

```yaml
release: 0.1.0-rc.1
platform: linux/amd64
images:
  runtime: ghcr.io/<namespace>/wechat-hub-runtime@sha256:...
  core: ghcr.io/<namespace>/wechat-hub-core@sha256:...
  console: ghcr.io/<namespace>/wechat-hub-console@sha256:...
  agent_wechat: ghcr.io/thisnick/agent-wechat@sha256:...
```

文件名建议：

```text
release/manifest-0.1.0-rc.1.yaml
```

Production Compose 从 manifest/env 获取 digest，不使用 `latest`。

Desktop production config 同时纳入 Release Manifest / env：

```text
WECHAT_SELKIES_ATTACH_ENABLED=true
WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=https
WECHAT_DESKTOP_GATEWAY_PUBLIC_HOST=<reverse-proxy-host>
WECHAT_DESKTOP_GATEWAY_PUBLIC_PORT=443
```

如暂时没有 HTTPS 域名，可以先保持 LAN HTTP 做基础 Gate，但 **system Clipboard API 不能因此宣称 Production PASS**。完整 clipboard Gate 必须在浏览器 secure context（HTTPS 或浏览器等价可信上下文）下完成。

## 9.3 AgentWechat upstream

固定当前经过 F-Live 验证的 upstream version 和实际 digest。

不要仅记录：

```text
:0.11.15
```

还要记录 pull 后实际 digest。

以后升级 AgentWechat：

```text
new upstream version
→ separate RC manifest
→ smoke Gate
→ promote digest
```

不要 Watchtower 自动更新。

## 9.4 Rollback

必须提供：

```text
deploy RC
health check
rollback previous manifest
```

Rollback 只切 image digest，不删除：

- account volumes
- Core DB
- `/data`
- `/home/wechat`
- Console DB
- account-private browser-files volume

Rollback 不得因为 Desktop provider 变化而删除登录数据、清空 browser-files，或启动第二份 WeChat。X11 socket 本身是 ephemeral，可在 primary 停止状态下重建，但对应账号的持久数据卷不得误删。

禁止 rollback script 调用：

```text
docker system prune
docker volume prune
```

## 9.5 Release Promotion

定义：

```text
rc image
→ H3 real NAS acceptance
→ promote same digest to Production manifest
```

**Production promotion 不能重新 build image。**

必须推广已经 H3 验证过的同一个 digest。

## 9.6 GHCR private pull 文档

对 Unraid private GHCR：

- 用户创建专门只读 PAT classic，只给 `read:packages`。
- 使用 `docker login ghcr.io --password-stdin`。
- credential 不写进 compose/env/git。
- 不给 Unraid `write:packages` / `delete:packages`。

GitHub 当前官方文档说明 GHCR CLI auth 使用 PAT classic；pull private package 只需 `read:packages`。

## 9.7 输出

```text
G4_DEPLOY_RELEASE_REPORT.md
```

完成标志：

```text
DEPLOY_RC_READY
```

在 G1/G2/G3 digest 出来前可以使用 placeholder/schema 完成大部分实现；拿到真实 digest 后再填 RC manifest。

---

# 10. Session G5 — Agent + EFB CI / Packaging

## 10.1 所有权

```text
work/agent
work/efb-linux-wechat-slave
```

这两个和 G1–G4 不共享代码，可以并行。

## 10.2 Agent

Agent 是 optional service。

目标：

- tests/compile CI
- 如果当前 Stack 以 container 运行 Agent，则构建对应 private GHCR image
- 如果当前部署方式不需要独立正式 image，不要为了“统一”强行引入新容器
- 保持 Core API 作为边界

## 10.3 EFB

EFB 当前仍允许 Host Python 运行。

因此本阶段：

- 不要求为了 GHCR 把 EFB 强制容器化
- 建 test/package CI
- 锁定 Python dependencies
- 确认 editable source / package 安装路径
- 保持 per-account capabilities
- 保持 uncertain 文案

不要在 G5 开始媒体 reconciliation；那属于 H1。

## 10.4 输出

```text
G5_OPTIONAL_SERVICES_RELEASE_REPORT.md
```

完成标志：

```text
OPTIONAL_SERVICES_CI_READY
```

---

# 11. Wave 1 结束 Gate

Session 0 汇总 G1–G5。

至少必须得到：

```text
RUNTIME_RC_READY
CORE_RC_READY
CONSOLE_RC_READY
DEPLOY_RC_READY
OPTIONAL_SERVICES_CI_READY
```

然后建立：

```text
release/manifest-0.1.0-rc.1.yaml
```

该 manifest 中所有 WeChat Hub production service 必须使用 digest。

此时才能进入 H3 real NAS RC acceptance。

---

# 12. Session H1 — EFB image/file echo reconciliation

## 12.1 依赖

必须等 G2 完成并把 Core baseline 固定后开始。

## 12.2 所有权

```text
work/core
work/efb-linux-wechat-slave
```

如果需要并行开发，必须建立新 branch/worktree；不要直接与另一个正在修改同一 repo 的 Agent 共用未提交 working tree。

## 12.3 目标

把当前：

```text
EFB media outbox submitted -> uncertain
```

尽可能升级成：

```text
submitted -> unique DB media echo -> sent
```

## 12.4 安全原则

和 text 一样：

> 只能唯一确认，不能猜。

File matcher 可以研究：

- account_id
- chat_id
- message type
- bounded time window
- original filename
- upstream rewritten filename normalization
- file size
- DB media metadata
- 可获得的 hash

Image matcher可以研究：

- account_id
- chat_id
- message type
- bounded time window
- media size
- decoded/media hash
- DB media metadata

如果 0 candidate：继续等待。

如果 >1 plausible candidate：

```text
uncertain
```

禁止取“第一条/最近一条”猜测。

## 12.5 Filename preservation

不要为了原始 filename Fork agent-wechat。

可以：

- normalize upstream `send_file_<ms>_` 前缀用于 reconciliation；
- UI 显示用户原始 requested filename；
- 同时保留 actual upstream/WeChat filename metadata。

但不能谎报远端真正保存了原名。

保持：

```text
content delivery = PASS
remote filename preservation = PARTIAL
```

直到 upstream 真正支持。

## 12.6 Gate

至少测试：

- file unique echo
- image unique echo
- wrong chat candidate 不确认
- multiple candidate 不确认
- timeout 不自动 retry
- EFB 正确显示 sent/uncertain

如果可安全访问 F-Live，再做极小真实测试：

- 1 image 到 filehelper
- 1 file 到 filehelper

禁止扩大压力测试。

输出：

```text
H1_MEDIA_RECONCILIATION_REPORT.md
```

---

# 13. Session H2 — Idle CPU / resource profiling

## 13.1 目标

解释当前双账号 no-send Docker CPU 瞬时约 85% 是否为持续 background load。

不要只看一次 `docker stats --no-stream`。

## 13.2 真实采样

在 NAS 无发送、无主动 Desktop 操作、Sync 已稳定后：

```text
10–15 minutes
每 30 seconds 采样一次
```

记录：

- Runtime
- Core
- Console
- AgentWechat A
- AgentWechat B
- child 内 WeChat processes
- Xvfb
- x11vnc
- agent-server
- Desktop Gateway
- Selkies Attach companion（打开增强 Desktop 后）

统计：

- mean CPU
- median CPU
- p95
- max
- RSS/working set

## 13.3 定位

如果持续高：

只做低风险 profiling，优先判断：

- WeChat renderer 本身
- GUI compositor/Xvfb
- x11vnc refresh loop
- agent-server poll
- Runtime health polling
- Core sync frequency
- media sync loop

不要为了降 CPU 修改微信客户端、禁用 DB Sync 或破坏 Desktop。

如果发现代码 busy loop，另开最小 patch + regression。

## 13.4 输出

```text
H2_RESOURCE_PROFILE_REPORT.md
```

明确区分：

```text
upstream WeChat cost
WeChat Hub overhead
```

不要把 Docker CPU 百分比误写成全机 CPU 百分比。

资源报告至少比较：

```text
Desktop closed / no active Selkies control session
Desktop active / Selkies Attach connected
```

如果 companion 在首次打开后继续常驻，必须如实记录 idle RSS/CPU；若持续开销明显，再单独提出 account-scoped idle shutdown/TTL patch，不要在 profiling 会话里顺手重构 Runtime 生命周期。

---

# 14. Session H3 — GHCR RC real NAS acceptance

这是最关键的 Release Gate。

## 14.1 依赖

必须已有：

- Runtime RC digest
- Core RC digest
- Console RC digest
- agent-wechat fixed digest
- RC Release Manifest
- rollback manifest

## 14.2 目标

证明：

> 之前 F-Live 的成功不是 hot-patch 偶然状态，而是可以从 Git/GitHub Actions/GHCR 重新部署的正式镜像行为。

## 14.3 数据保护

升级前备份/记录：

- Core DB path
- account registry
- A/B `/data` volume
- A/B `/home/wechat` volume
- current image digests
- current container labels

不打印 DB key/token。

不要删除 volume。

## 14.4 部署

Unraid 只做：

```text
docker login ghcr.io
docker pull <digest>
deploy RC manifest
```

不要在 NAS `docker build` RC。

## 14.5 最小真实复验

不再重复 F-Live 52 条。

只需：

1. Runtime/Core/Console image digest 与 manifest 完全一致。
2. A/B account registry 正确。
3. A/B health/login/sync 正确。
4. A/B Desktop 正确，鼠标键盘可用，无 token。
5. A → filehelper 1 条唯一 text：`submitted -> DB echo -> sent`。
6. B → filehelper 1 条唯一 text：`submitted -> DB echo -> sent`。
7. A/B 并行 5+5：全部 DB-confirmed；wrong-chat=0，duplicate=0，missing=0。
8. B stop/SIGSTOP：A 不受影响。
9. restart/recreate 后 volume/login 数据保持（如 WeChat 上游要求手机确认，如实记录）。
10. token-value logs no-hit。

### 14.5.1 Post-F Selkies Desktop Gate（必须执行）

至少选择一个 Canary AgentWechat 账号，在正式 RC Runtime/Core/Console digest 上正常 restart/recreate（保留 `/data`、`/home/wechat`），使新的 account-private X11/files mounts 生效，然后验证：

1. `desktop_provider=selkies`，不是因为旧 child 缺 mount 而自动 fallback 的 noVNC。
2. 每账号仍只有 **一份 WeChat process + 一份 Xvfb**；Selkies companion 只做 display/input/file transport。
3. Windows Edge/Chrome 本地中文 IME 可输入完整中文字符串。
4. 英文键盘、鼠标正常。
5. text clipboard PASS。
6. image/binary clipboard PASS；如 LAN HTTP 被浏览器 secure-context 阻止，切 HTTPS 后重新验证，不能把 HTTP limitation 当实现 PASS。
7. file upload PASS，上传文件只进入该账号 browser-files volume，并能从同账号 WeChat `/home/wechat/WeChatHubFiles/Desktop` 看到。
8. file download PASS。
9. dynamic resize / screen settings / DPI scaling PASS。
10. reload/reconnect 后桌面恢复。
11. A/B 都启用 Selkies 后，Desktop 与 browser-files 不串账号。
12. child `6174`、Selkies internal `8081/8082` 均无 Host PortBinding；浏览器 URL/JSON/log 无 upstream agent token 或 desktop secret。

### 14.5.2 Manual Desktop / Sender exclusion Gate（P0）

真实打开账号 A 的 Selkies Desktop 并保持控制 WebSocket active：

```text
A Desktop active
→ queue A text send
→ A send remains accepted/queued/deferred
→ upstream send endpoint NOT called
→ attempt_count remains 0

同时 queue B text send
→ B submitted -> unique DB echo -> sent
```

关闭 A Desktop 后：

```text
A queued send
→ automatically resumes
→ submitted
→ unique DB echo
→ sent
```

反向也要验证：A Sender 已经持有 GUI lease 正在执行时，新 A Desktop control WebSocket 必须 fail-closed/busy，而不是抢焦点；B Desktop 不受影响。

任意人工 Desktop + Sender race 导致 wrong-chat、重复或跨账号阻塞，均为 Release P0 FAIL。

如果 H1 已经完成且准备进入同一 RC：

- 再做 1 image + 1 file。

否则媒体 EFB 不阻塞基础 RC 发布，继续标记 PARTIAL。

## 14.6 Rollback drill

至少验证一次：

```text
RC manifest
→ previous manifest
→ services healthy
```

不删除 volume。

之后可以再切回 RC。

## 14.7 完成

输出：

```text
H3_GHCR_RC_LIVE_ACCEPTANCE.md
```

只有满足：

```text
same source commit
same GHCR digest
same tested production deployment
```

才能把 reproducibility 从 BLOCKED/PARTIAL 提升为 PASS。

Post-F Desktop 只有同时满足上面的 Selkies Live Gate 与 Manual Desktop/Sender exclusion Gate，才能从 `source complete / live pending` 提升为 `PASS`。

---

# 15. Final Release Sign-off

回到 Session 0。

Session 0 必须汇总：

```text
G1_RUNTIME_RELEASE_REPORT.md
G2_CORE_RELEASE_REPORT.md
G3_CONSOLE_RELEASE_REPORT.md
G4_DEPLOY_RELEASE_REPORT.md
G5_OPTIONAL_SERVICES_RELEASE_REPORT.md
H2_RESOURCE_PROFILE_REPORT.md
H3_GHCR_RC_LIVE_ACCEPTANCE.md
```

H1 如已执行也纳入。

最终发布时生成：

```text
release/manifest-0.1.0.yaml
docs/PRODUCTION_RELEASE_0.1.0.md
```

Production manifest 必须和通过 H3 的 RC 使用**完全相同 image digest**。

不要 Production promotion 时重新 build。

## 15.1 Production PASS 最低条件

```text
Runtime clean CI build              PASS
Core clean CI build                 PASS
Console clean CI build              PASS
GHCR immutable digests              PASS
Deploy manifest                     PASS
RC real NAS deployment              PASS
A/B DB-confirmed text               PASS
A/B 5+5                              PASS
wrong-chat                           0
duplicate                            0
token leak                           0
Desktop isolation                    PASS
Selkies Attach live UX               PASS
Manual Desktop / Sender exclusion    PASS
Failure isolation                    PASS
Rollback                             PASS
Volumes/data preserved               PASS
```

允许仍为：

```text
EFB media reconciliation             PARTIAL
Remote filename preservation         PARTIAL
Native Bridge                        RESERVED
```

但必须在 release notes 明确，不允许把 PARTIAL 写成 PASS。

---

# 16. Upstream AgentWechat 升级策略

当前 F-Live 验证的 upstream 不应被自动更新。

以后每次 upstream 发布新版本：

```text
new upstream tag/digest
→ create new RC manifest
→ no source fork
→ CI/API compatibility tests
→ A/B health/login
→ Desktop A/B
→ A text + B text
→ optional image/file
→ A/B 5+5
→ promote exact same digest
```

如果失败：

```text
rollback previous upstream digest
```

不要使用 Watchtower 自动更新 `agent-wechat`。

---

# 17. 用户本人需要做什么

Agent 应尽可能自动完成其余工作。用户只负责以下少量人工事项。

## 用户动作 U1 — GitHub 身份认证

在 Session 0 开始后，如果 Agent 报：

```text
GITHUB_AUTH_REQUIRED
```

用户需要在 Windows 主机完成 GitHub 登录。

优先：

```text
gh auth login
```

或通过 GitHub Web 创建 private repositories，再把 repo URL 告诉 Session 0。

不要把 GitHub 密码/PAT 粘贴到聊天中。

建议所有 WeChat Hub repo/package 初期都设为 PRIVATE。

## 用户动作 U2 — 确认 GitHub namespace

告诉 Session 0 你希望使用：

```text
GitHub username
```

或：

```text
GitHub organization
```

作为 GHCR namespace。

如果没有 organization，个人 namespace 完全可以。

## 用户动作 U3 — Unraid private GHCR 只读登录

当 G4/H3 通知需要拉 private GHCR 时：

在 GitHub 创建一个**只用于 Unraid pull** 的 PAT classic，权限仅：

```text
read:packages
```

然后在 Unraid 使用：

```text
docker login ghcr.io
```

或按 Agent 给出的 `--password-stdin` 方式登录。

不要把 PAT 写入：

- compose
- `.env`
- Git
- completion report
- 聊天消息

GitHub 官方文档当前说明 GHCR CLI authentication 使用 PAT classic，下载 package 只需要 `read:packages`。

## 用户动作 U4 — RC 时的微信手机确认

H3 替换正式 Runtime/Core/Console image 后：

正常情况下 A/B 的 `/data` 和 `/home/wechat` 保留，应尽量保持登录状态。

如果微信因为客户端重启要求手机重新确认：

用户只需按 H3 Agent 提示扫码/确认。

不要提前删除账号重建。

## 用户动作 U5 — 最终 Production promotion

H3 报告 PASS 后，Session 0 会给出最终：

```text
manifest-0.1.0.yaml
```

用户只需要确认：

```text
“使用已验证的 RC digest 发布 Production”
```

不要要求 Agent 重新 build 一遍 Production image。

---

# 18. 用户不需要做什么

正常情况下用户不需要：

- 在 NAS 手动 build Runtime/Core/Console。
- 手动上传 Docker image tar。
- 手动改 Dockerfile。
- 手动复制 hot-patch。
- 手动修改 agent-wechat Rust 源码。
- 再跑 52 条真实压力发送。
- 创建第三个微信账号。
- 开启 Native Bridge。
- 把 GitHub PAT 发给 Agent。
- 手工维护 `latest` tag。

---

# 19. 可以直接复制给各会话的启动指令

下面每段单独发给一个新会话即可。

## 会话 0

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session 0（Release Coordinator）。

请完整阅读：
docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md

然后只执行其中“Session 0 — Release Coordinator / Source Freeze”。

你的首要目标不是继续开发功能，而是把当前已经通过 F-Live 的多个未提交工作树安全冻结成无 secret、可追踪、可供 GitHub CI 使用的 baseline。

不要重构架构，不要覆盖 upstream remote，不要 force push，不要把 work/* 强行改成 monorepo。

完成后必须输出 RELEASE_BASELINE_READY；若 GitHub 登录/Repo 创建需要用户动作，则输出 GITHUB_AUTH_REQUIRED 和最小人工步骤。
```

## 会话 G1

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session G1，负责 Runtime reproducible CI/GHCR。

先阅读：
docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md
docs/POST_F_RELEASE_STATUS.md
F_COMPLETION_REPORT.md

必须确认 Session 0 已输出 RELEASE_BASELINE_READY。

只修改 work/runtime。

按任务书 Session G1 完成 Runtime clean GitHub build、Dockerfile/network reproducibility hardening、private GHCR RC image 和 digest。不要修改 Core/Console/Deploy，不要进行真实微信发送，不要把 NAS 本地 build 作为 Production build 必要条件。

完成后输出 RUNTIME_RC_READY 和实际 image digest。
```

## 会话 G2

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session G2，负责 Core reproducible CI/GHCR。

先阅读：
docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md
docs/POST_F_RELEASE_STATUS.md
F_COMPLETION_REPORT.md

必须确认 RELEASE_BASELINE_READY。

只修改 work/core。

重点确认所有 F-Live 修复，尤其 chat-open preflight、submitted->DB-confirmed sent、stable message identity、media key/XOR 修复，全部存在于 source tree 和 clean source-built image。

本会话不要开发大型 image/file media reconciliation；那是 H1。

完成 clean CI、private GHCR RC 后输出 CORE_RC_READY 和实际 image digest。
```

## 会话 G3

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session G3，负责 Console CI/GHCR 与 Desktop packaging。

阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md 和 docs/POST_F_RELEASE_STATUS.md。

必须确认 RELEASE_BASELINE_READY。

只修改 work/console。

建立 tests/JS/Python/Docker clean CI，发布 private GHCR RC image，确保 Desktop Gateway client、opaque session、token boundary、增强模式 Beta、submitted/uncertain UI 都来自正式 source tree。

不要连接真实微信做 write test。

完成后输出 CONSOLE_RC_READY 和 digest。
```

## 会话 G4

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session G4，负责 deploy/release manifest/rollback。

阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md 和 docs/POST_F_RELEASE_STATUS.md。

必须确认 RELEASE_BASELINE_READY。

只修改 canonical wechat-hub-deploy 范围：stack、docs、release、deploy workflows；不要修改 work/*。

建立 digest-pinned RC manifest、AgentWechat upstream digest pin、private GHCR pull 文档、rollback flow 和 Production promotion 规则。

可以先用 placeholder，等待 G1/G2/G3 实际 digest 后填入。

完成后输出 DEPLOY_RC_READY。
```

## 会话 G5

```text
G:\LLM\WeChat_Hub

你是 Post-F Release Session G5，负责 Agent + EFB CI/package readiness。

阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md 和 docs/POST_F_RELEASE_STATUS.md。

必须确认 RELEASE_BASELINE_READY。

只修改 work/agent 和 work/efb-linux-wechat-slave。

Agent 保持 optional；EFB 保持允许 Host Python。不要为了统一 Docker 而强制容器化 EFB。

只做 tests/dependency/package/CI 固化，本会话不要实现 media echo reconciliation。

完成后输出 OPTIONAL_SERVICES_CI_READY。
```

## 会话 H1

```text
G:\LLM\WeChat_Hub

你是 Post-F Session H1，负责 EFB image/file DB echo reconciliation。

完整阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md、F_COMPLETION_REPORT.md 和 G2 report。

只有 G2 已完成后才能开始。

可以修改 work/core 与 work/efb-linux-wechat-slave。

严格执行 unique-only reconciliation：无法唯一确认就 uncertain，不得猜，不得自动 retry。不要 Fork agent-wechat 来修 filename。

先单测，再根据任务书决定是否做极小 filehelper live Gate。
```

## 会话 H2

```text
G:\LLM\WeChat_Hub

你是 Post-F Session H2，负责双账号长期 idle CPU/RAM profiling。

完整阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md 和 F_COMPLETION_REPORT.md。

使用真实 NAS 但不做大量发送。按任务书进行 10–15 分钟连续采样，区分 WeChat upstream cost 与 WeChat Hub overhead。

除非明确找到 busy loop，否则不要改功能代码。
```

## 会话 H3

```text
G:\LLM\WeChat_Hub

你是 Post-F Session H3，负责 GHCR RC 正式镜像真实 NAS Acceptance。

完整阅读 docs/POST_F_RELEASE_PARALLEL_TASKBOOK.md、F_COMPLETION_REPORT.md、G1/G2/G3/G4 reports 和 RC manifest。

必须等 Runtime/Core/Console RC digest 和 DEPLOY_RC_READY 都存在。

NAS 只 pull 固定 digest，不本地 build。保留现有 A/B volumes/data。重新部署 RC 后只做最小真实复验：A/B health/sync/Desktop、A/B 各 1 text、A/B 5+5、failure isolation、token scan、rollback drill。

不要重复 52 条 F-Live Gate，不要创建第三账号，不要开启 Native Bridge。

完成后输出 H3_GHCR_RC_LIVE_ACCEPTANCE.md 和 RELEASE_CANDIDATE_PASS / FAIL。
```

---

# 20. 冲突避免规则

并行工作的绝对规则：

| Session | 可写范围 |
|---|---|
| 0 | freeze/coordination/deploy baseline；Wave 1 时不要并发改各 work repo |
| G1 | `work/runtime` |
| G2 | `work/core` |
| G3 | `work/console` |
| G4 | deploy root：`stack/docs/release/.github` |
| G5 | `work/agent`, `work/efb-linux-wechat-slave` |
| H1 | G2 完成后 `work/core` + EFB |
| H2 | 主要 NAS profiling，不与源码 Agent 抢 working tree |
| H3 | deployment/live acceptance；除真实 blocker 外不要开发新功能 |

如果发现另一个 Agent 已在自己的可写范围中产生未提交修改：

- 不覆盖；
- 不 reset；
- 不 checkout --；
- 不 clean；
- 停止并报告 ownership conflict。

---

# 21. Release 安全底线

以下任意发生，都不能发布 Production：

### P0

- wrong-chat > 0
- Desktop 串账号
- account DB/data 串号
- upstream token 出现在 browser-facing URL
- token/key 写入 persistent logs/Git
- child 6174 发布到 Host
- 一个账号同时出现两份主 WeChat
- RC 使用的实际 image digest 与 manifest 不一致
- Production 重新 build 而不是 promotion 已测试 RC digest
- rollback 删除 account volume

### P1

- `latest` 作为 Production image ref
- Core hot-patch 未进入正式 image
- Runtime hot-patch 未进入正式 image
- clean CI image build 不能从固定 commit 重现
- 一个账号故障拖死全部 `/v1/accounts`
- submitted/uncertain 自动 retry

---

# 22. 最终期望结果

完成本任务书后，最终部署应是：

```text
GitHub repos
   │
   ├─ Runtime commit ─→ GHCR runtime@sha256:A
   ├─ Core commit    ─→ GHCR core@sha256:B
   ├─ Console commit ─→ GHCR console@sha256:C
   └─ Deploy repo    ─→ manifest-0.1.0.yaml
                              │
                              └─ agent-wechat@sha256:D

Unraid
   ↓
pull A/B/C/D
   ↓
deploy exact manifest
   ↓
A/B real WeChat
```

并且：

```text
开发机器/NAS 坏掉
→ 仍可从 Git + GHCR 重建部署

新版本有问题
→ 直接回切旧 manifest/digest

AgentWechat 新版本适配新版微信
→ 新 RC digest
→ 小规模真实 Gate
→ promotion
```

这才是本阶段 Production Ready 的真正完成标准。

