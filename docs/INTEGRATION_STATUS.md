# Integration Status

Updated: 2026-09-01 (post-implementation integrator review, Asia/Shanghai)

## Executive state

The source-derived A/B/C/D/E implementations now exist and their local
development-boundary regression suites pass. Gate 0 has real Unraid evidence
and Gate 1 has real two-account read-path evidence. The remaining acceptance
work is concentrated in credentials/login-dependent write paths and the real
Docker/Telegram/WeChat integration matrix; Mock Core or YAML parsing is not
reported as live proof.

This review also repaired unattended deployment gaps in the shared stack,
Runtime/Core startup ordering, adapter capability negotiation, conservative
text-echo reconciliation, and Agent configuration persistence.

## Source and lineage audit

| Item | Status | Evidence |
|---|---|---|
| Required upstream repositories and lock | PASS | `docs/UPSTREAM_LOCK.md`, `docs/SOURCE_MAP.md` |
| A source audit | PASS | `work/runtime/SOURCE_AUDIT_A.md` |
| B source audit | PASS | `work/core/SOURCE_AUDIT_B.md` |
| C source audit / Kettly compatibility | PASS | `work/efb-linux-wechat-slave/SOURCE_AUDIT_C.md`, `work/efb-linux-wechat-slave/docs/EFB_BEHAVIOR_COMPAT.md` |
| D source audit | PASS | `work/console/SOURCE_AUDIT_D.md` |
| E source audit | PASS | `work/agent/SOURCE_AUDIT_E.md` |
| Frozen Core V1 | PASS | `docs/INTERFACE_CONTRACT_V1.md`, `stack/contracts/openapi.yaml` |
| Mock Core | PASS | `stack/mock-core/`; 5/5 HTTP tests |
| A-E upstream Git ancestry | PASS | all five locked base commits are ancestors of their work branches |
| C real local editable Kettly source | PASS | `.venv-c` compatibility tests load the locked editable source tree |

Branches remain the taskbook branches:

