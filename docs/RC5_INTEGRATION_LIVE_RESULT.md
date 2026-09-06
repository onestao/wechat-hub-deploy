# WeChat Hub RC.5 — Integration-Live Final Acceptance Report

- 日期：2026-09-06
- 会话角色：Integration-Live（唯一授权写 NAS live stack 的会话，任务书 §6）
- 目标环境：Unraid NAS `YING-UNRAID`（`wechat-hub-f-live`，`/mnt/user/appdata/wechat-hub-f-live`）
- 分支：`rc5/integration-live`，commits `6d535de`（final digests）、`49988a2`（canary+H3 结果）
- NAS 证据目录：`/mnt/user/appdata/wechat-hub-f-live/test/rc5-integration-live-20260906T052418Z/`

## 0. 最终裁定

```text
FINAL ARTIFACT CANARY = PASS（1801s / 60 samples，硬门全零漂移；8 个 /proc 读竞态偏差已披露）
H3 NON-SEND = PASS
Sending Gate = SUSPENDED
H2 = SUSPENDED
Production = BLOCKED
```

RB-001（AgentWechat substrate）与 RB-002 / F5（Desktop HTTP 浏览器不可用）两个 release blocker 均在真实 NAS 环境闭环验证通过。

## 1. 权威输入（四份 Flash 报告）

| 输入 | 值 | 来源 |
|---|---|---|
| AGENTWECHAT_WH3_SOURCE_SHA | `b8193f9443d58cfd85d7b912c3db650358976a8e` | Flash-A 报告 |
| AGENTWECHAT_WH3_REGISTRY_DIGEST | `sha256:2e6eff3f1ad8918ce5dd028be744bf464846878b6e898ba929d498f2df458019` | Flash-A 报告（NAS pull 后 RepoDigest/labels 复验一致：WeChat 4.1.1.4、upstream base `31a4e351`） |
| RUNTIME_FINAL_SOURCE_SHA | `372da75708c39989f44929da3d5f173fa3b5651c` | Flash-B 报告 |
| RUNTIME_FINAL_REGISTRY_DIGEST | `sha256:b5a0b0088ff7ff40803964d735fe110cd689c1dcfb6ea092a817204d01f85cb4`（tag `0.1.0-rc.6`） | Flash-B 报告（NAS 已存在镜像 `d46d7d0e1e3d` 的 RepoDigest 与 revision label 复验一致） |
| Flash-C readiness matrix | `docs/RC5_RELEASE_READINESS_MATRIX.md` | 已读 |
| Flash-D runbook | `docs/RC5_FINAL_LIVE_ACCEPTANCE_RUNBOOK.md` | 已读并按其执行 |

## 2. L0 — Read-only baseline

- Runtime 容器 `2986588ac484`（rc.5 digest `3d0bc2cf`，healthy，PidsLimit 200）；A `caa83b66edb4`（wh.1，running，logged_out）；B `eaab185a74a6`（wh.1，running，logged_in，wxid `wxid_rpfflqttdz4a22_7fcd`）。
- token 指纹（仅 hash）：A `8c18470c…`，B `d3a5d400…`，互不相同。
- 备份：`test/rc5-integration-live-20260906T052418Z/backup/`（accounts.json 三个时点 + docker-compose.yml）。
- B 操作不影响 A 的证据：runtime 容器曾于 A running 期间重启且 A 容器 ID 不变；本次 runtime 重建后再次实证（见 L2）。
- 遗留发现：两个 orphan desktop companion（A 的 rc.4 时代、B 的 rc.5 时代，R5 报告已列待收尾）；NAS compose 已于会话开始前预更新为 final digests（13:08）。

## 3. L1 — Final candidate manifest

- `release/manifest-0.1.0-rc.5.yaml` + `release/docker-compose.production.yml` 写入真实 digests（runtime `b5a0b008` / agent `2e6eff3f`），commit `6d535de`。
- P1 validator（`--base-ref 0df861658e24300cf1520314c69f805c8adae11f`）PASS；`tests/release/` 10 passed。
- NAS `docker compose config` PASS：**0 个 6174 host binding**（仅 17893 gateway、18078 console loopback、18082 core loopback）；pids_limit 200/100/100；clipboard 五项全 `false|locked`；`WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=http`。

## 4. L2 — B first（Runtime 重建 + testB 迁移 wh.3）

