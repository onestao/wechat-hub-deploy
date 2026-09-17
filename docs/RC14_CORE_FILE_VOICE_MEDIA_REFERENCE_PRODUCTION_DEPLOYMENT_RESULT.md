# RC.14 Core File / Voice Media Reference — Production Deployment Result

```text
RESULT_ID        = RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT
WORK_PACKAGE     = RC.14 Core Media Reference Coverage — File / Voice Engineering
PHASE            = PRODUCTION DEPLOYMENT + READ-ONLY RUNTIME QUALIFICATION
DATE             = 2026-09-17  (host UTC)
EXECUTED_UNDER   = explicit operator authorization (AUTHORIZED_CORE_RECREATE_COUNT = 1)
VERDICT          = DEPLOYMENT PASS — AWAITING SEPARATE EFB LIVE AUTHORIZATION
ACTION           = STOP
```

## 0. Return block

```text
PRE_CORE_SOURCE                     = 6538f79a664a325543c19391cc14601d282e07a4
PRE_CORE_IMAGE                      = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427

NEW_CORE_SOURCE                     = 9434e915b78b2eb5471acf282d4e223c03e8d83a
NEW_CORE_IMAGE                      = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
NEW_CORE_OCI_REVISION               = 9434e915b78b2eb5471acf282d4e223c03e8d83a

CORE_RECREATE_COUNT                 = 1

CORE_HEALTH_POST                    = PASS

AGENT_CHECKPOINT_PRE                = 195927
AGENT_CHECKPOINT_POST               = 195927

EFB_CHECKPOINT_PRE                  = 273844
EFB_CHECKPOINT_POST                 = 273844
EFB_CHECKPOINT_MUTATION             = 0

CHECKPOINT_REGRESSION               = ZERO

STREAM_HEAD_PRE                     = 274814
STREAM_HEAD_POST                    = 274947
REEMITTED_EVENT_COUNT               = 122   (message.updated; 0 message.created in the window)

QUOTE_REPLY_APPMSG_57_CLASSIFIED_AS_FILE = NO
MERGED_RECORD_CLASSIFIED_AS_FILE         = NO
GENUINE_FILE_CLASSIFIED_AS_FILE          = YES

274307_PROJECTED_AS_FILE            = NO

FILE_MEDIA_ID_PRESENT               = YES
FILE_MEDIA_ROLE                     = original
FILE_MEDIA_STATUS                   = ready          (when the original bytes are present)
FILE_BYTES_RETRIEVABLE              = YES
FILE_LENGTH_MATCH                   = YES

VOICE_MEDIA_ID_PRESENT              = YES
VOICE_MEDIA_ROLE                    = original
VOICE_MEDIA_STATUS                  = ready          (when the original bytes are present)
VOICE_BYTES_RETRIEVABLE             = YES
VOICE_DECLARED_LENGTH_MATCH         = YES
VOICE_CONTENT_TYPE                  = audio/silk
VOICE_TELEGRAM_DELIVERABILITY       = UNVERIFIED

F3_MESSAGE_PROJECTION_REGRESSION    = PASS
THUMBNAIL_SAFETY_REGRESSION         = PASS

CONSOLE_RESTART_DELTA               = 0
RUNTIME_RESTART_DELTA               = 0
AGENTWECHAT_RESTART_DELTA           = 0
AGENT_RESTART_DELTA                 = 0
EFB_RESTART_DELTA                   = 0

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS        = 0
ACTIVE_CORE_RAW_SQLITE_READS                = 0
ACTIVE_CORE_HOST_NON_CORE_STAGING_DB_READS  = 0

CORE_FILE_VOICE_MEDIA_REFERENCE_DEPLOYMENT  = PASS
EFB_FUNCTIONAL_RETRY_PREREQUISITE           = PASS

ACTION = STOP
```

### 0.1 Execution authority

```text
AUTHORIZED_CORE_RECREATE_COUNT = 1     (this message)
CORE_RECREATE_COUNT_ACTUAL     = 1
SECOND_RECREATE_REQUIRED       = NO
AUTHORIZATION_REUSABLE         = NO
```

The two sealed documents named in the authorization were verified byte-exact **before** any
mutation:

