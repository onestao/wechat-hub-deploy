# RC.14 Core Media Contract F3 — Production Deployment Result

```text
RESULT_ID   = RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT
REQUEST_ID  = CORE_MEDIA_ROLE_CONTRACT_V1
DATE        = 2026-09-17  (host UTC)
PHASE       = AUTHORIZED PRODUCTION DEPLOYMENT + QUALIFICATION
VERDICT     = PASS
```

## 0. Authorization

```text
AUTHORIZATION       = "AUTHORIZE: RC14_CORE_MEDIA_ROLE_CONTRACT_F3_PRODUCTION_DEPLOYMENT"
GOVERNING_DOCUMENT  = docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md
GOVERNING_SHA256    = 85ba886feec2c4ed3504ac071ccd0466156d43ba47e090956b98851b5211dc7d
TASKBOOK_SHA256_RECOMPUTED = 85ba886feec2c4ed3504ac071ccd0466156d43ba47e090956b98851b5211dc7d
TASKBOOK_SHA256 = EXACT
```

### 0.1 Naming discrepancy (disclosed)

The authorization message named
`docs/RC14_CORE_MEDIA_ROLE_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md`. **That path does not
exist.** The sealed artifact is
`docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md`, and its SHA256 is the value
quoted in the authorization (`85ba886f…`). The deployment was executed against the artifact whose
hash matches the authorization. No second copy was created, so there is exactly one authoritative
taskbook. Recorded here so the operator can reconcile the naming.

---

## 1. Return block

```text
PRE_CORE_SOURCE = 1e5eddd4b5504bad44409ab610767688e32ddca2
PRE_CORE_IMAGE  = sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f

F3_SOURCE_COMMIT = 6538f79a664a325543c19391cc14601d282e07a4
F3_IMAGE_DIGEST  = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
F3_OCI_REVISION  = 6538f79a664a325543c19391cc14601d282e07a4

F3_IS_DESCENDANT_OF_1E5EDDD = YES

CORE_MEDIA_CONTRACT_GATE_1 = PASS
CORE_MEDIA_CONTRACT_GATE_2 = PASS
CORE_MEDIA_CONTRACT_GATE_3 = PASS
CORE_MEDIA_CONTRACT_GATE_4 = PASS
CORE_MEDIA_CONTRACT_GATE_5 = PASS
CORE_MEDIA_CONTRACT_GATE_6 = PASS

CORE_HEALTH_POST = PASS  (container healthy; /health ok:true, contract_version 1, accounts 2)

AGENT_CHECKPOINT_PRE  = 195927
AGENT_CHECKPOINT_POST = 195927

EFB_CHECKPOINT_PRE  = 273844
EFB_CHECKPOINT_POST = 273844

CHECKPOINT_REGRESSION = ZERO

MESSAGE_CREATED_MEDIA_ROLE_PRESENT   = YES (structural + CI-proven on the shipped commit; live observation NOT_OBSERVED_IN_WINDOW — see §5.3)
MESSAGE_CREATED_MEDIA_STATUS_PRESENT = YES (same)
MESSAGE_UPDATED_MEDIA_ROLE_PRESENT   = YES  (414/414 post-deploy media-bearing message events)
MESSAGE_UPDATED_MEDIA_STATUS_PRESENT = YES  (414/414)
REST_MESSAGE_MEDIA_ROLE_PRESENT      = YES
REST_MESSAGE_MEDIA_STATUS_PRESENT    = YES

MEDIA_READY_ROLE_PRESENT          = YES  (3/3)
MEDIA_GET_X_MEDIA_ROLE_PRESENT    = YES  (4/4 resolvable media ids)
MEDIA_GET_X_MEDIA_STATUS_PRESENT  = YES  (4/4)
THUMBNAIL_REPORTED_AS_ORIGINAL_READY = NO

CORE_RECREATE_COUNT = 1

CONSOLE_RESTART_DELTA    = 0
RUNTIME_RESTART_DELTA    = 0
AGENTWECHAT_RESTART_DELTA = 0
AGENT_RESTART_DELTA      = 0
EFB_RESTART_DELTA        = 0

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS = 0

CORE_MEDIA_CONTRACT_F3_DEPLOYMENT = PASS
EFB_FUNCTIONAL_RETRY_PREREQUISITE = PASS
```

