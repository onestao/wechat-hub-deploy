# WeChat Hub RC.5 — R5 Integration Report

- 日期：2026-09-06
- 角色：R5（集成、发布、分阶段验收）
- 计划基线：R5 PLAN REVIEW = PASS（2026-09-05 批准版，含 4 项执行修正）
- 结论速览：**RC.5 R5 INTEGRATION = BLOCKED（final-artifact promotion）**；功能栈验证 PASS。阻塞原因为 AgentWechat `0.11.15-wh.2` 的两项构建缺陷（见 `docs/R5_RC5_FINDINGS.md` F1），按 operator 指示记录并延后修复。

---

## 1. 固定基线与权威输入

| 项 | 值 |
|---|---|
| DEPLOY_HISTORY_BASE_SHA | `0df861658e24300cf1520314c69f805c8adae11f`（修正：项目惯例允许向历史 manifest 追加 canary 证据；`d531a2b` 会误判该追加。P1 validator 以 `--base-ref` 显式传入，全程未用 HEAD） |
| R1 final | `fc634d0737375247b7add6aaf4c79a69237dba79`（`wechat-hub/0.11.15-health-recovery-v2`） |
| R2 pipeline | `948423c8f16478aeb0ace65ee395949a69855f09`（`wechat-hub/0.11.15-publish-pipeline`） |
| R3 runtime | `8e9e98ebbf8343bf5764d36904c95af20779b048`（`rc5/desktop-ux-navigable-web-client`） |
| R4 test-only | Runtime `6e08752dbf836969c9e0c0890a1a4c2a581fb8a0`、Core `13a048881e05a512bf5d1aac83b7a41ed0139a1e` |

## 2. AgentWechat 集成与发布

- 集成分支 `wechat-hub/0.11.15-rc5-integration`：R1 final + R2 cherry-pick。
- **7 文件白名单 PASS**（相对 R1 仅新增 workflow/CI scripts/.gitattributes；`docker/Dockerfile` 与 lockfile 无变化）。
- `cargo fmt` 183 处违规以独立 commit `3f5a0a6` 修复（纯格式化）；时序测试 `immutable_read_does_not_block_writer` 在 WSL2 稳定失败（241-539ms vs <100ms，ext4 fsync 慢），**GH runner CI preflight PASS**，判定为环境性。
- R2 workflow 审查 PASS：目标 repo 正确、双 fail-closed tag-absence 检查、OCI revision/upstream 标签、受版本控制 Dockerfile、per-tag 并发序列化、amd64-only。
- 发布 `0.11.15-wh.2`：run 33980180827 success。发布前 tag-absence 确认为确定性 `manifest unknown`（正例 rc.4 EXISTS）。
- Workflow 需在 default branch 注册方可 dispatch：以单一 additive commit `c8d53c7`（仅 `.github/workflows/publish-agent-wechat.yml`）fast-forward 到 `main`。

## 3. Artifact 三层 identity 闭环

### AgentWechat `0.11.15-wh.2`
| 层 | 值 | 一致性 |
|---|---|---|
| source commit | `3f5a0a6015f6fb9000a9d97e045c56b63ea8d18e` | — |
| OCI revision | `3f5a0a6015f6fb9000a9d97e045c56b63ea8d18e` | ✅ |
| registry digest | `sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd` | ✅（NAS pull 验证） |
| upstream 标签 | base-commit `3b7de890...` / base-tag `v0.11.15` | ✅ |
| NAS running == digest | **不成立**（见 §7：B 以 account 级覆盖运行 wh.1） | ❌ → 部署回退为功能组合 |

### Runtime `0.1.0-rc.5`（RUNTIME_RC5_FINAL_SHA = `57773abe807fa49eb044bbca266c6fb30ac83f36`）
| 层 | 值 | 一致性 |
|---|---|---|
| source commit（R3+R4+CI fix） | `57773abe807fa49eb044bbca266c6fb30ac83f36` | — |
| OCI revision | `57773abe807fa49eb044bbca266c6fb30ac83f36` | ✅（image label 实测） |
| registry tag digest | `sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116` | ✅（workflow 输出 == NAS pull RepoDigest） |
| NAS running Config.Image | `@sha256:3d0bc2cf...` | ✅ |
| platform | linux/amd64（index 唯一运行时 platform；attestation manifest 为 buildx 产物） | ✅ |

