# WeChat Hub 会话 F Completion Report

日期：2026-09-01  
范围：Runtime / Sender Driver 审阅补修  
状态：代码与自动化回归完成；真实 NAS acceptance 仍由原 B 会话执行

## 1. 结论

会话 F 主体架构未重构。本轮只针对审阅提出的 P0/P1/P2 项做增量补修，保留现有：

- Runtime Provider：`legacy` / `agent_wechat`
- Core / Outbox / Sender Driver
- Console
- EFB
- Agent
- Mock Core
- Legacy X11 Sender
- Native Driver skeleton

本轮没有执行真实微信发送，没有在 NAS 上替换/重启现有微信实例，没有自动 commit。

AgentWechat 在 Console 中继续标记为 **增强模式（Beta）**；在原 B 会话完成真实 NAS acceptance 前，不视为生产验证完成。

## 2. P0 — AgentWechat Web Desktop 安全边界

最终路径：

```text
Browser
  ↓ opaque Desktop Gateway session
WeChat Hub Runtime / Desktop Gateway :17892
  ↓ server-side auth injection, Docker internal network only
agent-wechat account container :6174
```

完成项：

- child container `6174` 不再创建 Docker `PortBindings`，不发布到 Host。
- child 只连接 WeChat Hub Docker internal network。
- 删除 `AGENT_WECHAT_DESKTOP_BIND`。
- Runtime 新增轻量 `aiohttp` Desktop Gateway。
- Browser/Core/Console 只看到随机、短期、账号绑定的 gateway session URL。
- upstream token 不出现在 Browser URL、Core JSON、Console JSON、gateway session descriptor。
- Gateway 丢弃浏览器提供的 `token` / `Authorization`，服务端读取对应账号 token 后只在 internal hop 注入。
- Gateway 代理 HTTP streaming。
- Gateway 代理 WebSocket Upgrade、TEXT、BINARY、PING、PONG 和无总超时长连接，可承载 noVNC/websockify。
- Gateway `access_log=None`，避免标准 access log 记录 gateway capability path；upstream token 从不进入该 path。
- Gateway HTTP 响应增加 `Cache-Control: no-store`、`Pragma: no-cache`、`Referrer-Policy: no-referrer`。
- 停止/删除账号会撤销对应 Desktop Gateway sessions。
- 双账号 session 分别解析到自己的 Registry account。

P0 专项静态扫描：

```text
AGENT_WECHAT_DESKTOP_BIND    absent from production path
desktop_port                 absent from production path
/vnc/?token=                 absent from production path
PortBindings                 absent from AgentWechat child payload
RESULT                       PASS
```

## 3. P1 — AgentWechat 两层 health + 登录状态

AgentWechat Runtime 不再用 Docker `State.Running` 代表完整健康：

```text
container_running
agent_server_healthy    ← internal GET /health
wechat_login_status     ← authenticated GET /api/status/auth
```

行为：

- stopped container → `runtime_health=stopped`
- container running + `/health` fail → `agent_server_healthy=false`, `runtime_health=degraded`
- agent healthy → 再读取 WeChat login/auth 状态
- Agent unhealthy 时 Runtime API、扫码和 Desktop 不把实例当作正常 agent-server
- Core account state 映射为 `degraded`
- Account Worker 即使 DB sync 成功也不会覆盖该 degraded 状态
- Console 账号卡显示 `Agent 服务异常` / degraded

## 4. P1 — Send uncertainty

AgentWechat 发送结果现在区分：

```text
明确 upstream HTTP/业务拒绝 -> failed
请求已发起、响应阶段 timeout/连接中断 -> uncertain
```

`uncertain`：

- 是终态，不进入 `pending_sends()`。
- 不自动 retry。
- `send.updated.error.code = agent_wechat_delivery_unknown`
- `send.updated.details.delivery_certainty = unknown`
- `send.updated.details.automatic_retry = false`
- EFB 对该状态记录明确 warning，不解释为“确定没发送”。

单元测试验证 timeout 后：

- `failed=0`
- `uncertain=1`
- receipt status=`uncertain`
- pending queue 为空
- error code/details 正确

## 5. P1 — Per-account sender capabilities

Core 顶层 `/health.sender_capabilities` 保持 Legacy-safe 的保守值，不全局开启 file。

每个账号通过：

```text
account.runtime.sender_capabilities
```

暴露实际 Driver 能力：

```text
AgentWechat account -> file=true
Legacy account      -> file=false
```

EFB 发送前按目标 `account_id` 读取该账号 capability；只有旧 Core 没有账号 capability 时才回退到旧的顶层 capability。

混合 Provider 回归验证：同一 EFB 实例中 AgentWechat 文件发送进入 Core，Legacy 文件发送在入 Core queue 前 fail-closed。

## 6. P2 — Fake Docker Engine 双账号生命周期

Runtime 自动测试加入 Fake Docker Engine，使用两个 AgentWechat account 覆盖：

- create
- start
- inspect
- stop
- restart
- remove preserve
- remove purge
- image recreate
- labels
- volumes
- cryptographically random per-account token
- token isolation
- child 无 Host `PortBindings`

并验证：

- stop A 不停止 B
- recreate A image 不删除/替换 B
- preserve-remove A 不删除 A/B volume
- purge-remove A 只删除 A volumes
- B container/volumes 全程保留
- A/B token 均为独立 64 hex characters，且不相等

## 7. Web Console

AgentWechat UI 标签：

```text
AgentWechat 增强模式（Beta）
```

“打开微信”返回的是 WeChat Hub Desktop Gateway URL，不是 child `6174` URL。Console 回归明确检查：

- provider=`agent_wechat`
- gateway port=`17892`
- path 包含 `/desktop/`
- path 不包含 `token=`

Legacy 的 Selkies Desktop 行为保持原样。

## 8. OpenAPI / Stack contract

OpenAPI 已补：

