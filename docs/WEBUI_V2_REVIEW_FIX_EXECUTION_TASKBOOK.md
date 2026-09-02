# WeChat Hub Console WebUI v2 — 审阅补修执行项目书

> **执行对象**：偏执行型 / 低推理预算 Agent（例如 Gemini 3.7 Flash）  
> **工作目录**：`G:\LLM\WeChat_Hub`  
> **日期**：2026-09-02  
> **任务性质**：已有 WebUI v2 的功能补修、回归测试、浏览器 QA 与完成报告纠偏  
> **不是**：重新设计、重构后端、迁移框架、重新做 Phase A/B/C

---

## 0. 先读这一节：执行规则

本任务已经完成架构与问题定位。**不要重新发散设计，不要自己重做架构判断。**

你只需要按本文 Gate 顺序逐项执行。

### 0.1 强制执行方式

每个 Gate 必须严格使用以下循环：

```text
读本 Gate 指定文件
→ 只修改本 Gate 允许修改的文件
→ 运行本 Gate 的最小测试
→ 失败就修到 PASS
→ 记录修改与测试结果
→ 再进入下一个 Gate
```

**禁止一次性修改所有文件后再测试。**

### 0.2 不允许自行省略

看到以下内容时，不允许因为“看起来已经差不多”而跳过：

- 已存在按钮但没有事件处理；
- 已存在文案但没有真实状态流；
- 静态字符串测试 PASS，但真实交互没有执行；
- 截图看起来正确，但数据源字段实际上不匹配；
- `node --check` PASS，但运行时对象方法缺失；
- Mock 页面可以显示状态，但真实 polling 生命周期没有验证。

### 0.3 任一 Gate 失败时

如果无法在本 Gate 允许范围内解决：

1. **停止进入后续 Gate**；
2. 记录：错误、命令输出、涉及文件、已尝试方案；
3. 不得把失败写成 PASS；
4. 不得为了“让测试通过”删除测试或降低断言。

### 0.4 本轮总目标

修复审阅发现的功能缺陷，使下面这些用户流程真实可用：

```text
收藏列表真实显示
文本发送后可持续跟踪发送结果
图片发送真实可用
文件发送真实可用
自动刷新开关真实生效
登录轮询在正确状态停止
Legacy Desktop fallback 可用
添加微信高级参数完整
危险操作 ESC 行为符合设计契约
普通用户层不泄露工程术语
高级诊断字段完整
Runtime 不可用状态正确门禁
“打开微信”执行与按钮文案一致
```

最终必须重新做浏览器交互 QA，并纠正旧 Completion Report 中不准确的“100%”描述。

---

# 1. 事实基线：不要重新猜

下面内容已经审阅确认，直接以此为事实基线。

## 1.1 当前前端架构正确，禁止推翻

保留：

```text
work/console/wechat_console/static/index.html
work/console/wechat_console/static/app.js
work/console/wechat_console/static/css/*.css
work/console/wechat_console/static/js/*.js
work/console/wechat_console/static/js/components/*.js
work/console/wechat_console/static/js/views/*.js
```

技术栈继续保持：

```text
Python stdlib HTTP
HTML
CSS
原生 ES Modules
```

禁止新增：

```text
React / Vue / Svelte
Vite / Webpack
npm runtime dependency
新的前端构建步骤
第三方 UI 框架
```

## 1.2 当前视觉方向正确，禁止重新设计

保留：

- 六项主导航；
- 清爽列表方向；
- 浅色为设计基准；
- system/light/dark 三档主题；
- CSS tokens；
- 原生 `<dialog>`；
- 移动端 tabbar；
- 3:4 登录窗口；
- 深色主题下登录窗口白底；
- 当前视觉截图风格。

本轮不是视觉翻新。

## 1.3 后端 API 已经存在，不要新造 API

以下 Console HTTP 接口已经存在：

```text
GET  /api/saved
GET  /api/sends/<send_id>
POST /api/send/text
POST /api/send/image
POST /api/send/file
GET  /api/runtime/accounts/<id>/desktop
```

Core `SendMediaRequest` 已支持：

```json
{
  "account_id": "...",
  "chat_id": "...",
  "content_base64": "...",
  "filename": "...",
  "mime_type": "...",
  "caption": "...",
  "client_request_id": "..."
}
```

Core inline media decoded size limit：**20 MiB**。

图片/文件发送前端应直接使用现有 JSON + base64 能力，**不要新增 multipart API**。

## 1.4 已确认的数据字段

Console：

```text
GET /api/saved
```

真实返回：

```json
{
  "items": [ ... ]
}
```

不是：

```json
{
  "saved_messages": [ ... ]
}
```

当前前端这里存在字段错配。

---

# 2. 修改红线

## 2.1 本轮禁止修改

除非本文某 Gate 明确允许，否则不要修改：

```text
work/core/
work/runtime/
work/agent/
work/efb-linux-wechat-slave/
stack/docker-compose.yml
work/console/Dockerfile
任何生产 Dockerfile
任何生产 docker-compose.yml
Desktop Gateway 安全模型
AgentWechat Runtime 实现
Sender Core 实现
```

