# WebUI 视觉重构 — 执行计划书（交接给实现 Agent）

来源任务书：`docs/WEBUI_VISUAL_REDESIGN_TASKBOOK.md`
设计说明书：`work/console/docs/WEBUI_DESIGN_V2.md`
设计概念画板：`work/console/design_v2/concepts/concepts.html`
日期：2026-09-02

---

## 0. 交接结论

**设计概念已定稿，不再重新设计。** Phase A（审计）、Phase B（视觉概念）、Phase C（设计系统）已完成并落盘。
你的任务是 **Phase D（实现）→ Phase E（浏览器 QA）→ Phase F（保真 QA）→ 交付物**。

定稿意味着以下决定不得再变更：

| 决定 | 内容 |
|---|---|
| 方向 | 方向 A「清爽列表」。禁止回到卡片矩阵 / 指标条 / 深色 DevOps 风格 |
| 技术栈 | Python stdlib HTTP + HTML + CSS + 原生 ES Modules。**不引入任何依赖、不引入构建步骤、不迁移框架** |
| 一级导航 | 首页 / 微信 / 消息 / 收藏 / 自动化 / 设置（六项，顺序固定） |
| 主题 | **默认跟随系统**（`prefers-color-scheme`），可手动覆盖为浅色 / 深色。浅色是设计基准 |
| 屏幕自适应 | 字号、gutter、导航宽、内容宽全部 `clamp()` 流体；控件热区按 `pointer: coarse` 放大；高度用 `dvh` |
| 容器模型 | 开放 section + 单层 `.surface`。禁止 card 套 card |
| 登录弹窗 | 微信窗口画面是唯一视觉焦点，`aspect-ratio: 3/4`，`object-fit: contain`，不裁切；底板在两种主题下都保持白色 |
| 设计 tokens | 已冻结在 `static/css/tokens.css`，只允许新增、不允许改动既有值 |

如果实现中发现设计稿某处无法落地，**先记录，再在 Completion Report 的「intentional deviations」里写明原因**，不要静默改设计。

---

## 1. 当前进度快照

### 1.1 已完成（不要重写）

```text
work/console/design_v2/audit/
├─ baseline-desktop-overview.png      改造前桌面总览
├─ baseline-desktop-accounts.png      改造前桌面账号页
└─ baseline-mobile-accounts.png       改造前 390×844

work/console/design_v2/concepts/
├─ concepts.html                      24 个画板，用 #anchor 打开；?theme=dark 强制深色
├─ wechat-login-window.svg            登录窗口占位（概念稿专用）
├─ wechat-attention-window.svg        安全验证窗口占位（概念稿专用）
└─ *.png                              24 张概念截图（Phase F 对比基准）

work/console/design_v2/qa/
└─ contrast_audit.py                  调色板 WCAG 审计，低于 AA 即非 0 退出

work/console/docs/WEBUI_DESIGN_V2.md  设计说明书（主题模型/tokens/IA/组件/响应式/登录/capability/诊断/对比度）

work/console/wechat_console/static/css/
├─ tokens.css        颜色·间距·圆角·流体字号·动效·深色覆盖·pointer/contrast 偏好
├─ base.css          元素重置·排版工具类·prefers-reduced-motion
├─ layout.css        app shell·导航·断点阶梯·split·settings·tabbar
└─ components.css    按钮·状态·行·表单·dialog/drawer/sheet·登录·消息·收藏·诊断

work/console/wechat_console/static/js/
├─ theme-boot.js     首屏前解析主题（经典脚本，非 module）+ window.__wechatHubTheme
├─ icons.js          stroke-only 图标 sprite（24px 网格 / 1.7px / round）
├─ api.js            唯一 fetch 边界 + ApiError
├─ format.js         时间·数字·字节·HTML 转义·头像首字
└─ capabilities.js   账号能力派生 + Provider 文案
```

概念画板锚点清单（Phase F 必须逐屏对比）：

```text
#system  #dir-a  #dir-b  #home  #accounts  #accounts-empty  #add-account
#login-waiting  #login-confirm  #login-attention  #login-success
#messages  #send-uncertain  #saved  #automation  #settings  #diagnostics
#core-offline  #m-home  #m-accounts  #m-login
#dark-accounts  #dark-login  #dark-system        ← 加 ?theme=dark
```

### 1.2 未完成（你要做的）

```text
static/index.html                 重写（语义骨架 + dialog）
static/styles.css                 改成 @import 四个 css 分片（保持旧入口可用）
static/app.js                     从 895 行单体拆成入口（路由 + 装配 + 生命周期）
static/js/state.js                应用状态 + 订阅
static/js/router.js               hash 路由
static/js/account-view-model.js   后端状态 → 用户文案 / 主操作
static/js/components/*.js         dialog toast menu status login-flow detail-drawer account-row
static/js/views/*.js             home accounts messages saved automation settings
```