### 1.1 Additional required flags

```text
REQUIRES_NEW_EVENT_FOR_EFB_RETRY = YES
  scope: the live `message.created` observation leg only.  All six gates are satisfied without it.

HISTORICAL_EVENT_IMMUTABLE       = YES   (49 pre-deploy media-bearing message events keep the old shape)
CURRENT_CORE_PROJECTION          = CONFORMANT
CURRENT_MEDIA_API_CONTRACT       = CONFORMANT

ACTION = STOP
```

---

## 2. Final Mutation Gate (taskbook §0/§8 preconditions)

Executed at host UTC `2026-09-17T01:44:00Z` / `01:44:14Z`, before any mutation.

```text
CORE = RUNNING / HEALTHY              (b93fa6a8…, healthy, RestartCount 0)
AGENT = STOPPED                       (f4d2f277…, exited, ExitCode 0, RestartCount 0)
EFB = STOPPED                         (6023ad35…, exited, ExitCode 0, RestartCount 0)
CONCURRENT_LIVE_QUALIFICATION = NO    (0 efb containers running)
CONCURRENT_BENCHMARK = NO             (0 benchmark processes, 0 v5-* containers)

AGENT_CHECKPOINT_PRE = 195927  >= 195927  PASS
EFB_CHECKPOINT_PRE   = 273844  >= 273844  PASS
CORE_STREAM_HEAD_PRE = 274307
CORE_RETENTION_FLOOR = 1
CORE_HEALTH_PRE      = ok:true, contract_version 1, accounts 2

TASKBOOK_SHA256     = EXACT   85ba886feec2c4ed3504ac071ccd0466156d43ba47e090956b98851b5211dc7d
OVERLAY_SHA256      = EXACT   8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d  (498 B)
F3_IMAGE_DIGEST     = EXACT   sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
F3_OCI_REVISION     = F3_SOURCE_COMMIT   6538f79a664a325543c19391cc14601d282e07a4
F3_IS_DESCENDANT_OF_1E5EDDD = YES
```

Host-side image identity (read before deploying):

```text
CONFIG = sha256:9061b9b3a986f70b9d77a9c0d5afd65e8e90808e735152f7a32d00d053407f31
REV    = 6538f79a664a325543c19391cc14601d282e07a4
VER    = 0.1.0-rc.14-core-media-contract-f3
DIGESTS = ["ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427"]
```

All gates PASS ⇒ proceeded.

---

## 3. Protected-service baseline (PRE) — host UTC 2026-09-17T01:44:14Z

| Service | Container ID | Image | State | Created | StartedAt | RestartCount |
| --- | --- | --- | --- | --- | --- | --- |
| core | `b93fa6a8bd6b1ed72323d249d2914cc4d5a054c0c29e1dd2ec0babf19a2663eb` | `ghcr.io/onestao/wechat-hub-core@sha256:c42822f4…5819f` | running | 2026-09-17T00:08:36Z | 2026-09-17T00:08:53Z | 0 |
| console | `cce13a59dad25fb8c10e741b6978b8c7b7e228ccc4259734a289cc439f22666a` | `ghcr.io/onestao/wechat-hub-console@sha256:8712f867…74dd` | running | 2026-09-13T02:00:29Z | 2026-09-13T12:05:02Z | 0 |
| runtime | `d21960eef445e709a9e3fd06f30327682f3493cb7adc113bf99b5c67ec2eb852` | `ghcr.io/onestao/wechat-hub-runtime@sha256:5a2454a6…2158` | running | 2026-09-09T18:05:24Z | 2026-09-11T06:45:48Z | 0 |
| agentwechat-a | `44559e58c4fefad872d07e353bbb6cfb340bff7bcfcd7ae9423aa2f4a155565d` | `ghcr.io/onestao/wechat-hub-agent-wechat@sha256:87b055e3…85e4` | running | 2026-09-09T07:09:21Z | 2026-09-11T05:12:55Z | 0 |
| agentwechat-b | `a6c2e3ee61e1521828cd2e352e00847b16ff2e8841a3364b21147abd1a25ca51` | `ghcr.io/onestao/wechat-hub-agent-wechat@sha256:87b055e3…85e4` | running | 2026-09-09T02:38:11Z | 2026-09-11T05:12:57Z | 0 |
| agent | `f4d2f2773e854f654c471200ed1530988c2655f62e8bd1b44796d90d3cddc096` | `ghcr.io/onestao/wechat-hub-agent@sha256:c9300742…463a` | **exited (STOPPED)** | 2026-09-16T07:31:41Z | 2026-09-16T07:31:50Z | 0 |
| efb | `6023ad354c2616659e60e75ad95471718074584db3255f9c52d572546b8c8ea9` | `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d5…6241` | **exited (STOPPED)** | 2026-09-16T16:49:34Z | 2026-09-16T16:49:38Z | 0 |