| Package | Branch | Locked base |
|---|---|---|
| A Runtime | `feat/multi-account-runtime` | `b3b5341a26b803e06a1a7daaf420151297da4e79` |
| B Core | `feat/multi-account-core` | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` |
| C EFB | `feat/linux-wechat-slave` | `989db6947f565dbbb5588d04edfca3cf5ca49c24` |
| D Console | `feat/decoupled-console` | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` |
| E Agent | `feat/mcp-monitor-agent` | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` |

The worktrees are intentionally **not described as clean** after this review:
A/B/C/E and `stack/` contain the integrator fixes listed below. D already
contained a complete uncommitted implementation before this review; those D
changes were preserved rather than overwritten or silently committed.

## Current local regression matrix

| Area | Result | Notes |
|---|---:|---|
| A Runtime | **12 / 12 PASS** | includes stale-bootstrap-readiness, Runtime account-control routing, and account-scoped in-memory login snapshot regression |
| B Core | **24 / 24 PASS** | full suite; includes watcher-driven registry hot reload, Runtime management, capability and conservative text-echo cases |
| C EFB | **18 / 18 PASS** | run with `.venv-c`; includes real editable Kettly compatibility |
| D Console | **8 / 8 PASS** | includes Runtime lifecycle plus direct login-status/no-store login-snapshot proxy through Core/Mock Core |
| E Agent | **9 / 9 PASS** | includes headless legacy-LLM env override behavior |
| Stack Mock Core | **6 / 6 PASS** | includes optional Runtime-management contract simulation |
| Stack topology | **6 / 6 PASS** | profiles, persistence, Runtime custom-service hook, health ordering and loopback bindings |
| Compose/OpenAPI YAML parsing | PASS | PyYAML parsing on current host |

The current Windows coding host has no Docker CLI. The coding sandbox also
does not inherit the user's password-protected PowerShell SSH agent, so this
review could not execute the final Docker build/matrix on Unraid. That boundary
is recorded as pending rather than inferred from YAML tests.

## Unattended deployment repairs completed

### 1. Stack is actually decoupled

`stack/docker-compose.yml` now makes Runtime + Core the minimum production
pair. Console, Agent and EFB have separate profiles and do not force each other
to start. Runtime retains the upstream Selkies/GPU/login/restart controls.

Persistent state is explicit:

- Runtime config/account homes;
- Runtime display-lock/readiness state;
- Core database/account worker state;
- Console projection/Saved Messages archive;
- Agent database and reused legacy AI configuration;
- operator-supplied EFB profile directory.

Core, Console and Agent host ports bind to loopback by default. Runtime's
Selkies ports retain their original externally reachable behavior.

### 2. Runtime -> Core startup race is guarded

`bootstrap.ready` can live on a shared/persistent Runtime state volume. A now
deletes any stale marker before bootstrap and writes a new marker only after
all account/UID reconciliation is complete. The shared stack waits for Runtime
health before starting Core, and optional services wait for Core health.

This is important for the legacy `default -> abc + /config` path because its
real UID is learned during bootstrap and persisted into the Runtime registry.

### 3. Production sender capability mismatch is explicit

Core V1 `/health` may now expose optional `sender_capabilities`. The current B
X11 sender truthfully advertises:

```text
text=false
image=false
file=false
native_reply=false
media_caption=false
max_mentions=0
echo_confirmation=false
verified_chat_target=false
```

The field is additive: absence means **unknown**, not unsupported. Mock Core
continues to advertise the full simulated V1 request surface.

C uses these capabilities to avoid known asynchronous failures. After the live
target-selection incident, the current B sender advertises every production
send primitive as unavailable. Requests must not enter the Core outbox until a
controller can verify the exact selected chat before paste/submit.

### 4. Conservative text echo reconciliation exists, but is not overclaimed

B now links a synced outgoing plain-text message to a `sent` outbox row only
when account, chat, exact text, time window and uniqueness all agree. Mention
sends and ambiguous candidates are intentionally left unmatched. The aliasing
`send.updated` event is emitted before the matching `message.created` event so
C can suppress a mapped Telegram-originated echo.

This is still **not** advertised as hard WeChat delivery confirmation because
it has not yet been proven against the live logged-in Unraid database path and
does not cover every send shape.

### 5. Agent configuration survives container replacement

The reused upstream AI configuration can now live under
`WECHAT_AGENT_LEGACY_RUNTIME_DIR`; the stack maps it inside the persistent Agent
data volume. A fresh headless deployment can optionally supply
`WECHAT_AGENT_LLM_*` base URL/model/API key/numeric settings through the
deployment environment without committing secrets or replacing the old config
format.

### 6. Console multi-WeChat management + Core registry hot reload

Runtime now owns a private root-side Unix-domain control service at
`/run/wechat-runtime/control.sock`. The socket is shared only through the
existing `runtime-state` volume; Console never receives Docker Socket or direct
process privileges. Core exposes an additive operator-only `/v1/runtime/*`
extension and Console proxies it through `/api/runtime/*`.

Console now has a **微信账号** page for create/start/stop/restart/remove. Create
can set stable `account_id`, display name, X11 display and autostart, and can
start the official WeChat client immediately for first-login scanning. Remove
stops the process and unregisters the account while preserving its HOME/login
data and Unix user.

Core no longer treats the Runtime account registry as a permanent startup
snapshot. It watches the persisted registry (default 1-second interval) and
atomically replaces the live registry object, so AccountWorker and
AccountSender see additions/removals without a Core restart. Console-driven
changes force the same reload synchronously. Removed accounts are hidden from
active `/v1/accounts`, retained as stopped historical store rows, and any
accepted/queued sends not yet dispatched are failed explicitly. In-flight
`sending` rows retain the existing lease-recovery semantics because delivery
may already have happened.

## Gate status after review

| Gate | Status | Remaining acceptance condition |
|---|---|---|
| **Gate 0** real two-WeChat single-container Runtime | **LIVE PASS** | Existing A Unraid evidence: two official clients, isolated UID/HOME, same DISPLAY and post-login window proof |
| **Gate 1** multi-account Core | **LIVE READ PASS; WRITE FAIL / DISABLED** | Replace blind X11 search selection with an exact, independently verified target primitive before any new live send test |
| **Gate 2** ComWechat + Kettly text duplex | **DEV BOUNDARY PASS; LIVE PENDING** | Real Telegram bot/admin credentials plus logged-in WeChat text round trip |
| **Gate 3** image/file/restart/echo/`/link` | **PARTIAL / BLOCKED** | Production arbitrary-file primitive is still unavailable; native reply uses visible-quote fallback; real image/restart/echo/`/link` acceptance still required |
| **Gate 4** independent Console + Saved Messages | **DEV BOUNDARY PASS** | 7/7 tests; real source-built container/Core deployment and persistence restart proof still required |
| **Gate 5** audited AI/Memory + MCP/Monitor/Records | **DEV BOUNDARY PASS** | 9/9 tests; real deployment plus external model/vision connectivity only where those actions are required |
| **Gate 6** five-component decoupling matrix | **TOPOLOGY PASS; LIVE MATRIX PENDING** | Execute source builds and start/stop matrix on Linux/Unraid; verify Runtime+Core remain healthy with each optional service absent |

## Existing Gate-1 live evidence retained

The prior isolated Unraid run proved the B read side without replacing the
Gate-0 Runtime:

- Core joined Runtime's PID namespace and shared X11/display lock state;
- account-scoped key extraction produced 16 valid DB-key entries for `gate0-a`
  and 15 for `gate0-b` without recording key values;
- sampled decrypted databases passed SQLite quick check;
- `gate0-a`: 101 chats, 4921 contacts, 5112 members, 1408 messages, 91 ready media;
- `gate0-b`: 100 chats, 3961 contacts, 4512 members, zero source messages and
  zero ready media, consistent with its source DB state at that time;
- Core health/accounts/chats, event poll/ack and media GET passed;
- sampled media returned `200 image/jpeg`, 9903 bytes;
- duplicate event-count sampling stayed stable after dedup fixes.

At the time of that proof both WeChat surfaces were on the login screen, so
earlier GUI attempts were corrected to failed and no write success was claimed.

## Gate-1 sender incident and containment

At 2026-09-01 10:11 (Asia/Shanghai), four live requests intended for the two
accounts' `filehelper` chats were accepted. The reused controller shortened the
display name `文件传输助手` to the query `文件`, pressed Return on the first search
result, and did not verify the selected chat title. The user reported that test
content appeared in an added group instead of File Transfer Assistant.

The database did not contain a matching `filehelper` echo, so the four X11
results are not delivery evidence. They were corrected from `sent` to `failed`
with an incident audit reason. The user must handle any recall manually; no
unverified automated recall action was attempted.

Containment completed:

- `wechat-core-b-gate1` was stopped immediately; Runtime and both WeChat clients
  remained running;
- the Core outbox had no accepted/queued/sending rows after correction;
- the original container and the first sync-only replacement remain stopped as
  forensic/rollback snapshots;
- the active service now runs `wechat-core:gate1-safe` with
  `--send-interval 0`;
- the controller's `open` action fails before any X11 input;
- the sender requires an explicit `controller_verifies_chat_target=true`
  capability, which the current Runtime/controller does not provide;
- local regression passed 26/26 tests.

## Residual issues that should not be hidden

1. **Production file send is not implemented by B's verified X11 primitives.**
   Core V1 retains the endpoint for future senders, but the current concrete
   sender advertises it false and C refuses it early.
2. **Native quoted reply is not verified.** Text uses a visible quote fallback;
   non-text reply semantics are rejected rather than silently changed.
3. **Production sending is disabled after a wrong-chat incident.** The current
   X11 controller cannot verify the exact selected chat. Echo reconciliation
   cannot make an unsafe pre-send target selection acceptable.
4. **Runtime management/hot reload still needs a real Linux/Unraid container acceptance run.**
   Unit/Mock Core/topology coverage is complete, but this Windows coding host
   cannot prove the s6 Runtime control service and shared Unix socket inside the
   source-built containers. No Core restart is expected after register/remove;
   that behavior must be observed on Unraid before calling it a live PASS.
5. **Console/Agent/Core HTTP endpoints do not implement their own user auth.**
   They bind to `127.0.0.1` by default in the shared stack. Any LAN/reverse
   proxy exposure must add an authentication/access-control layer.
6. **D is still uncommitted work.** Its existing working tree was intentionally
   preserved. No review step silently committed or rewrote it.

## Final live acceptance location

Use `docs/INTEGRATION_REVIEW_2026-09-01.md` for the exact safe Unraid commands
and evidence checklist. Do not convert a Mock Core result, a Compose config
render, or a successful X11 `submit` call into a claimed WeChat/Telegram Gate
PASS without the corresponding observable live evidence.
