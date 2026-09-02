# WeChat Hub WebUI 视觉与交互重构任务书

版本：2026-09-02  
目标执行者：擅长前端产品设计、视觉设计、交互设计与 Web 实现的 Agent  
目标：在**不破坏现有后端接口和轻量架构**的前提下，将现有 `wechat-console` 从“工程控制台”重构为面向普通用户、轻量、清晰、好用的多微信管理应用。

---

## 0. 先读：本任务的核心要求

本轮不是继续堆功能，也不是单纯“换皮”。

当前 Console 的主要功能已经存在，包括多账号管理、消息查看、收藏、扫码登录、Runtime 管理、AgentWechat / Legacy Provider、完整微信桌面入口、Core 热加载等。问题在于：**现有 UI 仍以工程实现和内部模块为中心，而不是以用户任务为中心。**

本任务要求你完成的是：

1. 重新定义 Console 的产品信息架构与视觉语言；
2. 先产出完整设计概念，再实现；
3. 保留现有轻量技术路线，不为了“现代化”强行引入沉重前端栈；
4. 普通用户不应被迫理解 Core、Runtime、PID、UID、Display、Agent Server、Docker、event cursor 等概念；
5. 高级信息仍需保留，但放进“设置 / 高级 / 诊断”；
6. **Console 内直接扫码登录微信是核心流程，必须重点设计**；
7. AgentWechat 与 Legacy 的能力差异、Sender capability、`uncertain` 状态、Desktop Gateway 安全边界必须在 UI 中正确表达，不能用视觉层掩盖后端事实；
8. 桌面端和移动端都必须可用；
9. 不能只做一个首页效果图，必须覆盖关键页面和关键状态；
10. 完成后必须进行真实浏览器视觉 QA，不能只做静态 HTML/CSS。

---

# 1. 项目定位

不要继续把本产品理解为：

> WeChat Hub Engineering Console

新版应该理解为：

> **WeChat Hub —— 在 NAS 上添加、登录、运行和管理多个微信的应用。**

用户打开 WebUI 后最关心的是：

- 我的几个微信现在是否正常？
- 哪个微信需要登录？
- 哪个微信出现异常？
- 最近有什么消息？
- 我能不能直接打开某个微信？
- 我能不能在这里直接扫码登录？
- 我能不能从这里启动、停止、重启微信？
- 我能不能查看消息、发送消息、收藏重要消息？
- 自动化、Telegram 集成是否开启？

用户**不应该**首先看到：

- Core health；
- registry reload；
- Durable events；
- event cursor；
- Runtime Provider；
- PID / UID；
- X11 Display；
- Docker image；
- Agent server health；
- SQLite / DB path；
- EFB / Kettly / Linux Slave 内部名。

以上内容不是删除，而是降级到高级诊断层。

---

# 2. 当前代码和事实基线

## 2.1 当前主要前端文件

当前 Console 是轻量静态前端：

```text
work/console/wechat_console/static/
├─ index.html
├─ styles.css
└─ app.js
```

当前没有 React / Vue / Node runtime 要求。

目前 `app.js` 已经较大，约 800+ 行，后续可以拆分 ES Modules，但**不要求因为重构 UI 就切换到 React**。

如果你认为现有静态架构足够完成本任务，应优先保留：

```text
Python HTTP backend
+ HTML
+ CSS
+ Vanilla JS / ES Modules
```

除非你能证明现有仓库已经有明确的前端框架约束，否则不要为了组件化而引入大体积依赖。

## 2.2 当前一级导航

当前导航偏工程化：

```text
总览
微信账号
聊天记录
Saved Messages
服务状态
Agent（可选）
日志
```

当前首页还直接展示：

```text
Core
账号
事件消息
Saved
可选组件
事件同步
账号运行状态
最近消息事件
```

这不是最终产品信息架构。

## 2.3 当前账号管理已经具备的能力

不要重复实现后端已经具备的能力。

目前已支持：

- 创建微信账号；
- 启动；
- 停止；
- 重启；
- 移除；
- Runtime Registry 热加载；
- Console 通过 Core 间接管理 Runtime；
- Console 不直接访问 Docker Socket；
- 动态新增账号后不需要手工重启 Core；
- `display_name`；
- `autostart`；
- AgentWechat / Legacy 两种 Provider；
- 登录入口；
- 打开完整微信桌面；
- Console 内登录窗口画面；
- AgentWechat 独立容器；
- AgentWechat Desktop Gateway；
- 账号级 Sender capability。

## 2.4 当前扫码登录实现事实

这部分必须严格按照真实能力设计，不要臆造接口。

Console 目前的登录流程已经包含：

```text
创建 / 启动微信
  ↓
POST login session
  ↓
获取 login status
  ↓
获取微信登录窗口 snapshot
  ↓
Console 每约 3 秒刷新登录状态 / 画面
  ↓
必要时打开完整微信桌面
  ↓
登录成功
```

注意：