```text
docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_TASKBOOK.md
  computed 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae
  required 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae   -> MATCH
docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_EXECUTION_ERRATUM.md
  computed 01b22a9845fc8f7309042ffbca9617d238987000d3d59daebb1aef74b8faa0ff
  required 01b22a9845fc8f7309042ffbca9617d238987000d3d59daebb1aef74b8faa0ff   -> MATCH
NEITHER_SEALED_DOCUMENT_MODIFIED = YES (both remain byte-identical)
```

---

## 1. Pre-flight

Captured `2026-09-17T12:50:29Z`. All taskbook §4.0 abort conditions were checked and none fired.

```text
CORE_CONTAINER_ID_PRE = e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9
CORE_IMAGE_PRE        = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
CORE_STATE_PRE        = running / healthy
CORE_RESTART_COUNT_PRE = 0
CORE_STARTED_AT_PRE   = 2026-09-17T01:45:06.839931379Z
CORE_OCI_REVISION_PRE = 6538f79a664a325543c19391cc14601d282e07a4
HEALTH_PRE            = ok:true, contract_version 1, accounts 2, consecutive_failed_cycles 0
AGENT_CHECKPOINT_PRE  = 195927   (updated_at 2026-09-16T08:04:11Z)
EFB_CHECKPOINT_PRE    = 273844   (updated_at 2026-09-16T17:14:43Z)
STREAM_HEAD_PRE       = 274814   (retention_floor 1)
AGENT_STATE_PRE       = STOPPED  (exited 0)
EFB_STATE_PRE         = STOPPED  (exited 0)
```

Candidate and overlay verification:

```text
DIGEST_PULL_RC              = 0    ("Image is up to date")
CONFIG_ID                   = sha256:a11731dafc06a93631a5726e1549e479462165efd1b0abd7377dbd877237e165
OCI_REVISION                = 9434e915b78b2eb5471acf282d4e223c03e8d83a   == NEW_CORE_SOURCE
OCI_VERSION                 = 0.1.0-rc.14-core-filevoice-media-ref
REPO_DIGESTS                = ["ghcr.io/onestao/wechat-hub-core@sha256:a0d4f70b...02e47"]
OVERLAY_SHA256              = a46b318f579bcf9c36b0cdb909b97639bd4f5c702f7dc7a1376f3147542afc9e
OVERLAY_BYTES               = 313
RENDER_DIFF_CHANGED_LINES   = 1    (services.core.image only)
RENDER_DIFF_UNEXPECTED      = NONE
```

---

## 2. The single authorized mutation

```text
MUTATED_SERVICES = core    (only)
COMMAND = docker compose -f docker-compose.yml \
            -f docker-compose.rc14-core-filevoice-media-ref-candidate.yml \
            up -d --no-deps core
DEPLOY_RC            = 0
DEPLOY_START_UTC     = 2026-09-17T12:51:02Z
CORE_STARTED_AT_POST = 2026-09-17T12:51:16.981532852Z
CORE_CONTAINER_ID_POST = 7737f3b7333f9454b65908228d5b6d24c929e609be588506cca7094533d8457a
```

`--no-deps` only; `--remove-orphans` was deliberately **not** used, so the stopped
`wechat-hub-f-live-efb` and `wechat-hub-f-live-agent` containers were left untouched (the
compose run emitted the expected orphan warning and nothing else).

---

## 3. Post-deploy health

```text
CORE_HEALTH_POST     = PASS
CORE_IMAGE_POST      = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
CORE_OCI_REVISION_POST = 9434e915b78b2eb5471acf282d4e223c03e8d83a
CORE_STATE_POST      = running / healthy
CORE_RESTART_COUNT_POST = 0
HEALTH_PAYLOAD       = ok:true, contract_version 1, accounts 2, consecutive_failed_cycles 0
SYNC_CYCLES_OBSERVED = 26 (by 12:57:01Z), 0 consecutive failed cycles, last_cycle_error ""
```

No rollback trigger fired, so no rollback action was taken and no recovery action was improvised.

---

## 4. EFB checkpoint hard rule (erratum E1)

```text
EFB_CHECKPOINT_PRE                  = 273844
EFB_CHECKPOINT_POST                 = 273844
EFB_CHECKPOINT_MUTATION             = 0
EFB_CHECKPOINT_UPDATED_AT_PRE       = 2026-09-16T17:14:43Z
EFB_CHECKPOINT_UPDATED_AT_POST      = 2026-09-16T17:14:43Z    (unchanged)
```

