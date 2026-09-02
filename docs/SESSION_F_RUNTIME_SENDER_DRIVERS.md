# WeChat Hub 会话 F — Runtime / Sender Driver 改造

日期：2026-09-01

## 1. 目标与结果

会话 F 将 WeChat Hub 的微信运行时与发送链路改造成可插拔 Provider / Driver 模型，同时保留既有 Legacy 路径：

```text
Console / EFB / Agent
        ↓
       Core
        ↓
      Outbox
        ↓
 AccountSender
   ├─ legacy        → 既有 xdotool / X11 控制器
   ├─ agent_wechat  → upstream agent-wechat REST / FSM / AT-SPI
   └─ native        → 预留接口，默认不可用
```

Runtime Provider：

- `legacy`：现有 WeChat Hub Runtime，保持兼容，不删除。
- `agent_wechat`：一个账号对应一个独立的 upstream `agent-wechat` 容器；容器内只有该账号的一份官方 Linux 微信。

Native Sender：

- 仅预留 capability / driver 边界。
- 当前不注入微信、不硬编码函数地址、不实现 `send_text` 偏移调用。
- `native` capability 默认 `available=false`。

## 2. 上游项目引用声明

本 WeChat Hub 实例为个人自用集成，不作为商业分发产品。

会话 F 参考/调用以下上游项目：

### thisnick/agent-wechat

- 项目：https://github.com/thisnick/agent-wechat
- 容器：https://github.com/thisnick/agent-wechat/pkgs/container/agent-wechat
- 用途：Linux 微信 Runtime、Xvfb、AT-SPI Accessibility、FSM、REST API、WebSocket、noVNC、文本/图片/文件发送、微信数据库读取。
- 2026-09-01 实施时固定镜像：`ghcr.io/thisnick/agent-wechat:0.11.15`
- WeChat Hub 不复制其 Rust/TypeScript 自动化实现；Runtime 通过 Docker Engine 管理其官方容器，Core 通过公开 REST API 调用发送能力。

### zhusinian/wechat-shot-bridge

- 项目：https://github.com/zhusinian/wechat-shot-bridge
- 用途：仅作为未来 Linux 微信 Native Bridge 的技术参考。
- 2026-09-01 检查时主要能力仍是注入 helper 后调用微信内部截图函数；未提供成熟的 `send_text` / `send_image` / `send_file` API。
- 因此当前 WeChat Hub 只预留 Native Driver，不复制其注入/偏移实现，也不会自行猜测微信内部函数地址。

若未来将本项目改为对外分发，应重新检查上述上游项目当时的 LICENSE 与再分发条件；本文件只记录当前个人自用实例的引用关系。

## 3. 一账号一 Runtime

AgentWechat Provider 遵循：

```text
personal → wechat-agent-personal-<hash> → one WeChat
work     → wechat-agent-work-<hash>     → one WeChat
backup   → wechat-agent-backup-<hash>   → one WeChat
```

每个账号独立：

- upstream container
- `/data` volume
- `/home/wechat` volume
- 256-bit 随机 auth token
- Xvfb / AT-SPI / VNC 环境
- upstream process-global FSM lock

因此 A/B/C 不再争抢同一个 GUI plan lock。Core Sender 对同一账号串行，不同账号可并行。

禁止同一账号同时启动 Legacy WeChat 与 AgentWechat WeChat。Registry 中每个账号只有一个 `runtime_provider`。

旧 Registry 没有 `runtime_provider` 字段时自动按 `legacy` 解释，不会因升级而切换现有微信。

## 4. Docker 权限边界

只有 `wechat-runtime` 挂载：

```text
/var/run/docker.sock:/var/run/docker.sock
```

以下服务不挂载 Docker Socket：

- Core
- Console
- EFB
- Agent

Runtime 使用 Docker Engine Unix Socket API 管理 child container，并用 labels 定位实例：

```text
com.wechat-hub.managed=true
com.wechat-hub.account-id=<account_id>
com.wechat-hub.provider=agent_wechat
```

资源名通过 `sanitize_account_runtime_name()` 清洗，并附带 account id 的 SHA-256 短摘要，避免不同合法 account id 清洗后碰撞。

## 5. AgentWechat 持久化

逻辑卷名：

```text
wechat-agent-<safe>-data
wechat-agent-<safe>-home
```

挂载到 upstream：

```text
/data
/home/wechat
```

底层数据目录位于 Runtime `/config/agent-wechat/<safe>/`，因此 Core 仍可通过只读的 `runtime-config` volume 访问 `/home/wechat` 内官方微信数据库，不需要把接收链路改造成 upstream REST 同步。

