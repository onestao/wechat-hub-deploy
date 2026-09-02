# Core Interface Contract V1

Status: frozen for work packages C/D/E on 2026-08-31.

Canonical machine-readable definition: `stack/contracts/openapi.yaml`.

## Boundary

`wechat-core` owns account-normalized chat/message data, durable events, media retrieval and outbound delivery requests. Runtime process control remains internal to Runtime/Core integration. EFB, Console and Agent must not open Core SQLite files or the Docker socket. An additive operator-only Runtime management extension is exposed through Core for Console; EFB and Agent do not depend on it.

Base URL in development: `http://mock-core:8080` inside Compose or `http://127.0.0.1:8080` on the host.

All JSON is UTF-8. Timestamps are RFC 3339 UTC strings. Identifiers are opaque strings and must never be parsed for business meaning.

## Identity Rules

- `account_id` is stable across Core restarts and scopes every WeChat object.
- `chat_id`, `message_id`, `member_id` and `media_id` are only unique within an account unless the schema explicitly includes `account_id`.
- Consumers should use `(account_id, chat_id)` and `(account_id, message_id)` as keys.
- EFB implementations should encode both account and chat in their channel chat UID to prevent ETM `/link` and Forum Topic collisions.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness/readiness and contract version |
| GET | `/v1/accounts` | List configured accounts and runtime/sync health |
| GET | `/v1/accounts/{account_id}/chats` | List chats; optional `cursor`, `limit`, `query` |
| GET | `/v1/runtime/accounts` | Optional operator extension: live Runtime account/process state |
| POST | `/v1/runtime/accounts` | Optional operator extension: register a Runtime account and hot-apply it to Core |
| POST | `/v1/runtime/accounts/{account_id}/start\|stop\|restart` | Optional operator extension: control one WeChat process |
| DELETE | `/v1/runtime/accounts/{account_id}` | Optional operator extension: unregister an account while preserving its HOME/login data |
| GET | `/v1/runtime/accounts/{account_id}/login` | Optional operator extension: ephemeral login-session state for Console |
| GET | `/v1/runtime/accounts/{account_id}/login/snapshot` | Optional operator extension: no-store PNG of that account's WeChat login window |
| GET | `/v1/events/poll` | Poll durable events after a cursor; optional account filter |
| POST | `/v1/events/ack` | Acknowledge delivered event IDs for one consumer |
| GET | `/v1/media/{media_id}?account_id=...` | Stream media bytes with MIME/disposition headers |
| POST | `/v1/send/text` | Queue account-aware text/reply/mention delivery |
| POST | `/v1/send/image` | Queue image delivery from `media_id` or base64 content |
| POST | `/v1/send/file` | Queue file delivery from `media_id` or base64 content |

## Event Delivery

`GET /v1/events/poll` accepts:

- `after`: opaque cursor returned by the previous response; omit for the retained beginning.
- `limit`: 1-200, default 50.
- `account_id`: optional filter.
- `consumer_id`: stable consumer name for diagnostics and acknowledgement tracking.
- `timeout`: requested long-poll seconds, 0-30. The Mock Core returns immediately.

Events are ordered by cursor and delivered at least once. Consumers must be idempotent by `event_id`. A response contains `events` and `next_cursor`; advance only after local processing succeeds. `POST /v1/events/ack` records `consumer_id` and `event_ids`, but acknowledgement does not replace cursor persistence.

Initial event types:

- `message.created`
- `message.updated`
- `message.removed`
- `chat.updated`
- `account.status`
- `media.ready`
- `send.updated`

Unknown event types must be ignored after being logged, not treated as fatal protocol errors.

## Runtime Management Extension

Runtime account lifecycle management is an **additive V1 operator extension**, not a new dependency for C/E or other Core V1 consumers. `GET /health` may advertise `runtime_management.configured`, `runtime_management.available` and `runtime_management.registry_hot_reload`. If these fields or `/v1/runtime/*` endpoints are absent, Console must fail soft and retain its normal account/chat/message/Saved workflows.

In the reference Linux deployment, Core does not use Docker Socket or `docker exec`. Runtime owns a private Unix-domain socket at `/run/wechat-runtime/control.sock` on the already shared Runtime state volume. Core is the only HTTP-facing component that talks to that root-side control service. Console sends management requests to Core over its existing HTTP boundary.