## 2.2 安全红线

不得：

- 在浏览器 URL 中暴露 upstream token；
- 在 Console JSON 中暴露 upstream token；
- 重新发布 child `:6174` 到 Host；
- 给 Console Docker Socket；
- 在 localStorage / IndexedDB 保存微信登录 snapshot；
- 默认 `purge_data`；
- 为测试删除真实微信账号；
- 为测试强制登出真实在线账号；
- 自动重试 `uncertain` 发送；
- 用 `window.confirm()` / `window.alert()`。

## 2.3 代码风格红线

- 不做无关重构；
- 不改已经冻结的设计 tokens，除非发现明确实现错误；
- 不因为一个函数不好看就整体重写文件；
- 不删除已有兼容逻辑；
- 所有用户可见动态数据进入 `innerHTML` 前继续使用 `escapeHtml/escapeAttr`；
- 新增文件上传逻辑不得把 base64 写入持久存储。

---

# 3. Gate 0 — 建立修改前基线

## 3.1 先运行现有测试

在修改代码之前执行：

```powershell
cd G:\LLM\WeChat_Hub\work\console
python -m unittest discover -s wechat_console/tests -t . -v
python design_v2/qa/contrast_audit.py

cd G:\LLM\WeChat_Hub\stack\mock-core
python -m unittest discover -s tests -t . -v

cd G:\LLM\WeChat_Hub\stack
python -m unittest tests.test_stack_wiring -v
```

如果 Node 可用：

```powershell
cd G:\LLM\WeChat_Hub\work\console\wechat_console\static
node --check app.js
```

并对所有当前前端 JS 继续执行语法检查。

## 3.2 记录基线

记录：

```text
Console tests: X/X
contrast audit: PASS/FAIL
Mock Core: X/X
Stack: X/X
JS syntax: X/X
```

注意：即使全部 PASS，也**不能**据此认为后面的功能缺陷不存在。

### Gate 0 PASS 条件

- 已记录基线；
- 没有修改任何生产代码；
- 明确知道后续测试需要补强真实交互覆盖。

---

# 4. Gate 1 — P0：修复收藏数据字段错配

## 4.1 问题

当前：

```text
app.js
→ api.saved()
→ GET /api/saved
→ 后端返回 {items:[...]}
→ app.js 却读取 saved_messages
→ state.saved 永远可能是 []
```

这会造成数据库中已有收藏，但 UI 仍显示“还没有收藏”。

## 4.2 允许修改

```text
work/console/wechat_console/static/app.js
work/console/wechat_console/tests/test_console.py
```

## 4.3 明确修改要求

在 `loadAllData()` 处理 `savedRes` 的地方：

优先读取：

```js
savedRes.value.items
```

为了兼容可能存在的旧响应，可以保留 fallback：

```js
savedRes.value.items || savedRes.value.saved_messages || []
```

**不要修改 Console 后端把 `items` 改成 `saved_messages`。**

本轮前端适配现有真实接口。

## 4.4 必须新增/调整测试

测试至少证明：

1. `GET /api/saved` 返回 `items`；
2. 前端加载逻辑使用 `items`；
3. 原有收藏 CRUD 测试仍 PASS。

不要只断言页面里有“收藏”两个字。

### Gate 1 PASS 条件

- 有收藏数据时 `state.saved` 不为空；
- 收藏页不再错误进入空状态；
- Console tests PASS。

---

# 5. Gate 2 — P0：补齐 `api.sendStatus()`

## 5.1 问题

当前 `messages.js` 已调用：

```js
api.sendStatus(sendId)
```

但 `static/js/api.js` 没有这个方法。

因此文本消息在 POST 成功后进入发送状态跟踪时会发生运行时错误。

## 5.2 允许修改

```text
work/console/wechat_console/static/js/api.js
work/console/wechat_console/tests/test_console.py
```

## 5.3 明确实现

在 `api` 对象增加：

```js
sendStatus: (sendId) => request(`/api/sends/${enc(sendId)}`),
```

必须继续对 `sendId` 做 `encodeURIComponent`。

不要在 `messages.js` 直接写新的裸 `fetch()`。

所有请求继续经过 `api.js` 唯一 fetch boundary。

## 5.4 测试

增加 HTTP 测试证明：

```text
POST /api/send/text
→ 获得 send_id
→ GET /api/sends/<send_id>
→ 200
→ 返回 status
```

如果 Mock Core 的状态不会自然推进到 `sent`，本 Gate 只要求 endpoint 与前端 API method 存在；完整状态 UI 在最终 Browser QA 使用拦截/fixture 验证。

### Gate 2 PASS 条件

- `api.sendStatus` 存在；
- `/api/sends/<send_id>` HTTP 测试 PASS；
- 不再有 `api.sendStatus is not a function` 风险。

---

# 6. Gate 3 — P1：图片 / 文件发送真正可用

## 6.1 问题