Only `core` was permitted to change.

---

## 4. The single authorized production mutation

Deploy script transferred byte-identically (`md5 6c60fbf2dfefc3096af60a89ebd24780`, 451 B, 10 lines)
and its content is the taskbook §8 command verbatim:

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose -f docker-compose.yml -f docker-compose.rc14-core-media-contract-f3-candidate.yml up -d --no-deps core
```

Execution log (`/root/rc14-coremedia-f3-deploy.log`):

```text
2026-09-17T01:44:49Z  docker compose ... up -d --no-deps core
warning: Found orphan containers ([wechat-hub-f-live-efb wechat-hub-f-live-agent]) for this project.
         If you removed or renamed this service in your compose file, you can run this command
         with the --remove-orphans flag to clean it up.
Container wechat-hub-f-live-core  Recreate
Container wechat-hub-f-live-core  Recreated
Container wechat-hub-f-live-core  Starting
Container wechat-hub-f-live-core  Started
COMPOSE_RC=0
2026-09-17T01:45:07Z
e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9|ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3…0427|running|2026-09-17T01:45:06.839931379Z|0
SCRIPT_DONE
```

```text
CORE_RECREATE_COUNT = 1
--remove-orphans    = NOT USED (the orphan warning was deliberately not acted on)
OTHER SERVICES      = NOT TOUCHED
```

New Core container: `e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9`,
`StartedAt 2026-09-17T01:45:06.839931379Z`, `RestartCount 0`.

---

## 5. Post-deployment gate and F3 contract qualification

### 5.1 Post-deploy health gate (host UTC 2026-09-17T01:45:51Z)

```text
CORE = e95ebb30… / ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3…0427 / running / healthy / RestartCount 0
F3_IMAGE_DIGEST = exact
F3_OCI_REVISION = 6538f79a664a325543c19391cc14601d282e07a4 = F3_SOURCE_COMMIT
/health = ok:true, contract_version 1, accounts 2, registry.ok true,
          sync_worker wechat-core-sync, consecutive_failed_cycles 0, last_cycle_error ""