---

## 2. 事实基线（禁止臆造，按此实现）

所有状态判定必须来自后端真实字段。以下是从代码里核实过的事实。

### 2.1 账号状态（Core `_apply_runtime_status`，`work/core/core/app.py:277`）

Core `account.state` 可能取值：`stopped` / `degraded` / `online` / `login_required` / `starting` / `offline` / `error`。

`degraded` 只在 `runtime_provider == "agent_wechat"` 且 `agent_server_healthy is False` 时出现。

### 2.2 登录状态（Core `runtime_login_status`，`work/core/core/app.py:311`）

返回字段：`state` / `core_state` / `running` / `container_running` / `agent_server_healthy` /
`runtime_health` / `snapshot_available` / `auth_status` / `logged_in_user` / `window_title` /
`window_count` / `login_flow_state` / `login_flow_status` / `login_flow_error` / `display_name`。

`state` 取值只有五个：`attention` / `online` / `stopped` / `starting` / `waiting`。

`login_flow_state` 由 Runtime FSM 写入（`work/runtime/root/scripts/wechat/agent_wechat_runtime.py`）：
`idle` / `starting` / `authenticating` / `waiting_for_scan` / `phone_confirm` / `logged_in` / `timeout` / `error`。

**`phone_confirm` 是真实存在的**（`agent_wechat_runtime.py:845`），所以「已扫描二维码，请在手机确认」这一屏可以实现，
但必须以 `login_flow_state === "phone_confirm"` 为唯一条件，不允许前端猜测。

Legacy Provider 走 `wechat_runtime_control.py:54`，没有 `login_flow_state`，只有 `snapshot_available`
（= `running && 存在窗口`）。因此 Legacy 只会经历 准备中 → 等待扫码 → 成功。

### 2.3 发送状态（Core outbox）

真实状态机：`accepted` → `queued` → `sending` → `submitted` → `sent`，异常分支 `failed` / `uncertain`。

- `submitted`：Sender/FSM 返回成功，但 Core 尚未在微信 DB 观察到唯一 echo（`delivery_certainty=pending_confirmation`）。
- `sent`：已观察到 echo（`echo_message_id` 非空，`delivery_certainty=confirmed`）。
- `uncertain`：终态，`delivery_certainty=unknown`，`automatic_retry=false`。两种来源：
  AgentWechat HTTP 超时；`expire_submitted_sends()` 确认窗口超时（`work/core/core/store.py:1133`）。

Console 侧投影：`GET /api/sends/<send_id>` 返回 `status` / `delivery_certainty` / `automatic_retry` /
`echo_message_id` / `error` / `details`。**`submitted` 必须单独有文案，不能合并进「已发送」。**

### 2.4 Capability

账号级：`account.runtime.sender_capabilities = {text,image,file,native_reply,media_caption,max_mentions,echo_confirmation,verified_chat_target,driver}`。

- `agent_wechat`：text/image/file 全 true。
- `legacy`：text/image/file 全 false（`work/core/core/registry.py:18`）。

Core 顶层 `health.sender_capabilities` 是 Legacy-safe 保守值，**只作为旧 Core 无账号 capability 时的回退**。
已实现在 `js/capabilities.js`，直接用它，不要另写判断。

### 2.5 Console HTTP 接口（不需要新增，全部已存在）

```text
GET    /api/status                                   Core+账号+runtime_management+integrations+sync
POST   /api/events/sync
GET    /api/runtime/accounts
POST   /api/runtime/accounts                         {account_id,display_name,display,runtime_provider,autostart,start}
POST   /api/runtime/accounts/<id>/{start,stop,restart}
DELETE /api/runtime/accounts/<id>                    默认 preserve（不要带 purge_data）
POST   /api/runtime/accounts/<id>/login              启动登录会话
GET    /api/runtime/accounts/<id>/login              登录状态
GET    /api/runtime/accounts/<id>/login/snapshot      PNG，no-store
GET    /api/runtime/accounts/<id>/desktop            {runtime_provider,scheme,port,path}
GET    /api/chats?account_id=&query=
GET    /api/messages?account_id=&chat_id=&query=&type=&limit=
GET    /api/media/<media_id>?account_id=
POST   /api/send/text                                Idempotency-Key 头
GET    /api/sends/<send_id>
GET/POST/DELETE /api/saved ...  /api/saved/<id>/archive  /api/saved-media/<id>
GET    /api/logs?limit=&level=&category=&query=
```