当前 Composer 会根据 capability 显示：

```text
发送图片
发送文件
```

但按钮没有真实事件处理。

这是“可见但不可用”的功能缺陷。

## 6.2 允许修改

```text
work/console/wechat_console/static/js/api.js
work/console/wechat_console/static/js/views/messages.js
work/console/wechat_console/tests/test_console.py
```

禁止修改 Core media API。

## 6.3 `api.js` 增加方法

新增：

```js
sendImage(payload, idempotencyKey)
sendFile(payload, idempotencyKey)
```

目标接口：

```text
POST /api/send/image
POST /api/send/file
```

必须带：

```text
Idempotency-Key
```

与文本发送规则一致。

## 6.4 Composer 增加真实 file input

根据 capability 条件渲染隐藏 input：

图片：

```html
<input type="file" accept="image/*" ...>
```

文件：

```html
<input type="file" ...>
```

按钮点击时触发对应 input `.click()`。

不要使用路径文本框。

## 6.5 文件读取规则

新增一个小型 helper，例如：

```text
readFileAsBase64(file, {imageOnly})
```

使用浏览器原生：

```js
FileReader
reader.readAsDataURL(file)
```

取 Data URL 逗号后的 base64 内容。

不要上传完整 `data:image/png;base64,` 前缀。

发送 payload：

```js
{
  account_id,
  chat_id,
  content_base64,
  filename: file.name,
  mime_type: file.type || "application/octet-stream",
  client_request_id
}
```

图片发送必须检查：

```js
file.type.startsWith("image/")
```

大小检查：

```text
file.size <= 20 * 1024 * 1024
```

超过时前端直接提示：

```text
文件不能超过 20 MB
```

## 6.6 发送状态复用

图片和文件 POST 成功后必须与文本复用同一个：

```text
watchSendStatus(sendId, ...)
```

状态仍然使用：

```text
accepted
queued
sending
submitted
sent
failed
uncertain
```

不得因为是图片/文件就直接显示“已发送”。

## 6.7 失败处理

必须处理：

- FileReader 失败；
- 图片类型错误；
- 超过 20 MiB；
- POST 失败；
- send status 查询失败。

失败时恢复按钮可操作状态。

发送后清空 file input value，保证用户可再次选择同一个文件。

## 6.8 不允许

不要：

- 新增 multipart endpoint；
- 新增后端 upload 临时路径；
- 用本机文件路径传给 Core；
- 把 base64 放进 localStorage；
- 自动重试 `uncertain`。

### Gate 3 PASS 条件

在 AgentWechat capability 为：

```json
{"text":true,"image":true,"file":true}
```

时：

- 图片按钮可以选择图片并发送；
- 文件按钮可以选择文件并发送；
- request 使用已有 `/api/send/image|file`；
- 发送后进入统一状态跟踪；
- Legacy capability false 时仍不渲染对应按钮。

---

# 7. Gate 4 — P1：自动刷新开关真实生效

## 7.1 问题

当前设置页存在：

```text
自动刷新 [switch]
```

但开关没有事件处理。

`app.js` 永远执行：

```text
30 秒轮询
页面回到前台刷新
```

因此关闭开关完全无效。

## 7.2 允许修改

```text
work/console/wechat_console/static/js/state.js
work/console/wechat_console/static/app.js
work/console/wechat_console/static/js/views/settings.js
```

## 7.3 明确实现

在 `state.js` 增加：

```js
autoRefresh: true
```

设置页 switch：

```text
checked = state.autoRefresh !== false
```

切换时通过 `setState()` 更新。

`app.js` 的 30s timer 改为：

```text
只有 state.autoRefresh !== false 时执行 loadAllData()
```

`visibilitychange` 同样受此开关控制。

## 7.4 本轮不要增加持久化复杂度

执行计划没有要求自动刷新偏好跨浏览器重启持久化。

本 Gate 不要再新增第二个 localStorage preference。

主题仍是唯一已经定义的本地持久化偏好。

### Gate 4 PASS 条件

- 默认自动刷新开启；
- 关闭后 30s 定时刷新不执行；
- 关闭后切回浏览器前台不自动刷新；
- 手工“刷新”按钮仍可用；
- 再次打开开关后自动刷新恢复。

---

# 8. Gate 5 — P1：修复登录轮询生命周期

## 8.1 问题 A：error/timeout 没有停止 polling

当前 `pollStatus()` 只在：

```text
state === online
```

时停止 timer。

计划要求：

```text
弹窗关闭
成功
终态 error/timeout
```

都立即停止。

## 8.2 问题 B：首次 immediate poll 存在 timer race

当前流程：

```text
await pollStatus()
pollTimer = setInterval(...)
```

如果第一次 poll 已经得到 `online`，`stopPolling()` 执行时 timer 还不存在，随后仍然会创建一个 interval。

## 8.3 允许修改

```text
work/console/wechat_console/static/js/components/login-flow.js
```

测试可修改：

```text
work/console/wechat_console/tests/test_console.py
```

## 8.4 推荐最小实现