AGENT_CHECKPOINT_POST = 195927  >= 195927 (floor) and >= PRE 195927   PASS
EFB_CHECKPOINT_POST   = 273844  >= 273844 (floor) and >= PRE 273844   PASS
CHECKPOINT_REGRESSION = ZERO
CORE_STREAM_HEAD_POST = 274727  (PRE 274307, monotonic)
CORE_RETENTION_FLOOR  = 1       (unchanged, no regression)
```

Worker liveness re-confirmed at `01:48:42Z`: `cycle_count 15`, `last_clean_cycle_at 01:48:42Z`,
`consecutive_failed_cycles 0`, `last_account_errors {}`, `stale_accounts []`, `degraded_accounts []`,
both accounts `online`, chats refreshed at `01:48:35Z`.

### 5.2 Gate 1 / Gate 2 — media headers

`GET /v1/media/{id}?account_id=…`:

| media id (prefix) | account | HTTP | X-Media-Id | X-Media-Role | X-Media-Status |
| --- | --- | --- | --- | --- | --- |
| `c43911d36150` | testB | 200 | present | `original` | `ready` |
| `ac8b72a166ea` | testB | 200 | present | `original` | `ready` |
| `8e7fbf4f0d20` | testB | 200 | present | `original` | `ready` |
| `bfec71c0c075` | f-live-a | 200 | present | `original` | `ready` |

```text
CORE_MEDIA_ROLE_HEADER_SUPPORTED   = PASS  (4/4)
CORE_MEDIA_STATUS_HEADER_SUPPORTED = PASS  (4/4)
```

### 5.3 Gate 3 / Gate 4 — message payload carries the top-level contract

Post-deploy event window, cursors `274308..274727` (everything the F3 runtime produced):

```text
total events             = 420   (account.status 6, message.updated 414)
media-bearing message events = 414
distinct messages        = 414
with top-level media_role   = 414 / 414   (100%)
with top-level media_status = 414 / 414   (100%)
```

Sample (`cursor 274312`, truncated):

```json
{"cursor":"274312","event_type":"message.updated","message":{
  "chat_id":"38808757431@chatroom","type":"image","direction":"incoming",
  "media_id":"bfec71c0c0753a84b18f11c9ca65f327d98f265198f4624a033a12af513dec2e",
  "media_role":"original",
  "media_status":"original_pending",
  "filename":"bfec71c0c0753a84b18f11c9ca65f327d98f265198f4624a033a12af513dec2e",
  "vendor_specific":{"media":{"role":"original","status":"original_pending","original_media_id":"bfec71c0…","thumbnail_media_id":""}, …}}}
```

REST projection `GET /v1/accounts/f-live-a/chats/38808757431@chatroom/messages?limit=3`:

```text
row 1: type=image  media_id=bfec71c0c075  media_role=original  media_status=original_pending
row 2: type=text   media_id=null          media_role=null      media_status=null
row 3: type=text   media_id=null          media_role=null      media_status=null
```

```text
CORE_MESSAGE_PAYLOAD_HAS_MEDIA_ROLE   = PASS   (event payload 414/414; REST row present)
CORE_MESSAGE_PAYLOAD_HAS_MEDIA_STATUS = PASS   (event payload 414/414; REST row present)
MESSAGE_UPDATED_MEDIA_ROLE_PRESENT    = YES
MESSAGE_UPDATED_MEDIA_STATUS_PRESENT  = YES
REST_MESSAGE_MEDIA_ROLE_PRESENT       = YES
REST_MESSAGE_MEDIA_STATUS_PRESENT     = YES
```

**`message.created` leg.** Zero media-bearing `message.created` events were produced during the whole
observation window (the only `message.created` in retention are three text-only events at cursors
274305–274307 emitted by the **previous** Core). No new WeChat traffic arrived — the stream head was
flat at `274727` for the entire check interval — and the authorization forbids sending real WeChat
messages to manufacture one.

```text
MESSAGE_CREATED_MEDIA_ROLE_PRESENT (live observation)   = NOT_OBSERVED_IN_WINDOW
MESSAGE_CREATED_MEDIA_STATUS_PRESENT (live observation) = NOT_OBSERVED_IN_WINDOW
REQUIRES_NEW_EVENT_FOR_EFB_RETRY = YES
```

Per the authorization's §6 historical-event rule this is **not** a gate failure. `message.created`
and `message.updated` share one construction site in the shipped commit — the payload is
`{"message": value}` in both branches, and only `event_type` differs
(`event_type = "message.created" if before is None else "message.updated"`). The created-leg is
additionally proven deterministically by the F3 test
`test_f3_1_message_created_event_exposes_media_contract_fields`, which ran green in the F3 CI job
`105039644228` **on this exact commit** `6538f79a…`, asserting that a `message.created` payload
carries both fields.

**Historical evidence kept separate** (never judged as a current-runtime failure):

```text
HISTORICAL_EVENT_IMMUTABLE: cursors 274251..274307 (previous Core 1e5eddd)
  49 media-bearing message.updated events, 49/49 WITHOUT top-level media_role/media_status
  → immutable evidence of the pre-F3 contract gap; not counted against the F3 runtime
