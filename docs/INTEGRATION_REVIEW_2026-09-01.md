# WeChat Hub Integration Review - 2026-09-01

## Scope

This review compared the V3.0 taskbook against the current A/B/C/D/E source
work, upstream Git ancestry, Core V1 contract, local regressions and shared
deployment stack. It also applied fixes that were safe to complete without a
logged-in WeChat client, Telegram credentials, external model credentials or
destructive access to the existing Unraid services.

The authoritative status summary is `docs/INTEGRATION_STATUS.md`.

## Review result

### Source-derived implementation

PASS for the taskbook's source-use requirement:

- A is a real descendant of locked `wechat-selkies` and keeps the original
  Selkies/runtime structure.
- B, D and E are real descendants of locked `linux-wechat-agent`.
- C is a real descendant of locked `efb-wechat-comwechat-slave`, retains the
  EFB adapter shape, and its compatibility suite loads the locked local
  editable Kettly ETM source.
- all five locked base commits were verified as Git ancestors of the current
  work branches.

The review found no production C/D/E code path that opens Core's SQLite DB.
Their shared integration boundary remains Core HTTP V1.

### Local regression evidence after review fixes

```text
A Runtime        12 / 12 PASS
B Core           24 / 24 PASS
C EFB            18 / 18 PASS (.venv-c, real editable Kettly source)
D Console         8 /  8 PASS
E Agent           9 /  9 PASS
Stack Mock Core   6 /  6 PASS
Stack topology    6 /  6 PASS
Compose YAML      parse PASS
OpenAPI YAML      parse PASS
```

The follow-up Web Console login flow is covered at the development boundary:
Runtime selects only X11 windows owned by the requested account UID, serializes
window activation/capture with the shared DISPLAY lock, emits the PNG only in
memory through its private Unix socket, and Core/Console proxy it with
`Cache-Control: no-store`. Console automatically opens this login dialog after
creating+starting an account and polls until Core reports `online`. Real QR
scanning against the rebuilt Runtime image on Unraid remains a live acceptance
item because this Windows host has no Docker executable and no inherited SSH
agent.

Docker image/build claims are deliberately absent: the current Windows coding
host has no Docker executable. The coding sandbox also does not inherit the
password-protected SSH agent that is available in the user's PowerShell
session, so the final Unraid commands below were not executed by this review.

## Repairs made in this review

### Shared stack

- Runtime + Core are now the minimum production pair.
- EFB, Console and Agent are independent Compose profiles.
- Runtime retains `/dev/dri`, Selkies ports, PUID/PGID, login credentials,
  nightly restart, auto-login, `/config` and shared-memory controls.
- Core has the PID/X11/display-lock sharing required by A/B.
- Console and Agent now have persistent data volumes.
- EFB has an ignored operator-owned profile bind mount.
- Core/Console/Agent bind to loopback by default.
- Runtime, Core, Console and Agent have explicit health ordering/checks.
- a stack topology regression suite freezes the intended decoupling.

### Runtime startup safety

A's `bootstrap.ready` marker is now invalidated before every bootstrap and
written only after account/UID reconciliation completes. This closes the
restart race in which a persisted stale marker could let Core consume an
incomplete Runtime registry.

### Runtime account management / Core hot reload

The follow-up implementation closes the previous dynamic-account gap without
giving Console Docker Socket access. Runtime now runs a root-side private Unix
control service at `/run/wechat-runtime/control.sock`; Core consumes that
socket through the already-shared `runtime-state` volume and exposes an
additive operator-only `/v1/runtime/*` extension. Console has a **微信账号** page
for create/start/stop/restart/data-preserving remove.

Core also watches the persisted Runtime registry (default every 1 second) and
atomically updates the shared `AccountRegistry` object, so direct Runtime CLI
register/unregister changes are picked up by existing sync and sender loops
without restarting Core. Safe removal now has explicit semantics: active API
listing hides the account, a historical stopped row remains, accepted/queued
sends fail, `sending` rows retain lease recovery, and a stale sync iteration
cannot resurrect a removed account.