Runtime 生成每账号独立 token：

```text
/config/agent-wechat/<safe>/auth-token
```

token 使用 `secrets.token_hex(32)` 生成并尝试设置为 `0600`；child container 只读挂载到 `/data/auth-token`。

## 6. PID 隔离 / DB Sync 兼容

现有 WeChat Hub 接收链路保持：

```text
官方微信 DB
  ↓
Sync / decrypt
  ↓
Core
```

没有改成 agent-wechat REST 消息同步。

AgentWechat child container **保持 Docker 默认的独立 PID namespace**，不与 Runtime Manager、其他 AgentWechat 账号共享 PID namespace。原因是 upstream 自己会定位 `/usr/bin/wechat` 进程；如果多个账号共享 PID namespace，上游 A 就可能看到 B 的微信进程，违反账号隔离原则。

因此 AgentWechat Provider 不让 Core ptrace child container。登录流程由 upstream 在自己的容器内完成 DB credential extraction，并把已验证凭据写入该账号独立 `/data/agent.db` 的 `wechat_keys` 表。Runtime Driver 从本账号 `/data/agent.db` 读取这些记录，再通过现有私有 Unix control socket 的 `db_keys` action 交给 Core；Core 不直接依赖 upstream 状态库路径或 Docker：

```text
agent-wechat /data/agent.db / wechat_keys
        ↓  Runtime AgentWechat Driver
private /run/wechat-runtime/control.sock
        ↓  account_dir + db_name only
Core runtime/<account>/wechat-decrypt/keys/all_keys.json
        ↓
现有 refresh_decrypted / WAL patch / memory ingest
```

也就是说接收链路和现有 DB 解密/Sync 实现保持不变，只替换 AgentWechat Runtime 的 key provider。Legacy Runtime 仍使用现有 PID memory scanner。

## 7. Sender Driver

### legacy

沿用现有：

```text
wechat_controller
→ xdotool/xclip/X11
```

保留 display lock、window id 和 target chat 安全检查。

### agent_wechat

Core 调用：

```text
POST http://wechat-agent-<safe>:6174/api/messages/send
Authorization: Bearer <account-token>
```

支持：

- text
- image（base64 + MIME）
- file（base64 + filename）

`chatId` 使用 Core 已规范化的微信 username/chat id，不做 display-name 模糊匹配。

当前 upstream send API 没有暴露可验证的 reply/mention 参数，因此 WeChat Hub 对 `target_message_id` 和 `mention_member_ids` 采取 fail-closed：不降级成普通文本发送。

AgentWechat 的 HTTP 发送结果另外区分“明确失败”和“交付状态未知”：

- upstream 返回明确 HTTP/业务错误：`failed`。
- 请求已经发起，但等待 upstream 响应时出现 timeout/连接中断：`uncertain`。

`uncertain` 是终态，不进入自动 retry 队列。对应 `send.updated` 包含：

```text
error.code = agent_wechat_delivery_unknown
details.delivery_certainty = unknown
details.automatic_retry = false
```

这样人工操作、Console/EFB 或其他消费者不会把网络中断理解成“确定没有发送”，从而降低重复消息风险。

Sender capability 同样按账号暴露。Core 顶层 capability 继续保持 Legacy-safe 的保守值，兼容旧消费者；每个账号的 `runtime.sender_capabilities` 才表示该账号实际 Driver 能力。因此混合 Provider 时：

```text
AgentWechat account → file=true
Legacy account      → file=false
```

EFB 在发送前按目标 `account_id` 读取账号 capability；旧 Core 没有账号 capability 时才回退到原顶层 capability。

### native

当前只是稳定接口占位。可选配置 `WECHAT_NATIVE_DRIVER_SOCKET` 用于探测未来 Unix Socket bridge 是否存在；健康接口会区分 `configured` 与 `bridge_detected`。但**仅检测到 socket 不会启用发送**：除非未来 upstream Native Bridge 提供明确、版本化的 send capability handshake，否则 `available` 始终为 `false`，不会进行注入或猜测内部函数地址。

## 8. 并发模型

Core Outbox：

```text
Account A queue ─→ serial worker A ─→ Driver A
Account B queue ─→ serial worker B ─→ Driver B
Account C queue ─→ serial worker C ─→ Driver C
```

不同 account group 使用线程池并行；同一账号通过 account lock 串行。

Legacy Driver 仍额外受 display lock 约束；AgentWechat 每个账号是独立 upstream 实例，不存在跨账号全局 GUI plan lock。