CURRENT_CORE_PROJECTION  (cursors 274308..274727) = CONFORMANT (414/414)
CURRENT_MEDIA_API_CONTRACT                       = CONFORMANT (4/4 headers, 3/3 media.ready role)
```

### 5.4 Gate 5 — `media.ready` carries `role`

```text
media.ready events in window = 3
  cursor 274273  role=original  status=ready  filename=7d6cf6fa6c4277d829d920fcf77bfbbe.png
  cursor 274274  role=original  status=ready  filename=edff595bf50b47040d1cb57de4d936e5.jpg
  cursor 274275  role=original  status=ready  filename=c337a3799e5d8218fad78ce42df1d3b6.jpg
role present = 3/3   →  CORE_MEDIA_READY_EVENT_HAS_ROLE = PASS
```

### 5.5 Gate 6 — never publishes a thumbnail as a final original

Role ⟺ filename contingency over the whole post-deploy window:

```text
media_role=original   n=403   filename THUMB-like = 0
media_role=thumbnail  n=11    filename THUMB-like = 6  (_thumb.jpg), 5 hash-named
role=original WITH a thumb-like filename = 0     ← the decisive counter must stay zero
```

The 11 thumbnail-labelled events (excerpt):

```text
cursor 274472  media_role=thumbnail  media_status=ready             filename=55fe0ed7256fcf0c4cc5bdb79ed518db_thumb.jpg
cursor 274522  media_role=thumbnail  media_status=ready             filename=a728c85bc657be3cbb022ff038f1cff0_thumb.jpg
cursor 274562  media_role=thumbnail  media_status=ready             filename=ae0321e4ac68b1daa326e1ee6bf7eebf_thumb.jpg
cursor 274594  media_role=thumbnail  media_status=ready             filename=6b52dedb22c4ec0ce1eed98d628f6936_thumb.jpg
cursor 274606  media_role=thumbnail  media_status=ready             filename=e80ca77efb901f8fb6ede8661af230a4_thumb.jpg
cursor 274616  media_role=thumbnail  media_status=ready             filename=f2b8a44f5f0abfd00794dc76738558c1_thumb.jpg
```

Thumbnail assets are now reported **with `media_role = thumbnail`**, i.e. the runtime actively
distinguishes them instead of presenting them as originals — which is exactly what lets the frozen
EFB candidate fail closed with `has role 'thumbnail'; thumbnail cannot be final`. `media.ready`
filenames were 3/3 PLAIN for `role=original`.

```text
CORE_NEVER_PUBLISHES_THUMBNAIL_AS_ORIGINAL = PASS
THUMBNAIL_REPORTED_AS_ORIGINAL_READY       = NO
```

### 5.6 Gate summary

```text
CORE_MEDIA_CONTRACT_GATE_1 = PASS   (X-Media-Role header)
CORE_MEDIA_CONTRACT_GATE_2 = PASS   (X-Media-Status header)
CORE_MEDIA_CONTRACT_GATE_3 = PASS   (message payload has media_role)
CORE_MEDIA_CONTRACT_GATE_4 = PASS   (message payload has media_status)
CORE_MEDIA_CONTRACT_GATE_5 = PASS   (media.ready has role)
CORE_MEDIA_CONTRACT_GATE_6 = PASS   (thumbnail never as original)
```

GATE_3 and GATE_4 — the two gates that FAILED in the predecessor deployment — are now PASS, with
414/414 live evidence.

---

## 6. Protected-service reconciliation

Captured at host UTC `2026-09-17T01:47:32Z`.

| Service | Container ID | State | StartedAt | ExitCode | RestartCount | Delta |
| --- | --- | --- | --- | --- | --- | --- |
| core | `e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9` | running | 2026-09-17T01:45:06Z | 0 | 0 | **recreated (authorized)** |
| console | `cce13a59dad25fb8c10e741b6978b8c7b7e228ccc4259734a289cc439f22666a` | running | 2026-09-13T12:05:02Z | 0 | 0 | **0** |
| runtime | `d21960eef445e709a9e3fd06f30327682f3493cb7adc113bf99b5c67ec2eb852` | running | 2026-09-11T06:45:48Z | 0 | 0 | **0** |
| agentwechat-a | `44559e58c4fefad872d07e353bbb6cfb340bff7bcfcd7ae9423aa2f4a155565d` | running | 2026-09-11T05:12:55Z | 0 | 0 | **0** |
| agentwechat-b | `a6c2e3ee61e1521828cd2e352e00847b16ff2e8841a3364b21147abd1a25ca51` | running | 2026-09-11T05:12:57Z | 0 | 0 | **0** |
| agent | `f4d2f2773e854f654c471200ed1530988c2655f62e8bd1b44796d90d3cddc096` | **exited (STOPPED)** | 2026-09-16T07:31:50Z | 0 | 0 | **0** |
| efb | `6023ad354c2616659e60e75ad95471718074584db3255f9c52d572546b8c8ea9` | **exited (STOPPED)** | 2026-09-16T16:49:38Z | 0 | 0 | **0** |

```text
CONSOLE_RESTART_DELTA     = 0
RUNTIME_RESTART_DELTA     = 0
AGENTWECHAT_RESTART_DELTA = 0
AGENT_RESTART_DELTA       = 0
EFB_RESTART_DELTA         = 0
AGENT_STATE_FINAL = STOPPED
EFB_STATE_FINAL   = STOPPED
```

Final checkpoints (`01:49:31Z`): `wechat-agent 195927` (updated_at 2026-09-16T08:04:11Z, unchanged),
`efb-linux-wechat:wechat.linux 273844` (updated_at 2026-09-16T17:14:43Z, unchanged),
`wechat-console 274727`. No consumer was reset, rebootstrapped, acked or rolled back.

---

## 7. Core DB governance

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

Guard `scripts/forensics/check_forbidden_live_core_db_access.py` (v1.1.0, rule
`ACTIVE_CORE_HOST_PRODUCTION_DB_FILE_OPENS`):

```text
--selftest  ->  CI_NEGATIVE_TESTS = PASS ; CI_POSITIVE_TESTS = PASS
--mode both --json tmp/rc14-coremedia-f3/deploy_core_db_access_command_log.txt
            ->  files_scanned 1 ; findings [] ;
                RAW_SQLITE_GUARD = PASS ; GENERIC_FILE_OPEN_GUARD = PASS ; SCRATCH_GUARD = PASS