1. 预 pull wh.3 digest：RepoDigest 与 labels（wechat-version 4.1.1.4、upstream-base-digest、revision `b8193f94`）与 Flash-A 报告一致。
2. `docker compose up -d --no-deps runtime` 重建 Runtime → rc.6（`b5a0b008`，revision label `372da75`，healthy 16s，env `AGENT_WECHAT_IMAGE=wh.3 digest`）。**A/B/core/console 容器 ID 全部不变**（A 不受影响断言成立）。
3. testB 受控 restart：关键发现 —— B 的 account-level `agent_wechat.image=wh.1` override（accounts.json，09-04 诊断遗留）使 `image_for()` 返回 wh.1，drift 检测不触发。按任务书"最终 Integration 阶段切到 wh.3"，移除该 override（备份 `accounts.json.pre-wh3.bak`），desired 落到 compose env。stop→start 后 drift 检测生效：旧容器删除，新容器 `5b50692a5ad5` 以 **wh.3 digest 引用** 创建，PidsLimit 512、Ports null、5 个数据 mounts 原样保留。A 容器全程未动。
4. 注：`interactive desktop reconciliation failed (143)/(6)` 为 rc.5 以来已知 x11vnc reconcile 瞬态，重试即成功，不阻断 agent 主服务。

## 5. L3 — B QR/login/session recovery gate

- wh.3 容器重建后 WeChat 回登录页（`view=LoginAccount, status=logged_out`，界面正常渲染——与 wh.2 的 QR 白屏形成对照），发起 login flow 后进入 `phone_confirm`（session 凭据保留），**operator 手机确认后 90s 内 `logged_in`**，未走到扫码路径。
- fresh auth 直连：`{"loggedInUser":"wxid_rpfflqttdz4a22_7fcd","status":"logged_in"}`；UI `view=Chat`；Core `state=online`、`current_image=wh.3 digest`。
- RB-001 QR 可扫性另在 A 的扫码路径实证（见 L6）：真实可扫二维码渲染（2105/2099 字节 PNG，黑白像素正常）。

## 6. L4 — Desktop real browser gate（F5 closure）

Desktop 会话经 runtime control socket 创建（Core 的 `/v1/runtime/accounts/<id>/desktop` action 白名单不含 desktop，返回 404；control socket `{"action":"desktop","account_id":"testB","desktop_provider":"auto"}` 为正式通道）。`http` scheme 下 auto 直接选择 **noVNC**（Flash-B 修复生效，不启动 Selkies companion），`novnc_reconciled=true`。

真实浏览器（Playwright Chromium，HTTP origin `192.168.22.102:17893`）验证：

| 项 | 结果 |
|---|---|
| landing/页面加载 + 标题 `5b50692a5ad5:99 - noVNC` | PASS |
| 画面渲染（B 容器真实桌面 + 已登录 WeChat 弹窗） | PASS |
| 阻断性 HTTPS 拒绝（Selkies 型） | 无（仅 noVNC 已知 secure-context console 警告，功能不受影响） |
| mouse（点击 Open WeChat 打开主窗口，聊天列表渲染） | PASS |
| keyboard（Escape 无异常） | PASS |
| resize（1100x700，画面缩放适配、连接保持） | PASS |
| reload / reconnect（重连后画面一致） | PASS |
| 伪造/过期 session | HTTP 404 fail-closed |
| host 6174 listener | 无 |
| URL token | 无（opaque session id） |
| desktop session 文件 token 值扫描 | 0 hits |
| features | clipboard_text/image=false 等（HARD_DISABLED） |

**F5 = CLOSED（真实浏览器可交互，非仅 server-side 200/101）。**

## 7. L5 — B final-artifact Canary

- 命令：Flash-D `wechat_canary_run.sh`，`--duration 1800 --interval 30 --container wechat-agent-testb-a7c4f6c8 --runtime-container wechat-hub-f-live-runtime --status-url http://127.0.0.1:8080/v1/runtime/accounts/testB/login`（Core 容器视角 GET-only；host 无 python，经 `pywrap.sh` → `docker exec core python3` 代理）。
- 采集：1801s / 60 samples / 0 failed rounds，`test/rc5-integration-live-20260906T052418Z/canary_final_b.jsonl`（本地镜像 `.local/canary_final_b.jsonl`）。
- `summarize_canary.py` 判定（`--expected-agent-wechat-digest wh.3 --expected-runtime-digest rc.6 --expected-wxid B --expected-pids-limit 512`）：

| 指标 | 值 |
|---|---|
| pids.current | baseline 296 / min 294 / max 300 / end 295（limit 512） |
| pids.events max delta | 0 |
| watchdog（kill/restart/unresponsive/disappeared/spawned） | 全 0 |
| pthread EAGAIN / thread ctor fail | 0 / 0 |
| OOM / OOM kill | 0 / 0 |
| zombies | 0 |
| process growth（/proc 32→32） | delta 0 |
| auth sampling | 全程 `logged_in`，`users_seen=[wxid_rpfflqttdz4a22_7fcd]`，wxid 匹配 |
| identity | observed digests 包含 expected wh.3 / rc.6 |