- Runtime `container_running`
- `agent_server_healthy`
- `runtime_health`
- `health_error`
- `wechat_login_status`
- Runtime Login health fields
- account-scoped sender capability 说明
- Desktop Gateway opaque path / expiry
- SendReceipt status `uncertain`

Stack 已补：

- child `6174` 不做 Host publish
- Runtime 发布 Desktop Gateway `17892`
- Gateway 配置项
- Runtime Docker image 安装固定 `aiohttp==3.12.15`
- Stack 自动测试检查 Gateway service、aiohttp、无 child `6174` Host port、无 `PortBindings`
- Docker Socket 仍只有 Runtime Manager 挂载

## 9. 最终自动化验收

```text
Runtime        22 / 22 PASS
Core           34 / 34 PASS
EFB            19 / 19 PASS
Console         8 /  8 PASS
Agent           9 /  9 PASS
Mock Core       6 /  6 PASS
Stack           8 /  8 PASS
```

Core 34 项由于单组 HTTP 测试耗时较长，按分组执行；各 class/test method 合计 34，全部 PASS。

附加门禁：

```text
Console JS syntax                  PASS
Affected Python py_compile         PASS
YAML / OpenAPI parse               PASS (6 files)
git diff --check                   PASS (5 work repositories)
P0 token/host-port static scan     PASS
Docker socket exclusivity          PASS
```

`git diff --check` 仅出现现有 Windows checkout 的 LF/CRLF conversion warning，没有 whitespace error。

## 10. 最终状态矩阵

| 项目 | 状态 | 说明 |
|---|---|---|
| AgentWechat Runtime | PARTIAL | 代码、Fake Docker、API/登录/DB credential/health 回归通过；真实 NAS acceptance 尚未执行 |
| Multi-account isolation | PASS | 一账号一 child container/volume/token；Fake Docker A/B 生命周期无交叉操作 |
| Concurrent sending | PASS | 同账号 account lock 串行，不同账号线程池并行；AgentWechat 实例之间无共享 upstream GUI plan lock |
| Web direct operation | PARTIAL | Desktop Gateway HTTP/WS/binary/long-connection 实现与自动测试通过；尚未在真实 NAS 浏览器/noVNC 上 acceptance |
| Token isolation | PASS | 每账号 cryptographic token；Browser/Core/Console/Gateway descriptor 不泄漏 upstream token |
| Agent health | PASS | container running、agent-server `/health`、WeChat login 三层状态已接入 Runtime/Core/Console |
| Send uncertainty | PASS | 网络响应未知进入 terminal `uncertain`，明确 no-auto-retry + error code/details |
| EFB per-account capabilities | PASS | AgentWechat `file=true` / Legacy `file=false` 混合 Provider 回归通过 |
| Legacy compatibility | PASS | Legacy Provider/Sender/X11/Selkies 保留，旧 Registry 默认仍解释为 `legacy` |
| Native skeleton | PASS | 仅 capability/Unix-socket detection skeleton，默认 fail-closed；未实现或猜测内部 send offset |

## 11. 真实 NAS acceptance 边界

本轮**没有真实微信发送**，也没有在 NAS 启动/迁移真实 AgentWechat 账号。

真实 acceptance 继续交给原 B 会话，至少验证：

1. child `6174` 在 Host 上不可访问、只有 Docker internal network 可达。
2. Desktop Gateway 从真实浏览器可加载 noVNC HTTP assets。
3. websockify WebSocket Upgrade 与 binary frame 可持续工作。
4. 两个真实测试账号的 Desktop 不串号。
5. 浏览器 URL/开发者工具可见请求中没有 upstream auth token。
6. `/health` 故障能在 Console 显示 degraded。
7. 登录 QR → full FSM → DB credential → 现有 Sync/Core。
8. 在明确授权的测试账号上再做真实文本/图片/文件发送 acceptance。
9. child container recreate 后 `/data` 与 `/home/wechat` 登录状态持久。

在上述真实 acceptance 完成前，AgentWechat 保持 **增强模式（Beta）**。

---

## 12. F-Live-A follow-up acceptance — 2026-09-02

本节只追加 2026-09-02 的 F-Live-A 真实验证结果，不改写前述历史 Gate 证据。本轮没有创建或扫码账号 B，也没有进入第十三至十五节。

### 12.1 Core media 修复保持有效

保留并已同步进入正式工作树/构建上下文的两项修复：

- `core/key_extract.py`：保留 `_image_aes/_image_xor`，写入账号级 `wechat-decrypt/config.json`，权限 `0600`，不进入普通 DB keys 文件。
- `memory/media_sync.py`：保留 `derive_xor_byte()`；仅在配置 XOR 失败后按已知 JPEG/PNG/GIF 语义推导，不做 `0..255` 盲扫。

此前真实 Gate 证据保持不变：`media ready 0 -> 13`、`decode_failed 13 -> 0`，且 `/v1/media/...` 返回真实 JPEG。本轮结束时随着后续真实消息变化，当前扫描统计为 `ready=14, decode_failed=0`；这不用于覆盖此前 Gate 数字。

### 12.2 FSM false-success containment

Core 发送状态机现在为：

```text
accepted -> queued -> sending -> submitted -> sent
                                      \
                                       -> uncertain
```

`agent-wechat /api/messages/send success=true` 只代表 `submitted`；只有唯一正确的 WeChat DB/Core outgoing echo 才能进入 `sent`。

真实 false-success fault injection 使用原版 upstream Rust sender，没有 fork、没有修改 upstream binary：