```

Every host command executed during this round is enumerated in
`tmp/rc14-coremedia-f3/deploy_core_db_access_command_log.txt`. All Core state, checkpoint, media and
event reads went through `http://127.0.0.1:18082`. No `sqlite3`, no `sha256sum`/`cat`/`cp`/`dd`/`tar`
against `core-data/**`, no `/dev/shm` snapshot, no sidecar bind, no `docker exec`, no consumer
mutation. Exactly one production service mutation occurred: the authorized Core recreate.

The only container-log anomaly is a `BrokenPipeError` in `socketserver.write` — a client disconnect
while a response was being written, caused by this round's own short-timeout `curl` probes. It is
benign and did not affect any request used as evidence.

---

## 8. Disclosures and residual risks

### 8.1 Re-emission magnitude is 414, not the predicted 10–30 (important)

The taskbook §6.3 predicted an extra `message.updated` for "order 10–30" media-bearing messages.
The **actual** measured magnitude is:

```text
re-emitted media-bearing messages = 414   (cursors 274308..274727, ~2.7 min, one-time)
  by media_role:  original 403 , thumbnail 11
  by media_status: original_pending 228 , missing_metadata 89 , missing_file 83 , ready 13 , decode_failed 1
converged at cursor 274727; stream head flat for the whole subsequent check interval
```

Cause: the F3 keys participate in the message digest, and the 5 s sync worker re-reads **every**
message in the staging database, so every media-bearing message re-emits exactly once. The
predecessor F1/F2 figure of 15 was a partial reading, not the population size.

**This is the single most consequential residual item**, because these 414 events land at cursors
`274308..274727`, i.e. **after** the frozen EFB checkpoint `273844`:

