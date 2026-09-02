# Linux WeChat Multi-Account Hub
## 源码拉取、改造与多 Agent 并行执行任务书 V3.0

> 面向 DeepSeek 4 Flash / GPT-5.6 Luna / Codex 类 Coding Agent  
> 本版本专门修正 V2.0 的缺陷：**禁止从零搭空壳；必须拉取、审计并基于指定上游仓库源码改造。**

---

# 0. 强制规则：本项目不是“按描述从零重写”

所有执行 Agent 必须遵守以下顺序：

```text
拉取指定上游源码
        ↓
记录 upstream commit
        ↓
实际阅读源码入口
        ↓
形成 SOURCE_AUDIT.md
        ↓
明确“复用 / 修改 / 抽取 / 删除 / 新增”
        ↓
才允许开始编码
```

禁止：
- 只阅读 README 就开始实现；
- 不拉取仓库，直接新建同名空服务；
- 自己重新写 Telegram Bot 代替 EFB；
- 自己重新写一套 Linux 微信 DB 解密器，忽略 `linux-wechat-agent` 已有实现；
- 自己重新做 Selkies 基础镜像，忽略 `wechat-selkies`；
- 自己凭印象实现 EFB Chat / Message，而不审 `efb-wechat-comwechat-slave`；
- 使用 PyPI 官方 ETM 代替用户指定的 `kettly1260/efb-telegram-master` fork 做最终集成测试；
- 修改上游源码后不保留 upstream remote / commit 来源；
- 把 Mock 测试写成真实微信/TG测试。

允许新增代码，但必须先证明：对应能力在指定上游仓库中不存在，或者现有实现无法直接复用。

---

# 1. 必须拉取的源码仓库

## R1. Linux 微信 Agent 主基线

```text
https://github.com/xiaoguiwucan/linux-wechat-agent.git
```

用于：
- 微信数据库发现；
- DB key 提取；
- 消息增量同步；
- 群成员同步；
- media sync；
- 微信 GUI Sender；
- 现有 Agent Console；
- AI/Memory 现有实现；
- Docker Compose 集成逻辑。

必须重点审计：
`agent_console/`、`ai/`、`memory/`、`tools/wechat-decrypt/`、`web/`、`scripts/`、`docker-compose.yml`、`.env.example`。

## R2. Selkies Linux 微信运行时

```text
https://github.com/nickrunning/wechat-selkies.git
```

用于：
- 官方 Linux 微信安装；
- Docker Runtime；
- `/config` 持久化；
- X11/Openbox/Selkies；
- WebRTC/Web UI；
- 微信启动脚本；
- 多账号 Runtime 改造基线。

## R3. ComWechat EFB Slave

```text
https://github.com/ehForwarderBot/efb-wechat-comwechat-slave.git
```

用于：
- 新 Linux Slave 的主要 EFB 行为参考；
- Chat / Group / Member 建模；
- Message 转换；
- `vendor_specific`；
- EFB → 微信发送 dispatch；
- reply/target；
- 文件 pending；
- MessageRemoval；
- EFB Channel 结构。

## R4. 老 efb-wechat-slave

```text
https://github.com/ehForwarderBot/efb-wechat-slave.git
```

用于：
- 旧 EWS 用户体验参考；
- `/link` 后的 Chat 行为；
- `GroupChat` / `PrivateChat`；
- 历史 EFB 微信交互兼容。

只作为行为/接口参考，不继续使用 Web 微信/ItChat backend。

## R5. 用户指定的 Telegram Master fork

```text
https://github.com/kettly1260/efb-telegram-master.git
```

必须用该 fork 的源码做最终集成测试。

禁止最终只执行：

```bash
pip install efb-telegram-master
```

然后声称兼容。

开发/集成测试必须至少一次：

```bash
pip install -e /path/to/efb-telegram-master-kettly
```

---

# 2. 会话 0 必须创建统一源码工作区

建议：

```text
wechat-hub-workspace/
├── stack/
├── upstream/
│   ├── linux-wechat-agent/
│   ├── wechat-selkies/
│   ├── efb-wechat-comwechat-slave/
│   ├── efb-wechat-slave/
│   └── efb-telegram-master-kettly/
├── work/
│   ├── runtime/
│   ├── core/
│   ├── efb-linux-wechat-slave/
│   ├── console/
│   └── agent/
└── docs/
    ├── UPSTREAM_LOCK.md
    ├── INTERFACE_CONTRACT_V1.md
    ├── INTEGRATION_STATUS.md
    └── SOURCE_MAP.md
```