- F-Live-A child label 在注入前再次校验为 `account_id=f-live-a`、`provider=agent_wechat`。
- 临时清空 clipboard 并把 child 的 `/usr/bin/xclip` 移到 `/usr/bin/xclip.gate`，同时安装 45 秒自动 restore guard；随后立即显式恢复。
- 真实发送 marker：`F-LIVE-20260902T035314Z-A-FALSE-SUCCESS`。
- send id：`send-0700efc55e6649da9fdfcfdd673de3bb`。
- upstream FSM 返回 `success=true`，Core 真实进入 `submitted`：`attempt_count=1`、`echo_message_id=''`、`delivery_certainty=pending_confirmation`、`automatic_retry=false`。
- 恢复 xclip 后继续经过至少两个正常 5 秒 Sync 周期，Core/DB `echo_count=0`。
- `submitted` 不在 `pending_sends()`。
- 为避免额外等待默认 120 秒，在已经确认超过两个正常 Sync 周期仍无 echo 后，使用同一生产 `expire_submitted_sends()` 路径把测试 confirmation window 缩短到 1 秒触发 expiry。
- 最终 outbox：`status=uncertain`、`attempt_count=1`、`echo_message_id=''`、`delivery_certainty=unknown`、`automatic_retry=false`。
- `uncertain` 同样不在 `pending_sends()`，没有自动 retry。

结果：**PASS**。

### 12.3 Submitted -> DB-confirmed sent

对 F-Live-A / `filehelper` 连续发送 5 条真实文本，脚本逐次采样 outbox 状态并最终与 Core normalized message 对账。

| Marker | submitted | final | attempt | echo_message_id == Core message_id |
|---|---:|---:|---:|---:|
| `F-LIVE-20260902T035114Z-A-B01` | yes | sent | 1 | yes |
| `F-LIVE-20260902T035114Z-A-B02` | yes | sent | 1 | yes |
| `F-LIVE-20260902T035114Z-A-B03` | yes | sent | 1 | yes |
| `F-LIVE-20260902T035114Z-A-B04` | yes | sent | 1 | yes |
| `F-LIVE-20260902T035114Z-A-B05` | yes | sent | 1 | yes |

五条均先真实进入 `submitted`，随后由唯一 DB echo 转为 `sent`；最终检查 `batch5=[('sent', 5)]`。所有 `attempt_count=1`。

结果：**PASS**。

### 12.4 Stable message identity + existing duplicate migration

在任何真实 migration 前，先用 SQLite online backup API 备份：

```text
/mnt/user/appdata/wechat-hub-f-live/core-data/backups/f-live-pre-migration-20260902-1054/
  wechat_core.sqlite
  wechat_memory.sqlite
```

两份备份均 `PRAGMA quick_check=ok`。

真实 migration 前：

```text
staging messages                 61
staging source duplicate groups  3
Core messages                    61
Core source duplicate groups      3
```

真实 migration 后：

```text
staging messages                 58
staging source duplicate groups  0
Core messages                    58
Core source duplicate groups      0
orphan message_media refs         0
```

且 migration 前后 `message.created` 事件总数都为 `61`，migration 没有制造第二个 `message.created`。

真实历史数据中 local_id 1/7 明确复现 `server_id=0 -> ACK`：

- local_id 1：最早 UID `923224...e98` 的 `server_id=0/status=1`；后续重复行 `server_id=8398212259929210110/status=2`。迁移后只保留最早 UID，mutable ACK 字段更新为后者值。
- local_id 7：最早 UID `32ae11...9ff4` 的 `server_id=0/status=1`；后续重复行 `server_id=6705313448850209113/status=2`。迁移后只保留最早 UID并更新 ACK 字段。
- local_id 8 同样收敛到最早 UID并采用更完整的后续 mutable 字段。

Core 对 source_local_id 1/7/8 最终各只有一个逻辑消息，`message_id` 等于 canonical 最早 UID；后续多轮 Sync 后 `core_dup_groups=0` 仍保持不变。

新增回归同时精确覆盖“第一次 server_id=0、第二次 ACK 非 0”：staging=1、Core=1、message_id 不变、server_id 更新、不产生第二个 `message.created`。

结果：

- Stable message identity：**PASS**
- Existing duplicate migration：**PASS**

### 12.5 Interactive Desktop

Runtime Manager 新增固定、安全的 `ensure_interactive_desktop(account)`，通过 Docker Engine Exec API 只对匹配 `account_id/provider/managed` labels 的 child 操作，且 Exec command 为代码内固定模板。

真实修改前 upstream x11vnc：

```text
x11vnc -display :99 -forever -nopw -shared -viewonly -xkb -rfbport 5900 -listen 127.0.0.1
```

Runtime reconcile 后：

```text
x11vnc -display :99 -forever -nopw -shared -xkb -rfbport 5900 -listen 127.0.0.1
```

child 的 Host `PortBindings=null`，`5900/6080/6174` 均没有发布到 Host；浏览器仍只经过 Desktop Gateway。

真实 Windows Edge + noVNC 验证：

- Desktop Gateway descriptor 为 opaque `/desktop/<session>/...`，浏览器 URL 无 upstream token。
- Edge 加载标题 `8828595e4c0e:99 - noVNC`，首屏获得 noVNC canvas。
- page reload 后 canvas 再次恢复，远端画面链路重新建立。
- 为避免误操作真实聊天，在相同 `DISPLAY=:99` 临时打开独立 `xev` 测试窗。
- Edge/noVNC 将 pointer 移到远端 `(162,190)` 并点击；`xev` 收到 `EnterNotify`、`ButtonPress`、`ButtonRelease`。
- Edge/noVNC 输入 `GateK7`；`xev` 逐键记录 `G/a/t/e/K/7` 的真实 `KeyPress/KeyRelease`。
- 测试窗随后关闭，不保留焦点干扰。

结果：

- Interactive Desktop mouse：**PASS**
- Interactive Desktop keyboard：**PASS**
- reload / reconnect：**PASS**

### 12.6 Account-list degraded isolation

当前遵守 F-Live-A-only 边界，没有创建账号 B。因此真实 fault test 只冻结现有 F-Live-A 的 `agent-server` PID 72；双账号 healthy-peer/frozen-peer 并行行为由 Runtime 回归覆盖，真正双账号 live isolation 留到用户扫码 B 后。

真实单账号 fault test：