- 当前 UI 展示的是**微信登录窗口实时画面 / snapshot**，不是一个独立的纯 QR Code API；
- 不要设计一个虚假的“二维码有效期 02:35”倒计时，除非后端真实提供对应数据；
- 登录流程中可能出现安全确认；
- AgentWechat 完整登录 FSM 成功后，还会进行账号识别和 DB credential extraction；
- UI 不应仅因为看到微信主界面就提前宣告最终完成；
- Console 目前只在后端判断真正 `online` 后显示成功；
- snapshot 不应永久存储；
- 登录画面相关响应使用 no-store；
- AgentWechat Desktop 的 upstream token 不允许进入浏览器 URL / Core JSON / Console JSON；
- Console 只使用 Desktop Gateway 生成的短期入口；
- Gateway session 与账号绑定，不能串号。

## 2.5 Runtime Provider 事实

当前有：

### AgentWechat

推荐的新模式，当前仍需显示 Beta 状态。

特点：

- 一账号一个独立 child container；
- 独立微信；
- 独立 `/data` 和 `/home/wechat`；
- 独立 auth token；
- 独立 AT-SPI/FSM；
- Sender 可支持 text / image / file；
- 登录走 AgentWechat 完整 FSM；
- Desktop 走安全 Desktop Gateway；
- 真实 NAS acceptance 完成前，UI 不应宣称“正式稳定生产模式”。

### Legacy

兼容旧数据的模式。

特点：

- 共享 X11；
- 现有登录数据可继续使用；
- GUI Sender 能力有限；
- 对普通用户应表达为“兼容模式”，而不是直接展示技术栈。

## 2.6 发送能力事实

Sender capability 是**账号级**的。

例如：

```text
AgentWechat account → text / image / file 可能可用
Legacy account      → 文件等能力可能不可用
```

UI 必须按当前账号 capability 决定按钮是否出现 / 是否禁用。

不能用全局固定发送栏假设所有账号能力相同。

另外必须正确表达：

```text
accepted / queued
sending
sent / confirmed
failed
uncertain
```

特别是 `uncertain`：

> 网络中断后，微信可能已经发送成功，也可能没有成功。系统为了避免重复消息，不会自动重试。

UI 不得把它简单显示成“发送失败”。

---

# 3. 产品设计原则

本任务必须遵守以下设计原则。

## 3.1 账号优先，不是服务优先

一级对象是：

```text
个人微信
工作微信
备用微信
```

不是：

```text
Runtime
Core
Agent
EFB
Worker
Container
```

## 3.2 任务优先，不是参数优先

普通用户的添加微信流程应是：

```text
给微信起名字
→ 系统准备环境
→ 微信启动
→ 扫码登录
→ 登录成功
```

而不是：

```text
填写 account_id
选择 Provider
填写 Display
勾选 autostart
勾选 start
```

## 3.3 高频操作直接显示，低频技术操作渐进披露

直接显示：

- 打开微信；
- 扫码登录；
- 启动；
- 查看消息。

放到 `···` 或详情抽屉：

- 重启；
- 停止；
- 重新登录；
- 移除；
- 技术信息。

高级信息继续下一层：

- account_id；
- runtime_provider；
- PID；
- UID；
- Display；
- HOME；
- Docker image；
- Registry revision；
- Agent server health。

## 3.4 状态必须告诉用户“下一步做什么”

不要只显示后端枚举。

建议统一 UI View Model：

| 内部状态 | 用户文案 | 主要操作 |
|---|---|---|
| `online` | 已连接 | 打开微信 / 查看消息 |
| `starting` | 正在启动 | 等待 |
| 未登录 | 等待登录 | 扫码登录 |
| `attention` | 需要在微信中确认 | 继续登录 / 打开微信 |
| `stopped` | 已停止 | 启动 |
| `degraded` | 微信服务异常 | 重新启动 / 查看详情 |
| Runtime unavailable | 微信运行服务不可用 | 重试 / 高级诊断 |
| Core unavailable | WeChat Hub 暂时不可用 | 重新连接 |

## 3.5 实现细节不应成为普通用户决策

普通用户不应直接看到：

```text
AgentWechat 增强模式（Beta，独立容器 / AT-SPI）
Legacy（兼容模式，共享 X11）
```

建议普通语言：

```text
推荐模式（Beta）
每个微信独立运行，支持更多操作。

兼容模式
用于继续使用已有旧版微信数据，部分操作能力可能受限。
```

只有展开“高级选项”后才显示真实技术名：AgentWechat / Legacy。

## 3.6 安全能力应该无感

用户只需看到：

```text
打开微信
```

不要要求用户理解：

- Gateway port；
- token；
- upstream URL；
- noVNC；
- WebSocket proxy。

AgentWechat 与 Legacy 的 Desktop 打开方式由代码内部决定。

## 3.7 轻量不仅是少依赖，也包括少常驻行为

建议：

- 登录弹窗打开时：约 3 秒短轮询可以保留；
- 登录结束或弹窗关闭：立即停止轮询；
- 首页状态：低频刷新；
- 页面重新获得焦点时主动刷新；
- 聊天消息如需实时，再使用现有事件流或合理轮询；
- 不要为了“现代感”创建大量无意义 WebSocket/SSE 常驻连接。