---

# 3. 会话 0：强制源码拉取步骤

实际执行等效命令：

```bash
mkdir -p upstream work stack docs

git clone https://github.com/xiaoguiwucan/linux-wechat-agent.git upstream/linux-wechat-agent
git clone https://github.com/nickrunning/wechat-selkies.git upstream/wechat-selkies
git clone https://github.com/ehForwarderBot/efb-wechat-comwechat-slave.git upstream/efb-wechat-comwechat-slave
git clone https://github.com/ehForwarderBot/efb-wechat-slave.git upstream/efb-wechat-slave
git clone https://github.com/kettly1260/efb-telegram-master.git upstream/efb-telegram-master-kettly
```

如果仓库已经存在，禁止直接删除。先：

```bash
git -C <repo> status --short
git -C <repo> remote -v
git -C <repo> fetch --all --tags --prune
```

确认没有用户未提交修改后再决定更新。

---

# 4. 必须锁定 upstream 版本

生成：

```text
docs/UPSTREAM_LOCK.md
```

至少包含：

| Repo | Remote | Branch | Commit | Dirty |
|---|---|---|---|---|
| linux-wechat-agent | ... | ... | 真实 hash | no/yes |
| wechat-selkies | ... | ... | 真实 hash | no/yes |
| efb-wechat-comwechat-slave | ... | ... | 真实 hash | no/yes |
| efb-wechat-slave | ... | ... | 真实 hash | no/yes |
| kettly1260/efb-telegram-master | ... | ... | 真实 hash | no/yes |

Commit 必须来自：

```bash
git rev-parse HEAD
```

---

# 5. 必须先输出 SOURCE_MAP.md

会话 0 在正式改造前必须建立：

```text
docs/SOURCE_MAP.md
```

## linux-wechat-agent

必须实际定位：
- 消息 ingest 入口；
- media sync 入口；
- member/contact sync；
- DB key 提取入口；
- GUI Sender / window controller；
- Console backend；
- Console frontend；
- AI Memory；
- outbox/reply 相关代码。

## wechat-selkies

必须实际定位：
- Dockerfile；
- docker-compose；
- `root/`；
- autostart/startup；
- Openbox/X11/Selkies 初始化；
- `AUTO_START_WECHAT`；
- `/config` 用户数据逻辑。

## ComWechat Slave

必须实际定位：
- Channel 主类；
- Chat manager；
- message processor；
- send_message dispatch；
- file/media handling；
- reply/target；
- MessageRemoval；
- vendor_specific。

## 老 EWS

实际定位：
- Channel；
- ChatManager；
- 消息转换；
- get_chats/get_chat；
- send_message。

## Kettly ETM

实际定位：
- master message handling；
- `/link`；
- chat mapping；
- reply target；
- database；
- proxy/network；
- Forum Topic。


---

# 6. 每个执行 Agent 必须先做自己的 SOURCE_AUDIT

禁止 A/B/C/D/E 开会话后直接编码。

第一份 commit 前必须生成：

```text
SOURCE_AUDIT_A.md
SOURCE_AUDIT_B.md
SOURCE_AUDIT_C.md
SOURCE_AUDIT_D.md
SOURCE_AUDIT_E.md
```

内容必须包含：

1. 实际阅读的仓库；
2. upstream commit；
3. 实际阅读的源码文件；
4. 可直接复用的函数/类；
5. 必须修改的函数/类；
6. 必须新增的功能；
7. 明确不复用的代码及原因；
8. 测试入口；
9. 风险；
10. 本工作包真实修改位置。

没有 `SOURCE_AUDIT_X.md`：

> 当前工作包自动 Gate FAIL。

---

# 7. 工作分支/工作副本规则

A/B/C/D/E 不得在同一个 checkout 同时修改。

## A Runtime

工作基线：

```text
upstream/wechat-selkies
```

创建：

```text
work/runtime
branch: feat/multi-account-runtime
```

## B Core

工作基线：

