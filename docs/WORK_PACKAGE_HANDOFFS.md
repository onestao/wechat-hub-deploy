# Work Package Handoffs

All packages start by reading `UPSTREAM_LOCK.md`, `SOURCE_MAP.md`, `INTERFACE_CONTRACT_V1.md` and this file. A missing package audit is an automatic Gate failure.

## A Runtime

- Checkout: `work/runtime`
- Branch: `feat/multi-account-runtime`
- Required first artifact: `SOURCE_AUDIT_A.md`
- Baseline: actual `wechat-selkies` source and Selkies base image
- First proof: same container + same display + different Unix user/HOME/XDG; only then try separate displays
- Preserve: `/config`, Web UI/WebRTC, GPU, official WeChat installation, PUID/PGID and existing environment variables
- Must replace global `pkill`/single-process scripts with account-specific registry, PID/window/display and health operations

## B Core

- Checkout: `work/core`
- Branch: `feat/multi-account-core`
- Required first artifact: `SOURCE_AUDIT_B.md`
- Reuse: `memory/`, `tools/wechat-decrypt/`, sender/controller and durable reply/outbox behavior
- Add: account registry, account-scoped workers, normalized durable database/events/API and account-aware sender
- Regression: compare original single-account chat/message/contact/member/media visibility with new mode
- Document every moved source file as `old path -> new path`

## C EFB Linux WeChat Slave

- Checkout: `work/efb-linux-wechat-slave`
- Branch: `feat/linux-wechat-slave`
- Required first artifact: `SOURCE_AUDIT_C.md`
- Read-only references: `upstream/efb-wechat-slave`, `upstream/efb-telegram-master-kettly`
- Base EFB design on ComWechat `ComWeChatChannel`, `ChatMgr`, `MsgProcess` and send dispatch; replace backend with Core HTTP API
- Do not retain `WeChatRobot`, Hook/Windows code, global mutable channel state, TTL delivery reliability or global file-pending dictionaries
- Required compatibility document: `docs/EFB_BEHAVIOR_COMPAT.md`
- Required integration proof: editable Kettly ETM source path, real `/link` mapping behavior and text duplex against Mock/real Core as appropriate

## D Console

- Checkout: `work/console`
- Branch: `feat/decoupled-console`
- Required first artifact: `SOURCE_AUDIT_D.md`
- Migrate existing `agent_console/`, `web/`, APIs, logs, memory, photos, skills and status workflows
- Required dependency: Core only; EFB and Agent are optional
- Saved Messages must use durable `saved_messages` and `saved_message_media` storage with snapshot, note, tags and attachment archive

## E Agent

- Checkout: `work/agent`
- Branch: `feat/mcp-monitor-agent`
- Required first artifact: `SOURCE_AUDIT_E.md`
- Audit and reuse `ai/`, `memory/`, builtin skills, image understanding, summaries and model configuration
- Add Streamable HTTP MCP, Monitor Engine, Records, Templates and Scheduler without duplicating existing working AI paths
- Core events/API are the input boundary; Core SQLite is off limits

## Shared Development Endpoint

Run `stack/mock-core/app.py` or the default `stack/docker-compose.yml` service and use Core API V1. The `implementation` profile is reserved for later full-source integration after the packages provide runnable service entrypoints.