---

# 4. 必须重新设计的信息架构

建议一级导航调整为：

```text
首页
微信
消息
收藏
自动化
设置
```

允许根据最终设计微调名称，但不能继续让 `Core / Agent / EFB / 日志` 成为普通用户一级导航核心。

## 4.1 首页

首页必须从“Dashboard”转成“当前需要关注什么”。

至少包含：

### 我的微信

每个微信展示：

- 名称；
- 用户状态；
- 一个主要操作；
- 可选的简单最近活动。

示意：

```text
个人微信
● 已连接
今天收到 12 条消息
[查看消息]

工作微信
● 等待登录
[扫码登录]

备用微信
○ 已停止
[启动]
```

### 需要处理

只有存在异常时显示。

例如：

```text
工作微信需要重新登录
[去登录]
```

### 最近消息

显示少量最近会话 / 消息。

不要展示：

- event cursor；
- Core URL；
- durable event 数量；
- Runtime registry 状态；
- optional module health statistics。

这些放设置 / 高级。

## 4.2 微信

这是整个产品最核心页面。

推荐形态：**开放列表 / 行，而不是密集卡片矩阵。**

示意：

```text
微信

管理运行在这台 NAS 上的微信账号

个人微信
● 已连接
今天 09:21 登录
[打开微信]                             ···

工作微信
● 等待登录
[扫码登录]                             ···

备用微信
○ 已停止
[启动]                                 ···

[＋ 添加微信]
```

`···` 中可以包含：

```text
重新启动
停止运行
重新登录
高级信息
移除微信
```

高级信息使用 Drawer / Sheet / Detail panel，不要直接铺在主列表。

## 4.3 消息

保持轻量，不需要复制完整微信客户端。

建议桌面为双栏：

```text
工作微信 ▾

┌───────────────┬──────────────────────────┐
│ 搜索会话       │ Alice                    │
│               │                          │
│ Alice         │ 下午开会吗？              │
│ 工作群        │                          │
│ 客户群        │              三点可以。   │
│               │                          │
│               ├──────────────────────────┤
│               │ 输入消息…          发送 │
└───────────────┴──────────────────────────┘
```

账号切换使用自然的 Account Switcher：

```text
工作微信 ▾
```

而不是全局顶部一直显示一个大型工程下拉框。

## 4.4 收藏

`Saved Messages` 在普通中文 UI 中统一改为：

```text
收藏
```

底层数据结构不变。

建议支持视觉分类：

```text
全部
图片
文件
链接
带注释
```

如果当前后端没有直接分类字段，可按现有 snapshot/media 数据做前端可实现的分类；不要为了视觉稿捏造后端不存在的数据。

## 4.5 自动化

不要把 `Agent（可选）` 作为普通用户入口名。

改成能力导向：

```text
自动化

自动回复
消息关注
定时任务
AI 总结 / AI 助手
```

后台仍然可以使用 Agent / Monitor / Scheduler / MCP / Records。

Agent 未启用时，不要显示：

```text
Agent probe unavailable
```

应显示：

```text
启用自动化功能

启动 WeChat Agent 后，可以创建自动回复、关键词关注和定时任务。
```

## 4.6 设置

普通设置建议包含：

```text
常规
微信
Telegram
AI 助手
数据与存储
```

高级设置：

```text
服务状态
运行模式
Core API
Runtime
同步状态
日志
诊断信息
```

EFB 在普通 UI 中应表现为：

```text
Telegram 集成
```

不要直接把 EFB / Kettly / Linux Slave 当作主产品语言。

---

# 5. Console 内扫码登录：必须重点设计

这一部分是本轮视觉与交互设计的最高优先级之一。

## 5.1 添加微信流程

当前新增账号表单过于工程化。

普通流程建议只要求用户输入：

```text
给这个微信起一个名字
[ 工作微信                 ]
```

系统自动：

- 生成内部 account_id；
- 选择推荐运行模式；
- 默认 autostart；
- 创建后立即启动；
- 启动完成后直接进入扫码登录。

“高级选项”可以展开：

- 自定义 account_id；
- 运行模式；
- Legacy Display；
- 自动启动。

## 5.2 登录完整状态设计

必须至少产出以下视觉状态：

### A. 准备中

```text
正在准备工作微信

正在启动微信并准备登录窗口…
```

不要使用假的百分比进度，除非后端提供真实 progress。

可以使用 indeterminate progress / skeleton / subtle motion。

### B. 等待扫码

```text
登录工作微信

请使用手机微信扫描窗口中的二维码

┌──────────────────────────┐
│                          │
│    微信登录窗口实时画面   │
│                          │
└──────────────────────────┘

登录画面只在当前会话中临时显示，不会保存。

[刷新画面]        [打开完整微信]
```

注意：这里是微信窗口画面，不要把它设计成“后端原生生成的 QR 卡片”除非真实实现发生变化。