Not done, as required:

```text
ADVANCED_TO_POST_DEPLOY_STREAM_HEAD = NO
ADVANCED_TO_REPLAY_WINDOW_BOUNDARY  = NO
CONSUMER_RESET_OR_REBOOTSTRAP       = NO
core-event-cursor.json_MODIFIED     = NO
EFFECT_LEDGER_MODIFIED              = NO
MESSAGE_MAPPING_MODIFIED            = NO
```

```text
STREAM_HEAD_PRE  = 274814
STREAM_HEAD_POST = 274947
STREAM_HEAD_POST = OBSERVABILITY_ONLY
POST_DEPLOY_STREAM_HEAD_USED_AS_EFB_CHECKPOINT_TARGET = NO
```

`STREAM_HEAD_POST` is recorded with its timestamp as a replay-window upper bound only. It is a
moving value (the `account.status` heartbeat advances it roughly every 5 s) and is not a
checkpoint target.

```text
AGENT_CHECKPOINT_PRE  = 195927
AGENT_CHECKPOINT_POST = 195927
AGENT_CHECKPOINT_MUTATION = 0
CHECKPOINT_REGRESSION = ZERO
```

---

## 5. Re-emission window (measured, not estimated)

Window `274814 .. 274947` (pre-deploy stream head → caught up), read through
`GET /v1/events/poll` with `consumer_id` omitted (a pure `SELECT`):

```text
window_event_histogram = {"account.status": 5, "media.ready": 6, "message.updated": 122}
TOTAL_EVENTS           = 133
REEMITTED_EVENT_COUNT  = 122        (message.updated)
message.created in window = 0
distinct message_ids in message.updated = 122   (no duplicate re-emission)
```

Breakdown of the 122 re-emitted messages by projected type, with the accounting:

```text
message.updated by projected type = {"text": 113, "voice": 5, "file": 4}

  113  link_or_file messages re-typed file -> text   (quote replies / merged records / type 62)
    5  voice messages gaining a media reference
    4  genuine type-6 file messages: 2 pre-existing (gaining a media reference)
                                     + 2 newly observed (previously projected as `link`
                                       because they carry a url; now correctly `file`)
  ---
  122
```

`media.ready` = 6, all `role = original`, `status = ready`: the 2 file originals plus the 4 voice
originals. No `media.ready` carried a non-original role.

The window is bounded and has converged: the 5 s sync worker re-reads the staging table each
cycle, and after the first cycle the digests match, so no further re-emission occurs. This is
consistent with `normalized.message_changes = 0` on the post-deploy cycles.

**Consequence, per erratum E1:** the next EFB round resumes from `273844` and will replay this
window. That is intended — the frozen candidate `69a1f58e` suppresses Core reprojection
idempotently via the EffectLedger plus durable subscription provenance, and a cursor fence is
unsound here because the same range also carries genuinely new business.

---

## 6. Classification contract

Read from the event payloads' own projection: `vendor_specific.source_type_label` is the upstream
label and `attributes.app_type` is the parsed outer `appmsg` subtype, so the discriminator is
observable through the HTTP API alone.

```text
app_type 19 (merged chat records)  -> text     2
app_type 57 (quote reply)          -> text   110
app_type 62 (other appmsg)         -> text     1
app_type  6 (file transfer)        -> file     4
```

```text
QUOTE_REPLY_APPMSG_57_CLASSIFIED_AS_FILE = NO      (110/110 -> text, 0 -> file)
MERGED_RECORD_CLASSIFIED_AS_FILE         = NO      (2/2 -> text, 0 -> file)
GENUINE_FILE_CLASSIFIED_AS_FILE          = YES     (4/4 -> file, 0 -> non-file)
```

### 6.1 Historical cursor 274307

```text
HISTORICAL_EVENT_IMMUTABLE:
  cursor 274307, message.created, account f-live-a, chat 38808757431@chatroom
  message_id 8745c1a931013b8941a0736d6fb890f1a4129129bd03b2b4842d09f7d5995d79
  historical projection = file
  appmsg type           = 57
  true semantic class   = quote reply
  (the sealed census value is preserved; no historical event was rewritten)

CURRENT_CORE_PROJECTION (observed live after deployment):
  {"event":"message.updated","type":"text","media_id":"","app_type":"57","stl":"link_or_file"}

274307_PROJECTED_AS_FILE = NO
```