Core watches the persisted Runtime account registry and atomically replaces its in-memory account snapshot when that file changes. This applies both to Console-driven changes and direct Runtime CLI changes. New accounts join the next sync/sender cycles without a Core restart. Removed accounts disappear immediately from active `/v1/accounts`; their historical Core data remains stored, while accepted/queued sends that were never dispatched are failed explicitly. An already `sending` row is not guessed or retried because GUI delivery may have occurred; its normal lease recovery preserves that uncertainty.

`DELETE /v1/runtime/accounts/{account_id}` is intentionally data-preserving: Runtime stops the WeChat process and removes the registry entry, but preserves the account HOME/login data and Unix user. Destructive account-data deletion is not part of V1.

Console login is also deliberately ephemeral. Runtime selects the WeChat window
from the requested account's Unix-UID-owned X11 windows, captures the selected
window in memory, bounds/resizes it, and returns PNG bytes through the private
control socket. Core and Console proxy the image with `Cache-Control: no-store`;
neither service writes it to its SQLite database, media store, logs or Saved
Messages. The full Selkies desktop remains the fallback for agreement dialogs,
security verification, upgrades or other interactive screens that cannot be
completed by scanning the displayed QR image alone.

## Normalized Message

Required fields are `account_id`, `message_id`, `chat_id`, `type`, `created_at`, `direction` and `author`. `type` initially supports `text`, `image`, `sticker`, `voice`, `video`, `file`, `link`, `location`, `contact_card`, `system`, `recall` and `unsupported`.

Optional fields include `text`, `media_id`, `filename`, `mime_type`, `target_message_id`, `substitutions`, `attributes` and `vendor_specific`. `vendor_specific` is a compatibility extension, not a substitute for normalized fields.

## Send Semantics

Every send request includes:

- `account_id`
- `chat_id`
- optional `target_message_id`
- optional `client_request_id`

Clients should also send `Idempotency-Key`. Repeating the same key returns the original receipt. A successful HTTP response means accepted into the Core outbox, not confirmed by WeChat. The receipt has `send_id`, `status`, `accepted_at`, account/chat fields and optional `echo_message_id`. Final states are observed through `send.updated` events.

Delivery status is intentionally two-phase after the concrete sender reports
success:

```text
accepted -> queued -> sending -> submitted -> sent
                                  |
                                  +-> uncertain
```

`submitted` means the Runtime/sender accepted the operation and returned
success, but Core has not yet observed a unique matching outgoing WeChat DB
echo. It is **not** confirmed delivery. Only a unique correct echo may move a
send from `submitted` to `sent`, at which point `echo_message_id` is populated.
If the confirmation window expires without a unique echo, Core moves the send
to `uncertain`, reports `delivery_certainty=unknown` and
`automatic_retry=false`, and must not automatically retry it. Transport
timeouts that may have reached WeChat use the same `uncertain` certainty
semantics. Text currently supports automatic unique echo reconciliation;
media/file sends may remain `submitted` until timeout when no reliable unique
matcher is available.

`GET /health` may include an optional `sender_capabilities` object describing
the verified primitives of the concrete sender behind that Core deployment.
This is additive V1 capability discovery: consumers must treat an absent field
as **unknown**, not as unsupported. The current Linux/X11 sender advertises
text/image support, no verified arbitrary-file or native-reply primitive, one
verified mention per text send, no media-caption primitive, and no database
echo confirmation. Adapters should use these hints to avoid knowingly queuing
requests that the concrete sender will later reject. Capability discovery does
not change the V1 request schemas; a future sender may advertise broader
support without a contract major-version change.

Text requests add `text` and optional `mention_member_ids`. Image/file requests must contain exactly one of `media_id` or `content_base64`, plus optional `filename`, `mime_type` and `caption`. V1 base64 payloads prioritize a simple stable contract; a future streaming upload endpoint may be added without changing these operations.

## Errors

Non-2xx responses use:

```json
{
  "error": {
    "code": "account_not_found",
    "message": "Unknown account_id: account-missing",
    "details": {}
  }
}
```

Clients must branch on `error.code`, not localized text. Expected status codes are 400 for invalid input, 404 for unknown resources, 409 for state conflicts, 413 for oversized inline media, 429 for backpressure and 503 for unavailable account/runtime.

## Compatibility Rules

- Adding optional response fields and new event/message types is backward compatible.
- Removing or changing existing fields requires V2.
- C/D/E pin to `contract_version: 1` and fail clearly if Core advertises an unsupported major version.
- Mock behavior is contract simulation, not proof of real WeChat, Telegram, media, login or GUI integration.