```text
upstream/linux-wechat-agent
```

创建：

```text
work/core
branch: feat/multi-account-core
```

## C EFB

工作基线：

```text
upstream/efb-wechat-comwechat-slave
```

派生：

```text
work/efb-linux-wechat-slave
branch: feat/linux-wechat-slave
```

同时只读使用：

```text
upstream/efb-wechat-slave
upstream/efb-telegram-master-kettly
```

## D Console

同样基于：

```text
upstream/linux-wechat-agent
```

但必须是独立 worktree/clone：

```text
work/console
branch: feat/decoupled-console
```

## E Agent

优先审计：

```text
upstream/linux-wechat-agent/ai
upstream/linux-wechat-agent/memory
upstream/linux-wechat-agent/agent_console
```

再建立：

```text
work/agent
branch: feat/mcp-monitor-agent
```

允许新服务化，但不能未经审计把现有 AI/Memory 全部重写。

---

# 8. 工作包 A：必须真正改造 wechat-selkies

A Agent 不能新建一个假的 runtime 服务。

首先审计：

```text
Dockerfile
docker-compose.yml
root/**
startup/autostart scripts
PUID/PGID
/config
AUTO_START_WECHAT
Openbox/X11/Selkies
```

## 8.1 P0-0 多微信 POC

必须尝试：

### 方案 A

```text
同 container
同 X Display
不同 Unix user
不同 HOME/XDG
多个官方微信进程
```

若失败，再尝试：

### 方案 B

```text
同 container
不同 X Display
不同 Unix user
不同 HOME/XDG
```

只有两种都真实验证失败，才允许结论：

```text
单容器多微信不可行
```

## 8.2 必须在源码中新增/改造

至少：

```text
account runtime registry
multi-user bootstrap
account-specific HOME
account-specific XDG
微信进程 start/stop/restart
window registry
account_id -> PID/window/display
health/status
```

若共享 DISPLAY：

```text
global clipboard/xdotool lock
```

## 8.3 必须保留

不得破坏：

```text
Selkies Web UI
GPU acceleration
/config persistence
official WeChat install/update
WebRTC
existing environment variables
```

---

# 9. 工作包 B：必须真正改造 linux-wechat-agent

B 不能新建一个完全不使用原项目的 `wechat-core`。

必须优先复用：

```text
memory/
tools/wechat-decrypt/
现有消息/成员/媒体同步
现有 sender/controller
现有 outbox/状态代码
```

## 9.1 强制审计对象

必须实际找出并阅读：

```text
memory ingest
media sync
member/contact sync
find_all_keys_linux.py 或当前等效实现
wechat_controller.py 或当前等效实现
docker-compose.yml
.env.example
```

## 9.2 改造方向

从：

```text
单 WECHAT_ACCOUNT_DIR_NAME
单 memory sqlite
单窗口 sender
```

改为：

```text
account registry
多账号 sync worker
account_id 全链路
统一 normalized DB
stable Core API
account-aware sender
```

## 9.3 Regression

必须比较：

```text
原单账号模式
vs
新多账号模式
```

至少确认原项目可读取的：

```text
聊天
消息
成员
图片/媒体
```

新 Core 仍能读取。

## 9.4 文件迁移追踪

若把：

```text
memory_ingest.py
media_sync.py
wechat_controller.py
```

拆成新模块，必须在 `SOURCE_AUDIT_B.md` 明确：

```text
old path -> new path
```

---

# 10. 工作包 C：以 ComWechat Slave 为 EFB 源码基线

C Agent 不允许：

```text
从空白创建只有 poll()/send_message() 的简陋 Slave
```

必须：

1. clone ComWechat Slave；
2. 阅读真实 Channel/Chat/Message 代码；
3. 以其 EFB 适配结构作为主要参考/派生基线；
4. 替换 ComWechatRobot/Windows backend；
5. 改为 `wechat-core HTTP API` backend。

## 10.1 必须保留/迁移的设计

逐项审计并尽可能复用：

```text
GroupChat
PrivateChat
ChatMember
incoming message conversion
vendor_specific
send_message type dispatch
msg.target / reply
file pending
MessageRemoval
EFB status
```

## 10.2 明确禁止照搬