The message now projects as `text` with an empty `media_id` and therefore receives no media
reference. `HISTORICAL_EVENT_IMMUTABLE` and `CURRENT_CORE_PROJECTION` are kept distinct: the
historical record still reads `file`, and only the current projection was re-verified.

No real WeChat event was manufactured to prove any of this.

---

## 7. Genuine file contract

Four messages carry `appmsg type 6`. All four carry a media reference with `role = original`;
`status` is `ready` **only** where the original bytes are actually present.

| message_id (prefix) | projected type | media_id present | role | status | bytes served |
| --- | --- | --- | --- | --- | --- |
| `88e671bf…` | `file` | YES | `original` | `ready` | 32 |
| `1fd0be80…` | `file` | YES | `original` | `ready` | 32 |
| `2d90d1a7…` | `file` | YES | `original` | `missing_file` | — (404) |
| `e0c9b808…` | `file` | YES | `original` | `missing_file` | — (404) |

```text
FILE_MEDIA_ID_PRESENT   = YES   (4/4)
FILE_MEDIA_ROLE         = original   (4/4)
FILE_MEDIA_STATUS       = ready for the 2 files whose original is present;
                          missing_file for the 2 whose original is absent — never falsely ready
FILE_BYTES_RETRIEVABLE  = YES   (2/2 ready files)
FILE_LENGTH_MATCH       = YES
```

Live `GET /v1/media/{id}` for a ready file:

```text
GET /v1/media/88e671bfdb314157a3003ef06c8425af0b2015f79f6eab6ed87a9a7d2bc6bf61?account_id=f-live-a
  HTTP/1.0 200 OK
  Content-Type: text/plain
  Content-Length: 32
  Content-Disposition: inline; filename="send_file_1788297195381_F-LIVE-20260901T210920Z-A-FILE.txt"
  X-Media-Id: 88e671bfdb314157a3003ef06c8425af0b2015f79f6eab6ed87a9a7d2bc6bf61
  X-Media-Role: original
  X-Media-Status: ready
  bytes_returned = 32   (declared totallen 32 == Content-Length 32 == bytes returned 32)

GET /v1/media/1fd0be8065252db6e8449fc2264add48f33d0ab52e7d44b82584b0c01b0d021a?account_id=f-live-a
  HTTP/1.0 200 OK, Content-Length 32, X-Media-Role original, X-Media-Status ready
  bytes_returned = 32   (same sha256 as the sibling projection: 164cf321e00e0b9d...)
```

`FILE_LENGTH_MATCH = YES`: the declared `totallen` 32 (frozen in the sealed engineering evidence
for `send_file_1788297195381_F-LIVE-20260901T210920Z-A-FILE.txt`) equals the served
`Content-Length` and the byte count actually returned.

For the two not-ready files, `GET /v1/media/{id}` returns **404 `media_not_found`** — no bytes are
served and no content is fabricated. Their projection is `role=original, status=missing_file`,
which is the truthful pending-original state, and **no thumbnail is substituted**.

---

## 8. Voice contract

Five voice messages exist; four resolve to an original, one does not (its chat is a mirrored
staging table with no `VoiceInfo` entry). The contract holds in both directions.

| message_id (prefix) | media_id present | role | status | content type | declared length | served bytes |
| --- | --- | --- | --- | --- | --- | --- |
| `4a9395ca…` | YES | `original` | `ready` | `audio/silk` | 6196 | 6196 |
| `bcc03e4a…` | YES | `original` | `ready` | `audio/silk` | 16132 | 16132 |
| `a8fe7ecc…` | YES | `original` | `ready` | `audio/silk` | 13234 | 13234 |
| `a37914e6…` | YES | `original` | `ready` | `audio/silk` | 4522 | 4522 |
| `9cb13cc3…` | YES | `original` | `missing_file` | — | — | — (404) |

```text
VOICE_MEDIA_ID_PRESENT       = YES   (5/5)
VOICE_MEDIA_ROLE             = original   (5/5)
VOICE_MEDIA_STATUS           = ready for the 4 resolvable originals; missing_file otherwise
VOICE_BYTES_RETRIEVABLE      = YES   (4/4 ready)
VOICE_DECLARED_LENGTH_MATCH  = YES   (6196 / 16132 / 13234 / 4522 — all four match exactly)
VOICE_CONTENT_TYPE           = audio/silk
VOICE_TELEGRAM_DELIVERABILITY = UNVERIFIED
```