**不允许修改任何后端 API。** 若确实缺字段，先记录问题，用现有接口绕过，只有阻塞核心流程时才提最小变更。

### 2.6 静态资源已验证可用

`app.py:_serve_static` 支持子目录，已实测：

```text
GET /css/tokens.css  → 200 text/css        Cache-Control: no-cache
GET /js/icons.js     → 200 text/javascript Cache-Control: no-cache
GET /css/nope.css    → 404
```

ES Modules 可直接用，无需改后端。

### 2.7 主题：已实现的部分与你要接上的部分

`static/js/theme-boot.js` 已写好，**不要重写**。它做三件事：

1. 读 `localStorage["wechat-hub.theme"]`（`system` | `light` | `dark`，默认 `system`）；
2. 解析成 `light` / `dark` 并写到 `<html data-theme>`，同时写 `data-theme-preference`；
3. 偏好为 `system` 时监听 `matchMedia("(prefers-color-scheme: dark)")` 的 `change`，系统切换即时跟随。

对外暴露 `window.__wechatHubTheme`：

```js
window.__wechatHubTheme.preference   // "system" | "light" | "dark"
window.__wechatHubTheme.resolved     // "light" | "dark"
window.__wechatHubTheme.set("dark")  // 持久化 + 应用 + 派发 wechat-hub:themechange
```

你要做的：

- `index.html` 的 `<head>` 里以 **同步经典脚本**引入：`<script src="/js/theme-boot.js"></script>`。
  **不要**加 `defer`/`type="module"`，也不要挪到 `<body>` 末尾 —— 否则深色环境首屏会闪白。
  顺序：`theme-boot.js` → `styles.css` → `<script type="module" src="/app.js">`。
- 设置页「外观」三选项（跟随系统 / 浅色 / 深色）调 `window.__wechatHubTheme.set(...)`，
  当前值读 `.preference`。
- 需要在 JS 里响应主题变化时监听 `window` 上的 `wechat-hub:themechange`。

CSS 侧已完成：深色只有 `:root[data-theme="dark"]` 一处覆盖，组件样式不分叉。
`prefers-contrast: more`、`pointer: coarse`、`prefers-reduced-motion` 三个偏好也已接好。

---

## 3. Phase D 实现分解

按顺序做，**每完成一项立刻浏览器截图检查**，不要攒到最后。

### D1 — App Shell + 导航

产出：`index.html`、`styles.css`、`js/router.js`、`js/state.js`、`app.js`。

- `index.html`：`<div class="app">` + `<nav class="nav">` + `<main class="content">` + 6 个 `<section class="page" hidden>` +
  `<nav class="tabbar">` + `<div class="nav-scrim">` + `<div class="toast-stack" role="status">` + 6 个 `<dialog>`。
- `<head>` 顺序：`<script src="/js/theme-boot.js">`（同步，见 §2.7）→ `<link rel="stylesheet" href="/styles.css">`；
  `styles.css` 内 `@import` 四个分片（旧入口保持有效）。
- `<script type="module" src="/app.js">` 放 `<body>` 末尾或加 `defer`。
- 路由：hash `#/home` `#/accounts` `#/messages` `#/saved` `#/automation` `#/settings`（`#/settings/advanced` 为诊断子页）。
- **向后兼容**：旧链接 `?view=overview|accounts|chat|saved|services|agent|logs` 必须映射到
  `home|accounts|messages|saved|settings/advanced|automation|settings/advanced`。
- 导航项：图标 + 文案 + 可选红点数字（仅「微信」在有需要处理的账号时显示）。`aria-current="page"`。
- 侧栏底部 `.nav-core-state`：Core 正常显示「运行正常」，异常 `data-tone="bad"` 显示「无法连接 WeChat Hub」。
- ≤1023px：顶栏汉堡打开抽屉，`body.nav-open`，点 scrim / ESC 关闭。
- ≤767px：底部 tabbar 五项（首页/微信/消息/收藏/更多），「更多」进设置。

`state.js` 形态：

```js
export const state = { status, accounts, runtimeAccounts, runtimeManagement, coreOk,
  activeAccountId, chats, selectedChatId, messages, saved, selectedSavedId, logs, sendResult };
export function setState(patch) // 浅合并 + 通知订阅者
export function subscribe(fn)
```

### D2 — 账号视图模型

产出：`js/account-view-model.js`。**这是全局唯一的状态→文案映射，任何视图不得自行解释后端枚举。**

```js
export function accountViewModel(runtimeAccount, coreAccount, { runtimeManagement, coreOk })
// → { accountId, name, initial, tone, statusText, hint,
//     primaryAction: {id,label,variant}, menu: [...], capabilities, advanced }
```

映射表（`tone` 用于头像与 `.status[data-tone]`）：