让 `pollStatus()` 返回本次解析出的 phase：

```text
starting
waiting
phone_confirm
attention
online
stopped
error
degraded
```

`startLogin()`：

```text
await pollStatus()
```

之后只有在：

```text
dialog 仍 open
且 phase 不是 online
且 phase 不是 error
```

时创建 3s interval。

在 polling 中，如果 phase 为：

```text
online
error
```

立即 `stopPolling()`。

HTTP 异常被渲染为 error 后也应停止 timer，等待用户主动“重新尝试”。

不要让 error 页面背后继续每 3 秒刷 API。

### Gate 5 PASS 条件

- waiting 状态继续 3s poll；
- online 立即停止；
- error/timeout 立即停止；
- dialog close 立即停止；
- 首次 poll 已 online 时不会再多创建 interval。

---

# 9. Gate 6 — P1：Legacy Desktop fallback

## 9.1 事实

Console `/api/status` 顶层已经提供：

```text
desktop_url
```

用于 Legacy Selkies desktop fallback。

当前 `openDesktopEntry()` 只处理：

```text
port + path
```

没有 Legacy fallback。

## 9.2 允许修改

```text
work/console/wechat_console/static/js/components/login-flow.js
```

如果需要读取全局状态，可使用现有 `state.js`，不要新做全局 singleton。

## 9.3 明确规则

调用：

```text
GET /api/runtime/accounts/<id>/desktop
```

如果：

```text
runtime_provider === "agent_wechat"
```

继续执行当前安全校验：

```text
1 <= port <= 65535
path.startsWith("/")
```

然后构造当前 host 上的 Desktop Gateway URL。

如果：

```text
runtime_provider !== "agent_wechat"
```

优先使用：

```text
state.status.desktop_url
```

Legacy URL 打开时仍使用：

```js
window.open(url, "_blank", "noopener,noreferrer")
```

为空时提示：

```text
微信桌面入口尚未就绪，请稍后重试。
```

## 9.4 安全红线

不得为 Legacy fallback 放宽 AgentWechat path/token 校验。

不得将 upstream AgentWechat token 放进 URL。

### Gate 6 PASS 条件

- AgentWechat Desktop 仍走 Gateway；
- Legacy 有 `desktop_url` 时可打开；
- Legacy 没有 `desktop_url` 时显示友好提示；
- AgentWechat token 安全模型无变化。

---

# 10. Gate 7 — P1：添加微信向导补完整

## 10.1 允许修改

```text
work/console/wechat_console/static/js/views/accounts.js
```

必要时测试：

```text
work/console/wechat_console/tests/test_console.py
```

## 10.2 补 Legacy Display

高级选项中，运行模式为：

```text
兼容模式 — Legacy
```

时显示：

```text
Legacy Display
```

建议文案：

```text
Legacy Display
例如：:1；留空则使用 Runtime 默认 Display。
```

AgentWechat 模式下该输入隐藏，并且提交时不要传无意义的 Legacy display 值。

提交 Legacy 时 payload 加：

```js
display
```

## 10.3 修正 account_id 自动生成规则

执行计划要求：

```text
只允许 [A-Za-z0-9_.-]
首字符必须是字母或数字
最长 64
空结果 → wechat-<n>
冲突 → 追加数字后缀
```

不要继续把中文名称直接变成单独的 `wechat`。

例如：

```text
“工作微信”
现有无账号 → wechat-1
已有 wechat-1 → wechat-2
```

英文名称：

```text
"Work WeChat" → workwechat
```

或者等价的、符合计划“非法字符去除”规则的 slug。

**不要因为追加 `-2`、`-3` 使最终 ID 超过 64 字符。**

如果基础字符串很长，追加 suffix 前必须截断到：

```text
64 - suffix.length
```

## 10.4 表单错误后保留所有输入

重新渲染错误状态时必须保留：

- 名称；
- account_id；
- provider；
- Legacy Display；
- autostart；
- start。

### Gate 7 PASS 条件

- AgentWechat 模式不显示 Legacy Display；
- Legacy 模式显示 Legacy Display；
- payload 正确；
- 中文名称自动生成 `wechat-n`；
- 冲突处理稳定；
- 最终 ID 始终满足正则与 64 字符限制。

---

# 11. Gate 8 — P2：危险确认框 ESC 契约

## 11.1 问题

`dialog.js` 已支持：

```text
preventCancel
```

但 `confirmAction()` 没有在危险确认时使用。

## 11.2 允许修改

```text
work/console/wechat_console/static/js/components/confirm.js
```

## 11.3 明确要求

当：

```text
tone === "danger"
```

调用 `openDialog()` 时传：

```js
preventCancel: true
```

效果：

- ESC 不直接关闭危险确认；
- 用户仍可点“取消”；
- 用户仍可点右上角关闭；
- 非 danger 普通确认仍允许 ESC。

### Gate 8 PASS 条件

- 删除微信确认：ESC 不关闭；
- uncertain 强制重发确认：ESC 不关闭；
- 普通弹窗 ESC 行为不被破坏。

