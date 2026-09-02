# Source Map

Audit date: 2026-08-31. This map is based on source files read from the commits locked in `UPSTREAM_LOCK.md`; it is not inferred from README files alone.

## linux-wechat-agent

Upstream: `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb`

| Capability | Source entry | Important symbols / behavior | Session 0 conclusion |
|---|---|---|---|
| Message ingest | `memory/sync_worker.py`, `memory/memory_ingest.py` | `run_once`, `ingest_memory`, `iter_message_tables`, `ingest_chat`, `init_memory_db` | Reuse the decrypt -> ingest orchestration and SQLite parsing. Add `account_id` to worker inputs, primary keys, tables, status and normalized output. |
| Incremental decrypt | `memory/decrypt_sync.py` | `refresh_decrypted`, `source_signature`, WAL patching and state-file logic | Reuse per-account by namespacing decrypted directories, keys and sync state. |
| Media sync | `memory/media_sync.py` | `sync_media`, `sync_image`, `sync_sticker`, `sync_video`, `upsert_media` | Reuse decoders and resource lookup. Add account-scoped paths and media identifiers. |
| Contact/session sync | `memory/memory_ingest.py` | `load_contact_names`, `load_sessions`, `resolve_paths` | Reuse queries; normalize contacts/sessions by `(account_id, remote_id)`. |
| Group member decoding | `agent_console/daily_report.py` | `decode_chatroom_members_buffer`, `contact_names` | Extract from Console ownership into Core member sync; retain decoding behavior and tests. |
| DB key extraction | `tools/wechat-decrypt/find_all_keys_linux.py`, `tools/wechat-decrypt/key_scan_common.py`, `scripts/extract-wechat-keys.sh` | `get_pids`, `_get_readable_regions`, `scan_memory_for_keys`, `cross_verify_keys`, `save_results` | Reuse Linux `/proc/<pid>/mem` scanner. It already enumerates multiple WeChat PIDs, but output/config is single-account and must be associated with runtime account records. Requires root or `CAP_SYS_PTRACE`; this is a practical security risk, not a normal unprivileged operation. |
| Account discovery | `scripts/detect-wechat-account.sh`, `.env.example`, `docker-compose.yml` | Selects one most-recent `db_storage` and writes `WECHAT_ACCOUNT_DIR_NAME` | Replace single selection with a registry; retain discovery heuristics as an import/bootstrap path. |
| GUI sender/window control | `agent_console/wechat_controller.py` | `find_main_window`, `open_chat`, `paste_active`, `paste_mention_active`, `paste_image_active`, `window_status` | Reuse interaction primitives. Replace global `DISPLAY = ":1"` and global window selection with account-aware display/window selection and a shared-display lock. |
| Reply/outbox | `agent_console/app.py` | `create_reply_outbox`, `update_reply_outbox`, `reply_outbox_list`, `paste_reply_to_wechat`, send confirmation helpers | Move durable delivery state into Core. Preserve statuses, attempts, confirmation details and idempotency semantics. |
| Console backend | `agent_console/app.py` | status/config, memory review, photo gallery, reply, skills, logs and suite-control APIs | D must migrate existing behavior, then make Core its only required dependency. Docker-socket and AI/Agent controls become optional integrations. |
| Console frontend | `agent_console/static/index.html`, `agent_console/static/app.js`, `agent_console/static/styles.css`, `design_mockups/` | chats/messages, memory, photos, skills, logs, auto-reply and status views | Reuse UI flows and visual assets; remove direct knowledge of local SQLite and container names. |
| Read-only message viewer | `web/app.py`, `web/static/` | `api_summary`, `api_chats`, `api_messages`, `api_search`, media serving | Candidate for a small Core-backed compatibility view or regression oracle. |
| AI memory | `memory/ai_memory_core.py`, `memory/ai_memory_worker.py`, `ai/app.py`, `ai/cli.py` | `index_once`, `search_chunks`, `build_context`, `list_chats`, FTS/vector tables | E should retain indexing/search/context behavior and make account scope explicit. |
| Existing AI/skills | `agent_console/app.py`, `agent_console/builtin_skills/`, `memory/ai_memory_core.py` | LLM calls, image understanding, group summaries, skill registry/runs, web search and meme sender | Reuse proven model/skill paths; separate optional Agent service from Core and Console. |