| 条件 | statusText | tone | primaryAction |
|---|---|---|---|
| `agent_server_healthy === false` | 微信服务异常 | bad | 重新启动 |
| `core.state === "online"` | 已连接 | good | 打开微信 |
| running && `login_flow_state` ∈ {error,timeout} | 登录窗口暂时不可用 | warn | 重新登录 |
| running && (`core.state === "login_required"` \|\| snapshot 可用) | 等待登录 | warn | 扫码登录 |
| running && 其他 | 正在启动 | busy | （disabled） |
| !running | 已停止 | idle | 启动 |

`menu` 固定顺序：重新启动 / 停止运行 / 重新登录 / 高级信息 / ——— / 移除微信（danger）。
运行中不显示「启动」，停止时不显示「停止运行」「重新登录」。
Legacy default account（`legacy === true`）的「移除微信」必须 disabled 并给出原因。

`hint` 取值示例：`今天 09:21 登录`（用 `format.js:fmtLastActivity`）、`微信已启动，等待扫码`、
`微信进程仍在运行，控制服务暂时不可用`、`自动启动已关闭`。

### D3 — 通用组件

产出：`js/components/`。

| 文件 | 契约 |
|---|---|
| `dialog.js` | `openDialog(el)` / `closeDialog(el)`；ESC 关闭非危险弹窗；危险弹窗 `preventDefault()` cancel；关闭时清理定时器回调 |
| `confirm.js` | `confirmAction({title, text, confirmLabel, tone})` → Promise\<boolean\>。**替换所有 `confirm()` / `alert()`** |
| `toast.js` | `toast({title, text, tone})`，4s 自动消失，容器 `role="status"` |
| `menu.js` | 桌面 popover / ≤767px bottom sheet，同一份 `items` 数据；点外部或 ESC 关闭；返回焦点 |
| `status.js` | `statusMarkup(tone, text)` → `.status` + `.status-glyph`（形状+文案+颜色三重编码） |
| `account-row.js` | 由 view model 渲染 `.row`；≤767px 加 `data-stack="true"`；icon-only 按钮 `aria-label="<名称>的更多操作"` |
| `detail-drawer.js` | 账号高级信息 `<dialog class="drawer">`，`.kv` 列表 |
| `login-flow.js` | 登录弹窗全部逻辑，见 D5 |

### D4 — 首页 + 微信页

产出：`js/views/home.js`、`js/views/accounts.js`。

首页三段（对照 `#home`）：
1. **需要处理** — 仅在存在非 online 且非正常启动中的账号时出现；`.banner` + 一个动作按钮。
2. **我的微信** — 每账号一行，右侧「全部管理 ›」跳 `#/accounts`。
3. **最近消息** — 取投影里最近 5 条，头像 + 会话名 + 账号名 + 单行摘要 + 时间；右侧「打开消息 ›」。

空状态（对照 `#accounts-empty` / `#core-offline`）：
- 无账号：`还没有添加微信` / `添加第一个微信后，可以在这里扫码登录并管理消息。` / `[添加微信]`
- Core 离线：`WeChat Hub 暂时无法连接` / `账号和消息可能暂时无法更新。已经同步过的消息和收藏仍然可以查看。` / `[重新连接]`
- Runtime 控制通道离线：`微信管理暂时不可用` / `已存在的消息仍然可以查看。` / `[重试]`（control.sock 等细节只进诊断页）

微信页（对照 `#accounts`）：页头右侧「刷新」（次要）+「添加微信」（主要）；列表行 + `···`；
Runtime 不可用时 disable 添加/刷新并显示 banner。删除后行做 `.is-removing` collapse 动画再移除。

### D5 — 添加向导 + 登录弹窗（最高优先级）

产出：`js/views/accounts.js` 内的向导 + `js/components/login-flow.js`。

**添加向导**（对照 `#add-account`）：
- 主表单只有一个输入：`给这个微信起一个名字`，hint `只用于在 WeChat Hub 里区分不同微信，随时可以改。`
- info banner：`创建后会自动启动并进入扫码登录` / `默认使用推荐模式（Beta），每个微信独立运行，支持更多操作。`
- `<details class="disclosure">高级选项`：账号 ID（留空自动生成）、运行模式（`推荐模式（Beta）— AgentWechat` / `兼容模式 — Legacy`）、
  Legacy Display（仅 Legacy 可用）、自动启动、创建后立即启动并登录。
- account_id 自动生成规则：从名称转 slug，非 `[A-Za-z0-9_.-]` 去除；为空则 `wechat-<n>`；与现有 id 冲突则加数字后缀。
  必须匹配 `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`。