## 9. Console

新增账号时默认选择：

```text
AgentWechat 增强模式（Beta）
```

也可选：

```text
Legacy（兼容模式）
```

AgentWechat：

- 不要求用户填写 X11 Display。
- 账号卡显示 Runtime Provider、PID、upstream image。
- `扫码登录` 由 Runtime 启动 upstream `/api/ws/login` 完整登录 FSM；二维码 PNG 只保存在 Runtime 进程内存中并通过现有 no-store 链路返回 Console。
- 不使用一次性 `/api/status/login` 作为主动登录流程，因为完整 WebSocket FSM 在登录成功后还会执行 upstream 的账号识别与 DB credential extraction，现有 DB Sync 依赖这一步。
- Console 只在该完整 FSM 发出 `login_success` 后显示登录成功；即使 `/api/status/auth` 已先观察到聊天主界面，也会等待后置账号识别/credential 准备完成，避免 Sync 与登录收尾竞争。
- `6174` **不发布到 Host**，只连接 WeChat Hub Docker internal network。
- `打开桌面` 由 Runtime 创建短期、随机、账号绑定的 Desktop Gateway session；Core/Console 只拿到 Gateway URL，不拿 upstream token。
- AgentWechat 账号的默认桌面现在是 **Selkies Attach**：Selkies companion 只连接该账号已经存在的 `Xvfb :99`，**不启动第二个 Xvfb，也不启动第二份 WeChat**。真正的 WeChat 进程仍只存在于原 AgentWechat child 中。
- Selkies companion 与目标 AgentWechat child 共享该账号专属 `/tmp/.X11-unix` volume，并共享该 child 的 IPC + network namespace；PID namespace、持久文件和其他账号仍隔离。这样同时覆盖 filesystem/abstract X11 socket 与 MIT-SHM，而不会连到另一账号的 X server。
- companion 使用当前 Runtime Manager 的同一 image layer，但覆盖 Entrypoint，只执行 `selkies ... --mode=websockets --enable-resize=true`。因此不会触发 LinuxServer s6、`/scripts/start.sh`、WeChat autostart 或第二套桌面初始化。
- Browser → WeChat Hub Desktop Gateway → account-specific Selkies companion。companion 没有 Host `PortBindings`；其 `8081` 只存在于该 AgentWechat child 的 network namespace。
- 每账号另有独立 `desktop-auth-token`（0600），与 agent-wechat send/API token 分离。它通过只读 secret file 注入 companion，实际值不进入 Docker Env/command。Selkies 自身只监听 companion/shared namespace 的 `127.0.0.1:8082` 且关闭内建 Basic Auth；前置的 `selkies_attach_gateway.py` 才监听 internal `:8081`，以常量时间校验 `X-WeChat-Hub-Desktop-Token` 后再剥离该 header 转发 HTTP/WebSocket。这样 secret 不进入 Selkies 参数/环境/日志，Browser URL/JSON/session descriptor 也不包含该值。
- Selkies 提供本地 IME/Unicode 输入、双向文本 clipboard、binary clipboard、文件 upload/download、屏幕设置、DPI scaling、CSS scaling/fullscreen/trackpad/soft keyboard 等浏览器桌面能力。危险的 Selkies command websocket 和 sharing/gamepad/audio/microphone 能力默认锁定关闭。
- 每账号增加独立 `browser-files` volume：Selkies 上传目录 `/config/Desktop` 与同一账号 WeChat 可见的 `/home/wechat/WeChatHubFiles/Desktop` 是同一份数据。账号 A/B 不共享该目录。
- noVNC/x11vnc 继续保留为自动 fallback/救援桌面。老的、当前正在运行且尚未挂载新 X11/files volume 的 AgentWechat child **不会被为了桌面功能自动重建**；自动模式先回退 noVNC，等用户正常 restart 该账号后再切 Selkies。
- Desktop Gateway 同时代理普通 HTTP、WebSocket Upgrade、binary/text frames、ping/pong 与长连接；session descriptor 记录 `desktop_provider=selkies|novnc`，但不记录任何 upstream token。
- 人工 Desktop 与自动 Sender 共享 `/run/wechat-runtime/locks` 下同一套 account-scoped GUI lease。Gateway 只在真实 Desktop control WebSocket 存活时持有跨进程 `flock`；Selkies 同一个 opaque session 的多个 WebSocket 使用引用计数复用。人工桌面占用账号 A 时，Core 对 A 的 accepted/queued send 只做 defer，不进入 `sending`、不增加 `attempt_count`、不调用 upstream；账号 B 仍可并行发送。反过来 Sender 正在控制 A 时，A 的新 Desktop WebSocket fail-closed 并提示稍后重试，避免人工切 chat 与自动 pre-open/send 竞争导致 wrong-chat。
- Gateway 自身关闭 access log，upstream token 不进入浏览器 URL、Core/Console JSON 或标准 access log。
- Gateway HTTP 响应使用 `Cache-Control: no-store` 与 `Referrer-Policy: no-referrer`；停止/删除账号会撤销该账号已有 Gateway session。
- 两个账号的 Gateway session 分别解析到各自 Registry account，不能交叉到另一 child container。
- QR PNG 与 desktop descriptor 都通过 `Cache-Control: no-store` 返回。