- Runtime 发布前补强：publish workflow 的 tag-absence 检查改为 fail-closed（auth/network/未知错误不再被当作 tag absent），commit `78d97f1`。
- R4 CI 兼容修复：aiohttp 缺失环境下的 `TestClient` 导入 NameError，commit `57773ab`（纯测试基建，84 tests 基线不变；模拟无 aiohttp 环境 84 run / 10 skipped / OK）。

## 4. RC.5 Manifest 重组

- Commit `506a9f6`：`release/manifest-0.1.0-rc.5.yaml` + `release/docker-compose.production.yml`。
- 仅使用真实 registry digest（runtime `3d0bc2cf`、agent-wechat `53bff2ad`）；local-only `a5b15ab` 已全部移除。
- canary 段重置为 `PENDING/NOT_STARTED`（此前 draft 中的 wh.1 32.32min PASS 按 operator 裁定只作功能证据）；wh.2 缺陷确认后维持 PENDING。
- P1 validator：**PASS**（`--base-ref 0df8616`）；validator 自身测试 10 passed。
- `docker compose config`（NAS，implementation profile）：PASS；runtime/core digest、pids 200/100、`AGENT_WECHAT_IMAGE`、clipboard locked 全部符合；渲染结果 **0 个 6174 host binding**（仅 core 8080、runtime 3000/3001、gateway 17893、console 18078、core loopback 18082）。

## 5. 部署与 A 隔离

- 部署前源码级证明：`agent_wechat_runtime.py:1092` stopped-drift recreate 仅对非运行容器；running 容器只告警 + `image_update_pending` 标记（L1095-1102、L1414-1427）。
- Runtime service 更新（compose 仅 `up -d runtime`）：manager 重建为 rc.5 digest、healthy；**A 与其 desktop companion 容器 ID 全程逐字节未变**；A 从未被 stop/restart/recreate/login。
- Controlled restart(testB)（17:41）：stop → stopped-drift detect → remove container object → recreate（当时 desired=wh.2 digest）→ start；数据卷保留。

## 6. B Session Recovery / Login Gate

- wh.2 阶段：WeChat 4.1.13.9 QR 区域渲染纯白无法扫码（F1.1）；`view=LoginQr, status=unknown` fresh 语义正确；R1 bounded logging 实测生效（约 60s 一条 WARN，明确 "continuing without kill"）；零破坏不变量全程成立。
- 19:00 testB 经 stopped-drift 重建为 wh.1（account 级 image 覆盖生效，见 F2）；WeChat 4.1.1.4 QR 正常，operator 经 **Console 登录流二维码快照**（`qr_data_url`）完成扫码登录。
- Gate 结果：`wechat_login_status=logged_in`、`logged_in_user=wxid_rpfflqttdz4a22_7fcd`（与 B authoritative wxid 一致）、PidsLimit=512、无 Host 端口、agent server healthy。

## 7. Final-artifact Canary（功能组合：rc.5 runtime + wh.1 child）

- 由于 F1，"rc.5 + wh.2" 精确组合 canary **BLOCKED**；按 operator 指示以功能组合执行。
- 工具：`scripts/canary/wechat_canary_run.sh`（只读采样器，含防破坏守卫）。
- 证据：`/mnt/user/appdata/wechat-hub-f-live/test/r5-canary-20260906/canary-r5-rc5-wh1.jsonl`（66 样本 / 1980s / 0 failed rounds；2026-09-06T03:00:26Z 起）。
- 结果（`summarize_canary.py --minimum-duration 1800 --minimum-samples 60 --expected-pids-limit 512`）：**PASS**
  - `pids.current` 基线 303 / min 302 / peak 308 / end 302（limit 512）
  - `pids.events max` delta **0**；pthread EAGAIN delta **0**；thread ctor failure delta **0**
  - watchdog kill / restart / unresponsive / disappeared delta 全 **0**
  - `events_oom` / `oom_kill` delta **0**；zombies 全程 **0**；task reconciliation delta **0**（end 302 threads）
  - warnings 无；promotion_performed=false
- Canary 后复核：B 容器 ID/登录态/wxid 不变；A 未动。
- 未覆盖项：`--status-url` auth 采样本轮未接线（Q1 轮有）；登录稳定性以状态轮询佐证。

## 8. Desktop UX（重验）