- 提交后按钮立即 disabled + spinner，防重复创建；失败**保留输入**，错误显示在表单内（`.field-error` + `aria-describedby`），不用 `alert()`。
- 成功且 `start=true` → 关闭向导 → 直接打开登录弹窗，用户不需要再去找账号行。

**登录弹窗八态**（对照 `#login-waiting` `#login-confirm` `#login-attention` `#login-success`）：

| 后端条件 | 标题 / 正文 | 画面区 | 底部按钮 |
|---|---|---|---|
| `state=starting` 或 `!snapshot_available` | `正在准备<名称>` / `正在启动微信并准备登录窗口…` | 骨架 + indeterminate | 刷新画面 · 打开完整微信 |
| `state=waiting` | `请使用手机微信扫描窗口中的二维码。` | snapshot | 刷新画面 · 打开完整微信 |
| `login_flow_state=phone_confirm` | `已扫描二维码` / `请在手机微信中确认登录。` | 勾选图标 + indeterminate | 刷新画面 · 打开完整微信 |
| `state=attention` | banner `微信需要额外确认` / `请在下面的微信窗口中完成安全验证。` | snapshot（不裁切） | 刷新画面 · **打开完整微信（主）** |
| `state=online` | `<名称>已连接` / `消息正在开始同步。以后 WeChat Hub 会自动启动这个微信。` | 成功勾选 | 完成（主） |
| `state=stopped` | `这个微信当前已停止` | 占位 | 启动微信（主） |
| `login_flow_state` ∈ {error,timeout} 或 `login_flow_error` | `登录窗口暂时不可用` / `微信可能仍在启动，或者登录流程已经超时。` | 占位 | 重新尝试 · 打开完整微信 |
| `agent_server_healthy=false` | `微信服务异常` / `微信进程仍在运行，但控制服务暂时不可用。` | 占位 | 重新启动 · 查看详情 |

硬性要求：
- 固定文案 `登录画面只在当前会话中临时显示，不会保存。`
- 3 秒轮询；弹窗关闭 / 成功 / 终态错误 **立即** `clearInterval`。
- snapshot 每次带 `?t=<ts>`（用 `api.loginSnapshotUrl`）；**禁止** localStorage / IndexedDB / Cache API。
- `img.onerror` → 占位 + `微信窗口正在准备，稍后会自动刷新。`；`img.onload` → 淡入。
- 状态区 `aria-live="polite"`；`<img alt="微信登录窗口，使用手机微信扫描其中的二维码">`。
- 不出现 token / Gateway path / upstream host / port。
- ≤767px 顶部 info banner：`建议在电脑或平板上打开此页面` / `再使用手机微信扫码会更方便。`（对照 `#m-login`）
- 「打开完整微信」：`GET /desktop` → `runtime_provider !== "agent_wechat"` 用 `status.desktop_url` 回退；
  否则校验 `1 ≤ port ≤ 65535` 且 `path.startsWith("/")`，`window.open(url, "_blank", "noopener,noreferrer")`；
  不就绪时 toast `微信桌面入口尚未就绪，请稍后重试。`

### D6 — 消息页

产出：`js/views/messages.js`。对照 `#messages` / `#send-uncertain`。

- 页头右侧 Account Switcher（`工作微信 ›`），不是全局工程下拉框。
- 桌面 `.split` 双栏：左搜索 + 会话列表，右工具栏（类型筛选 + 搜索）+ thread + composer。
- ≤767px：`.split[data-pane="list"|"detail"]` 切页，详情页顶部返回按钮。
- 气泡：`.bubble > .bubble-text`（`white-space: pre-wrap`）+ 可选 `.bubble-attachment`；outgoing 右对齐绿底；
  撤回显示 `[消息已撤回/移除]` 斜体灰。hover/focus 才出现「收藏」按钮。
- composer 按 capability：`canSendImage` / `canSendFile` 决定图片/文件按钮是否渲染；
  `canSendText === false` → 输入与发送 disabled + `.composer-note` 显示 `sendDisabledReason`。
- 发送：`Idempotency-Key` = `client_request_id`，成功后 `watchSendStatus` 轮询 `/api/sends/<id>`（首次 500ms，之后 2s，上限 90 次）。

发送结果文案（`.send-result[data-state]`）：

| status | 标题 | 说明 |
|---|---|---|
| accepted/queued | 正在排队发送… | — |
| sending | 发送中… | — |
| submitted | 已提交，等待微信确认 | 微信已接收提交，正在确认送达结果。 |
| sent | 已确认发送 | — |
| failed | 发送失败 | 微信没有接收这条消息，可以重新发送。 `[重新发送]` |
| uncertain | 发送结果未知 | 微信可能已经收到这条消息。为避免重复发送，系统没有自动重试。 `[查看消息] [仍然重新发送]` |