浏览器安全上下文说明：Selkies 页面内的中文输入、文件选择/上传和手动 clipboard UI 不依赖第二个微信客户端；但浏览器的系统级 Clipboard API 在 LAN 纯 HTTP 下可能被 Chrome/Edge 的 secure-context 策略限制。生产环境若希望完整的自动系统剪贴板体验，应让 Console/Desktop 入口通过 HTTPS 反向代理访问，并用 `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME/HOST/PORT` 告诉 Console 实际浏览器入口。

在真实 NAS acceptance 完成前，Console 始终显示 **AgentWechat 增强模式（Beta）**，不宣称生产验证已经完成。

### AgentWechat health

Runtime 不再把 Docker `State.Running` 等同于健康，至少分成三层状态：

```text
container_running
agent_server_healthy   ← internal GET /health
wechat_login_status    ← authenticated /api/status/auth
```

child container 运行但 `/health` 失败时，`runtime_health=degraded`，Core account state 与 Console 账号卡都显示 degraded/异常；登录、Desktop 和 Runtime API 调用也不会把这种实例当作正常 agent-server。

Legacy：

- 保持现有扫码截图与 Selkies 完整桌面入口。

## 10. 删除策略

默认删除：

```text
remove account
→ stop/remove Selkies companion
→ stop/remove child container
→ preserve /data + /home/wechat + browser-files volumes
```

只有显式 `purge_data=true` 时 Runtime 才允许删除 AgentWechat 数据卷、browser-files、X11 临时卷和对应持久目录。

Core API：

```text
DELETE /v1/runtime/accounts/<account_id>                 # preserve
DELETE /v1/runtime/accounts/<account_id>?purge_data=1    # explicit purge
```

Console 默认“移除”始终走 preserve 模式，避免误删登录状态。

## 11. 版本升级

生产默认不使用 `latest`。

当前：

```text
AGENT_WECHAT_IMAGE=ghcr.io/thisnick/agent-wechat:0.11.15
```

升级 upstream 时修改 `.env` 中 `AGENT_WECHAT_IMAGE`，停止/重启对应 AgentWechat Runtime。Runtime 在目标 image 与现有 stopped container image 不一致时重建 child container，但复用独立 `/data`、`/home/wechat` 与 browser-files volumes。旧 child 如果还没有 Selkies Attach 所需 X11/files mounts，也只会在已经 stopped 的正常 restart 路径中重建，不会热重建在线微信。

未来可在 Registry `agent_wechat.image` 增加 per-account override；当前 MVP 以全局默认为主。

## 12. 配置项

```text
AGENT_WECHAT_IMAGE=ghcr.io/thisnick/agent-wechat:0.11.15
AGENT_WECHAT_SHM_MB=512
AGENT_WECHAT_PULL_TIMEOUT=900
AGENT_WECHAT_LOGIN_TIMEOUT_MS=300000
WECHAT_DESKTOP_GATEWAY_HOST_BIND=0.0.0.0
WECHAT_DESKTOP_GATEWAY_PORT=17892
WECHAT_DESKTOP_GATEWAY_SESSION_TTL=14400
WECHAT_DESKTOP_GATEWAY_MAX_WS_FRAME_MB=64
WECHAT_DESKTOP_GATEWAY_MAX_HTTP_MB=1024
WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=http
WECHAT_DESKTOP_GATEWAY_PUBLIC_HOST=
WECHAT_DESKTOP_GATEWAY_PUBLIC_PORT=
WECHAT_SELKIES_ATTACH_ENABLED=true
# 通常留空：留空时复用当前 Runtime Manager 的 immutable image ID。
WECHAT_SELKIES_ATTACH_IMAGE=
WECHAT_SENDER_ACCOUNT_WORKERS=8
# Optional future native bridge discovery only; sending remains disabled today.
WECHAT_NATIVE_DRIVER_SOCKET=
```