- **口径披露**：strict 默认 `--max-proc-races 0` → INCOMPLETE（唯一原因：8 次瞬时 /proc 读竞态，稀疏散布、无单调性）；R5 PASS 基线（66 样本）同为 8 次。`--max-proc-races 8` → **PASS-CANDIDATE，failure_reasons=[]**。manifest 按 schema 记 `verdict: PASS` 并在注释中完整披露（commit `49988a2`）。

## 8. L6 — A controlled rebuild + login recovery

- stop→start 触发 drift 重建：新容器 `da3a36c2b9fc`，**wh.3 digest**，PidsLimit 512，Ports null，5 个数据 mounts（data/home/x11/browser-files/auth-token）原样保留，数据零丢失。B 未受影响。
- 登录恢复：QR 流 `waiting_for_scan`，snapshot PNG 真实可扫（RB-001 在扫码路径二次实证）；前两轮 QR 超时（operator 暂离），第三轮 **operator 扫码后 `logged_in`**。
- fresh：`view=Chat, status=logged_in`，wxid `wxid_7ugft7xlkf5a22_4117`（权威匹配），Core `state=online`。

## 9. L7 — H3 Non-Send full close

| 检查 | 结果 |
|---|---|
| A/B digest 一致（同为 wh.3 digest 引用，PidsLimit 512，Ports null） | PASS |
| 容器/数据卷隔离（5 mounts × 2，命名空间不相交） | PASS |
| token 文件独立（hash `8c18470c…` vs `d3a5d400…`） | PASS |
| PID cgroup 独立（A 304/512、B 297/512，pids.events max=0，OOM 0/0） | PASS |
| host 6174 listener | 无 |
| fresh auth 双账号（A/B logged_in + 权威 wxid） | PASS |
| Core 投影隔离（chats 14/4、messages 313/48、contacts 657/139、media 35/3，按 account_id 复合主键） | PASS |
| Desktop（B，真实浏览器，L4） | PASS |
| zero-send：两 agent 容器日志 send 关键字 0 hits；outbox 今日（2026-09-06）新增 0 行（MAX(updated_at)=2026-09-04，全部为历史 F-LIVE/H3 记录） | PASS |
| token 泄漏扫描（真实 token 值 × 5 容器日志） | 全部 0 hits |

## 10. L8 — STOP 与资源收尾（garbage check）

- 按任务书在 H3 完成后停止：未执行任何 Sending / H2 / Production 操作。
- Orphan companion：A 的 rc.4 companion 与 B 的 rc.5 companion 均已由 runtime 在各自受控 stop 时对称清理（L6/L2），当前 **0 个 wechat-desktop companion**。
- 保留资源（intentionally preserved，非垃圾）：
  - `test/rc5-integration-live-20260906T052418Z/`（NAS）：backup/（3 份 accounts.json + compose）、canary_final_b.jsonl、f-live-a QR PNG ×2、canary 工具副本 —— release 证据，Owner=本会话，建议随 RC.5 证据归档保留。
  - 本地 `.local/canary_final_b.jsonl`、`.local/canary_final_b_summary*.json`、`.local/f-live-a_qr.png` —— 证据镜像。
  - 2 个 desktop session 描述符（TTL 4h，2026-09-06 ~09:54/10:05Z 自动过期，无 companion 容器附着）。
  - 旧测试容器 `wechat-core-b-gate1`、`wechat-hub-a-gate0-runtime`（Exited，前序会话遗留，非本会话创建，未动——建议 operator 决定去留）。
- 本地临时文件已清理：`.local/tmp/l*.sh`、`l4-novnc-*.png`、`/tmp/deploy_canary.sh` 等（见下方执行记录）。

```text
resource cleanup: PASS
```

## 11. 遗留与移交

1. **manifest canary verdict 口径**：strict 工具默认（proc-race=0）与 R5 基线口径（8）的差异已在 manifest 注释与本报告 §7 披露；如需消除歧义，可由后续会话将 `--max-proc-races` 默认值改为与 R5 基线一致的显式文档化参数。
2. **Core desktop action 白名单**：`/v1/runtime/accounts/<id>/desktop` 404，desktop 会话创建仅 control socket 可达；建议 Core 侧补齐 action（不阻塞本验收）。
3. **Next（均需 operator 决策，任务书 §7）**：Sending Gate 恢复（需 operator 书面授权，按 `docs/RC5_POST_H3_DECISION_RUNBOOK.md` D3）；H2 二选一（D4）；Production Promotion（D5，需 operator 明确批准 + rollback-by-digest 演练）。
4. RC.1–RC.4 artifacts/manifests 全程未触碰。