```text
Hook backend
Windows-only code
global mutable class state
TTLCache 作为可靠投递
单账号全局变量
ComWechatRobot API
```

---

# 11. C Agent 必须使用 Kettly ETM 本地源码测试

不能只说“理论兼容”。

建立测试 venv，例如：

```bash
python -m venv .venv
. .venv/bin/activate

pip install -e ../../upstream/efb-telegram-master-kettly
pip install -e .
```

必须确认实际加载路径：

```python
import efb_telegram_master
print(efb_telegram_master.__file__)
```

应指向用户指定 Kettly fork 的 editable source。

---

# 12. C Agent 必须同时读老 EWS

建立：

```text
docs/EFB_BEHAVIOR_COMPAT.md
```

逐项对比：

| 行为 | old EWS | ComWechat | Linux Slave |
|---|---|---|---|
| get_chats | | | |
| GroupChat | | | |
| member | | | |
| /link | | | |
| private text | | | |
| group text | | | |
| image | | | |
| file | | | |
| reply | | | |
| recall | | | |

目标：

> Telegram 使用体验尽可能接近原 EWS，而不是只做到“能发文字”。

---

# 13. 工作包 D：Console 必须从现有 agent_console 改造

D 不允许抛弃当前控制台后重画空 Dashboard。

必须先审计：

```text
agent_console/
web/
design_mockups/
现有 API
现有状态页面
现有日志
现有消息/记忆相关 UI
```

必须先列出：

```text
现有 Console 已有功能
继续保留的功能
移动到 Agent 的功能
删除/弱化的功能
新增功能
```

目标：

```text
wechat-console
  required: wechat-core
  optional: efb-multi
  optional: wechat-agent
```

Saved Messages 必须真实落库：

```text
saved_messages
saved_message_media
```

并支持：

```text
snapshot
note
tags
permanent attachment archive
```

---

# 14. 工作包 E：Agent 必须先复用现有 AI/Memory

E 必须审：

```text
linux-wechat-agent/ai/
linux-wechat-agent/memory/
现有 skill 机制
现有群摘要
现有图片理解
现有 model config
```

然后明确：

```text
哪些保留
哪些作为可选 AI Memory
哪些迁移到 Monitor
哪些删除
哪些新增 MCP
```

重点新增：

```text
MCP Streamable HTTP
Monitor Engine
Records
Template
Scheduler
```

但不能为了 MCP 把现有有效的：

```text
模型调用
图片理解
群摘要
```

全部重新实现一遍。


---

# 15. Stack 仓库必须真实集成源码 build

会话 0 / Integrator 必须在：

```text
stack/
```

创建最终 Compose。

禁止最终 Compose 全部指向不存在的未来镜像。

开发模式至少应能指向真实源码：

```yaml
services:
  wechat-runtime:
    build:
      context: ../work/runtime

  wechat-core:
    build:
      context: ../work/core

  efb-multi:
    build:
      context: ../work/efb-linux-wechat-slave

  wechat-console:
    build:
      context: ../work/console

  wechat-agent:
    build:
      context: ../work/agent
```

若 EFB 采用 Host Python，也必须提供：

```text
pyproject/requirements
venv setup script
systemd/supervisor sample
```

---

# 16. 五组件必须继续完全解耦

最低可用：

```text
wechat-runtime
+
wechat-core
```

可选：

```text
efb-multi
wechat-console
wechat-agent
```

必须真实测试：

```text
无 EFB
无 Agent
无 Console
```

核心继续工作。

---

# 17. Core API 契约必须先冻结

会话 0 必须提供：

```text
docs/INTERFACE_CONTRACT_V1.md
```

建议同时：

```text
stack/contracts/openapi.yaml
```

C/D/E 只能依赖：

```text
OpenAPI / Interface Contract
```

不能因为 B 未完成而直接读：

```text
work/core/*.sqlite
```

---

# 18. C/D/E 必须使用 Mock Core，而不是等待 B

会话 0 必须提供：

```text
stack/mock-core/
```

至少模拟：

```text
GET /health
GET /v1/accounts
GET /v1/accounts/{id}/chats
GET /v1/events/poll
POST /v1/events/ack
GET /v1/media/{id}
POST /v1/send/text
POST /v1/send/image
POST /v1/send/file
```

---

# 19. 每个 Agent 的开工提示词

