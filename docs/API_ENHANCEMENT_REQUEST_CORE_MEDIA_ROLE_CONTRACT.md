# API Enhancement Request — Core Media Role / Status Contract

> **STATUS: OPEN / BLOCKING FOR RC.14 EFB FUNCTIONAL CORRECTNESS (F1, F2)**
>
> **POLICY_REF:** `docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md`
>
> **RULE_REF:** `CORE_API_GAP = media_role, media_status, X-Media-Role, X-Media-Status`
>
> **SIBLING:** `docs/API_ENHANCEMENT_REQUEST_CORE_READONLY_OBSERVABILITY.md`
> (that document is sealed with its own `.sha256`; it was deliberately **not** edited by this
> round — see §5).

```text
REQUEST_ID = CORE_MEDIA_ROLE_CONTRACT_V1
RAISED_BY = RC.14 EFB Functional Correctness Production Live Qualification
RAISED_ON = 2026-09-17 (host UTC 2026-09-16/17)
CORE_RUNNING_REVISION = 08a4e746e66fe94cbe73f99f7284ae7f01963447
CORE_REQUIRED_REVISION = 1e5eddd4b5504bad44409ab610767688e32ddca2
                          (branch rc14-efb-functional-correctness-core)
BLOCKED_GATES = LQ-01 / F1 (original image), LQ-02 / F2 (delayed media / sticker)
ACTION_WHILE_OPEN = STOP  (the frozen EFB candidate fails closed and emits MEDIA_FAILED)
```

---

## 1. Summary

The frozen RC.14 EFB Functional Correctness candidate
(`91a69cef323d120f0e32196917a630d2cf3baa88`,
`ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d5…456241`)
**requires** Core to advertise the media artefact role and status. The production Core that is
deployed today does **not** advertise them.

Consequence, observed live: every media message whose `media_id` is resolved is rejected by the
candidate as a non-original artefact and recorded as `MEDIA_FAILED`. No thumbnail is ever
delivered as the final image (fail-closed works), but **no original is delivered either**.

---

## 2. Required contract (as consumed by the frozen candidate)

| Consumer site | Field | Where the candidate reads it |
| --- | --- | --- |
| `efb_wechat_comwechat_slave/CoreMessage.py:226-241` | `message.media_role` | normalized message payload |
| `efb_wechat_comwechat_slave/CoreMessage.py:226-241` | `message.media_status` | normalized message payload |
| `efb_wechat_comwechat_slave/Core.py:261-276` (`get_media`) | `X-Media-Role` response header | `GET /v1/media/{media_id}?account_id=<id>` |
| `efb_wechat_comwechat_slave/Core.py:261-276` (`get_media`) | `X-Media-Status` response header | `GET /v1/media/{media_id}?account_id=<id>` |
| `efb_wechat_comwechat_slave/ComWechat.py:1083-1084` | `media.ready` payload `.role` | `media.ready` event |

Hard requirements enforced by the candidate:

```text
media_role   must equal "original"   else MediaPermanentError  -> MEDIA_FAILED
media_status must equal "ready"      else MediaPendingError    -> PENDING_MEDIA (retry)
```

`thumbnail` is **never** an acceptable final artefact.

---

## 3. Observed production behaviour (running Core, revision `08a4e74`)

```text
GET /v1/media/be065d8c…00bfa6?account_id=f-live-a
HTTP/1.0 200 OK
Content-Type: image/jpeg
Content-Length: 4049
Content-Disposition: inline; filename="32f0abad12ef49fface579929a91a55f.jpg"
X-Media-Id: be065d8c…00bfa6
                                    <-- no X-Media-Role, no X-Media-Status
```

`media.ready` event payload as emitted today:

```json
{"media":{"account_id":"f-live-a","disposition":"inline",
          "filename":"32f0abad12ef49fface579929a91a55f.jpg",
          "media_id":"be065d8c…00bfa6","mime_type":"image/jpeg","status":"ready"}}
```

No `role` key. And `message.created` payloads carry `media_id` / `filename` / `mime_type` but
**no** `media_role` / `media_status`.

Observed candidate reaction (`core-effect-ledger.sqlite3`, live round):

```text
MEDIA_FAILED  f-live-a:be065d8c…  "image media be065d8c… has role ''; thumbnail cannot be final"
MEDIA_FAILED  f-live-a:8015346c…  "image media 8015346c… has role ''; thumbnail cannot be final"
```

### 3.1 Post-stop re-confirmation (2026-09-16T17:25:59Z, EFB stopped)

Re-probed after the live window closed, against a **different** media id, to rule out a
transient/partial response:

```text
GET /v1/media/bfec71c0c0753a84b18f11c9ca65f327d98f265198f4624a033a12af513dec2e?account_id=f-live-a
HTTP/1.0 200 OK
Server: WeChatCore/1 Python/3.12.14
Content-Type: image/jpeg
Content-Length: 5701
Content-Disposition: inline; filename="e505d4e740ff62450cf797f04df67567.jpg"
X-Media-Id: bfec71c0c0753a84b18f11c9ca65f327d98f265198f4624a033a12af513dec2e
                                    <-- still no X-Media-Role, no X-Media-Status
```

And `GET /v1/accounts/f-live-a/chats/38808757431@chatroom/messages?limit=5` still returns
`media_role = NULL` / `media_status = NULL` on every message. The gap is structural, not
transient.