`uncertain` 用 `--warning` 系，**不得**用红色失败样式。「仍然重新发送」必须走 `confirmAction()` 二次确认，
确认文案：`这条消息可能已经发出。再发一次可能让对方收到两条相同消息。`

### D7 — 收藏页

产出：`js/views/saved.js`。对照 `#saved`。

- 标题统一「收藏」，底层数据结构与接口不变。
- 分类 chips：全部 / 图片 / 文件 / 链接 / 带注释 —— **前端按现有 snapshot 字段派生**：
  `type==="image"` → 图片；`type` ∈ {file,video,audio} 或有 `filename` → 文件；
  text 内含 `http(s)://` → 链接；`note` 非空 → 带注释。不要臆造后端分类字段。
- 双栏：左搜索 + 列表；右 snapshot + 标题/标签/注释 + 保存 + 重试附件归档 + 附件归档列表。
- 删除走 `confirmAction()`。空状态：`还没有收藏` / `在消息中点击「收藏」，重要内容会出现在这里。`

### D8 — 自动化页

产出：`js/views/automation.js`。对照 `#automation`。

- 未配置/不可用时 **不显示 probe 报错**，显示功能引导：
  `启用自动化功能` / `启动 WeChat Agent 后，可以创建自动回复、关键词关注和定时任务。`
- 下方「启用后可以做什么」四行：自动回复 / 消息关注 / 定时任务 / AI 总结 / AI 助手。
  这是能力说明，不是已实现功能，措辞必须是「启用后可以…」。
- Agent 在线时显示在线状态 pill；**不要伪造任何 Agent 数据或列表**。

### D9 — 设置 + 高级诊断

产出：`js/views/settings.js`。对照 `#settings` / `#diagnostics`。

- 左导航：常规 / 微信 / Telegram 集成 / AI 助手 / 数据与存储 / 高级与诊断。
- 常规：
  - **外观**：三选项「跟随系统 / 浅色 / 深色」，调 `window.__wechatHubTheme.set(...)`，
    当前值读 `.preference`（见 §2.7）。不要自己写 localStorage 或 `data-theme`。
  - 自动刷新开关（用 `.switch`，不要用裸 checkbox）。
- 微信：默认运行模式说明 + Beta 提示（保留）。
- Telegram 集成：EFB 对外一律叫「Telegram 集成」，未配置显示 `未启用` pill + 一句说明。
- 数据与存储：Console 归档说明（不显示 DB 路径，路径进诊断页）。
- 高级与诊断三块：
  1. 服务状态：wechat-core（必需·在线/异常 + URL + contract）、wechat-agent、efb-multi（可选·未配置 = 正常）
  2. 账号运行详情 `.kv`：account_id / runtime_provider / runtime_health / agent_server_healthy /
     PID / UID / Display / HOME / image / autostart / sender capability / 窗口数 / registry 热加载 / 事件游标 / 最近同步
  3. Console 日志：等级下拉 + 搜索 + `.log-row`

### D10 — 屏幕自适应收尾

CSS 侧的流体 token 与断点阶梯已经写好，这一步是**逐屏验证 + 修实现层的破版**。

必测视口（每个都跑浅色 + 深色）：

```text
1920×1080   宽屏 / 4K 缩放
1440×900    常见桌面
1280×800    小型笔记本
1024×768    平板横向 / 小屏桌面
768×1024    平板竖向
390×844     手机
360×780     窄手机（最小支持宽度）
```

另外必测：
- **系统主题切换**：偏好设为「跟随系统」，用 devtools 切 `prefers-color-scheme`，
  页面应**无需刷新**即时变色；然后手动选「浅色」，再切系统，页面应保持浅色。
- **首屏无闪白**：系统为深色时硬刷新，不应看到白底闪一下。
- **矮视口**：780×420 横屏手机，登录弹窗二维码不需要滚动即可看到。
- `pointer: coarse` 模拟（devtools 设备模式）下控件热区变大。
- `prefers-contrast: more` 下边界与次要文字加深，主按钮白字仍清晰。
- `prefers-reduced-motion` 下无动画。

检查项：无横向滚动、无 11px 以下操作文字、触摸目标 ≥44px、
长中文账号名不破版、`···` 打开 bottom sheet、登录弹窗不溢出、tabbar 不遮内容。

---

## 4. 必须逐字使用的文案

普通层禁止出现：`Core` `Durable events` `Console projection` `Runtime Provider` `Agent probe`
`EFB probe` `Registry hot reload` `X11 Display` `AT-SPI` `outbox` `PID` `UID` `event cursor` `Docker`。
这些只允许出现在「设置 → 高级与诊断」和账号高级信息抽屉。