### Core/EFB send semantics

B publishes optional concrete sender capabilities without changing Core V1's
request schemas. C consumes those hints so a Mock Core feature is not confused
with a feature the current X11 sender can really execute.

Current production sender boundary:

```text
verified: plain text, one mention, image paste
not verified: arbitrary file, native quoted reply, image caption, hard echo confirmation
```

C therefore uses visible text quoting when native reply is absent and rejects
known-unexecutable operations before they become misleading asynchronous
outbox failures.

B also has a conservative exact-text echo matcher. It requires a unique recent
same-account/same-chat plain-text candidate and refuses ambiguous/mention
cases. This improves C's send-id/echo aliasing but is not treated as hard Gate-3
delivery proof until exercised against real logged-in WeChat data.

### Agent unattended configuration

The reused legacy AI config can live on Agent's persistent `/data` volume.
Fresh headless deployments can optionally supply:

```text
WECHAT_AGENT_LLM_BASE_URL
WECHAT_AGENT_LLM_MODEL
WECHAT_AGENT_LLM_API_KEY
WECHAT_AGENT_LLM_TEMPERATURE
WECHAT_AGENT_LLM_MAX_TOKENS
WECHAT_AGENT_LLM_TIMEOUT_SECONDS
```

The API key remains an operator secret; `.env` is ignored.

## Safe Unraid validation - no credentials required

Run these from a PowerShell/terminal context where `ssh unraid` already works,
then `cd` on Unraid to the copied/synced WeChat Hub repository. Replace
`<WECHAT_HUB_ROOT>` with the real remote path.

### 1. Read-only preflight

```bash
cd <WECHAT_HUB_ROOT>/stack
docker --version
docker compose version
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker compose config --profiles
docker compose --profile implementation config --services
docker compose --profile console config --services
docker compose --profile agent config --services
docker compose --profile efb config --services
```

Expected service sets:

```text
implementation -> wechat-runtime, wechat-core
console        -> wechat-runtime, wechat-core, wechat-console
agent          -> wechat-runtime, wechat-core, wechat-agent
efb            -> wechat-runtime, wechat-core, efb-multi
```

Do not continue if the proposed container names, bind mounts or ports would
collide with unrelated existing services.

### 2. Source image builds only

Image build does not need to stop existing Gate-0/Gate-1 containers:

```bash
cd <WECHAT_HUB_ROOT>/stack
docker compose --profile implementation build wechat-runtime wechat-core
docker compose --profile console build wechat-console
docker compose --profile agent build wechat-agent
docker compose --profile efb build efb-multi
```

For EFB, build success does not imply Telegram credentials/config are present.

### 3. Isolated Runtime + Core smoke test

Use a separate Compose project and non-default host ports. Do not use
`docker compose down -v`; the command below is intentionally isolated from the
existing project and its volumes.

```bash
cd <WECHAT_HUB_ROOT>/stack

AUTO_START_WECHAT=false \
RUNTIME_HTTP_PORT=39000 \
RUNTIME_HTTPS_PORT=39001 \
CORE_PORT=39080 \
docker compose -p wechat-hub-review --profile core up -d --build

docker compose -p wechat-hub-review --profile core ps
curl -fsS http://127.0.0.1:39080/health
```

Minimum success evidence:

- Runtime becomes healthy only after `bootstrap.ready` is recreated;
- Core becomes healthy after Runtime;
- Core `/health` reports contract version 1 and `sender_capabilities`;
- no Console, Agent or EFB review container exists.

Cleanup only the isolated review project, preserving volumes unless they are
explicitly confirmed disposable:

```bash
docker compose -p wechat-hub-review --profile core down
```

### 4. Gate-6 profile isolation smoke tests

Run each case with its own project name and non-conflicting ports. Keep
`AUTO_START_WECHAT=false` for the structural smoke test.

Console-only optional layer:

