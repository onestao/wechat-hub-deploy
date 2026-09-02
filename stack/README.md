# WeChat Hub Stack

This directory is the integration layer for the source-derived work packages in
`../work`.  Runtime and Core are the minimum production pair; EFB, Console and
Agent are optional and can be enabled independently.

## Profiles

| Command | Services started |
|---|---|
| `docker compose --profile mock up --build` | Mock Core only |
| `docker compose --profile implementation up --build -d` | Runtime + Core |
| `docker compose --profile core up --build -d` | Runtime + Core |
| `docker compose --profile console up --build -d` | Runtime + Core + Console |
| `docker compose --profile agent up --build -d` | Runtime + Core + Agent |
| `docker compose --profile efb up --build -d` | Runtime + Core + EFB |

Profiles can be combined.  For example, Console + Agent without EFB:

```bash
docker compose --profile console --profile agent up --build -d
```

This layout is deliberate: enabling one optional component never starts the
other optional components.  It is therefore suitable for the Gate-6
decoupling matrix instead of treating all five services as an inseparable
stack.

## First configuration

Copy `.env.example` to `.env` and adjust it.  An empty `WECHAT_ACCOUNTS`
preserves Package A's upstream-compatible single `default` account using
`/config`.  To opt in to two isolated accounts, set for example:

```text
WECHAT_ACCOUNTS=personal,work
WECHAT_DEFAULT_ACCOUNT_ID=personal
WECHAT_LEGACY_DEFAULT_ACCOUNT=false
```

Runtime keeps the original Selkies controls (`CUSTOM_USER`, `PASSWORD`, GPU
`/dev/dri`, nightly restart, auto-login, `/config` persistence and shared
memory sizing).  Core shares Runtime's PID namespace, X11 socket and display
lock as required by Packages A/B.

Runtime also owns a private root-side account control socket at
`/run/wechat-runtime/control.sock`.  The socket is carried only by the existing
`runtime-state` volume and is consumed by Core; it is not published to the
host.  Console account management therefore remains `Console -> Core HTTP ->
Runtime Unix socket` and never needs Docker Socket access.

For `runtime_provider=agent_wechat`, Runtime Manager alone also owns
`/var/run/docker.sock` and creates one upstream `agent-wechat` child container
per account. Core, Console, EFB and Agent never mount Docker Socket. The pinned
default is `AGENT_WECHAT_IMAGE=ghcr.io/thisnick/agent-wechat:0.11.15`; do not
use `latest` for production defaults.

AgentWechat child port `6174` is Docker-internal only and is **not** published
to the NAS/host. Browser desktop access goes through Runtime's lightweight
WeChat Hub Desktop Gateway (default host port `17892`):

```text
Browser -> Desktop Gateway -> agent-wechat internal :6174
```

Core/Console receive only a short-lived opaque gateway-session path. The real
per-account upstream token is read and injected by the gateway on the internal
hop, never returned in public JSON or the browser URL. The gateway proxies both
normal HTTP and long-lived/binary WebSocket traffic required by noVNC and has
its own access log disabled. `WECHAT_DESKTOP_GATEWAY_HOST_BIND` controls only
the browser-facing gateway; it does not expose the child REST/noVNC port.

Runtime status for AgentWechat deliberately separates `container_running`,
`agent_server_healthy` (the internal `/health` probe), and WeChat login/auth
state. A running child whose agent-server probe fails is reported as degraded,
not healthy.