Provider 文案两层：

```text
普通层：推荐模式（Beta）   兼容模式
高级层：AgentWechat        Legacy
```

**真实 NAS acceptance 未完成前，`推荐模式（Beta）` 的 Beta 字样不得移除。**

移除账号确认文案（默认 preserve，绝不默认 purge）：

```text
移除微信「<名称>」？
AgentWechat：上游容器会删除，但账号数据会保留，重新添加同一账号可继续使用。
Legacy：微信进程会停止，但登录数据会保留。
```

---

## 5. 测试与必须调整的断言（关键坑，先读）

现有 `work/console/wechat_console/tests/test_console.py` 有三处**基于旧文件形态的字符串断言**，
重构后必然失败。必须**改断言指向新位置、保持同等覆盖**，不得删除测试或降低覆盖：

| 位置 | 现断言 | 处理方式 |
|---|---|---|
| `test_runtime_management_status_and_lifecycle` L89 | `index.html` 含 `AgentWechat 增强模式（Beta` | 改为：普通层文案 `推荐模式（Beta）` 出现在 `index.html` 或 `js/capabilities.js`，**且**技术名 `AgentWechat` 出现在 `js/capabilities.js`。两者都断言，保住「Beta 不丢 + 技术名仍可见」这个真正意图 |
| 同上 L90-92 | `app.js` 含 `startLoginSession` / `` /login`, { `` | 改为断言 `js/components/login-flow.js` 含 `startLogin`，且 `js/api.js` 含 `/login` POST 调用 |
| `test_send_projection_...` L306-308 | `app.js` 含 `已提交，等待微信确认` / `已确认发送` | 改为断言承载发送文案的新模块（建议 `js/views/messages.js`）含这两个字符串 |

改动这三处**必须在 Completion Report 里明确写出**「改了哪个断言、为什么、覆盖是否等价」。

必跑测试：

```bash
# Console（8+ 个用例）
cd work/console && python -m unittest discover -s wechat_console/tests -t . -v

# 调色板对比度审计（改了任何颜色 token 就必须跑）
cd work/console && python design_v2/qa/contrast_audit.py

# Mock Core
cd stack/mock-core && python -m unittest discover -s tests -t . -v

# Stack topology（若动了 compose / static 路径）
cd stack && python -m unittest tests.test_stack_wiring -v

# JS 语法 / 模块导入（无 node 时至少做 import 图检查）
node --check static/app.js   # 若环境有 node
```

另外自查：所有 `.js` 用 `type="module"` 加载（**`theme-boot.js` 例外，必须是同步经典脚本**）；
`git diff --check` 无空白错误；无 `console.log` 遗留；无 `alert()` / `confirm()` 残留。

---

## 6. Phase E 浏览器 QA

启动方式（已验证可用）：

```bash
# 1. Mock Core
python stack/mock-core/app.py --host 127.0.0.1 --port 8099

# 2. Console（指向 Mock Core，用独立 runtime dir 避免污染）
cd work/console
WECHAT_CONSOLE_RUNTIME_DIR=../../.tmp/ui-qa/console-v2 \
  python -m wechat_console.app --host 127.0.0.1 --port 8078 --core-url http://127.0.0.1:8099