Current single-account constraints are visible in `WECHAT_ACCOUNT_DIR_NAME`, one `runtime/memory/wechat_memory.sqlite`, one fixed display, and one sender/outbox ownership boundary.

## wechat-selkies

Upstream: `b3b5341a26b803e06a1a7daaf420151297da4e79`

| Capability | Source entry | Important behavior | Session 0 conclusion |
|---|---|---|---|
| Runtime image | `Dockerfile` | Extends `ghcr.io/linuxserver/baseimage-selkies:ubuntunoble`, installs official Linux WeChat per architecture, preserves Selkies/GPU base | A must modify this image rather than replace it. |
| Compose | `docker-compose.yml` | `/config` persistence, `/dev/dri`, ports 3000/3001, PUID/PGID and restart policy | Preserve these interfaces while adding account registry/runtime control. |
| Autostart | `root/defaults/autostart`, `root/scripts/start.sh` | `/scripts/start.sh` launches one `/usr/bin/wechat` when `AUTO_START_WECHAT=true` | Replace the single launch with registry-driven bootstrap while retaining legacy one-account behavior. |
| Process control | `root/scripts/wechat/wechat-start.sh`, `wechat-stop.sh`, `wechat-restart.sh` | Global `pgrep/pkill -f /usr/bin/wechat`; no account identity | Refactor to account-specific Unix user, HOME/XDG, PID and display. Global `pkill` cannot remain. |
| X11/Openbox/Selkies | inherited base image plus `root/scripts/start.sh`, `root/defaults/menu.xml` | Openbox config lives under `/config/.config`; one desktop/display is assumed | POC A should first test same display with different Unix users/HOME/XDG, then separate displays only if required. |
| Window discovery | `root/scripts/window_switcher.py` | Enumerates `_NET_CLIENT_LIST` on the current display | Useful reference for window registry, but current implementation is display-global and deprecated in startup. |

`AUTO_START_WECHAT`, official package installation, `/config`, WebRTC UI, hardware acceleration and existing environment variables are compatibility requirements.

## efb-wechat-comwechat-slave

Upstream: `989db6947f565dbbb5588d04edfca3cf5ca49c24`

| Capability | Source entry | Important symbols / behavior | Session 0 conclusion |
|---|---|---|---|
| Channel | `efb_wechat_comwechat_slave/ComWechat.py` | `ComWeChatChannel`, EFB metadata, supported message types, `poll`, `stop_polling` | Use as the C package structure and EFB lifecycle baseline. Replace `WeChatRobot` backend with Core HTTP client. |
| Chat manager | `ChatMgr.py`, `CustomTypes.py` | `build_efb_chat_as_group`, `build_efb_chat_as_private`, `build_efb_chat_as_member`, system chat | Reuse/adapt constructors; remove global `ChatMgr.slave_channel` and bind per channel instance/account. |
| Incoming conversion | `MsgProcess.py`, `MsgDeco.py` | `MsgProcess`, `MsgWrapper`, quote formatting and message-type wrappers | Reuse conversion ideas and tests; translate normalized Core events rather than ComWechat callback dictionaries. |
| Send dispatch | `ComWechat.py` | `send_message`, `send_text`; text/link/image/sticker/file/video/animation/voice dispatch | Preserve EFB type dispatch and reply behavior, but dispatch to `/v1/send/*`. |
| Reply/target | `ComWechat.py:send_text`, `MsgProcess.py` | Creates WeChat quote XML for outgoing target; incoming type 57 can set `Message.target` | Preserve `msg.target` semantics with stable Core message IDs and `target_message_id`. |
| File/media pending | `ComWechat.py:handle_msg`, `handle_file_msg` | Global `file_msg` waits for files, then emits EFB messages; timeout fallback | Replace global polling dictionary with Core media readiness/events and durable state. |
| Recall | `ComWechat.py:on_revoked_msg` | Emits EFB `MessageRemoval` | Preserve by mapping `message.removed` Core events. |
| `vendor_specific` | `MsgProcess.py` | `wx_xml`, `comwechat_info`, `is_mp`, `is_forwarded`, share/refer metadata | Preserve stable useful fields; namespace backend-specific data and do not expose Windows Hook details. |
| Local DB | `db.py` | Peewee `GroupChatInfo` alias cache | Migrate only alias/member persistence needed by EFB; account scope is mandatory. |