Note the `Content-Length: 5701` on a chatroom image: an artefact of this size is consistent with a
thumbnail, which is exactly the case the missing `X-Media-Role` cannot disambiguate.

---

## 4. Reference implementation (already authored, not deployed)

Branch `rc14-efb-functional-correctness-core`, head `1e5eddd4b5504bad44409ab610767688e32ddca2`:

| Commit | Substance |
| --- | --- |
| `2caee27` — *RC14 F1: preserve original image media role* | `core/normalize.py` emits `media_role` / `media_status` on the normalized message plus a `vendor_specific.media` block (`role`, `status`, `original_media_id`, `thumbnail_media_id`); `core/app.py` adds the `X-Media-Role` / `X-Media-Status` response headers. |
| `1e5eddd` — *RC14 F2: expose pending original media state* | `memory/media_sync.py` `choose_dat()` returns `None` instead of falling back to `_t.dat` when full-image mode is active, so a thumbnail-only artefact keeps the message pending rather than being published as the original; media import stops filtering on `status='ready'` and records `role` / `status`. |

`git diff --stat 08a4e74..1e5eddd`:

```text
 core/app.py                                        |   2 +
 core/normalize.py                                  |  39 +++++--
 core/store.py                                      |  15 ++-
 .../tests/test_efb_media_functional_correctness.py | 117 +++++++++++++++++++++
 docs/openapi.yaml                                  |   6 ++
 memory/media_sync.py                               |  13 ++-
 6 files changed, 174 insertions(+), 18 deletions(-)
```

The **running** Core's OCI revision is exactly `08a4e74` — the parent of `2caee27`, i.e. the
media-role work is absent. No Core image built from `1e5eddd` / `2caee27` exists on the host
(`docker images` + label scan for `org.opencontainers.image.revision`).

Additional consequence of running the pre-fix Core: `normalize.py` at `08a4e74` resolves a media
path from `media_path or thumb_path` and publishes it with `status='ready'`, i.e. it can publish
thumbnail bytes as though they were the original. The frozen candidate's role check is what stops
that from reaching Telegram. The defect F1 fixes is therefore **live in production right now**.

---

## 5. Why the sibling document was not edited

`docs/API_ENHANCEMENT_REQUEST_CORE_READONLY_OBSERVABILITY.md` is sealed alongside its own
`.sha256`. Appending to it would invalidate that seal, which the project forbids. The gap is
therefore filed as this new sibling document; the sealed file is left byte-identical.

---

## 6. Acceptance criteria for closing this request

```text
CORE_MEDIA_ROLE_HEADER_SUPPORTED = YES
CORE_MEDIA_STATUS_HEADER_SUPPORTED = YES
CORE_MESSAGE_PAYLOAD_HAS_MEDIA_ROLE = YES
CORE_MESSAGE_PAYLOAD_HAS_MEDIA_STATUS = YES
CORE_MEDIA_READY_EVENT_HAS_ROLE = YES
CORE_NEVER_PUBLISHES_THUMBNAIL_AS_ORIGINAL = YES
```

Each must be demonstrable through the Core HTTP API alone, with Core at revision
`1e5eddd4b5504bad44409ab610767688e32ddca2` or a descendant.

---

## 7. What must NOT happen

- Do **not** relax the frozen candidate's `media_role == "original"` check to make F1 pass.
- Do **not** treat `MEDIA_FAILED` as a PASS for LQ-01 / LQ-02.
- Do **not** obtain media role/status from the raw production Core DB.

---

## 8. Related

- `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md` §0, §2, §7 (LQ-01, LQ-02)
- `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_EXECUTION_ERRATUM.md` (E1, E3)
- `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_RESULT.md`

---

## 9. Live round closure (2026-09-17)

```text
REQUEST_STATUS_AFTER_LIVE_ROUND = OPEN / BLOCKING
EFB_FUNCTIONAL_LIVE_QUALIFICATION = FAIL
EFB_PRODUCTION_PROMOTION_READY = NO
ACTION = STOP
```

The live round ran the frozen candidate end-to-end against the production Core and stopped on this
gap, exactly as §0 of the taskbook directs. It did **not**:

- relax the candidate's role check,
- read media role/status out of the raw production Core DB,
- promote any `MEDIA_FAILED` row to `DELIVERED`.

Live ledger totals after the round: `DELIVERED = 375` (274 historical + 101 new, **all
`MsgType.Text`**), `MEDIA_FAILED = 42` (8 × *role `''`; thumbnail cannot be final*, 34 × *media
retry deadline exceeded*), `RESERVED = 0`, `UNCERTAIN = 0`, `PENDING_MEDIA = 0`.

The candidate's fail-closed behaviour is therefore **proven live**: a thumbnail was never delivered
as final. What is missing is the Core-side contract that would let a *genuine original* through.

## 10. Follow-up required before a re-run

1. Land `2caee27` + `1e5eddd` on the Core branch that produces the deployed Core image.
2. Build and publish a Core image whose `org.opencontainers.image.revision` is `1e5eddd…` or a
   descendant, and deploy it **without** touching the protected Core SQLite.
3. Re-verify this document's §6 acceptance criteria through the HTTP API alone.
4. Only then re-authorize an EFB Functional Correctness live window.