---

# 12. Gate 9 — P2：普通层去除工程术语

## 12.1 允许修改

主要：

```text
work/console/wechat_console/static/js/views/accounts.js
work/console/wechat_console/static/js/views/settings.js
```

必要时只做文案级修改。

## 12.2 当前已发现违规

普通账号页存在类似：

```text
当前 Core 未配置 Runtime 管理控制通道
```

改成计划中的普通用户文案：

```text
微信管理暂时不可用
已存在的消息仍然可以查看。
```

普通设置“数据与存储”存在：

```text
与 Core 解耦
```

改成用户语义，例如：

```text
消息快照、收藏与归档文件保存在 WeChat Hub 的持久化数据目录中。
```

普通“微信运行设置”不要出现：

```text
AgentWechat
Legacy
```

只写：

```text
推荐模式（Beta）
兼容模式
```

技术名只留：

```text
账号高级信息
设置 → 高级与诊断
添加向导中的“高级选项”若原执行计划明确要求技术名，可保留
```

## 12.3 禁止普通层出现的词继续检查

检查：

```text
Core
Durable events
Console projection
Runtime Provider
Agent probe
EFB probe
Registry hot reload
X11 Display
AT-SPI
outbox
PID
UID
event cursor
Docker
```

允许它们存在于高级与诊断层。

### Gate 9 PASS 条件

- 普通业务页面无违规工程术语；
- 高级诊断信息没有被错误删除；
- AgentWechat Beta 标记仍保留为「推荐模式（Beta）」。

---

# 13. Gate 10 — P2：高级诊断字段补齐

## 13.1 允许修改

```text
work/console/wechat_console/static/js/views/settings.js
```

必要时可 import：

```text
capabilitySummary
```

来自现有：

```text
static/js/capabilities.js
```

## 13.2 每个账号至少显示

在「设置 → 高级与诊断 → 账号运行详情」中确认以下字段可见：

```text
account_id
runtime_provider
runtime_health
agent_server_healthy
PID
UID
Display
HOME
image
autostart
sender capability
窗口数
registry hot reload
事件游标
最近同步
```

没有值时显示：

```text
--
```

不要伪造值。

## 13.3 数据来源

优先使用现有：

```text
state.runtimeAccounts
state.accounts
state.runtimeManagement
state.status.sync
```

不要为了显示字段新增后端 API。

### Gate 10 PASS 条件

- 字段完整；
- 未知字段用 `--`；
- 无 token；
- 无密码；
- 无 snapshot 内容；
- 页面仍能在 Agent/EFB 未配置时正常显示。

---

# 14. Gate 11 — P2：Runtime 不可用时正确门禁

## 14.1 允许修改

```text
work/console/wechat_console/static/js/views/accounts.js
work/console/wechat_console/static/js/views/home.js
```

## 14.2 微信页

Runtime 管理不可用时：

- 添加微信 disabled；
- 刷新 Runtime 状态按钮 disabled；
- 显示友好 banner；
- 已同步消息仍可通过其他页面查看。

当前“添加”已有部分门禁，但“刷新”需要一起处理。

## 14.3 首页无账号状态

如果：

```text
没有账号
且 Runtime management 不可用
```

不要给一个看起来能成功的“添加微信”按钮。

显示：

```text
微信管理暂时不可用
已存在的消息仍然可以查看。
```

并提供：

```text
重试
```

不要暴露 control.sock 等内部细节。

### Gate 11 PASS 条件

- Runtime 正常：添加/刷新正常；
- Runtime 离线：添加/刷新正确 disabled；
- 首页不会把用户引导进注定失败的添加流程。

---

# 15. Gate 12 — P2：修复“打开微信”动作语义

## 15.1 问题

当前账号主操作显示：

```text
打开微信
```

但实际只是跳转：

```text
#/messages
```

这与按钮文案不一致。

## 15.2 允许修改

```text
work/console/wechat_console/static/js/views/accounts.js
work/console/wechat_console/static/js/views/home.js
```

可复用：

```text
openDesktopEntry()
```

来自：

```text
js/components/login-flow.js
```

## 15.3 明确要求

`primaryAction.id === "open"`：

```text
真正打开微信 Desktop
```

不要再跳消息页。

查看消息已有独立入口：

```text
首页 → 打开消息
消息导航
```

### Gate 12 PASS 条件

- “打开微信”真正打开微信 Desktop；
- AgentWechat 走 Gateway；
- Legacy 走 desktop_url fallback；
- 消息页面导航不受影响。

---

# 16. Gate 13 — P2：收藏附件单项重试按钮

## 16.1 问题

`saved.js` 已渲染：

```text
data-archive-retry
```

按钮，但没有事件绑定。

## 16.2 允许修改

```text
work/console/wechat_console/static/js/views/saved.js
```

## 16.3 明确实现

对：

```text
button[data-archive-retry]
```

绑定点击事件。

现有后端接口是按 saved message 重试：

```text
POST /api/saved/<saved_id>/archive
```