# 3. 概念稿静态服务（Phase F 并排对比用）
cd work/console && python -m http.server 8090 --bind 127.0.0.1
```

必测视口：`1920×1080` `1440×900` `1280×800` `1024×768` `768×1024` `390×844` `360×780`，
**每个视口都要跑浅色与深色两轮**。

必测状态：Hover / Focus-visible / 键盘 Tab 全流程 / Dialog focus trap / ESC / Drawer / Sheet /
空状态 / Loading / Error / 八个登录态 / 长中文文本 / 超长账号名 / ≥3 账号 /
AgentWechat + Legacy 混合 / Agent 未启用 / EFB 未启用 / Core 不可用（停掉 mock core）/
系统主题实时切换 / 深色首屏无闪白 / `prefers-contrast: more` / `prefers-reduced-motion`。

**关于 Mock Core 无法产生的登录态**（`phone_confirm` / `attention` / `error` / `timeout` / `degraded`）：

优先方案（零后端改动）：建 `work/console/design_v2/qa/login-states.html`，
`import` 真实的 `js/components/login-flow.js` 渲染函数，喂 8 份 fixture payload，一屏出全部状态。
这样用的是真 CSS + 真渲染代码，不伪造后端。

次选方案：给 `stack/mock-core/app.py` 加一个仅 mock 用的状态注入端点。允许，但必须
(a) 只改 mock-core（不碰 Core/Runtime/Console），(b) 不破坏现有 mock-core 与 stack 测试，
(c) 在 Completion Report 里声明。

混合 Provider QA：Mock Core 两个种子账号都是 `legacy` 且 `runtime` 里**没有** `sender_capabilities`，
会走「旧 Core 回退」路径（顶层 capability 全 true）。要测真实差异，请通过
`POST /api/runtime/accounts {runtime_provider: "agent_wechat"}` 新建一个账号（mock 会写入 per-account capability），
和 legacy 账号并列对比。

截图统一放 `work/console/design_v2/qa/`。

---

## 7. Phase F 保真 QA

把 `design_v2/concepts/*.png` 与 `design_v2/qa/*.png` **并排**逐项检查，最少 12 项：

```text
 1. Layout（栏宽、留白、对齐）        7. Account row（头像/名称/pill/状态/主操作/···）
 2. Typography（字号/行高/字重层级）  8. Mobile collapse（切页、tabbar、整行按钮）
 3. Color（语义色用法、绿色克制）      9. Icon style（stroke-only、1.7px、同一网格）
 4. Spacing（间距刻度一致）          10. Visible copy（逐字对照第 4 节）
 5. Component anatomy                11. 深色对照（#dark-accounts / #dark-login / #dark-system）
 6. Login Dialog（画面比例、焦点）    12. 宽屏与窄屏（1920 / 360 不破版、不像放大的手机版）
```

发现偏差就改，**不允许写进「已知问题」了事**。任何专业设计 Review 会指出的明显问题都要修完。

---

## 8. 交付物清单

```text
A. 视觉概念     work/console/design_v2/{audit,concepts}/            已完成
B. 前端实现     work/console/wechat_console/static/                 待完成
C. 设计说明     work/console/docs/WEBUI_DESIGN_V2.md                已完成（实现后校订）
D. QA 截图      work/console/design_v2/qa/                          待完成
                至少：桌面首页/微信/添加微信/扫码登录/消息/设置 + 手机首页/手机微信
                另加：深色账号页 + 深色登录 + 1920 宽屏 + 360 窄屏
E. 完成报告     work/console/WEBUI_VISUAL_REDESIGN_COMPLETION_REPORT.md   待完成
```

Completion Report 必答 14 项（任务书 §24.E）：

1. 修改了哪些文件 2. 设计概念路径 3. 最终截图路径 4. 浏览器验证方式
5. 设计稿 vs 实现 fidelity 检查结果（含深色与宽/窄屏）6. Desktop / Mobile viewport 清单
7. 功能测试结果（含第 5 节三处断言调整 + `contrast_audit.py` 结果）
8. 保留的 intentional deviations（至少含 `--text-secondary` 加深、白字压品牌绿两项）
9. 未完成项 10. 是否修改后端 API（预期：否）
11. 是否引入新依赖（预期：否）12. 是否修改容器/build（预期：否）
13. 是否进行真实扫码登录验证（本地无 Docker，预期：否，需如实说明）
14. AgentWechat Beta 是否保留（预期：是）

额外必答（本轮新增要求）：

15. 主题：是否实现「跟随系统 + 手动覆盖」，系统切换是否无需刷新，深色首屏是否无闪白
16. 屏幕自适应：实测视口清单，以及 1920 / 360 两端是否有破版

---

## 9. 红线

- 不重构 Core / Runtime 架构，不改 Sender 实现，不改 AgentWechat upstream，不改 EFB 架构，不改 Desktop Gateway 安全模型。
- 不删减现有功能：账号 CRUD/启停/重启、登录全流程、Desktop、消息查看/搜索/类型过滤/发送/附件预览、
  收藏全套（列表/搜索/snapshot/title/tags/note/media archive/retry/delete）、服务状态、日志、
  Core 热加载可见性（放诊断层）。Agent/EFB 缺席时 Console 必须照常可用。
- 不给 Console Docker Socket，不直读 Core SQLite，不发布 AgentWechat `:6174` 到 Host，
  浏览器 URL 不出现 upstream token，登录 snapshot 不做任何持久化缓存。
- 「移除微信」永远 preserve；purge 不提供入口。
- 不引入依赖 / 构建步骤 / Node runtime；不改 `Dockerfile`、`docker-compose.yml`。
- 不臆造数据：无假二维码倒计时、无假 progress 百分比、无假联系人数/在线时长、无后端不存在的 Telegram 字段。
  占位 demo 内容必须明显是 demo。
- 主题相关：不新增第二套深色组件样式（只能覆盖 token）；不给登录画面加 `filter` / `mix-blend-mode`；
  深色下登录底板必须保持白色；不因为深色而改动二维码区域的任何视觉处理。