- 服务端 gate 全 PASS：landing 200 HTML、全部静态资源 200、WS upgrade 101、帧级流验证（`MODE websockets`/cursor/settings/stats）、HTML 无 token、companion 按需创建、idle TTL 生命周期按 P0 规则工作。
- **交互使用 FAIL（F5）**：Selkies 客户端 JS 强制 HTTPS，gateway 无 TLS 监听（https → ERR_CONNECTION_RESET）；`http://localhost` 隧道下仍被客户端拒绝。修复方向：gateway TLS 或 noVNC fallback（deferred，R3-scope）。
- 不宣称人工 UX PASS。Desktop 依赖的登录已由 Console 快照路径替代完成。

## 9. H3 Non-Send 重验（Q1 检查单在 R5 栈上的适用项）

| 检查 | 结果 |
|---|---|
| fresh status 语义（PID 存在 + UI 未识别 → unknown、零破坏） | ✅ wh.2 阶段实测（LoginQr→unknown、bounded WARN、无 kill） |
| 双账号隔离 | ✅ 全程 A 容器 ID `caa83b66...` 未变；B 的所有操作（重建×2、canary、desktop）零波及 |
| Core 数据隔离 | ✅ 每账号独立 `agent_wechat/<id>` 目录与密钥路径 |
| 6174 无 Host binding | ✅（两 child 仅 EXPOSE；渲染配置与实际 inspect 双确认） |
| Token 泄漏 | ✅ accounts API 64-hex 命中均为 container_id；runtime/console 访问日志无 `token=` |
| 安全环境变量 | ✅ clipboard `false|locked` 全链路；PidsLimit 全符合（512/200/100） |
| 真实发送 | 未发生（严格 Non-Send） |
| A 登录状态 | ⚠️ A 当前 `logged_out`（容器健康、wh.1、wxid 记忆保留；WeChat 自身回退登录页，非 R5 操作导致）。恢复路径：保持现有容器 + Console 扫码；**不要重建 A**（无 account 覆盖 → 会落到 wh.2 → 白码） |

## 10. 遗留与 intentionally preserved resources

| 资源 | Owner | 保留原因 | 处置 |
|---|---|---|---|
| `test/r5-canary-20260906/`（JSONL+baseline+runner log） | R5 | 发布证据，被本报告引用 | 保留至 wh.3 重做 canary 后归档 |
| `test/r5-deploy-20260906/docker-compose.yml.pre-r5` | R5 | 部署回滚对照 | A 处置决定后删除 |
| `wechat-desktop-testb-a7c4f6c8`（managed companion，无客户端） | testB desktop | — | 收尾清理（managed label 验证后） |
| agent-wechat `main` 上的 workflow 注册 commit `c8d53c7` | R2/R5 | 后续 wh.3 发布必需 | 保留 |
| WSL rustup 工具链 + `~/wh-rc5-preflight-target`（约 2.5G） | 本机 ying | wh.3 重跑 preflight 加速 | 可 `rustup self uninstall` / `rm -rf` 移除 |
| SSH 隧道 17893/18078 | R5 会话 | Console 访问（A 登录仍需要） | operator 确认后关闭 |
| `tests/canary/`、`scripts/canary/` 等先前会话 untracked 产物 | 前序会话 | 非本任务创建 | 未动 |

resource cleanup: **PARTIAL**（上表已列明；companion 与隧道待 operator 确认 A 登录计划后收尾）

## 11. 最终裁定

```
RC.5 R5 INTEGRATION = BLOCKED (final-artifact promotion)
  功能栈（rc.5 runtime + wh.1 child）：CANARY PASS / H3 Non-Send 适用项 PASS
  阻塞项：F1.1 wh.2 WeChat 4.1.13.9 QR 白屏不可登录
          F1.2 wh.2 构建不可复现（unversioned WeChat 下载 URL）
  解除条件：Dockerfile pin WeChat 版本 → 发布 wh.3 → tag-absence →
            manifest 换 wh.3 digest → rc.5+wh.3 final-artifact canary → A 重建登录 →
            Desktop HTTPS（F5）修复或 noVNC fallback 落地
  后续动作归属：Integration agent（wh.3 发布 + 重跑 R5 验收闭环）
```

Production Promotion 保持 BLOCKED；本轮全程未发生真实发送、未做 H2 live profiling、未动 RC.1-RC.4 artifacts、未覆盖任何 immutable tag/digest。