### C. 已扫描 / 等待手机确认

如果后端提供足够状态，应显示：

```text
已扫描二维码

请在手机微信中确认登录。
```

如果后端无法精确区分，则不要在前端假造状态。

### D. 需要安全确认 / attention

```text
微信需要额外确认

请在下面的微信窗口中完成安全验证。

[打开完整微信]
```

### E. 登录成功

```text
✓ 工作微信已连接

消息正在开始同步。
以后 WeChat Hub 会自动启动这个微信。

[完成]
```

### F. 微信已停止

```text
这个微信当前已停止

[启动微信]
```

### G. 登录超时 / 登录流程异常

```text
登录窗口暂时不可用

微信可能仍在启动，或者登录流程已经超时。

[重新尝试]        [打开完整微信]
```

### H. Agent Server degraded

```text
微信服务异常

微信进程仍在运行，但控制服务暂时不可用。

[重新启动]        [查看详情]
```

## 5.3 登录移动端

如果用户在手机浏览器里打开 Console，用同一台手机扫码会不方便。

移动端应明确提示：

```text
建议在电脑或平板上打开此页面，
再使用手机微信扫码。
```

可以继续允许显示登录窗口，但不要让布局挤压到不可用。

## 5.4 登录画面视觉要求

- 登录画面应成为弹窗唯一视觉焦点；
- 不要在周围放太多说明和技术字段；
- 不要出现 token、Gateway path、upstream host 等信息；
- 要兼容浅色微信登录窗口；
- 避免深色 UI 对登录截图造成强烈视觉冲突；
- 登录 snapshot 的 aspect ratio 要稳定；
- image load / error / empty / refresh 状态必须设计；
- 对屏幕阅读器保留有意义的 alt / live region；
- 不要通过 CSS 截掉可能包含安全确认按钮的关键区域。

---

# 6. 账号能力差异必须进入设计系统

不同账号能力不同，不允许统一假装功能都存在。

建议做 `Account Capability View Model`。

例如：

```js
{
  canSendText: true,
  canSendImage: true,
  canSendFile: false,
  canOpenDesktop: true,
  canLogin: true,
  canRestart: true,
  providerLabel: "推荐模式（Beta）"
}
```

消息输入区域应根据当前账号动态变化。

例如：

```text
AgentWechat 账号：
[图片] [文件]  输入消息…                         [发送]

Legacy 账号：
        输入消息…                               [发送]
```

对于不可用能力，可采用：

- 直接不展示；或
- disabled + 简短 tooltip。

避免长期显示工程说明。

---

# 7. 发送状态和错误状态

当前 UI 中类似：

```text
Core 已接收：<send_id> · accepted
```

这是典型工程信息，应改成用户语言。

建议状态：

```text
发送中…
已发送
发送失败
发送结果未知
```

## 7.1 `uncertain` 必须单独设计

推荐文案：

```text
发送结果未知

微信可能已经收到这条消息。
为避免重复发送，系统没有自动重试。

[查看消息]   [仍然重新发送]
```

“仍然重新发送”属于危险二次操作，必须二次确认。

不要把 `uncertain` 画成红色普通失败然后给一个“重试”按钮。

---

# 8. 视觉方向

## 8.1 总体气质

目标：

> **现代 NAS 应用 + 桌面通信工具**

不要继续做：

> 深色 DevOps Dashboard / Server Admin Console

建议默认：

- 浅色；
- 深色可选；
- 低到中等信息密度；
- 大量开放布局；
- 少嵌套 Card；
- 文字层级清晰；
- 微信绿只用于主要动作与正向状态；
- 异常状态使用语义色，但不要大面积告警色。

## 8.2 建议基础色

这是方向，不要求机械照抄，可以在概念阶段微调：

```text
页面背景       #F5F6F7
主内容         #FFFFFF
主要文字       #1F2329
次要文字       #7D858F
边界           #E7E9EC
微信绿         #07C160
危险           #D94B4B
警告           #C7831D
```

要求：

- 不要大面积荧光绿色渐变；
- 不要霓虹 glow；
- 不要把所有面板都做成高圆角 glass card；
- 不要默认 Bento Grid；
- 不要为了“高级感”加入无意义装饰。

## 8.3 容器模型

优先使用：

- 开放 section；
- List row；
- Split view；
- Drawer；
- Dialog；
- Settings group；
- Table / log list；
- 少量真正需要强调的 Panel。

避免：

```text
card
  card
    card
```

## 8.4 圆角 / 阴影

建议：

- Radius 8–14px；
- Shadow 很轻；
- 更多依赖间距、边界和背景层级，而不是浮空卡片。

## 8.5 字体

优先系统字体栈，避免为了视觉效果引入大量字体资源。

中文环境要求：

- Windows；
- macOS；
- Linux；
- Android；
- iOS；

都要可读。

要定义明确的：

- Page title；
- Section title；
- Body；
- Label；
- Caption；
- Button text；
- Input text；
- Log / technical monospace。

不要让 button/input 落回浏览器默认字号。