- `SIGSTOP` agent-server，同时设置 30 秒自动 `SIGCONT` guard；不停止 WeChat，不停止/重建 child container。
- `/v1/accounts` 在 `2.978068s` 返回，而不是被网络 probe 长时间卡住。
- 返回状态：`state=degraded`、`agent_server_healthy=false`、`runtime_health=degraded`、`wechat_login_status=unknown`，health error 为 `/health` timeout。
- 显式 `SIGCONT` 后，`/v1/accounts` 在 `0.213251s` 返回 `online/healthy/logged_in`。

Runtime 自动回归同时验证：Registry snapshot 在锁内快速读取后释放；AgentWechat probes 最多 8 workers 并行；list 使用 1.25 秒短 probe timeout；一个 degraded peer 不阻塞另一个正常 peer。

结果：**PASS**。

### 12.7 Remote filename preservation

当前同步的 upstream main 仍在文件发送时构造临时路径：

```text
/tmp/send_file_<ms>_<safe_name>
```

已合并的 upstream #143 是非 ASCII filename/temp-path 安全修复，不是 remote filename preservation。当前 main 没有发现把远端展示文件名恢复为原始 filename 的实现；本轮也没有为了该问题 fork upstream sender。

因此：文件内容发送此前真实 Gate 证据保持 **PASS**，remote filename preservation 为 **PARTIAL**。

### 12.8 Image build / deployment reproducibility

Core 正式从 NAS 上的 source build context 成功构建：

```text
image: wechat-core:f-live-fsm-20260902
id:    sha256:e15e4fee1a5473dfd3ce46af58438742770003fd18f8400b97fe6bed68bb907a
```

构建后 image 内 `store.py`、`sender.py`、`memory_ingest.py`、`media_sync.py` SHA-256 与 `G:\LLM\WeChat_Hub` 工作树逐项一致。

Runtime 正式 source build 也已尝试，但在到达腾讯下载步骤之前，NAS 无法连接 `archive.ubuntu.com:80`，APT layer exit code 100；因此没有生成新的 Runtime image。没有使用 `docker commit` 冒充生产构建。

当前 F-Live Runtime/Core/Console 容器保留并用于 smoke/Gate；Runtime/Core 的 live 代码有 hot patch，因此 **recreate/redeploy 仍不能视为最终 PASS**。

结果：Reproducible image build：**BLOCKED**（外部 Ubuntu archive 网络 blocker；Core image 本身 source build PASS）。

### 12.9 本轮回归

```text
Runtime             27 / 27 PASS
EFB                 19 / 19 PASS (.venv-c)
Console               9 /  9 PASS
Agent                 9 /  9 PASS
Stack + Mock Core    14 / 14 PASS
Core related suites        PASS (按 class/专项分组执行)
OpenAPI submitted enum     PASS
Python / Console JS syntax PASS
git diff --check           PASS
```

Core 相关回归覆盖：FSM false-success、submitted expiry/no-retry、唯一 text echo、wrong-chat echo、ambiguous candidates、stable source identity、existing staging/Core dedupe、message_media migration、media key/XOR 修复、Runtime registry/health/sender routing。由于单个 Core HTTP suite 耗时较长，仍按专项 class/test 分组执行；所有本轮相关组均 PASS。

工作树保持未提交状态；本轮没有自动 commit。

### 12.10 F-Live acceptance 状态追加

| Acceptance item | Result |
|---|---|
| FSM false-success containment | **PASS** |
| Submitted -> DB-confirmed sent | **PASS** |
| Stable message identity | **PASS** |
| Existing duplicate migration | **PASS** |
| Interactive Desktop mouse | **PASS** |
| Interactive Desktop keyboard | **PASS** |
| Account-list degraded isolation | **PASS** |
| Remote filename preservation | **PARTIAL** |
| Reproducible image build | **BLOCKED** |

最终 sanity check：Runtime、Core、Console 均 healthy；F-Live-A 为 `online / agent_server_healthy=true / runtime_health=healthy / wechat_login_status=logged_in`；`xclip` 已恢复；x11vnc 保持 interactive 且只监听 `127.0.0.1:5900`；child Host PortBindings 仍为 null；staging/Core source duplicate groups 均为 0；五条本轮 text 均保持 `sent`；false-success send 保持 terminal `uncertain`、`attempt_count=1`、`delivery_certainty=unknown`、`automatic_retry=false`。

在不创建账号 B 的前提下，本轮要求的 F-Live-A pre-B Gate 已完成。**可以扫码账号 B。**

## 13. F-Live 双账号 Acceptance：账号 B 与隔离 Gate

本节是在第 9–12 节既有证据之后追加的真实双账号 Gate，不覆盖此前单账号 PASS 项。

### 13.1 B 登录与 Runtime identity

从当前 Runtime Registry 读取到第二个真实账号：

```text
A account_id = f-live-a
B account_id = testB
```

B 完整登录 FSM 多次在真实 stop/restart 后重新走过扫码流程，最终均只在 upstream auth probe 返回真实登录态后进入：

```text
login_flow_state = logged_in
auth_status       = logged_in
state             = online
runtime_health    = healthy
agent_server      = healthy
```

结果：B login **PASS**。

最新 B DB credential / Sync 仍使用 B 自己的 `account_dir=wxid_rpfflqttdz4a22_7fcd`；本轮扫码后稳定数据曾达到：

```text
chats       4
contacts    139
members     133
messages    32  (随后 Gate 消息继续增加)
media ready 0
```

后续发送 Gate 结束时 B normalized messages 为 34。新账号历史量小不判失败。

结果：B DB credential / Sync **PASS**。

### 13.2 Two-account container / data isolation

真实审计确认：

