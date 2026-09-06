# WeChat Hub RC.5 — Sending Gate Preflight（Flash-S）

- 日期：2026-09-06
- 会话角色：Flash-S（第 2 节 Sending Gate Preflight，任务书 `docs/FLASH_RC5_POST_H3_PARALLEL_TASKBOOK.md`）
- 输入：`docs/RC5_POST_H3_DECISION_RUNBOOK.md` D3、`docs/RC5_INTEGRATION_LIVE_RESULT.md`
- 性质：**纯静态/只读**。本会话未调用任何发送接口，未触碰 NAS live stack，未创建任何容器/卷/目录。

```text
SENDING GATE PREFLIGHT = READY_FOR_OPERATOR_AUTHORIZATION
REAL SEND COUNT = 0
Sending Gate 授权状态 = 仍为 SUSPENDED / NOT AUTHORIZED（本报告不授予任何授权）
```

---

## 1. 静态核验结果（当前 Core lineage）

Core 源码 lineage：`work/core` HEAD `13a048881e05a512bf5d1aac83b7a41ed0139a1e`，工作树 clean（仅未跟踪缓存）；发送链路代码定格于 `ed171a8`（post-f-live baseline freeze），其后无任何 send/outbox 改动。行号引用均出自该 HEAD。

### 1.1 Core 发送接口与 outbox schema

| 项 | 结论 | 证据 |
|---|---|---|
| 路由 | `POST /v1/send/{text,image,file}`，返回 `202` + receipt（send_id/status），**202≠sent** | `core/app.py:679-713` |
| 必填字段 | `account_id` + `chat_id`（**不是** `recipient`）+ `text`；`chat_id` 必须已存在于 Core 归一化 chats，否则 `404 chat_not_found` | `core/app.py:458-466,684-686` |
| Idempotency-Key | header `Idempotency-Key`（或 `client_request_id` 回退），≤200 字符；命中已存在 key → 直接回放 receipt（202） | `core/app.py:683-698` |
| outbox schema | 表名 **`outbox`**（D3 runbook 写的 `outbox_messages` 是过时引用）：`send_id PK, idempotency_key UNIQUE, kind, account_id, chat_id, status, client_request_id, request_json, request_digest, details_json, error, attempt_count, accepted_at, updated_at, echo_message_id` | `core/store.py:243-261` |
| NAS 实际 DB 路径 | host：`/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite`；容器内：`/app/runtime/core/wechat_core.sqlite`（D3 的 `core/wechat_hub.db` 是过时引用） | `docs/P0_RC4_FULL_CHAT_PIDS_CANARY_RESULT.md:157`、`stack/docker-compose.yml`（core `--database` 参数） |
| Outbox loop | `--send-interval ${CORE_SEND_INTERVAL:-1}`（1s 轮询）；pending 取 `status IN ('accepted','queued')` | `stack/docker-compose.yml:145`、`core/store.py:1043-1048` |
| 状态机 | `accepted → queued → sending(attempt_count+1) → submitted → sent`；分支 `failed` / `uncertain`。schema 中**不存在** `delivered` 状态（D3 的 "sent 或 delivered" 应只按 `sent` 断言） | `core/sender.py:591-626`、`core/store.py:1189-1218` |

### 1.2 幂等逻辑

- `queue_send`（`core/store.py:938-1000`）：key 已存在且 kind/account/chat/request_digest 匹配 → 返回既有 receipt（不重复入队）；不匹配 → `409 idempotency_conflict`（`_assert_idempotency_match`，`store.py:913-936`）。`INSERT OR IGNORE` + 二次查询兜底并发竞态。
- 每个 send 请求必须携带**独立** Idempotency-Key；重放同一 key 绝不产生第二条消息。
- 确认窗口超时（`expire_submitted_sends`）→ `uncertain` 且 `automatic_retry=False`（`store.py:1133-1187`）；crash 后遗留 `sending` → lease 过期转 `failed`，**绝不自动重发**（`recover_stale_sends`，`store.py:1089-1131`）。

### 1.3 GUI lease 互斥（Desktop vs Sender）