Live example:

```text
GET /v1/media/4a9395ca83b71a665408fe158a4a46eb06ffdd73c90b6e4975cca10a929acf72?account_id=f-live-a
  HTTP/1.0 200 OK
  Content-Type: audio/silk
  Content-Length: 6196
  Content-Disposition: inline; filename="4a9395ca....silk"
  X-Media-Role: original
  X-Media-Status: ready
  bytes_returned = 6196
```

**Disclosed limitation.** The Core gate is satisfied: the original voice artifact exists and is
retrievable byte-for-byte with `role=original` / `status=ready`, and its length matches the
message's declared length. `VOICE_TELEGRAM_DELIVERABILITY = UNVERIFIED` — the artifact is raw SILK
and no SILK transcoder was added in this round, by instruction. This is **not** a Core deployment
FAIL condition.

---

## 9. F3 contract regression

```text
message.media_role present   = PASS
message.media_status present = PASS
```

Every media-bearing message payload in the window carried both top-level fields:

```text
media-bearing payloads with (has_role=true, has_status=true) = 9 / 9
```

```text
message.created projection  = PASS   (0 in window; path unchanged, asserted by FMR-7 in CI)
message.updated projection  = PASS   (122/122 carry the contract fields where media is present)
REST projection             = PASS   (chat message listing exposes type/media_role/media_status)
media.ready role            = PASS   (6/6 role=original, status=ready)
X-Media-Role                = PASS
X-Media-Status              = PASS
F3_MESSAGE_PROJECTION_REGRESSION = PASS
```

`message.created` had no natural occurrence in this window. Rather than manufacture one, this is
recorded as `NOT_OBSERVED_IN_WINDOW`, backed by the shared construction site (`event_type` is the
only difference between created and updated) and by the CI-verified FMR-7 / F3 tests at the
deployed commit `9434e915`. `REQUIRES_NEW_EVENT_FOR_LIVE_CREATED_LEG = YES`.

### 9.1 Thumbnail safety

```text
THUMBNAIL_REPORTED_AS_ORIGINAL_READY = NO
THUMBNAIL_SAFETY_REGRESSION          = PASS
```

Live evidence — a video message, whose only artifact is a thumbnail, is reported as a thumbnail
and is never presented as an original:

```text
GET /v1/media/19dd1eb1e17dfcc256f7c89ba49e45a8ec805d470438ef0edaf4cda8e10b408c?account_id=f-live-a
  HTTP/1.0 200 OK
  Content-Type: image/jpeg
  Content-Length: 13884
  X-Media-Role: thumbnail
  X-Media-Status: ready
  bytes = 13884
```