- A/B `runtime_provider` 均为 `agent_wechat`。
- A child：`wechat-agent-f-live-a-faf35abb`；B child：`wechat-agent-testb-a7c4f6c8`，container identity 不同。
- Docker account-id labels 与各自 Registry account 一致。
- `/data` 与 `/home/wechat` 使用不同 account-scoped volume；没有共享账号 home。
- 两个 auth token 文件均为 `0600`，实际值不同；报告与命令输出均未打印 token/key 实值。
- child 6174 的 Host `PortBindings` 均为 null；只接内部 Docker 网络。
- PID namespace 独立。
- 最终 sanity：A 仅一份主 `/usr/bin/wechat`（PID 73），B 仅一份主 `/usr/bin/wechat`（PID 93）。
- B `key_extract.account_dir` 与 source DB dir 指向 B 自己的 wxid/home；A/B DB credential 未串号。
- 在双账号发送前的 Core 基线中，A/B chats/contacts/messages 按 `account_id` 分组独立；后续所有唯一 marker 也保持 account/chat scope。

结果：

- Two-account container isolation：**PASS**
- Two-account data isolation：**PASS**

### 13.3 Two-account Desktop isolation

真实 Windows Edge + noVNC 双窗口验证：

- A Desktop 与 B Desktop 显示明显不同的微信账号/会话内容。
- noVNC title 分别绑定不同 child。
- reload 后 A/B 各自重新建立画面。
- 在各自 DISPLAY 临时打开独立 `xev`：A 只收到 `AKey7`，B 只收到 `BKey8`；两边均收到独立 `ButtonPress`。
- 停止 B 后，先前 A opaque Desktop session 仍 HTTP 200，B 旧 session 变 HTTP 404；A 不受影响。
- Desktop descriptor/browser URL 不含 upstream token。
- 最终再次用 A/B token 实值只做日志匹配，Runtime/Core/Console/A-child/B-child 均为 `A_token_leak=no / B_token_leak=no`。

结果：Two-account Desktop isolation **PASS**。

### 13.4 A healthy + B SIGSTOP

真实 `SIGSTOP` B 的 `/opt/agent-server/agent-server`，不停止 A：

```text
/v1/accounts        1.829588 s
Console /           0.001010 s / HTTP 200
A Desktop API       0.544060 s / HTTP 200
```

期间 A 保持 online/healthy，B 被标记 degraded / upstream health timeout；A Console、Sync、Desktop 未被 B 拖住。显式 `SIGCONT` 后 B 恢复 online/healthy/logged_in。

结果：A healthy + B degraded list latency = **1.829588 s / PASS**。

## 14. F-Live 双账号真实发送 Gate

### 14.1 B first smoke：发现并修复首次打开 chat 的假成功

第一次 B smoke：

```text
F-LIVE-20260902T061711Z-B-SMOKE
```

真实状态到达 `submitted`、`attempt_count=1`，但 120 秒无 DB echo，最终进入 `uncertain`；A/B Core 与 staging 对 marker 都为 0。upstream execution log 显示 FSM step 已走完，但微信没有真实落库。Core 正确没有误标 `sent`。

进一步无发送诊断证明：B/filehelper 的 a11y 输入框为 `EDITABLE + FOCUSED`；直接使用 upstream `/opt/tools/input` 能让 Send 按钮由 disabled 变 enabled。问题集中在首次 `Chat -> ChatOpen -> Type` 同一 send plan 的 UI 时序。

因此新增一个 **Core-side、非 upstream fork** 的稳定化修复：`AgentWechatSenderDriver` 在 `/api/messages/send` 前先调用 upstream 官方 `POST /api/chats/{id}/open?clearUnreads=false`，并校验返回 username 与目标 chat_id 一致；预打开失败或目标不一致时，在触碰 send endpoint 之前 fail-closed。

专项 `AgentWechatSenderRoutingTest`：**6 / 6 PASS**，含 target mismatch fail-closed。

修复后新 marker：

```text
F-LIVE-20260902T063140Z-B-SMOKE
```

真实 event log：

```text
accepted -> queued -> sending -> submitted -> sent
attempt_count = 1
echo_message_id == Core message_id
account_id = testB
chat_id = filehelper
```

B/filehelper 恰好 1 条；A 全账号 0 命中；B 其他 chat 0 命中。

结果：B single text submitted->sent **PASS（修复后重跑）**。第一次 `uncertain` 证据保留，不删除、不改写。

### 14.2 Concurrent A/B 5+5

run prefix：

```text
F-LIVE-20260902T063305Z-P5
```

A/filehelper 与 B/filehelper 并发提交各 5 条。最终：

```text
accepted      10
submitted     10
sent          10
uncertain      0
failed         0
duplicate      0
missing        0
wrong-chat     0
elapsed       60.234 s
```

A source local_id `[19,20,21,22,23]`；B `[2,3,4,5,6]`，各自 01->05 顺序正确。A/B `sending` 与 `submitted` events 持续交错，不存在跨账号 global sender lock 或相互等待同一个 GUI plan lock。

结果：Concurrent A/B 5+5 **PASS**。

### 14.3 Concurrent A/B 20+20

run prefix：

```text
F-LIVE-20260902T063503Z-P20
```

最终：

```text
accepted      40
submitted     40
sent          40
uncertain      0
failed         0
duplicate      0
missing        0
wrong-chat     0
total time   242.196 s
```

每账号实测：

| Account | Count | Account duration | Throughput | submitted->echo avg | min | max |
|---|---:|---:|---:|---:|---:|---:|
| A `f-live-a` | 20 | 238 s | 0.0840 msg/s | 7.8 s | 2 s | 16 s |
| B `testB` | 20 | 183 s | 0.1093 msg/s | 9.2 s | 2 s | 24 s |

A source local_id 24->43、B 7->26 均严格递增；A/B execution events 在大量区间交错。不同账号真实并行。

结果：Concurrent A/B 20+20 **PASS**。

### 14.4 Failure isolation：stop B child

B child 完全停止期间：

```text
/v1/accounts        1.878974 s / HTTP 200
A saved Desktop     0.007034 s / HTTP 200
Console /           0.001024 s / HTTP 200
```

B = stopped/unavailable；A 保持 online/healthy，Sync `finished_at` 持续前进，原 Desktop session 正常。A/filehelper 发送：