- 两侧使用**同一把 flock 文件**：`$WECHAT_GUI_LEASE_DIR/account-gui-<sha256(account_id)[:32]>.lock`，Core 默认 `/run/wechat-runtime/locks`（`core/sender.py:134-137`）＝Runtime Desktop Gateway（`work/runtime/root/scripts/wechat/desktop_gateway.py:141-144`）。
- 共享挂载：compose 中 Core 挂 `runtime-state:/run/wechat-runtime` 且显式 `WECHAT_GUI_LEASE_DIR=/run/wechat-runtime/locks`（`stack/docker-compose.yml` core service environment/volumes）。浏览器桌面会话建立时 Runtime 持锁（`acquire_manual_gui_lease`，`desktop_gateway.py:151-193`），最后一个连接关闭才释放。
- Sender 行为（`core/sender.py:575-582`）：lease 忙 → **defer**：不改状态、不增 `attempt_count`、不触碰 upstream；下一轮 outbox loop 自动重试。lease 文件打开失败 → fail-closed 同样 defer（`sender.py:166-173`）。
- ⚠️ 语义校正：D3 S1 说任务"置于 `queued`/`waiting_for_gui_release`"——实际实现是 **status 原样保持 `accepted`（不动）**。S1 断言应写：`status ∈ {accepted}`（未被推进）、`attempt_count == 0`。
- 单账号严格串行（`_account_lock`），跨账号并行且互不影响（`sender.py:567-675`）；Runtime lease 测试确认 per-session 可重入、per-account 排他（`work/runtime/tests/test_wechat_runtime.py:806-821`）。

### 1.4 false-success 修复——全部在当前 lineage

| 防线 | 实现 | 证据 |
|---|---|---|
| chat-open/target verification | `_preopen_chat` 先经上游专用 open 端点打开目标会话，校验返回 `username == chat_id`，不匹配即 fail-closed（此时 send 端点尚未调用） | `core/sender.py:288-338` |
| API success ≠ sent | driver 成功仅置 `submitted`，`confirmed: False`，`delivery_certainty: pending_confirmation`；上游成功 = FSM 到 Done | `core/sender.py:383-389,597-604` |
| DB-confirmed outgoing | `_reconcile_text_echo`：仅当存在**唯一**一条近期 submitted 纯文本候选且文本精确匹配（时间窗 -10s..+180s），才置 `status='sent'` + `echo_message_id`；歧义一律不确认 | `core/store.py:640-716` |
| 不确定态永不重试 | 传输无响应 → `DeliveryUncertainError` → `uncertain`；submitted 超时 → `uncertain`；`automatic_retry=False` 贯穿 | `core/sender.py:267-275,605-618`、`store.py:1133-1187` |
| 未验证语义拒发 | native reply / mention 在调用 upstream 前直接拒绝 | `core/sender.py:340-346,494-501` |

上游侧对照（`.worktrees/agent-wechat-wh3`，HEAD 精确等于 wh.3 source SHA `b8193f9443d58cfd85d7b912c3db650358976a8e`）：`packages/agent-server-rust/src/plans/send_message.rs:265-301` 的 Confirming 阶段仍以 **Send 按钮 DISABLED = 成功（Done）**，`src/router/messages.rs:292-296` 直接把它作为 `success` 返回。即上游成功信号依旧偏弱（这正是历史 false-success 根因），Core 侧上述防线是必要补偿——已确认全部在场。发送前置健康门：`agent_server_healthy is False → 拒发`（`sender.py:350-353`）。

### 1.5 测试证据（本会话于本地 Windows 执行，不触 NAS）

```
work/core:  python -m pytest core/tests -q            → 55 passed, 3 subtests passed (146.9s)
work/core:  python -m pytest core/tests -k "send or outbox or idempot or lease"
            → 15 passed (53.9s)，关键用例：
            - test_manual_desktop_defers_only_that_account_without_attempting_upstream
            - test_agent_false_success_expires_from_submitted_to_uncertain_without_retry
            - test_agent_chat_preopen_target_mismatch_fails_before_send_endpoint
            - test_agent_timeout_becomes_uncertain_and_is_never_auto_retried
            - test_idempotency_key_reuse_with_different_account_or_request_conflicts
            - test_send_idempotency_and_inline_media
            - test_distinct_accounts_use_distinct_agent_hosts_tokens_and_chat_ids
work/runtime: python -m pytest tests/test_wechat_runtime.py -k "lease" → 3 passed (1.5s)
```