Correlating pair (role vs the artifact's own provenance) across the media-bearing rows of chat
`38808757431@chatroom`:

```text
image/original/original_pending   22
image/original/missing_file        1
image/original/decode_failed       1
sticker/original/missing_file     13
```

No row anywhere pairs `role=thumbnail` with a file/voice artifact, and no `ready` row lacks a
materialised artifact. A `thumbnail` role is fail-closed for every consumer that requires
`original` (the frozen EFB candidate raises `MediaPermanentError`).

---

## 10. Protected-service reconciliation

| Service | Status | RestartCount | StartedAt | Restart delta | StartedAt changed |
| --- | --- | ---: | --- | ---: | --- |
| core | running | 0 | 2026-09-17T12:51:16.981532852Z | (recreated — authorized) | yes (authorized) |
| console | running | 0 | 2026-09-13T12:05:02.973659468Z | 0 | no |
| runtime | running | 0 | 2026-09-11T06:45:48.455808964Z | 0 | no |
| agentwechat-a | running | 0 | 2026-09-11T05:12:55.911370452Z | 0 | no |
| agentwechat-testb | running | 0 | 2026-09-11T05:12:57.593190942Z | 0 | no |
| agent | exited (0) | 0 | 2026-09-16T07:31:50.371571612Z | 0 | no |
| efb | exited (0) | 0 | 2026-09-16T16:49:38.345169161Z | 0 | no |

```text
CONSOLE_RESTART_DELTA    = 0
RUNTIME_RESTART_DELTA    = 0
AGENTWECHAT_RESTART_DELTA = 0
AGENT_RESTART_DELTA      = 0
EFB_RESTART_DELTA        = 0
AGENT = STOPPED
EFB   = STOPPED
EFB_FUNCTIONAL_LIVE_ENTERED = NO
```

---

## 11. Production DB governance

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS       = 0
ACTIVE_CORE_RAW_SQLITE_READS               = 0
ACTIVE_CORE_HOST_NON_CORE_STAGING_DB_READS = 0
```

Guard: `scripts/forensics/check_forbidden_live_core_db_access.py`
(sha256 `a81015cc953a1fc5376f4a005221c57d0172026daa2ed9ab0d8829657933dfe1`);
selftest `CI_NEGATIVE_TESTS = PASS` / `CI_POSITIVE_TESTS = PASS`.

```text
-- on this round's command log:
   files_skipped 0, fixture_exempt_files 0, authorized_offline_tools 0 (expected 1)
   no findings
   RAW_SQLITE_GUARD        = PASS
   GENERIC_FILE_OPEN_GUARD = PASS
   SCRATCH_GUARD           = PASS
```

This round deliberately avoided `core-data/accounts/**` entirely — no `sqlite3` was run anywhere on
the host, and every runtime qualification probe went through the Core HTTP API
(`/health`, `/v1/accounts`, `/v1/accounts/{id}/chats`, `.../messages`, `/v1/media/{id}`,
`/v1/events/checkpoint`, `/v1/events/poll` without `consumer_id`).

Note for the record: the guard's `PRODUCTION_CORE_PATH_PATTERNS[0]` is still broader than policy
`docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md` §1.2 (it matches the whole `core-data` subtree),
as disclosed in the engineering result §10.1. It does not surface here only because no staging
store was read, and the guard implementation was **not** modified in this round, by instruction.
The guard/policy alignment remains an open finding.

---

## 12. Sealed artefacts

```text
RESULT_PATH   = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_RESULT.md
COMMAND_LOG   = tmp/rc14-filevoice/deploy/core_db_access_command_log.txt
HOST_SCRIPTS  = /root/rc14fv-deploy.sh   (md5 70303b534119d6f656de68b7eae5584b, 510 B)
                /root/rc14fv-window.sh   (md5 c878313a5f3cc89bffb8960fa87a2c06, 744 B)
                /root/rc14fv-qual.sh     (md5 6d03232b9f0db986129784b9d62787d6, 3307 B)
ROLLBACK_OVERLAY = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-media-contract-f3-candidate.yml
ROLLBACK_OVERLAY_SHA256 = 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d
ROLLBACK_IMAGE_PRESENT_ON_HOST = YES
ROLLBACK_PERFORMED = NO   (no rollback trigger fired)
```

---

## 13. Next step

```text
ACTION = STOP
```

```text
CORE_FILE_VOICE_MEDIA_REFERENCE_DEPLOYMENT = PASS
EFB_FUNCTIONAL_RETRY_PREREQUISITE          = PASS
```

All Core runtime contract, classification, checkpoint and governance gates are satisfied, so both
verdicts are PASS. This result **does not** authorize anything further:

```text
EFB_FUNCTIONAL_LIVE_RETRY = NOT AUTHORIZED   (do not run)
EFB   = STOPPED   (do not start)
AGENT = STOPPED   (do not start)
CORE_RECREATE = NOT AUTHORIZED AGAIN          (budget consumed; a second recreate needs a new authorization)
```

Residual items carried forward, none of which block the EFB prerequisite:

1. **Voice Telegram deliverability UNVERIFIED.** The Core contract is met (raw SILK, length-verified,
   `role=original`, `status=ready`). Whether the downstream consumer can deliver SILK was not
   verified; adding a transcoder is a separate work package.
2. **`message.created` leg not observed live** in this window (§9). Covered by the shared
   construction site and the CI-verified tests at the deployed commit.
3. **Two genuine file messages and one voice message are legitimately `missing_file`** — their
   originals are not present locally. They fail closed with no bytes served; they are truthful
   pending states, not contract failures.
4. **Guard/policy divergence** remains un-reconciled (§11).