Do not reuse: `WeChatRobot`, Hook/Windows paths, class-level contacts/groups/caches, TTLCache as delivery reliability, global file dictionaries, or the Dockerfile's remote installation of an unrelated ETM fork.

## efb-wechat-slave

Upstream: `80dadf21558c1be28d7ec23f247383b5a229975b`

| Capability | Source entry | Important symbols / behavior | Compatibility use |
|---|---|---|---|
| Channel | `efb_wechat_slave/__init__.py` | `WeChatChannel`, `poll`, `send_message`, `send_status`, `get_chats`, `get_chat`, `get_message_by_id` | Behavioral reference only; do not reuse Web WeChat/wxpy backend. |
| Chat model/cache | `efb_wechat_slave/chats.py` | ChatManager conversions, members, aliases and pictures | Reference expected GroupChat/PrivateChat/member behavior after `/link`. |
| Incoming conversion | `efb_wechat_slave/slave_message.py` | `SlaveMessageManager`, decorators, text/media/link/system/recall handlers | Reference EWS UX, substitutions, recall and file lifecycle. |
| Outgoing conversion | `efb_wechat_slave/__init__.py:send_message` | Target quote fallback, media dispatch, edit/recall policy, returned message IDs | Compatibility target for Telegram behavior and error reporting. |

The vendored `itchat`/`wxpy` tree is explicitly not a Linux backend candidate.

## kettly1260/efb-telegram-master

Upstream: `36b3382ed784efeba176dba269df47d4df0ef4e7`

| Capability | Source entry | Important symbols / behavior | C integration requirement |
|---|---|---|---|
| Master channel | `efb_telegram_master/__init__.py` | `TelegramChannel`, manager wiring, `send_message`, `send_status`, polling | Install this local source editable for integration tests and verify `efb_telegram_master.__file__`. |
| Telegram -> Slave | `master_message.py` | `MasterMessageProcessor`, `process_telegram_message`, `attach_target_message`, type map, per-message DB logging | Linux Slave must accept the EFB messages and target objects produced here. |
| Slave -> Telegram | `slave_message.py` | `SlaveMessageProcessor.send_message`, `dispatch_message`, media handlers, reply resolution, status/recall | Linux Slave events must provide stable IDs, chat/author objects, files and targets compatible with this processor. |
| `/link` and mapping | `chat_binding.py` | `link_chat_show_list`, `link_chat_exec`, `link_chat`, `unlink_all`, chat heads and suggestions | `get_chats/get_chat` quality directly controls `/link` UX. |
| Forum Topic | `chat_binding.py` | `_update_forum_group_info`, `_update_single_topic_info`, `create_topic`, topic migration | Preserve unique account-aware chat IDs so topics do not collide across accounts. |
| Chat objects | `chat.py`, `chat_object_cache.py`, `chat_destination_cache.py` | ETM chat wrappers, link state and cached destinations | C tests must cover GroupChat, PrivateChat and members. |
| Reply target | `master_message.py:attach_target_message`, `slave_message.py:_find_wechat_quote_target` | DB-backed target resolution and WeChat quote fallback | Core message IDs must remain stable across restarts and echoes. |
| Database | `db.py` | `TopicAssoc`, `ChatAssoc`, `MsgLog`, aliases and slave chat info | Integration tests should use real ETM migrations and mappings, not a fake master. |
| Proxy/network | `wizard.py`, `bot_manager.py`, configuration `request_kwargs` | HTTP/SOCKS proxy, read/connect timeouts, retry/rate limiting | Preserve configuration compatibility; tests may mock Telegram transport. |

## Cross-Component Ownership

| Concern | Owner | Consumers |
|---|---|---|
| WeChat process, user/HOME/XDG/display/window | Runtime | Core sender and health |
| Decrypt, normalize, durable events, send outbox | Core | EFB, Console, Agent |
| EFB chat/message adaptation | EFB Linux WeChat Slave | Kettly ETM |
| Human operations and Saved Messages | Console | Core; optional Agent/EFB |
| AI memory, MCP, monitor, records and scheduler | Agent | Core events/API; optional Console |

C/D/E must not read Core SQLite files. Their development dependency is `stack/contracts/openapi.yaml` and `stack/mock-core/`.