---

# 9. 动效要求

动效需要克制，只用于状态变化与空间层级。

建议：

- Dialog：120–180ms fade + scale；
- Drawer：150–220ms slide；
- 状态切换：淡入淡出；
- 创建微信：indeterminate progress；
- 登录成功：轻量 success transition；
- 删除账号：row collapse/fade；
- Account switch：100–160ms content fade；
- Toast：轻量进入/退出。

必须支持：

```css
@media (prefers-reduced-motion: reduce)
```

不要：

- 无限 pulse；
- 大面积 shimmer；
- 动态渐变背景；
- 强烈弹簧动画；
- 对 NAS 环境没有意义的重 GPU 动画。

---

# 10. 响应式设计

必须至少验证：

```text
1440×900   常见桌面
1280×800   小型笔记本
1024×768   平板横向 / 小屏桌面
768×1024   平板竖向
390×844    手机
```

## 10.1 桌面

- 左侧主导航可以常驻；
- 消息页使用双栏；
- 设置页可使用左导航 + 主内容；
- 登录 Dialog 可大尺寸显示微信窗口。

## 10.2 平板

- 侧栏可收起；
- 账号列表仍使用整洁列表；
- 消息页允许 35/65 或可切换详情；
- Dialog 不得溢出。

## 10.3 手机

- 底部导航 / Drawer / Compact top navigation 均可，但要统一；
- 消息列表与聊天详情切页，不要硬塞双栏；
- 登录界面重点提示建议在电脑/平板扫码；
- 高级设置使用分层页面；
- 账号操作 `···` 适合 Bottom Sheet。

---

# 11. 可访问性

必须做到：

- 键盘可导航；
- 所有 icon-only button 有 `aria-label`；
- Dialog focus trap 正确；
- ESC 能关闭非危险 Dialog；
- 破坏性动作有确认；
- Color contrast 满足基本可读性；
- 状态不能仅靠颜色区分；
- 登录状态变化使用 `aria-live`；
- 表单错误与输入关联；
- 触摸目标建议 ≥ 40px；
- Mobile 不出现 11px 过小操作文字。

---

# 12. 不允许破坏的架构与安全边界

视觉重构过程中，不允许为了“前端方便”破坏以下边界。

## 12.1 Console 不允许获取 Docker Socket

Console 只能走：

```text
Console → Core → Runtime private control
```

不能改成：

```text
Console → Docker socket
```

## 12.2 Console 不允许直接读 Core SQLite

继续使用 Core HTTP / Console 自身投影。

## 12.3 AgentWechat 6174 不允许发布到 Host

浏览器访问 Desktop 必须继续：

```text
Browser
→ WeChat Hub Desktop Gateway
→ agent-wechat internal :6174
```

不允许为了前端开发直接暴露 upstream 6174。

## 12.4 Browser URL 不允许出现 upstream token

不要在前端 debug UI 中显示 token。

## 12.5 登录 snapshot 不允许长期缓存

不要把 login image 放进 localStorage / IndexedDB / persistent app cache。

## 12.6 删除默认保留账号数据

普通“移除微信”仍然应该是 preserve 行为。

Purge data 属于高级危险动作，如果未来 UI 暴露，必须明确二次确认，不要默认提供。

---

# 13. 技术实现建议

本项目优先轻量。

建议将现有单体前端拆成：

```text
wechat_console/static/
├─ index.html
├─ css/
│  ├─ tokens.css
│  ├─ base.css
│  ├─ layout.css
│  └─ components.css
└─ js/
   ├─ app.js
   ├─ api.js
   ├─ router.js
   ├─ state.js
   ├─ account-view-model.js
   ├─ capabilities.js
   │
   ├─ views/
   │  ├─ home.js
   │  ├─ accounts.js
   │  ├─ messages.js
   │  ├─ saved.js
   │  ├─ automation.js
   │  └─ settings.js
   │
   └─ components/
      ├─ account-switcher.js
      ├─ account-row.js
      ├─ login-flow.js
      ├─ dialog.js
      ├─ toast.js
      ├─ status.js
      └─ detail-drawer.js
```

不要求文件名完全一致，但要求：

- 不再把全部 UI 状态堆在一个 1000+ 行 `app.js`；
- 业务状态映射与 DOM rendering 分开；
- Provider-specific 判断集中处理；
- Capability 判断集中处理；
- 文案状态集中处理；
- 重复按钮 / dialog / row 用统一组件函数或模块。

如果你决定迁移框架，必须在任务结果里明确说明：

1. 为什么 Vanilla + ES Modules 无法满足；
2. 新依赖增加了什么成本；
3. 镜像大小和启动复杂度变化；
4. 是否需要 Node runtime；
5. 为什么这对 NAS 场景仍然值得。

无充分理由，不要迁移。

---

# 14. 视觉概念产出要求

**不要直接打开 CSS 开始改。**

先做完整设计概念。

建议至少产出以下独立视觉稿 / screenshot concept：