Core watches `/app/config/wechat-runtime/accounts.json` (the read-only view of
Runtime's persisted registry) every `CORE_REGISTRY_RELOAD_INTERVAL` seconds,
default 1.  Direct Runtime CLI register/unregister changes are picked up
without restarting Core.  Console-driven create/remove operations ask Core to
force the same reload immediately.

With the Console profile enabled, open the Console and use **微信账号** to add,
start, stop, restart or data-preservingly remove a WeChat instance.  Removing
an account preserves its Runtime HOME/login data. AgentWechat accounts preserve
their dedicated `/data` and `/home/wechat` volumes when removed; destructive
deletion requires the explicit Core API query `purge_data=1` and is not the
Console's default action.

New/running accounts that still need login expose **扫码登录** in Console. The
Legacy flow remains `Console -> Core -> Runtime Unix socket -> account-scoped
X11 window`. AgentWechat accounts instead use the upstream login status/QR API
inside that account's isolated child container. Neither flow persists QR PNGs;
Core and Console return them with `Cache-Control: no-store`. **打开完整微信桌面**
opens Selkies for Legacy accounts and an account-scoped Desktop Gateway session
for AgentWechat accounts. AgentWechat desktop auto mode now prefers an on-demand
**Selkies Attach** companion connected to that account's existing Xvfb/WeChat;
it does not start a second WeChat or X server. The companion restores the richer
local IME/clipboard/file-transfer/resize/DPI controls familiar from the Legacy
Selkies UI. noVNC remains the automatic rescue fallback, including for an older
live AgentWechat child that has not yet been normally restarted with the new
account-private X11/files mounts. Set `WECHAT_DESKTOP_URL` only to override the
Legacy desktop URL.

Each AgentWechat account has its own browser-file exchange volume. Files uploaded
from Selkies `/config/Desktop` are visible to that same WeChat account at
`/home/wechat/WeChatHubFiles/Desktop`; another account cannot see that volume.
While a browser Desktop control WebSocket is active, Runtime holds the same
account-scoped GUI lease that Core Sender must acquire before driving the GUI.
This intentionally pauses automated sends only for the account being operated
manually; other WeChat accounts remain independent. The queued send is not
attempted or marked failed and resumes after the manual desktop disconnects.
System Clipboard API integration in Chrome/Edge is most reliable through an
HTTPS reverse proxy because LAN HTTP is not a browser secure context.
When the reverse proxy preserves the `/desktop/...` path, set
`WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=https` and optionally
`WECHAT_DESKTOP_GATEWAY_PUBLIC_HOST` / `WECHAT_DESKTOP_GATEWAY_PUBLIC_PORT` so
Console opens the secure browser-facing address while Runtime continues to
proxy the private AgentWechat/Selkies hops internally.

Core, Console and Agent host ports bind to `127.0.0.1` by default.  Change the
corresponding `*_BIND` value only when a LAN/reverse-proxy exposure is intended.
The Selkies Runtime ports retain their existing host-wide binding behavior.
`WECHAT_DESKTOP_GATEWAY_HOST_BIND` controls the separate AgentWechat browser
gateway and defaults to `0.0.0.0`; exposing that gateway never publishes the
child `6174` API or Selkies attach `8081` itself.

## EFB / Kettly Telegram Master

EFB needs operator credentials, so it is never part of the unattended
`implementation` profile.  `EFB_PROFILE_DIR` is bind-mounted at
`/root/.ehforwarderbot` and is ignored by this Git repository.  Populate a
normal EFB profile there before enabling `--profile efb`, including:

```text
profiles/default/config.yaml
profiles/default/blueset.telegram/config.yaml
profiles/default/wechat.linux/config.yaml
```

The profile-level config selects `blueset.telegram` as master and
`wechat.linux` as slave.  The Telegram module config contains the real bot
token/admin IDs.  The Linux slave config points Core to
`http://wechat-core:8080`.  Do not commit those credentials.

## Persistence

- `runtime-config`: official WeChat/Selkies config and account homes.
- `runtime-state`: shared Runtime/Core X11 automation lock/readiness state,
  private Runtime account-control Unix socket, and short-lived Desktop Gateway
  session descriptors (upstream tokens are not stored in those descriptors).
- `core-data`: Core normalized DB, per-account decrypt/sync/media runtime.
- `console-data`: Console event projection, Saved Messages and archived media.
- `agent-data`: Agent records/monitors/schedules/memory and reused legacy AI
  configuration under `/data/legacy-agent-console`.
- `EFB_PROFILE_DIR`: EFB/Kettly configuration, database and module state.

## Mock Core without Docker

```powershell
python mock-core\app.py --host 127.0.0.1 --port 8080
```

Mock Core is contract simulation only.  Passing Mock Core tests does not prove
real WeChat delivery or Telegram connectivity.

## Current live-test boundary

Package A Gate 0 and Package B's real two-account read path have been proven on
Unraid.  B's logged-in GUI send + database echo proof is still required before
declaring the write side of Gate 1 complete.  C/D/E have development-boundary
tests against Core V1, but credentials/login-dependent end-to-end Gates remain
separate acceptance work.