所以该按钮可调用现有：

```js
api.archiveSaved(savedId)
```

成功：

```text
toast + reloadData()
```

失败：

```text
toast bad + 恢复按钮
```

### Gate 13 PASS 条件

- 单项“重试归档”不再是死按钮；
- “重试附件归档”总按钮仍可用；
- 不新增后端 endpoint。

---

# 17. Gate 14 — 补强测试：禁止继续只测字符串存在

本 Gate 很重要。

旧测试之所以漏掉 P0，是因为部分测试只检查：

```text
某个字符串是否存在于 JS 文件
```

这不能证明交互可运行。

## 17.1 Python / HTTP 测试必须新增的覆盖

至少包含：

### A. Saved response shape

```text
GET /api/saved
→ payload 含 items
```

### B. Send status

```text
POST /api/send/text
→ send_id
→ GET /api/sends/<send_id>
→ status
```

### C. Media send Console surface

至少直接 HTTP 验证：

```text
POST /api/send/image
POST /api/send/file
```

使用极小 base64 fixture，不要提交大型二进制测试文件。

验证：

```text
202
send_id
kind=image/file
```

### D. Desktop security regression

继续保留：

```text
desktop path 不含 token=
```

## 17.2 JS 语法

所有前端 JS 执行：

```powershell
node --check <file>
```

不得只检查 `app.js`。

## 17.3 静态禁止项扫描

确认生产前端中没有：

```text
window.alert(
window.confirm(
console.log(
```

`console.warn/error` 可保留用于真实异常，不要为了静态扫描删除必要错误日志。

### Gate 14 PASS 条件

- Python/HTTP tests 新增上述真实接口覆盖；
- JS 全部语法 PASS；
- 原测试没有删除；
- 没有降低已有安全断言。

---

# 18. Gate 15 — 浏览器 QA：必须测真实交互

仅截图静态页面不算本 Gate PASS。

## 18.1 启动本地 QA 服务

按原计划：

### Mock Core

```powershell
cd G:\LLM\WeChat_Hub
python stack/mock-core/app.py --host 127.0.0.1 --port 8099
```

### Console

另一个终端：

```powershell
cd G:\LLM\WeChat_Hub\work\console
$env:WECHAT_CONSOLE_RUNTIME_DIR="..\..\.tmp\ui-v2-review-fix"
python -m wechat_console.app --host 127.0.0.1 --port 8078 --core-url http://127.0.0.1:8099
```

目标：

```text
http://127.0.0.1:8078
```

## 18.2 Browser 工具选择

如果当前 Agent 环境提供 Browser plugin：

```text
优先 Browser plugin
```

如果不存在：

```text
使用本机已有 Playwright
```

不要为了 QA 引入生产依赖。

## 18.3 必须执行的交互路径

### Flow 1 — 收藏不再错误为空

```text
通过 Console API 创建一条收藏
→ 打开 #/saved
→ 列表必须出现该收藏
→ 不能显示“还没有收藏”
```

### Flow 2 — 文本发送状态

对 `/api/sends/<id>` 使用测试拦截或可控 fixture，依次模拟：

```text
accepted
submitted
sent
```

页面必须依次显示：

```text
正在排队发送…
已提交，等待微信确认
已确认发送
```

再单独模拟：

```text
uncertain
```

必须显示：

```text
发送结果未知
```

且：

```text
不自动重试
点击“仍然重新发送”出现二次确认
```

### Flow 3 — 图片发送

创建一个很小的临时 PNG/JPEG（放临时目录，不要提交进生产源码）。

```text
AgentWechat account
→ 选择图片
→ POST /api/send/image
→ request payload 有 content_base64 / filename / mime_type
→ UI 进入发送状态
```

### Flow 4 — 文件发送

创建一个很小的临时 txt/bin：

```text
选择文件
→ POST /api/send/file
→ UI 进入发送状态
```

### Flow 5 — Legacy capability

Legacy account：

```text
不显示图片发送按钮
不显示文件发送按钮
文本不可发送时 composer disabled
```

### Flow 6 — 自动刷新

```text
设置 → 关闭自动刷新
→ 等待超过 30 秒或使用 timer instrumentation
→ 不应触发自动 status fetch
→ 切换 tab / visibility 回前台
→ 不应自动刷新
→ 手工刷新仍可用
```

### Flow 7 — 登录 polling

用 browser route/mock 控制 `/login` 返回：

```text
waiting → waiting
```

确认持续轮询。

然后测试：

```text
waiting → online
```

确认 online 后不再请求。

再测试：

```text
waiting → error
```

确认 error 后不再请求，只有用户点“重新尝试”才重新开始。

### Flow 8 — 危险确认

```text
移除微信
→ danger confirm 打开
→ 按 ESC
→ dialog 保持打开
→ 点取消
→ dialog 关闭
```

不要真的删除真实账号；Mock 环境即可。

### Flow 9 — Desktop

AgentWechat：

```text
打开微信
→ Gateway URL
→ URL 无 token
```

Legacy：