1. 首页 —— 多微信混合状态；
2. 微信账号页 —— 已连接 / 等待登录 / 已停止 / 异常混合；
3. 添加微信向导；
4. 扫码登录 —— 等待扫码；
5. 扫码登录 —— 安全确认 / attention；
6. 扫码登录 —— 成功；
7. 消息页 —— 桌面双栏；
8. 消息发送 —— `uncertain` 状态；
9. 收藏页；
10. 自动化页；
11. 设置页；
12. 高级诊断页；
13. 手机首页；
14. 手机微信账号管理；
15. 手机扫码登录提示。

可以先做一个全局 Design System Board，但不能只做一张压缩的“大而全长图”。

复杂区域必须有独立可读的概念图。

## 14.1 概念稿不得 invent 的内容

不要凭空增加：

- 虚假业务指标；
- 虚构联系人数量；
- 虚构在线时长；
- 虚假 AI 功能；
- 虚假二维码倒计时；
- 后端不存在的登录 progress percentage；
- 不存在的 sender confirmation；
- 不存在的 Telegram 配置字段。

占位数据可以有，但必须是明显的 demo content，不能把 demo 功能误当已实现功能。

---

# 15. 设计稿批准后的实现要求

视觉概念一旦确定，后续实现必须忠实于设计稿。

不要出现：

```text
概念稿：开放白色列表
实现：重新变成深色 Card Grid
```

或：

```text
概念稿：账号页简单状态
实现：为了方便又把 PID / UID 全放回主行
```

必须先从概念稿提取：

- design tokens；
- type scale；
- spacing scale；
- radius；
- semantic colors；
- button variants；
- status patterns；
- icon style；
- navigation pattern；
- dialog pattern；
- drawer pattern；
- list row anatomy；
- mobile breakpoint strategy。

再开始编码。

---

# 16. 必须保留并适配的现有功能

视觉重构后，以下功能不得丢失：

## 首页 / 状态

- Core 连通状态；
- 账号状态；
- 最近消息；
- 异常提醒。

Core 状态正常时可隐藏在主 UI；异常时必须清晰出现。

## 微信账号

- 创建；
- 启动；
- 停止；
- 重启；
- 移除；
- 自动启动信息；
- 登录；
- Desktop；
- AgentWechat / Legacy 能力差异；
- Runtime degraded 状态；
- Core hot reload 状态至少在高级诊断里可见。

## 扫码登录

- Start login session；
- Login status polling；
- snapshot；
- refresh snapshot；
- desktop fallback；
- login success；
- stopped；
- timeout / error；
- attention；
- AgentWechat / Legacy 都能正确工作。

## 消息

- 按账号查看；
- 会话列表；
- 搜索；
- 类型过滤；
- 文本发送；
- 附件预览；
- 保存消息；
- capability-aware controls；
- send result state。

## 收藏

- 列表；
- 搜索；
- snapshot；
- title；
- tags；
- note；
- media archive；
- retry archive；
- delete。

## 集成 / 自动化 / 高级

- Agent probe；
- EFB probe；
- Console logs；
- service health；
- 不配置 Agent/EFB 时 Console 仍能正常使用。

---

# 17. 文案规范

## 普通用户文案

优先：

```text
微信
消息
收藏
自动化
设置
已连接
等待登录
正在启动
已停止
需要处理
扫码登录
打开微信
重新启动
连接异常
发送结果未知
```

避免：

```text
Core accepted
Durable events
Console projection
Runtime Provider
Agent probe
EFB probe
Registry hot reload
X11 Display
AT-SPI
outbox
```

技术字段只能出现在高级诊断里。

## AgentWechat Beta

真实 NAS acceptance 未完成前，不要移除 Beta 提示。

普通文案：

```text
推荐模式（Beta）
```

高级详情：

```text
AgentWechat
```

---

# 18. 空状态 / 错误状态

必须设计，不允许临时用一句灰色文字敷衍。

至少覆盖：

## 无微信账号

```text
还没有添加微信

添加第一个微信后，可以在这里扫码登录并管理消息。

[添加微信]
```

## Core 离线

```text
WeChat Hub 暂时无法连接

账号和消息可能暂时无法更新。

[重新连接]
```

## Runtime 控制通道离线

普通用户：

```text
微信管理暂时不可用

已存在的消息仍然可以查看。

[重试]
```

高级信息中再显示 control.sock 等。

## 无消息

```text
还没有同步到消息
```

## 无收藏

```text
还没有收藏

在消息中点击“收藏”，重要内容会出现在这里。
```

## Agent 未启用

用功能引导，不用 Probe error。

---

# 19. 交互细节

## 添加账号

- 创建按钮点击后立即 disabled；
- 显示进行中状态；
- 防止重复创建；
- 创建成功后如果 `start=true`，自动进入登录流程；
- 不要求用户再次寻找账号卡点击扫码；
- 创建失败保留用户输入；
- 错误在表单上下文中显示，不用 `alert()`。

## 删除账号

- 默认文案使用“移除微信”；
- 明确告诉用户登录数据默认保留；
- Legacy default account 的特殊保护仍保留；
- 不要把“删除容器”作为主文案。