```bash
AUTO_START_WECHAT=false \
RUNTIME_HTTP_PORT=39100 RUNTIME_HTTPS_PORT=39101 CORE_PORT=39180 \
WECHAT_CONSOLE_PORT=39178 \
docker compose -p wechat-hub-review-console --profile console up -d --build

docker compose -p wechat-hub-review-console --profile console ps
curl -fsS http://127.0.0.1:39180/health
curl -fsS http://127.0.0.1:39178/api/health
```

Agent-only optional layer:

```bash
AUTO_START_WECHAT=false \
RUNTIME_HTTP_PORT=39200 RUNTIME_HTTPS_PORT=39201 CORE_PORT=39280 \
WECHAT_AGENT_PORT=39291 \
docker compose -p wechat-hub-review-agent --profile agent up -d --build

docker compose -p wechat-hub-review-agent --profile agent ps
curl -fsS http://127.0.0.1:39280/health
curl -fsS http://127.0.0.1:39291/health
```

For each case confirm the unrelated optional containers are absent. Then stop
only that isolated project without `-v`:

```bash
docker compose -p wechat-hub-review-console --profile console down
docker compose -p wechat-hub-review-agent --profile agent down
```

EFB is excluded from the no-credential run because a valid EFB profile and
Telegram credentials are an operator prerequisite, not something an
unattended code review should fabricate.

## Manual / credential-dependent acceptance

### Gate 1 write side

Prerequisites:

- both real WeChat clients logged in;
- each account's Runtime PID/window remains account-scoped;
- no login overlay is mistaken for a chat-ready window.

Use a unique marker per account and send only to that account's own
`filehelper`:

```text
gate0-a -> one uniquely marked text + one PNG
gate0-b -> a different uniquely marked text + one PNG
```

Acceptance requires more than an HTTP 202 or X11 submit:

- the correct WeChat window visibly receives the action;
- the correct account source DB advances;
- no peer account receives that marker;
- the subsequent normalized outgoing message/echo is observable;
- ambiguous echo matching is not accepted as proof.

### Gate 2 / Kettly Telegram

Populate the ignored EFB profile directory with real operator configuration,
including the Kettly Telegram Master token/admin IDs and the Linux WeChat Slave
pointing at `http://wechat-core:8080`. Then verify both directions with unique
text markers and account-qualified chats. `/link` must show non-colliding
account-scoped chat identities.

Never commit the Telegram token or generated EFB profile database.

### Gate 3

Current blockers/conditions are explicit:

1. arbitrary-file send needs a real production primitive in B before this
   portion can pass;
2. native quoted reply is currently a visible-quote fallback, not a native
   WeChat quote operation;
3. captioned image semantics are not supported by the current sender;
4. conservative text echo mapping needs live proof;
5. image, restart and `/link` still need real cross-component acceptance.

Do not weaken these requirements merely to turn Gate 3 green.

### Gate 4 persistence

With the Console profile running against real Core:

1. save at least one text item and one media-backed item;
2. restart/recreate only the Console container;
3. verify Saved Messages and archived media remain available from its data
   volume;
4. stop Console and verify Runtime + Core continue to work.

### Gate 5 deployment

Records/Monitor/MCP/Scheduler do not require an external LLM for their basic
service proof. Summary/vision actions do. If those actions are in the
acceptance scope, provide model credentials through the environment and verify
real request/response behavior without recording the secret in logs/reports.

## Remaining live-validation limitation

Runtime account lifecycle management and Core hot reload are covered by local
unit/Mock Core/topology tests, but the new s6 Runtime Unix-socket service has
not yet been built and exercised inside real Linux/Unraid source images from
this Windows coding environment. The next live check should prove that a
Console-created account starts an official WeChat instance, appears in Core
without a Core restart, and disappears after data-preserving removal while the
remaining accounts keep syncing.

## Git/worktree note

No automatic commits were made by this integration review.

D's full Console implementation was already uncommitted before the review and
was preserved as such. A/B/C/E/stack now also contain explicit review fixes.
Review/commit those changes per worktree after the remote acceptance level you
want is reached; do not accidentally attribute D's pre-existing uncommitted
implementation to this integrator pass.