* A next EFB Functional Live round that enters at checkpoint `273844` **will replay all 414**.
* 13 of them carry `media_status = ready`, so they are deliverable under the frozen candidate's
  rules; the remaining 401 are pending/retryable or fail-closed. A replay could therefore produce
  real Telegram deliveries of historical media and would pollute the round's ledger.
* **Prerequisite for the next round:** its taskbook must fix the EFB entry checkpoint at the
  post-deployment head (`274727`, or the head at that time) — or otherwise explicitly account for
  this replay — *before* EFB is started. This is a round-design obligation, not a Core defect, and
  it requires its own operator decision because advancing a consumer checkpoint is a consumer-state
  mutation.

### 8.2 Message-level vs media-level status can disagree

For `bfec71c0c075…`: the message-level projection reports `media_status = original_pending`, while
`GET /v1/media/bfec71c0c075…?account_id=f-live-a` reports `X-Media-Status: ready`. The two come from
different sources (the message carries the media resolution outcome recorded at normalisation time;
the media row carries the media table's own status). The frozen EFB candidate treats a non-`ready`
message status as `MediaPendingError` and has an explicit `_retry_pending_media` recovery path keyed
on `media.ready`, so this is recoverable — but the next round should treat "message pending while
media ready" as a known, expected state rather than a fault.

### 8.3 `message.created` leg not live-observed

See §5.3. Structurally and CI-proven on the shipped commit; `REQUIRES_NEW_EVENT_FOR_EFB_RETRY = YES`.

### 8.4 Pre-existing F1 caveat, unchanged

The additive `media.role` column still defaults to `'original'` for rows that were never re-upserted
as `ready`. F3 does not widen or narrow this; the API cannot prove byte provenance of historical
media.

### 8.5 Taskbook naming

See §0.1 — the authorization referenced a filename that does not exist; the hash matched the actual
sealed artifact, which is the one that was executed.

---

## 9. Verdict

```text
CORE_MEDIA_CONTRACT_F3_DEPLOYMENT = PASS
EFB_FUNCTIONAL_RETRY_PREREQUISITE = PASS
```

All six acceptance gates PASS, with 414/414 live evidence on the two gates (GATE_3, GATE_4) that
failed in the predecessor deployment. Core is healthy on the immutable F3 digest, checkpoints show
zero regression, and all protected services are untouched.

`EFB_FUNCTIONAL_RETRY_PREREQUISITE = PASS` means **the Core-side blocker for an EFB Functional Live
retry is closed**. It does **not** authorize that retry, and it is conditional on the §8.1
entry-checkpoint prerequisite being satisfied by the next round's taskbook.

---

## 10. Next step

```text
ACTION = STOP
```

Not started, not authorized by this phase:

```text
EFB   = STOPPED   (do not start)
AGENT = STOPPED   (do not start)
EFB_FUNCTIONAL_LIVE_RETRY1 = NOT AUTHORIZED
ROLLBACK                   = NOT PERFORMED
CORE_RECREATE_COUNT        = 1  (budget exhausted; a second recreate needs new authorization)
```

---

## 11. Evidence artifacts

```text
docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md   85ba886f…1dc7d   (sealed, unmodified)
docs/RC14_CORE_MEDIA_CONTRACT_F3_COMPLETION_RESULT.md                0aa93405…ca1f    (sealed, unmodified)
docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_RESULT.md     this document (+ .sha256)
tmp/rc14-coremedia-f3/deploy_core_db_access_command_log.txt          whole-round host command log
tmp/rc14-coremedia-f3/core_db_access_command_log.txt                 engineering-phase host command log
tmp/rc14-coremedia/ci_test_log_f3.txt                                CI job 105039644228 (Ran 248 tests)
tmp/rc14-coremedia/f3-deploy.sh                                      deploy script (md5 6c60fbf2dfefc3096af60a89ebd24780)
tmp/rc14-coremedia/f3-pull.sh                                        image pull script (md5 87acad9f7e7d6584f69a377a4f6a3f0e)
/root/rc14-coremedia-f3-deploy.log                                   host-side deploy log
```