### 1.6 Recipient 白名单与隔离

- 结构性防线：未知/不存在 recipient 在 Core API 层即 `404 chat_not_found`（`app.py:458-460`）；driver 层二次校验 `store.chat(account_id, chat_id)` 否则拒发（`sender.py:354-356`）。不存在"任意字符串都能发"的路径。
- 测试会话必须由 operator 在授权记录中显式指定（见 §3 模板），且 Live agent 发送前必须回显该 chat 的 `display_name` + 成员数供二次确认（§3 S0 步骤）。禁止使用普通联系人、非测试群、未知 recipient。
- 消息类别：仅纯文本（image/file 虽有路由但本次 Gate 不授权）；内容携带唯一 UUID 便于四层比对。
- 跨账号隔离：A/B 各自独立 GUI lease/token/agent host；已由 H3 Non-Send 全套隔离验证（`docs/RC5_INTEGRATION_LIVE_RESULT.md` §9），发送阶段复用同一隔离事实。

---

## 2. D3 runbook 勘误（Live agent 执行时必须按本表校正）

| # | D3 原文 | 实际（以当前代码为准） |
|---|---|---|
| E1 | payload 字段 `"recipient"` | **`"chat_id"`**（`app.py:459`），值取 Core chats 列表里的 `chat_id` |
| E2 | `sqlite3 .../core/wechat_hub.db`；表 `outbox_messages` | `/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite`；表 **`outbox`** |
| E3 | "置于 queued / waiting_for_gui_release" | lease 忙时 status **保持 `accepted` 不变**，`attempt_count == 0` |
| E4 | "跃迁至 `sent` 或 `delivered`" | 只有 **`sent`**（schema 无 delivered） |
| E5 | Agent DB 直接 sqlite 查询 | `/data/agent.db` 为 SQLCipher 加密（key=agent token，`agent-server-rust/src/db/mod.rs:81`）。Agent 层证据改用 agent-server 只读 API：`GET /api/chats/{chat_id}/messages`（WeChat 客户端 DB 行：`is_self`、`server_id≠0`、content 匹配），从 docker 网络内侧调用（agent 容器无 host 端口，PortBindings=null 为 H3 已验证事实） |

---

## 3. Stage S Execution Worksheet（供 operator 授权后由唯一 Live agent 执行）

### 3.0 权威身份（来自任务书，执行时用 S0 复验）

| 账号 | account_id | 权威 wxid |
|---|---|---|
| A | `f-live-a` | `wxid_7ugft7xlkf5a22_4117` |
| B | `testB` | `wxid_rpfflqttdz4a22_7fcd` |

最终制品：Runtime rc.6 `sha256:b5a0b008…`，AgentWechat wh.3 `sha256:2e6eff3f…`。

### 3.1 Operator 授权记录（发送前必须完整落盘）

按 D3 §1.2 模板填写并归档至 `.tmp/sending_gate_authorization.txt`，其中必须明确：

- `Authorized Test Chat / Recipient`：A、B 各一个**已存在于 Core chats 的** `chat_id`（operator 从自己的手机端确认该会话是测试用；Live agent 在 S0 用只读 API 回显 `display_name` 供 operator 书面确认）。
- 数量与顺序：**Phase 1 = A/B 各 1 条 smoke；双 smoke 三重确认全部 PASS 后才允许 Phase 2 = A 5 + B 5**。任何单 smoke FAIL → 立即停止，不进 5+5、不启动 H2、Production 保持 BLOCKED。
- 时间窗 ≤2h；消息类别 = 纯文本；每条独立幂等键强制。

### 3.2 执行序列与断言

**S0 只读基线（无发送）**