```text
F-LIVE-20260902T064136Z-A-BSTOP
accepted -> queued -> sending -> submitted -> sent
attempt_count = 1
```

Core/Console 未崩。恢复 B 后微信要求真实重新确认/扫码；重新发起登录并扫码后，B 再次回到 online/healthy/logged_in。

结果：Failure isolation **PASS**。

### 14.5 正式 Core Gate 统计与失败尝试分离

post-fix 必需 Core write set（修复后 B smoke + 5+5 + 20+20 + B-stop 时 A smoke）：

```text
confirmed sent 52 / 52
wrong-chat      0
duplicate       0
missing         0
uncertain       0
failed          0
```

另外保留的修复前诊断：B 第一次 smoke `uncertain=1 / missing=1`。它不是 post-fix Gate 的成功统计，但必须作为真实失败证据保留。

## 15. EFB、资源与最终 Production Gate

### 15.1 EFB live adapter

NAS 当前没有常驻 `efb-multi` 实例。为验证真实 EFB slave 路径，本轮使用工作树 `.venv-c` 中的 `LinuxWeChatChannel` / `CoreClient`，通过临时 SSH tunnel 连接 **真实 F-Live Core**；不是 Mock Core，也没有直接调用 Core send 绕过 `LinuxWeChatChannel.send_message()`。Telegram Master/network 不在本 Gate 声明范围内。

EFB 实际发现 A/B filehelper，且账号级 capability 均为 AgentWechat：

```text
text=true image=true file=true
native_reply=false
```

EFB text：

- B `F-LIVE-20260902T075337Z-EFB-B-TEXT`：**sent / DB-confirmed**。
- A `F-LIVE-20260902T075337Z-EFB-A-TEXT`：`submitted -> uncertain`，marker 在 Core messages 中 0 命中。

随后只选择 B/filehelper 验证媒体：

- image：`submitted -> uncertain`，未观察到对应 outgoing image DB row。
- file：Core outbox 最终 `uncertain`，但 B 的真实 WeChat/Core DB 出现 outgoing `file` row：`send_file_<timestamp>_F-LIVE-...-EFB-B-FILE.txt`。这证明文件内容确实进入微信 DB，同时也直接证明 upstream 临时文件名前缀仍存在，且 Core 当前只对 text 做唯一 echo reconciliation，无法把这条 media DB echo 反链到 outbox。

因此本轮 EFB：**PARTIAL**。

更细分：

```text
B text                        PASS
A text                        PARTIAL / uncertain
B image                       PARTIAL / uncertain, no DB echo
B file content delivery       PASS (outgoing file DB row exists)
B file outbox DB-confirmation PARTIAL / uncertain
original filename preservation PARTIAL
```

当前 F-Live Registry 没有 Legacy live account；没有创建或启用 Legacy X11 sender。真实 Core `/health` 仍明确广告：

```text
legacy.text  = false
legacy.image = false
legacy.file  = false
```

因此 Legacy file capability boundary 保持关闭；没有为了 EFB Gate 重新启用 Legacy live sender。

本轮所有新增 write attempts（包含保留的 pre-fix smoke 与 EFB）合计 terminal `uncertain=4`：pre-fix B text 1、EFB A text 1、EFB B image 1、EFB B file 1。整个本轮 `wrong-chat=0`、`duplicate=0`。按“真实内容/DB row 缺失”口径，额外 missing 为 pre-fix B text、EFB A text、EFB B image 共 3；EFB B file 虽 outbox uncertain，但实际 outgoing file row 已存在，不计 content missing。

### 15.2 Two-account resource sample

在无 accepted/queued/sending/submitted 队列残留时执行 `docker stats --no-stream`。第二个较稳定 no-send 样本：

| Component | Memory | CPU |
|---|---:|---:|
| Runtime Manager | 643.2 MiB | 3.25% |
| Core | 42.13 MiB | 4.10% |
| Console | 43.44 MiB | 0.01% |
| AgentWechat A | 1.028 GiB | 37.16% |
| AgentWechat B | 870.5 MiB | 40.81% |
| **Total** | **~2.59 GiB** | **~85.33%** |

这里的 CPU 是 Docker 的即时百分比口径；采样时没有 send queue，但微信客户端自身仍有明显后台 CPU。前一个无发送样本总 CPU 约 99.69%，因此不能把 85.33% 描述成操作系统级“接近 0 的 idle”。

旧第 9–12 节报告没有保存一份可直接逐项对照的单账号 `docker stats --no-stream` 原始表，因此不伪造绝对 delta；当前可直接观测的第二账号 child 本身为 **870.5 MiB / 40.81%**（该即时样本）。A/B 最终各只有一份主 WeChat，没有重复客户端。

### 15.3 Runtime/source-build blocker

Runtime production build 状态保持不变：**BLOCKED**。本轮没有为了双账号 Gate 重建或删除当前 `wechat-runtime` container，也没有用 `docker commit` 冒充 source build。

先前 Core source image build 成功，但本轮在 live Gate 中又增加了 `AgentWechatSenderDriver` chat-preopen 稳定化修复；该修复目前已在工作树、专项单测和 live Core hot-patch 中验证，尚未重新生成一个正式 Core source image。尝试准备新的 NAS Core build context 时，本机到 NAS 的文件传输通道未成功，因此不能把已有旧 Core image 当成这项新修复的可重复部署证据。

所以最终 Production Ready 仍为 **PARTIAL**。至少还需要：

1. Runtime 从当前源码成功正式 build；
2. 新 Runtime image 包含全部 F-Live Runtime 修复并重启复验；
3. 当前 Core chat-preopen 修复进入正式 source-built Core image并复验；
4. 不能用当前 hot patch / docker cp 作为可重复部署证据。

### 15.4 Final acceptance summary