## Desktop

- 主按钮统一叫“打开微信”；
- Provider-specific Desktop 行为由代码决定；
- 新开窗口需 `noopener,noreferrer`；
- Gateway 暂未就绪时给用户可理解的错误。

## 状态刷新

- 不要把“刷新”作为每个页面最显眼的主按钮；
- 自动刷新合理工作时，刷新可放次要位置；
- 页面 `visibilitychange` / focus 时可刷新；
- 避免每 10 秒导致大面积布局闪烁。

---

# 20. 视觉 Agent 实施流程

请严格按以下阶段执行。

## Phase A — 现状审计

1. 阅读：

```text
docs/INTEGRATION_STATUS.md
docs/SESSION_F_RUNTIME_SENDER_DRIVERS.md
work/console/wechat_console/static/index.html
work/console/wechat_console/static/styles.css
work/console/wechat_console/static/app.js
```

2. 启动现有 Console；
3. 截图现有 Desktop 和 Mobile；
4. 列出当前至少 10 个主要 UX 问题；
5. 不改代码。

## Phase B — Visual Concept

先生成完整视觉设计。

要求：

- 不只做首页；
- 覆盖第 14 节要求的状态；
- 保持同一设计系统；
- 所有文字可读；
- 不用一张巨型长图代替细节设计；
- 登录 Dialog、账号行、消息栏等复杂组件要有独立稿。

如果有用户可交互审批流程，先给用户确认设计概念后再实施。

如果执行环境要求无人值守，则：

- 生成至少 2 个候选方向；
- 自行选择更符合“轻量、亲和、非工程师化”的方案；
- 在报告中保留候选和选择理由；
- 不因为无法等待确认而跳过概念阶段。

## Phase C — Design System

从设计稿提取：

- tokens；
- typography；
- component families；
- icon rules；
- spacing；
- responsive rules；
- states；
- motion。

写入项目内文档或 CSS tokens。

## Phase D — Implement

优先按页面 / 组件分阶段完成：

1. App Shell + Navigation；
2. 首页；
3. 微信账号；
4. 添加账号向导；
5. 登录 Dialog；
6. 消息；
7. 收藏；
8. 自动化；
9. 设置 / 高级；
10. Mobile。

每完成一个主要区域就浏览器截图检查，不要等全部做完才 QA。

## Phase E — Browser QA

必须实际运行应用。

检查：

- Desktop；
- 小屏 Laptop；
- Tablet；
- Mobile；
- Hover；
- Focus；
- Keyboard；
- Dialog；
- Drawer；
- Empty；
- Loading；
- Error；
- Login states；
- Long Chinese text；
- Long account name；
- 3+ accounts；
- Mixed AgentWechat + Legacy accounts；
- Agent disabled；
- EFB disabled；
- Core unavailable。

## Phase F — Fidelity QA

必须将：

```text
设计概念截图
vs
浏览器最终截图
```

并排检查。

至少检查：

1. Layout；
2. Typography；
3. Color；
4. Spacing；
5. Component anatomy；
6. Login Dialog；
7. Account row；
8. Mobile collapse；
9. Icon style；
10. Visible copy。

任何会被专业设计 Review 指出的明显问题都应继续修改，而不是写进“已知问题”后结束。

---

# 21. 测试与验收

## 21.1 现有功能测试不能回退

不要为了 UI 改造破坏现有 Console 测试。

修改后至少执行：

- Console 原有 Python tests；
- JS syntax / module import 检查；
- HTML/CSS 基本检查；
- Core / Runtime 相关契约测试（如改动 API 调用）；
- Stack topology test（如修改 Compose/static path）。

如果仅做视觉，不应修改 Core API。

## 21.2 关键 E2E 流程

至少验证：

### Flow 1：首次添加微信

```text
无账号
→ 添加微信
→ 输入名称
→ 创建
→ 自动启动
→ 自动进入扫码登录
→ snapshot 出现
→ 登录成功
→ 返回账号页 / 首页
→ 账号显示已连接
```

### Flow 2：已有微信重新登录

```text
等待登录
→ 扫码登录
→ attention / 安全确认
→ 打开完整微信
→ 登录成功
```

### Flow 3：微信生命周期

```text
已连接
→ 停止
→ 已停止
→ 启动
→ 正在启动
→ 已连接 / 等待登录
→ 重启
```

### Flow 4：账号删除

```text
移除微信
→ preserve 数据提示
→ 确认
→ 从活动列表消失
→ 其他微信保持正常
```

### Flow 5：消息发送

```text
选择账号
→ 选择会话
→ 发送
→ 发送中
→ 成功 / 失败 / uncertain 正确显示
```

### Flow 6：Capability 差异

```text
AgentWechat
→ 可见支持的媒体按钮

Legacy
→ 不显示或禁用不支持能力
```

---

# 22. 明确不在本任务中做的事情

除非视觉改造确实被后端 bug 阻塞，否则不要顺手扩大范围。