## 会话 A

> 不要从零创建 runtime。先读取 `SOURCE_MAP.md`，确认 `wechat-selkies` 源码已 clone；若不存在则自行 clone `https://github.com/nickrunning/wechat-selkies.git`。先完成源码审计并生成 `SOURCE_AUDIT_A.md`，然后在该源码派生分支上实施多账号 Runtime。

## 会话 B

> 不要从零创建 Core。必须 clone/使用 `https://github.com/xiaoguiwucan/linux-wechat-agent.git`，先审计 `memory/`、`tools/wechat-decrypt/`、`agent_console/wechat_controller.py` 或当前等效代码，再将现有同步/解密/Sender 多账号化并服务化。

## 会话 C

> 不要从零写 EFB Slave。必须 clone `efb-wechat-comwechat-slave`、`efb-wechat-slave` 和用户指定的 `kettly1260/efb-telegram-master`，以 ComWechat Slave 的 EFB 适配层为主要基线，替换 backend 为 Core HTTP API，并用 Kettly fork 的本地 editable 源码做真实集成测试。

## 会话 D

> 不要新画一个与原项目无关的 Dashboard。必须从 `linux-wechat-agent` 当前 `agent_console/` / `web/` 源码审计和迁移已有功能，然后拆成只强依赖 Core 的 Console。

## 会话 E

> 不要从零重写 AI Memory。必须先审计 `linux-wechat-agent/ai/`、`memory/` 和现有 skill/模型代码，复用有效能力，再新增通用 MCP / Monitor / Records。

---

# 20. 完成报告必须附“源码利用报告”

每个 Agent 最后必须增加：

## Upstream used

```text
repo @ commit
```

## Reused code

列出：

```text
原文件
原类/函数
新位置
改造内容
```

## New code

说明为什么无法从指定仓库直接复用。

## Not reused

说明哪些上游代码故意不采用及原因。

如果某工作包明确要求基于上游改造，但最终：

```text
Reused code = none
```

默认判定任务未按要求执行。

---

# 21. Git 历史和许可证

尽量保留：

```text
upstream remote
```

派生项目必须保留原 LICENSE 和必要 attribution。

不得删除原版权/许可证文件来伪装成全新项目。

---

# 22. 总控会话最终审计重点

会话 0 必须检查：

```text
A 是否真的基于 wechat-selkies 修改
B 是否真的基于 linux-wechat-agent 修改
C 是否真的审并使用 ComWechat/EWS/Kettly ETM
D 是否真的迁移现有 agent_console
E 是否真的审现有 AI/Memory
```

不仅看“功能是否跑通”，还要看：

```text
有没有错误地重新造轮子
```

---

# 23. 并行开发顺序

会话 0 先完成：

```text
clone
UPSTREAM_LOCK
SOURCE_MAP
INTERFACE_CONTRACT
Mock Core
工作分支/工作副本
```

然后：

```text
A Runtime
B Core
C EFB
D Console
E Agent
```

五个会话可同时开始。

---

# 24. Gate

## Gate 0
真实双微信单容器 Runtime。

## Gate 1
基于 `linux-wechat-agent` 改造的多账号 Core。

## Gate 2
基于 ComWechat EFB 层 + Kettly ETM fork 的 Text 双向。

## Gate 3
Image / File / restart / echo / `/link`。

## Gate 4
基于原 Console 改造后的独立 Console + Saved Messages。

## Gate 5
基于原 AI/Memory 审计后的 MCP/Monitor/Records。

## Gate 6
五组件解耦矩阵全部通过。

---

# 25. 最终定义

本项目不是：

```text
“看完几个 GitHub README 后重新写五个服务”
```

而是：

```text
wechat-selkies
      ↓ 实际派生
wechat-runtime

linux-wechat-agent
      ↓ 实际派生/拆分
wechat-core + wechat-console + 可复用 AI 基础

efb-wechat-comwechat-slave
      ↓ EFB Adapter 基线
efb-linux-wechat-slave

efb-wechat-slave
      ↓ 行为兼容参考

kettly1260/efb-telegram-master
      ↓ 原源码直接集成
Telegram Master
```

只有完成真实源码审计后，才允许新增缺失组件。

这条规则优先级高于开发速度。