```bash
CORE=http://127.0.0.1:18082   # NAS core loopback
# 双账号 status/view/wxid 复验（期望 logged_in + view=Chat + 权威 wxid）
curl -fsS "$CORE/v1/runtime/accounts/f-live-a" | python3 -m json.tool
curl -fsS "$CORE/v1/runtime/accounts/testB"    | python3 -m json.tool
# 回显 operator 指定测试会话（display_name 供二次确认；确认其非普通联系人/非正式群）
curl -fsS "$CORE/v1/accounts/testB/chats?query=<operator关键词>&limit=20" | python3 -m json.tool
# 发送前资源快照（见 §4 命令），留存到 evidence 目录
```

**S1 桌面租约互斥（用 A 演练，1 条受权 smoke 承载）**

1. 为 A 建立桌面会话（control socket 正式通道 `{"action":"desktop",...}`，同 Integration-Live L4）。
2. 持租约期间提交 A 的 smoke 请求（§3.3 curl）。
3. 在桌面开启全程（每 2-3s）轮询 outbox，断言：`status` 保持 `accepted`（未被推进）、`attempt_count == 0`、B 的 outbox 无任何新行。
4. 关闭 A 桌面会话释放租约，断言：任务恰好被调度**一次**（`attempt_count == 1`，最终 `sent`，无重复行）。
5. A 持租约期间 B 独立可用（B 的 outbox 状态不受影响）。

**S2 单条 smoke（B 先，后 A；独立幂等键）**

```bash
KEY_B="smoke-b-$(uuidgen)"
curl -s -X POST "$CORE/v1/send/text" -H "Content-Type: application/json" -H "Idempotency-Key: $KEY_B" \
  -d '{"account_id":"testB","chat_id":"'"$AUTHORIZED_CHAT_ID_B"'","text":"WeChat Hub RC.5 Smoke Test B '"$KEY_B"'"}'
# 期望 202 + receipt(send_id, status=accepted/queued)。202 绝不单独作为成功凭据。
KEY_A="smoke-a-$(uuidgen)"   # A 同型，account_id=f-live-a
```

三重交付判定（每条消息逐层取证）：

| 层 | 证据 | 判定 |
|---|---|---|
| ① API | curl receipt | 202 + send_id（仅是受理） |
| ② Core DB | §3.4 查询 outbox + messages | `status='sent'`、`attempt_count==1`、`echo_message_id≠''`；messages 表出现 `direction='outgoing'` 且 text 含同一 UUID 的行 |
| ③ Agent DB | `GET /api/chats/{chat_id}/messages?limit=10`（docker 网络内侧，Bearer=账号 token 文件值，禁止回显 token） | 出现 `is_self=true`、`server_id≠0`、content 含同一 UUID 的行 |
| ④ 手机端 | operator 在测试会话肉眼确认 | 收到 1 条，内容 UUID 一致 |

**S3 5+5 批量（仅双 smoke PASS 后）**

- A 5 条、B 5 条，间隔 3-5s，每条独立幂等键（建议 `rc5s-{a|b}-{1..5}-$(uuidgen)`），每条重复 §S2 四层判定。
- 断言：10 条全 `sent`；接收端收到 10 条、无缺失/乱序/重复；**零跨账号投递污染**（逐条核对 sender 侧 wxid 与内容 UUID 归属）；watchdog/EAGAIN/PidsLimit/restart 计数零增量（§4）。

**S4 发送后终检**：§4 全套 + 日志无敏感凭据 + `resource cleanup` 检查。

### 3.3 幂等键与 outbox 查询（含勘误后的正确命令）

```bash
# Core DB 只读查询（NAS host 无 sqlite3/python，走 core 容器内 python3——沿 pywrap 惯例）
docker exec wechat-hub-f-live-core python3 - <<'PY'
import sqlite3
key = "__IDEMPOTENCY_KEY__"
db = sqlite3.connect("file:/app/runtime/core/wechat_core.sqlite?mode=ro", uri=True)
db.row_factory = sqlite3.Row
row = db.execute("SELECT send_id,status,attempt_count,echo_message_id,error,updated_at FROM outbox WHERE idempotency_key=?", (key,)).fetchone()
print(dict(row) if row else "NOT FOUND")
PY
```