```text
打开微信
→ status.desktop_url
```

### Flow 10 — 添加微信高级选项

```text
推荐模式（Beta）
→ Legacy Display 不显示

切换兼容模式
→ Legacy Display 显示
```

中文名称：

```text
工作微信
```

自动 ID：

```text
wechat-<n>
```

## 18.4 浏览器健康检查

每个核心 flow 都检查：

- 页面不是空白；
- Console 无相关 runtime error；
- 没有 JS uncaught exception；
- 没有横向破版；
- 操作后 DOM 状态真的变化。

### Gate 15 PASS 条件

上述 Flow 1~10 全部真实执行 PASS。

只给截图、不执行点击和状态断言，算 FAIL。

---

# 19. Gate 16 — 响应式 / 主题最终回归

功能修复完成后，再跑完整矩阵。

## 19.1 视口

```text
1920×1080
1440×900
1280×800
1024×768
768×1024
390×844
360×780
```

每个至少：

```text
Light
Dark
```

## 19.2 核心页面

至少快速 smoke：

```text
home
accounts
messages
saved
settings
login dialog
```

## 19.3 额外偏好

继续验证：

```text
prefers-color-scheme 实时切换
prefers-reduced-motion
prefers-contrast: more
pointer: coarse
```

## 19.4 不要再写“100% pixel-perfect”

允许结论：

```text
与定稿概念保持一致
无重大视觉偏差
关键布局/组件/主题/移动端行为通过保真检查
```

除非真正使用自动化像素 diff 并定义阈值，否则禁止写：

```text
100% 像素级吻合
```

### Gate 16 PASS 条件

- 7 视口 × 双主题 smoke PASS；
- 无明显破版；
- 修改功能没有破坏原视觉方向。

---

# 20. Gate 17 — WCAG 报告纠偏，不要错误宣传

## 20.1 事实

`contrast_audit.py` 当前定义：

```text
31 个强制检查 pair
```

全部达到 AA。

另外存在明确记录的 ACCEPTED exceptions，其中：

```text
浅色主按钮白字 / #07C160 ≈ 2.38:1
```

低于 4.5:1。

这是设计阶段已经记录的 intentional deviation，不要求本轮改品牌绿。

## 20.2 完成报告必须正确写

正确：

```text
31/31 个强制审计组合达到 WCAG AA；另有 2 个文档化例外，
其中品牌绿主按钮白字在普通模式低于 4.5:1，
prefers-contrast: more 下切换到更深品牌绿满足更高对比度。
```

禁止写：

```text
所有文本颜色对全部 WCAG AA
所有文本均达到 4.5:1+
```

### Gate 17 PASS 条件

- 审计脚本继续 PASS；
- 报告措辞与脚本事实一致。

---

# 21. Gate 18 — 修正 Completion Report

## 21.1 必须更新旧报告

更新：

```text
work/console/WEBUI_VISUAL_REDESIGN_COMPLETION_REPORT.md
```

不要保留明显错误的：

```text
100% 像素级吻合
所有文本组合全部 WCAG AA
8 态 harness 覆盖 polling / desktop / cache 全部行为
未完成项：无（在补修完成前）
```

补修全部 PASS 后，可以恢复“无未完成项”，但必须以本轮真实 QA 为依据。

## 21.2 新增补修报告

创建：

```text
work/console/WEBUI_V2_REVIEW_FIX_COMPLETION_REPORT.md
```

报告必须包含：

### A. 审阅发现

逐项列出：

```text
收藏字段错配
sendStatus 缺失
图片发送死按钮
文件发送死按钮
自动刷新假开关
登录 polling 生命周期
Legacy Desktop fallback
Legacy Display / ID slug
danger ESC
普通层工程术语
诊断字段
Runtime 门禁
打开微信语义
收藏单项 archive retry
```

### B. 每项修复文件

不要只写“已修复”。

写：

```text
问题 → 文件 → 修改点
```

### C. 测试命令与结果

列出真实运行结果：

```text
Console unittest
Mock Core unittest
Stack unittest
contrast audit
node --check
Browser/Playwright QA
```

### D. Browser QA

列出 Flow 1~10：

```text
PASS / FAIL
```

### E. 视口矩阵

列出 7 个视口和 Light/Dark。

### F. 剩余风险

如果没有做真实 NAS / 真实微信扫码：

必须明确写：

```text
本轮 Browser QA 基于 Mock Core；没有重新登出/扫码真实在线微信账号。
```

不要把 Mock QA 写成真实物理扫码验收。

---

# 22. 最终完整测试命令

全部代码修改后重新执行。

## 22.1 Console

```powershell
cd G:\LLM\WeChat_Hub\work\console
python -m unittest discover -s wechat_console/tests -t . -v
```

## 22.2 Contrast

```powershell
cd G:\LLM\WeChat_Hub\work\console
python design_v2/qa/contrast_audit.py
```

## 22.3 Mock Core

```powershell
cd G:\LLM\WeChat_Hub\stack\mock-core
python -m unittest discover -s tests -t . -v
```