本任务默认不负责：

- 重写 Core；
- 重写 Runtime；
- 修改 Sender 实现；
- 更改 AgentWechat upstream；
- 改 EFB 架构；
- 真正新增 Backend QR parser；
- 新增 Native Sender；
- 修改 Desktop Gateway 安全模型；
- 增加用户认证系统；
- 把 Console 强行合并进 Agent 容器；
- 把 Runtime + Core 强行合并为单容器。

如果发现后端确实缺少一个阻塞 UX 的字段或接口：

1. 先记录问题；
2. 优先使用现有接口解决；
3. 只有无法完成核心流程时再提出最小 API 变更；
4. 不允许为了视觉稿随意修改接口语义。

---

# 23. 必须保留的安全提醒

## Beta

AgentWechat 真实 NAS acceptance 完成前：

```text
推荐模式（Beta）
```

必须保留。

## 登录 snapshot

建议简洁提示：

```text
登录画面只在当前会话中临时显示，不会保存。
```

## `uncertain`

必须明确避免重复发送风险。

## Remove vs Purge

普通 UI 默认“移除”，保留数据。

---

# 24. 交付物

最终必须交付以下内容。

## A. 视觉概念

保存到例如：

```text
work/console/design_v2/
```

至少包含：

- design overview；
- Desktop key screens；
- login states；
- Mobile key screens；
- design tokens / system notes。

## B. 实际前端实现

修改 `work/console/wechat_console/static/`。

## C. 设计说明

新增例如：

```text
work/console/docs/WEBUI_DESIGN_V2.md
```

至少说明：

- 视觉理念；
- 信息架构；
- tokens；
- typography；
- component anatomy；
- responsive；
- login flow；
- capability display；
- advanced diagnostics disclosure。

## D. QA 截图

至少包含：

- Desktop 首页；
- 微信账号；
- 添加微信；
- 扫码登录；
- 消息；
- 设置；
- Mobile 首页；
- Mobile 微信账号。

## E. Completion Report

新增：

```text
work/console/WEBUI_VISUAL_REDESIGN_COMPLETION_REPORT.md
```

必须包含：

1. 修改了哪些文件；
2. 设计概念路径；
3. 最终截图路径；
4. 浏览器验证方式；
5. 设计稿 vs 实现的 fidelity 检查；
6. Desktop / Mobile viewport；
7. 功能测试结果；
8. 保留的 intentional deviations；
9. 未完成项目；
10. 是否修改了后端 API；
11. 是否引入新依赖；
12. 是否修改了容器 / build；
13. 是否进行了真实扫码登录验证；
14. AgentWechat Beta 是否仍保持。

---

# 25. 最终验收标准

满足以下条件才可以声明 WebUI 视觉重构完成。

## 产品层

- 普通用户第一次打开首页，不需要理解 Core / Runtime / Agent / EFB；
- 添加微信默认只需极少输入；
- Console 内扫码登录流程完整、清晰；
- 用户随时能知道某个微信是否正常，以及下一步可以做什么；
- 技术信息仍然可查，但不污染主体验；
- 不同 Provider / capability 的 UI 不会误导用户。

## 视觉层

- 不再像 DevOps Dashboard；
- 不再大面积 Card Grid；
- 中文排版清晰；
- 默认浅色足够成熟；
- Desktop / Tablet / Mobile 均无明显破版；
- 登录画面是视觉焦点；
- 账号页是产品核心页面；
- 设计系统一致；
- 没有明显 prototype 感；
- 没有 browser-default button/input typography。

## 技术层

- 保持轻量；
- 不破坏 Console/Core/Runtime 安全边界；
- 不暴露 AgentWechat token；
- 不发布 AgentWechat 6174 到 Host；
- 不给 Console Docker Socket；
- 不缓存登录 snapshot；
- 原有功能测试不回退；
- 页面加载与交互对 NAS 环境友好。

## QA 层

- 已用真实浏览器运行；
- 已检查 Desktop + Mobile；
- 已检查关键登录状态；
- 已将设计概念与最终截图进行直接视觉对比；
- 没有仍可修复的明显视觉偏差；
- 没有临时 placeholder / debug UI 遗留。

---

# 26. 给执行 Agent 的最终指令

请不要把本任务理解为“重新配一下 CSS”。

你要做的是：

> **在不改变 WeChat Hub 核心架构和安全边界的情况下，把当前工程型 Console 重构成真正面向普通用户的轻量多微信管理应用。**

优先级：

```text
1. 信息架构
2. 微信账号管理体验
3. Console 内扫码登录
4. 状态与错误反馈
5. 消息体验
6. 响应式
7. 视觉细节
8. 高级诊断
```

先设计，再编码；先让用户任务简单，再考虑工程信息；先保证真实后端语义，再追求视觉效果。

完成标准不是“页面比以前漂亮”，而是：

> 普通用户不看文档，也能自然完成“添加微信 → 扫码登录 → 查看状态 → 打开微信 → 查看/发送消息 → 处理异常”这一整条核心路径。