- 幂等重放验证（可选、无副作用）：同 key 重发同请求 → 202 回放同 `send_id`；同 key 换内容 → `409 idempotency_conflict`。

### 3.4 中止判据（任一命中即 STOP）

- S2 任一 smoke：outbox 落入 `uncertain`/`failed`，或 10 分钟内四层证据不齐。
- 任何 `attempt_count ≥ 2` 的行（重试迹象）或重复消息。
- watchdog kill/restart、EAGAIN、OOM、`pids.events max` 增量、进程数单调增长、`RestartCount` 增量任一非零。
- 日志出现真实 token/凭据（→ 按 H3 runbook 泄漏处置流程，作废本次运行）。
- 收到消息的会话与授权 chat_id 不一致（target verification 失效迹象）。

---

## 4. 发送前/后资源与安全检查命令（pre/post 各跑一遍，比对增量）

```bash
AGENT_A=wechat-agent-f-live-a-…   # 以 S0 时 docker ps 实际名为准
AGENT_B=wechat-agent-testb-…      # H3/L5 已知 wechat-agent-testb-a7c4f6c8
RUNTIME=wechat-hub-f-live-runtime
CG=/sys/fs/cgroup                 # cgroup v2

# 1) cgroup pids（A/B 各自 cgroup；经 runtime 容器读，host 侧亦可）
docker exec $RUNTIME sh -c "cat $CG/pids.current; grep -H . $CG/pids.events"
#    断言：post 与 pre 相比 current 稳定震荡、pids.events max 计数零增量
# 2) OOM
docker exec $RUNTIME sh -c "grep -H . $CG/memory.events"     # oom/oom_kill 零增量
# 3) watchdog / 重启计数
docker logs --since <pre_ts> $AGENT_B 2>&1 | grep -ciE "watchdog|kill|restart"   # 期望 0 增量
docker inspect -f '{{.RestartCount}}' $AGENT_A $AGENT_B                          # 零增量
# 4) zombie / 进程数（复用既定采样器，或单点快照）
scripts/canary/wechat_cgroup_sample.sh --help   # 既定只读采样口径（/proc 遍历 + cgroup v2）
# 5) token 泄漏（真实值比对、只输出计数，绝不打印 token）
A_TOKEN=$(cat <A 账号 token 文件>); B_TOKEN=$(cat <B 账号 token 文件>)
for c in wechat-hub-f-live-core $RUNTIME $AGENT_A $AGENT_B; do
  docker logs --since <pre_ts> "$c" 2>&1 | grep -cF "$A_TOKEN"; 
  docker logs --since <pre_ts> "$c" 2>&1 | grep -cF "$B_TOKEN";
done   # 全部期望 0
# 6) zero-send 对照锚点：发送窗口前 MAX(outbox.updated_at) 记录为基线
```

推荐：smoke 前后各跑一次 120s `wechat_canary_run.sh` 短采样（profile=canary），与 §4 单点命令互补。

---

## 5. 结论与移交

- 发送链路四要素（接口/outbox/幂等/GUI lease）与三道 false-success 防线均已在当前 Core lineage 静态核验 + 本地测试实证。
- D3 runbook 存在 5 处过时引用（§2 勘误表），Live agent 必须按勘误执行；建议后续会话把勘误回写进 `RC5_POST_H3_DECISION_RUNBOOK.md`（本会话不改动既有 runbook 文档）。
- 裁定：**READY_FOR_OPERATOR_AUTHORIZATION** —— Stage S 执行包已就绪，等待 operator 按 §3.1 落盘书面授权；在此之前任何人调用 `/v1/send/*` 或 AgentWechat send API 均属违规。
- 本会话 garbage check：未创建任何容器/卷/NAS 目录/临时文件（仅本地 pytest 运行，`.pytest_cache` 为既有缓存）；`resource cleanup: PASS`（无 intentionally preserved 新资源）。

```text
REAL SEND COUNT = 0
SENDING GATE = SUSPENDED（未变）
```