## 22.4 Stack

```powershell
cd G:\LLM\WeChat_Hub\stack
python -m unittest tests.test_stack_wiring -v
```

## 22.5 所有 JS

如果 Node 可用，逐个检查：

```text
work/console/wechat_console/static/app.js
work/console/wechat_console/static/js/**/*.js
```

要求：

```text
全部 node --check PASS
```

## 22.6 静态自查

确认：

```text
无 window.alert(
无 window.confirm(
无 console.log(
无 token= 出现在 Desktop 前端 URL 拼接
无新 localStorage snapshot 缓存
```

---

# 23. 最终验收表

执行 Agent 在结束前逐项打勾。

## 功能

- [ ] 收藏真实数据能显示
- [ ] `api.sendStatus()` 已实现
- [ ] 文本发送状态链可运行
- [ ] 图片发送按钮真实可用
- [ ] 文件发送按钮真实可用
- [ ] media 20 MiB 门禁存在
- [ ] Legacy 不显示不支持的 media 操作
- [ ] 自动刷新开关真实生效
- [ ] login online 后停止 polling
- [ ] login error/timeout 后停止 polling
- [ ] dialog close 后停止 polling
- [ ] AgentWechat Desktop Gateway 正常
- [ ] Legacy desktop_url fallback 正常
- [ ] AgentWechat Desktop URL 无 upstream token
- [ ] 添加向导 Legacy Display 正常
- [ ] 中文名自动 ID 使用 `wechat-n`
- [ ] ID 冲突与 64 字符处理正确
- [ ] danger confirm ESC 不关闭
- [ ] Runtime 离线门禁正确
- [ ] “打开微信”真正打开 Desktop
- [ ] 收藏单项归档重试按钮可用

## 文案 / 诊断

- [ ] 普通层无违规工程术语
- [ ] 推荐模式（Beta）仍存在
- [ ] 高级诊断字段完整
- [ ] Agent/EFB 未配置仍视为可选正常状态

## 测试

- [ ] Console tests 全 PASS
- [ ] Mock Core tests 全 PASS
- [ ] Stack tests 全 PASS
- [ ] contrast audit PASS
- [ ] 所有 JS `node --check` PASS
- [ ] Browser Flow 1~10 全 PASS
- [ ] 7 视口 Light/Dark smoke PASS

## 报告

- [ ] 旧 Completion Report 已纠偏
- [ ] 新 Review Fix Completion Report 已生成
- [ ] 没有“100% pixel-perfect”无依据表述
- [ ] WCAG 31 PASS + documented exceptions 表述正确
- [ ] Mock QA 与真实扫码 QA 没有混为一谈

---

# 24. 最终允许修改文件清单

正常情况下，本轮修改应集中在：

```text
work/console/wechat_console/static/app.js
work/console/wechat_console/static/js/state.js
work/console/wechat_console/static/js/api.js
work/console/wechat_console/static/js/components/login-flow.js
work/console/wechat_console/static/js/components/confirm.js
work/console/wechat_console/static/js/views/accounts.js
work/console/wechat_console/static/js/views/home.js
work/console/wechat_console/static/js/views/messages.js
work/console/wechat_console/static/js/views/saved.js
work/console/wechat_console/static/js/views/settings.js
work/console/wechat_console/tests/test_console.py
work/console/WEBUI_VISUAL_REDESIGN_COMPLETION_REPORT.md
work/console/WEBUI_V2_REVIEW_FIX_COMPLETION_REPORT.md
```

如果你准备修改此清单以外的生产文件：

**先停下来确认是否真的必要。**

本轮理论上不需要修改 Core / Runtime / Docker / Compose。

---

# 25. 给执行 Agent 的最终输出格式

完成后只使用可核验事实，不写“圆满完成”“100% 完美”一类无法证明的结论。

最终回复按以下结构：

```markdown
## 结论
PASS / PARTIAL / FAIL

## 已修复
1. ...
2. ...

## 修改文件
- ...

## 自动化测试
| Test | Result |
|---|---|
| Console | x/x PASS |
| Mock Core | x/x PASS |
| Stack | x/x PASS |
| Contrast | PASS |
| JS syntax | x/x PASS |

## Browser QA
| Flow | Result |
|---|---|
| Saved real data | PASS |
| Text send lifecycle | PASS |
| Image send | PASS |
| File send | PASS |
| Auto refresh switch | PASS |
| Login polling | PASS |
| Danger ESC | PASS |
| Desktop AgentWechat | PASS |
| Desktop Legacy | PASS |
| Add wizard | PASS |

## 未完成 / 风险
- ...

## 报告
- work/console/WEBUI_V2_REVIEW_FIX_COMPLETION_REPORT.md
```

如果任何核心 Flow 未测：

```text
最终结论不得写 PASS。
```

---

# 26. 一句话任务边界

> **保留现有 WebUI v2 视觉与原生 ES Modules 架构，只修审阅确认的真实功能缺陷，补上真实交互测试，再用准确证据重新签署 WebUI v2 验收。**