| Acceptance item | Result |
|---|---|
| B login | **PASS** |
| B DB credential/sync | **PASS** |
| Two-account container isolation | **PASS** |
| Two-account data isolation | **PASS** |
| Two-account Desktop isolation | **PASS** |
| A healthy + B degraded list latency | **1.829588 s / PASS** |
| B single text submitted->sent | **PASS**（pre-fix false-success evidence retained） |
| Concurrent A/B 5+5 | **PASS** |
| Concurrent A/B 20+20 | **PASS** |
| Wrong-chat | **0** |
| Duplicate | **0** |
| Missing | **0 in post-fix required Core Gate**；**3 across all new attempts incl. pre-fix/EFB** |
| Uncertain | **0 in post-fix required Core Gate**；**4 across all new attempts incl. pre-fix/EFB** |
| Failure isolation | **PASS** |
| EFB | **PARTIAL** |
| Two-account RAM/CPU | **~2.59 GiB / ~85.33% no-send instantaneous sample** |
| File content delivery | **PASS** |
| Remote filename preservation | **PARTIAL** |
| Reproducible Runtime image | **BLOCKED** until formal source build succeeds |
| Native Bridge | **NOT TESTED / RESERVED** |

最终安全 sanity：`wrong-chat=0`；未发现 Desktop 串号、account 数据串号或 token 泄漏。Runtime/Core/Console 与 A/B child 的最终 token-value log scan 全部为 no-hit。工作树保持未提交状态；**本轮没有自动 commit**。

## 16. Post-F-Live Desktop UX enhancement — Selkies Attach（source complete / live pending）

在完成上面的双账号 F-Live Gate 后，继续审查发现 AgentWechat 默认 `x11vnc + noVNC` 虽已真实验证鼠标/键盘可用，但产品体验仍弱于原 `wechat-selkies`：Windows 本地中文 IME、clipboard、文件上传下载、DPI/缩放/动态分辨率等能力不足。

本轮补充实现遵守新的硬约束：**同一个微信账号仍然只允许一份 Linux WeChat 客户端在线。** 没有启动第二份 `wechat-selkies` 微信，也没有让 Selkies 启动第二个 Xvfb。

最终 source 架构：

```text
Browser
  ↓ opaque Desktop Gateway session
WeChat Hub Desktop Gateway
  ↓
Selkies Attach companion (on demand; display/input/file transport only)
  ↓ same account network + IPC namespace
  ↓ account-private /tmp/.X11-unix volume
AgentWechat child
  ├─ Xvfb :99        ← only X server
  ├─ WeChat          ← only WeChat client
  ├─ AT-SPI
  └─ agent-server
```

实现要点：

- Selkies companion 默认复用当前 Runtime Manager 的 immutable image ID，因此不额外拉取另一套 `wechat-selkies` image/layers。
- companion 覆盖 image Entrypoint，只执行 `selkies --mode=websockets --enable-resize=true`；不会进入 s6、`/scripts/start.sh`、WeChat autostart 或 Xvfb 初始化。
- companion 与目标 AgentWechat child 共享该账号的 network + IPC namespace，并共享账号专属 `/tmp/.X11-unix` volume，覆盖 Linux abstract X11 socket 与 MIT-SHM；不同账号仍是不同 namespace/volume。
- companion 没有 Host `PortBindings`。其内部 `8081` 通过该账号 primary child 的 Docker DNS/name 访问，Browser 仍只见 Desktop Gateway opaque path。
- Selkies 使用独立于 agent-wechat API token 的 per-account `desktop-auth-token`。该 secret 为 0600 文件，只读挂载到 companion，实际值不进入 Docker Env/Cmd。Selkies 自身只监听 `127.0.0.1:8082` 且关闭内建 Basic Auth；companion 内的 `selkies_attach_gateway.py` 才监听 internal `:8081`，常量时间校验 WeChat Hub 的 secret header 后将其剥离再转发 HTTP/WebSocket，避免 Selkies 参数/环境/启动日志接触 secret。
- 每账号新增独立 browser-files volume：Selkies `/config/Desktop` ↔ WeChat `/home/wechat/WeChatHubFiles/Desktop`。
- Selkies 启用：本地 IME/Unicode 输入、双向 text clipboard、binary clipboard、upload/download、screen settings、DPI scaling、fullscreen/trackpad/on-screen keyboard。
- 默认锁定关闭：Selkies command websocket、sharing/collab/player links、audio、microphone、gamepad，减少浏览器桌面的权限面。
- noVNC 保留为 fallback/rescue。正在运行且尚未有新 X11/files mounts 的旧 AgentWechat child 不会被自动重建；`desktop_provider=auto` 直接 fallback noVNC，正常 account restart 后才具备 Selkies Attach。
- stop/remove account 会先撤销 Gateway sessions 并删除 companion container；普通 remove 保留 browser-files，只有 `purge_data=true` 才删除 data/home/browser-files/X11 对应资源。
- Core/OpenAPI 已透传 `desktop_provider`、`features`、`fallback_reason` 与 `file_exchange_path`。
- Browser Desktop 与自动 Sender 现在共享同一份 account-scoped GUI lease。Gateway 只在真实控制 WebSocket 存活期间持有跨进程 `flock`；同一个 opaque session 的多个 Selkies WebSocket 采用引用计数复用，同账号第二个 Desktop session 会被拒绝。Core Sender 在同一账号 GUI lease 被人工桌面占用时保持 outbox 为 accepted/queued，`attempt_count` 不增加、upstream 不被调用；其他账号的 Sender 不受影响。反过来，如果 Sender 正在持锁，Desktop WebSocket 会收到可重试的 busy 响应，而不是与发送动作争抢 chat/focus。
- Desktop Gateway 可通过 `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME/HOST/PORT` 发布 HTTPS 反向代理后的浏览器入口；Runtime 内部仍保持私有 HTTP hop。Console 会使用该公开地址打开桌面，从而可以在 HTTPS secure context 下恢复浏览器系统级 clipboard 能力。

source-side 回归：