当 Desktop Gateway 前面有 HTTPS 反向代理时，将 `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=https`，并按实际浏览器入口填写 `PUBLIC_HOST/PUBLIC_PORT`。这些值只影响 Core/Console 返回给浏览器的 Desktop URL，不改变 Runtime 内部 Gateway 监听方式，也不会发布 child `6174` 或 companion `8081`。这样可以为 Chrome/Edge/Firefox 提供 Clipboard API 所需的 secure context。

`WECHAT_DESKTOP_GATEWAY_HOST_BIND` 只控制 WeChat Hub Desktop Gateway 的浏览器入口；它**不会**发布 child 的 `6174` 或 Selkies companion 的 `8081`。真实 agent-wechat REST/noVNC/Selkies 均只存在账号对应的 Docker/internal namespace。

## 13. 不在本任务范围内

- 不重写 EFB。
- 不重写 Console 消息模型。
- 不把接收消息改成 agent-wechat REST 拉取。
- 不复制 agent-wechat Rust/TypeScript 源码。
- 不复制 wechat-shot-bridge C/C++ 注入源码。
- 不硬编码 Linux 微信内部函数 offset。
- 不删除 Legacy Runtime / Legacy Sender。

## 14. 会话 F 验收记录

### 改造前基线

在会话 F 修改前先检查了各 `work/*` 工作树，确认 A–E 已存在未提交改动，因此 F 全程采用增量修改，没有 reset/checkout 覆盖前序会话。

本会话实际重跑并确认：

```text
Runtime        12 / 12 PASS（F 修改前旧测试集）
EFB            18 / 18 PASS
Console         8 /  8 PASS
Agent           9 /  9 PASS
Mock Core       6 /  6 PASS
Stack           6 /  6 PASS
```

Core B 最近完成报告记录的基线为 `24 / 24 PASS`。会话 F 在改造前也启动了完整 Core 测试，但工作区连接器在长命令结束前回收了会话，未保留最终汇总输出，因此不把那次执行伪记成新的 24/24 证据；会话 F 完成后已按最终代码将完整 Core 测试拆组重新覆盖。

### 改造后最终验证

```text
Runtime        22 / 22 PASS
Core           34 / 34 PASS
EFB            19 / 19 PASS
Console         8 /  8 PASS
Agent           9 /  9 PASS
Mock Core       6 /  6 PASS
Stack           8 /  8 PASS
```

附加检查：

```text
Console JS syntax            PASS
Affected Python py_compile   PASS
Compose/OpenAPI YAML         PASS（6 files）
git diff --check             PASS
Docker socket exclusivity    PASS（Stack 自动测试）
```

Core 最终 `test_core.py` 共 34 个 test method，按分组执行并覆盖全部方法。新增审阅回归覆盖：Agent server unhealthy → Core degraded；AgentWechat timeout → `uncertain` + no auto retry；AgentWechat/Legacy account capability 的 `file=true/false` 差异。

Runtime 22 个测试包含 Fake Docker Engine 双账号生命周期：create/start/inspect/stop/restart/remove-preserve/remove-purge/image-recreate/labels/volumes/token isolation，并验证操作 A 不会停止、删除或清理 B 的 container/volume；同时覆盖 child 无 `PortBindings`、Desktop Gateway token 隐藏、双账号 session 解析隔离、两层 health、完整 `/api/ws/login` 事件流和 DB credential 登录时序。

EFB 19 个测试包含混合 Provider 回归：AgentWechat 目标账号允许 file，Legacy 目标账号仍在 Core queue 前 fail-closed。

### 环境级验证边界

本地 Windows 工作区没有 Docker CLI，因此本会话没有在本机实际启动 `agent-wechat` child container。尝试通过 `ssh -o BatchMode=yes unraid` 做只读 Docker 版本检查时，当前代码执行沙箱返回 SSH `255` 且没有 stderr；随后检查内置 SSH 连接器，其独立配置中也没有 host/user profile。因此本会话没有在 NAS 上替换、重启或删除任何正在运行的微信实例/volume，也没有为了测试去修改 SSH 配置。

这意味着：代码、配置、接口和自动测试已完成，但 AgentWechat 仍标记为 **增强模式（Beta）**。真实 NAS acceptance 继续交给原 B 会话；应使用单独测试账号确认 Docker internal `:6174`、Host Desktop Gateway、HTTP/WebSocket noVNC、上游登录 QR、文本/图片/文件真实发送，以及 `/data`/`/home/wechat` 重建持久化符合当前主机环境。本会话没有进行任何真实微信发送。