```text
Runtime desktop/runtime tests     39 / 39 PASS
Core previous full regression     48 / 48 PASS
Core latest sender/desktop paths  13 / 13 PASS（AgentWechat Sender 7 + Legacy Sender 5 + Desktop API 1）
Core test methods now             49 total（新增 manual-desktop defer regression）
EFB                               19 / 19 PASS
Console regression                 9 /  9 PASS
Agent                              9 /  9 PASS
Stack wiring                       8 /  8 PASS
Mock Core                          6 /  6 PASS
Python compile                     PASS
Compose/OpenAPI YAML parse         PASS
git diff --check                   PASS（仅现有 LF/CRLF warning）
```

新增测试明确验证：

- Selkies companion payload 中没有第二个 WeChat/Xvfb 启动命令；
- `IpcMode` / `NetworkMode` 都只指向目标 account primary container；
- companion 无 Host `PortBindings`；
- A/B X11/files volume 不共享；
- command websocket locked off，clipboard/file/screen controls enabled；
- 外层 Desktop Gateway 路由不会注入/暴露 agent-wechat token；每账号 desktop secret 只进入 internal header；
- companion 内层 proxy 会在转给 Selkies 前校验并剥离 desktop secret，因此 Selkies 自身不接触 secret；
- 自动 fallback noVNC 时不会重建正在运行的旧账号；
- Selkies companion remove 不停止 primary AgentWechat/WeChat。
- 同账号人工 Desktop active 时自动 Sender defer 且 attempt_count=0；释放 Desktop 后下一轮正常 submitted；账号 B 不会被账号 A 的人工 Desktop 阻塞。
- 同一个 Desktop session 可以为 Selkies 的多个 WebSocket 复用同一 GUI lease；同账号不同 session 不能同时取得人工控制权。

浏览器安全上下文注意：文件 `<input>`、Selkies 页面内中文输入和手动 clipboard UI 可通过普通 HTTP 工作；Chrome/Edge 的系统级 Clipboard API 可能要求 HTTPS secure context。要恢复最完整的“本地系统剪贴板自动同步”体验，Production UI 建议使用 HTTPS 反向代理，并配置 `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=https` 及实际公开 HOST/PORT。

本节目前属于 **source complete / live pending**。由于 Runtime reproducible source build 仍被 NAS 外网/APT 阻塞，本轮没有重建当前真实 A/B Runtime，也没有为 UI 功能打断已经登录的微信。正式 Live Gate 仍需在可 source-build 的 Runtime image 上验证：中文 IME、text/image clipboard、file upload/download、resize/DPI、A/B Desktop/files isolation、on-demand RAM/CPU，以及每账号仍然只有一份 WeChat process。

## 17. P0 Host Stability superseding note — 2026-09-04

第 16 节记录的是 **P0 xclip 事故发生前** 的 Selkies Desktop source 状态，其中关于 clipboard 可启用/HTTPS 下恢复 clipboard 的描述已被本节和 `P0_SELKIES_XCLIP_INCIDENT_REPORT.md` **明确取代**，不得再作为 rc.2 验收依据。

真实事故中，Unraid load average 达到 `277.11 / 281.70 / 240.95`，`wechat-hub-f-live-runtime` 内观测到 7,000+ 个 `xclip -selection clipboard -o -t TARGETS` task，Host 失去正常 SSH/Ping 响应并最终物理重启。`0.1.0-rc.1` 因此保持 **BLOCKED — P0 HOST STABILITY**；H2/H3 保持停止。

独立复核原 P0 hotfix 后又补出三个必须进入 rc.2 的 source 修复：

1. Runtime Manager 镜像本身继承 LinuxServer `baseimage-selkies`，其原生 clipboard 默认开启；仅设置 `WECHAT_SELKIES_CLIPBOARD_ENABLED` 只能保护 AgentWechat companion，不能保护事故发生的 Runtime Manager。rc.2 现已在 Dockerfile、Stack、production overlay、standalone Runtime compose 中直接锁定 `SELKIES_CLIPBOARD_* = false|locked`。
2. companion 原 shell `trap` 后使用 `exec python3`，trap 实际不会存活；且 `pkill -u wechat` 依赖并未保证存在的真实 UID。rc.2 改为 Docker `Init=true` + Bash lifecycle supervisor，Selkies/internal proxy 任一退出都会触发对称清理，Docker stop/remove 作为最终 whole-cgroup reap 边界。
3. 原 `PidsLimit/Memory/CPU` override 可通过 `-1/0/超大值` 绕过“硬上限”。rc.2 对 companion 和 primary 的安全资源变量增加正值校验和 bounded clamp，不能通过环境变量恢复 unlimited。

此外，rc.2 **彻底取消 clipboard runtime opt-in**：即使设置 `WECHAT_SELKIES_CLIPBOARD_ENABLED=true` 也保持 text/binary clipboard 关闭。HTTPS 只解决浏览器 secure-context，不是 xclip subprocess safety proof。未来重新启用 clipboard 必须先完成 backend/reaper 独立审计和新的 Host Stability Gate。

最新 source regression：

```text
Runtime complete tests             49 / 49 PASS
Stack wiring                       10 / 10 PASS
60-cycle lifecycle churn            PASS（仅模拟；不是 NAS Host Soak）
```

这里特别纠正旧报告口径：模拟 churn 使用 dummy companion manager，不启动真实 Selkies/xclip/Docker cgroup，因此不能声称 `xclip=0` 的真实 Soak 证据。真正 Principle G 仍为 **NOT RUN / BLOCKING rc.2 promotion**。

rc.2 Canary 必须在真实单账号容器上至少 30 分钟记录：`pids.current`、`pids.max`、`pids.events max`、真实 xclip count、companion create/reap、CPU/RAM、Host load、SSH latency、Ping loss 和退出后的 orphan 状态。cgroup PIDs 包含 Linux threads/tasks，因此 `100/256` 只能在采集正常基线与峰值 headroom 后正式接受。

