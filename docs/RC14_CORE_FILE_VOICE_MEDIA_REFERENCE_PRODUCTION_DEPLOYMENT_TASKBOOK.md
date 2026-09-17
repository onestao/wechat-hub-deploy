# RC.14 Core File / Voice Media Reference — Production Deployment Taskbook

```text
DOCUMENT_TYPE                     = PRODUCTION_DEPLOYMENT_TASKBOOK
DOCUMENT_STATUS                   = SEALED / NOT_EXECUTED
WORK_PACKAGE                      = RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_ENGINEERING
PRODUCED_BY                       = RC.14 Core file/voice media-reference engineering round
SEALED_AT_UTC                     = 2026-09-17T11:37:00Z
AUTHORIZES                        = nothing by itself
ACTION                            = STOP
```

> **This document does not authorize anything.** It records the exact, reproducible
> procedure that a *separately authorized* operator run would follow to make the
> candidate in §2 the running production Core. Executing it without a new, explicit
> operator authorization is a governance violation.

---

## 0. Mandatory governance statement — ACTIVE CORE PRODUCTION DB ACCESS RULE

This work package executes under the **ACTIVE CORE PRODUCTION DB ACCESS RULE**
(`docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md`). While production Core is
RUNNING, no host-side or side-channel command may open the *contents* of the
production Core database set. The rule's required return values are:

```text
ACTIVE_CORE_RAW_SQLITE_READS = 0
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
```

Both are required at the end of the executing round. Allowed while Core is RUNNING:
the Core HTTP API (`curl http://127.0.0.1:18082/v1/...`), `docker inspect` /
`docker logs` / `docker ps` / `docker image inspect`, `docker compose config`, and
filesystem **metadata** inspection (`ls`, `stat`, `find`, `lsof`). Forbidden:
`sqlite3`, `sha256sum`, `cat`/`head`/`tail`, `cp`/`dd`/`rsync`/`tar`, `docker exec`
into the Core container, and any bind-mount side channel — all against the protected
set, which is enumerated in §7.

---

## 1. Pinned production state at seal time

Captured `2026-09-17T11:36:38Z` (host UTC) through the read-only Core HTTP API and
`docker inspect` only. No service was mutated by this round.

```text
CORE_CONTAINER_ID            = e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9
CORE_STATE                   = running / healthy
CORE_RESTART_COUNT           = 0
CORE_STARTED_AT              = 2026-09-17T01:45:06.839931379Z
CORE_SOURCE_COMMIT_CURRENT   = 6538f79a664a325543c19391cc14601d282e07a4
CORE_IMAGE_DIGEST_CURRENT    = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
CORE_OCI_VERSION_CURRENT     = 0.1.0-rc.14-core-media-contract-f3

AGENT_CHECKPOINT             = 195927      (updated_at 2026-09-16T08:04:11Z)
EFB_CHECKPOINT               = 273844      (updated_at 2026-09-16T17:14:43Z)
CONSOLE_CHECKPOINT           = 274796      (updated_at 2026-09-17T11:09:01Z)
STREAM_HEAD_CURSOR           = 274796      (moving value; account.status heartbeat ~5 s)
RETENTION_FLOOR_CURSOR       = 1

AGENT_STATE                  = STOPPED     (wechat-hub-f-live-agent, exited 0)
EFB_STATE                    = STOPPED     (wechat-hub-f-live-efb, exited 0)
CONSOLE_STATE                = running / healthy
RUNTIME_STATE                = running / healthy
AGENTWECHAT_STATE            = running     (wechat-agent-f-live-a-*, wechat-agent-testb-*)
```

Pinned consumer floors — **must be re-read and re-confirmed immediately before any
execution**, never assumed from this document:

```text
AGENT_CHECKPOINT_FLOOR       >= 195927
EFB_CHECKPOINT_FLOOR         >= 273844
CHECKPOINT_PROTOCOL_CHANGE   = NONE  (this work package does not touch it)
```

---

## 2. Immutable candidate identity

```text
NEW_SOURCE_COMMIT            = 9434e915b78b2eb5471acf282d4e223c03e8d83a
NEW_SOURCE_BRANCH            = rc14-core-filevoice-media-ref  (origin/rc14-core-filevoice-media-ref)
NEW_SOURCE_PARENT            = 6538f79a664a325543c19391cc14601d282e07a4
NEW_SOURCE_DESCENDANT_OF_F3  = YES
NEW_SOURCE_COMMIT_MESSAGE    = RC14 FMR: cover file/voice media references, stop projecting non-files as files

NEW_IMAGE_REF                = ghcr.io/onestao/wechat-hub-core@sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
NEW_IMAGE_DIGEST             = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
NEW_IMAGE_CONFIG_ID          = sha256:a11731dafc06a93631a5726e1549e479462165efd1b0abd7377dbd877237e165
NEW_IMAGE_TAG                = 0.1.0-rc.14-core-filevoice-media-ref   (mutable label; NOT a production identity)
NEW_IMAGE_SIZE_BYTES         = 500804144
NEW_IMAGE_CREATED            = 2026-09-17T11:33:40.35797917Z
NEW_OCI_REVISION             = 9434e915b78b2eb5471acf282d4e223c03e8d83a
NEW_OCI_VERSION              = 0.1.0-rc.14-core-filevoice-media-ref
OCI_REVISION == SOURCE_COMMIT = YES

CI_RUN                       = 35215908801   (Core CI, push, headSha 9434e915b78b2eb5471acf282d4e223c03e8d83a)
CI_TEST_JOB                  = 105184218086  -> success
CI_DOCKER_BUILD_JOB          = 105184992777  -> success
CI_TESTS                     = Ran 268 tests in 147.343s ; 0 FAIL ; 0 ERROR
CI_TEST_DELTA                = +20 (248 at F3 -> 268), i.e. exactly the new FMR-1..FMR-8 module
PUBLISH_RUN                  = 35216281684   (Core Publish RC Image, workflow_dispatch) -> success

DIGEST_PULL_PROOF            = PASS  (docker pull <ref>@sha256:a0d4f70b... -> rc 0, "Image is up to date")
DIGEST_EXTRACTED_ON_HOST     = /root/rc14-filevoice-pull.log
HOST_PULL_SCRIPT_MD5         = b43b96da925a62e9f6be81be8bcef9ac  (850 B, verified byte-identical after transfer)
```

The tag `0.1.0-rc.14-core-filevoice-media-ref` is a mutable convenience label. The
production identity is the **manifest digest** above, extracted on the host from
`docker image inspect <config-id> .RepoDigests` and then proved pullable by digest.
The digest printed by the build log is never used as a production identity.

---

## 3. Recreate budget — ⛔ EXHAUSTED

```text
CORE_RECREATE_COUNT_USED              = 1        (consumed by the F3 deployment on 2026-09-17)
CORE_RECREATE_BUDGET_REMAINING        = 0
REQUIRES_NEW_OPERATOR_AUTHORIZATION   = YES
PRIOR_AUTHORIZATION_INHERITABLE       = NO
```

The F3 work package's single permitted production Core recreate has been spent. This
work package does **not** carry a recreate allowance, and the F3 authorization must
not be treated as reusable or transferable.

> **The next production Core recreate requires a new, explicit operator
> authorization that names this work package, this taskbook, and this exact image
> digest. Without it, the correct action is `STOP`.**

---

## 4. Exact deployment procedure (ONLY after a new authorization)

All steps run on the unraid host as root. `run-command` is single-line and the
transport gives up after 60 s — long steps must be launched detached and read back
from a log file. A transport timeout after `LAUNCHED` is **not** a failure.

### 4.0 Pre-flight (read-only, mandatory)

```bash
date -u "+%Y-%m-%dT%H:%M:%SZ"
docker inspect wechat-hub-f-live-core --format "{{.Id}}|{{.Config.Image}}|{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}"
curl -s -m 10 http://127.0.0.1:18082/health
curl -s -m 10 "http://127.0.0.1:18082/v1/events/checkpoint?consumer_id=wechat-agent"
curl -s -m 10 "http://127.0.0.1:18082/v1/events/checkpoint?consumer_id=efb-linux-wechat%3Awechat.linux"
curl -s -m 10 "http://127.0.0.1:18082/v1/events/poll?after=0&limit=1"      # stream head; NO consumer_id
```

Abort if any of these hold:

```text
CORE_CONTAINER_ID      != e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9
CORE_IMAGE             != sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
AGENT_CHECKPOINT       <  195927
EFB_CHECKPOINT         <  273844
AGENT_STATE            != STOPPED
EFB_STATE              != STOPPED
```

Record `STREAM_HEAD_CURSOR` with its timestamp — it is a moving value.

### 4.1 Confirm the candidate digest is present and pullable

```bash
docker pull ghcr.io/onestao/wechat-hub-core@sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
docker image inspect sha256:a11731dafc06a93631a5726e1549e479462165efd1b0abd7377dbd877237e165 --format "{{json .RepoDigests}}"
```

Both must succeed (`rc 0`) and the reported digest must equal §2.

### 4.2 Verify the overlay is byte-identical to the sealed artifact

```bash
cd /mnt/user/appdata/wechat-hub-f-live
sha256sum docker-compose.rc14-core-filevoice-media-ref-candidate.yml
wc -c    docker-compose.rc14-core-filevoice-media-ref-candidate.yml
```

```text
OVERLAY_PATH   = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-filevoice-media-ref-candidate.yml
OVERLAY_SHA256 = a46b318f579bcf9c36b0cdb909b97639bd4f5c702f7dc7a1376f3147542afc9e
OVERLAY_BYTES  = 313
```

The file is already on the host (written during engineering; it is inert and touches
no running service). If the hash does not match, **stop** — do not regenerate it.

### 4.3 Re-prove the render diff is one line

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose -f docker-compose.yml -f docker-compose.rc14-core-media-contract-f3-candidate.yml config > /tmp/rc14fv-running.yml
docker compose -f docker-compose.yml -f docker-compose.rc14-core-filevoice-media-ref-candidate.yml config > /tmp/rc14fv-cand.yml
diff -u /tmp/rc14fv-running.yml /tmp/rc14fv-cand.yml
```

Required:

```text
RENDER_DIFF_CHANGED_LINES = 1     (services.core.image only)
RENDER_DIFF_UNEXPECTED    = NONE
```

### 4.4 Recreate Core only

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose -f docker-compose.yml -f docker-compose.rc14-core-filevoice-media-ref-candidate.yml up -d --no-deps core
```

Constraints:

* `--no-deps` is required.
* **Do not** add `--remove-orphans`: the intentionally stopped
  `wechat-hub-f-live-efb` and `wechat-hub-f-live-agent` containers legitimately
  appear as orphans and must be left alone.
* Exactly one service may change: `core`. Console, Runtime, AgentWechat, Agent and
  EFB must not be recreated, restarted or started.

### 4.5 Post-recreate confirmation

```bash
sleep 20
docker inspect wechat-hub-f-live-core --format "{{.Id}}|{{.Config.Image}}|{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}"
curl -s -m 10 http://127.0.0.1:18082/health
```

```text
CORE_IMAGE              == sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
CORE_OCI_REVISION       == 9434e915b78b2eb5471acf282d4e223c03e8d83a
CORE_STATE              == running / healthy
CORE_RESTART_COUNT      == 0
```

---

## 5. Post-deployment acceptance gate

All of the following must hold before the deployment may be called PASS.

### 5.1 Service identity and health

```text
CORE_IMAGE_IS_CANDIDATE_DIGEST = YES
CORE_OCI_REVISION              = 9434e915b78b2eb5471acf282d4e223c03e8d83a
CORE_STATE                     = running / healthy
CORE_RESTART_COUNT             = 0
HEALTH_ENDPOINT                = ok:true, contract_version 1, accounts 2
```

### 5.2 Untouched neighbours

```text
CONSOLE_STARTED_AT   unchanged
RUNTIME_STARTED_AT   unchanged
AGENTWECHAT_STARTED_AT unchanged (both accounts)
AGENT_STATE          = STOPPED   (do not start)
EFB_STATE            = STOPPED   (do not start)
SERVICE_RESTART_DELTA_EXCLUDING_CORE = 0
```

### 5.3 Consumer checkpoint protocol

```text
AGENT_CHECKPOINT   >= 195927    (expected: exactly 195927, untouched)
EFB_CHECKPOINT     >= 273844    (expected: exactly 273844, untouched)
CHECKPOINT_PROTOCOL_REGRESSION = ZERO
```

### 5.4 Contract probes

Capture the pre-deployment baseline first, then the post-deployment value, so the
result is self-evidently a delta.

```bash
curl -s -m 10 "http://127.0.0.1:18082/v1/accounts/f-live-a/chats/38808757431@chatroom/messages?limit=5"
curl -s -m 20 "http://127.0.0.1:18082/v1/events/poll?limit=200&after=<STREAM_HEAD_BEFORE>" \
  | jq -c ".events[] | select(.event_type|startswith(\"message.\")) | {cursor, type:.payload.message.type, media_id:.payload.message.media_id, role:.payload.message.media_role, status:.payload.message.media_status}"
```

Required:

```text
NO_MESSAGE_PROJECTED_AS_FILE_WITHOUT_A_MEDIA_REFERENCE = YES
NO_TOP_LEVEL_MEDIA_ROLE_STATUS_REGRESSION              = YES   (F3 fields still present)
X_MEDIA_ROLE / X_MEDIA_STATUS still returned by GET /v1/media/{id}
```

### 5.5 Bounded re-emission disclosure and the next-round entry obligation

The candidate changes the projected **type** of `link_or_file` messages that are not
genuine file transfers, and gives genuine file/voice messages a media reference. Any
message whose persisted digest changes is re-emitted by the 5 s sync worker as one
`message.updated`, **after** the current consumer checkpoints.

Measured on the production account staging store at seal time:

```text
link_or_file messages in staging                        = 134
  genuine file transfers (appmsg type 6)                =   2   -> stay `file`, gain a media reference
  url shares with a real url                            =  19   -> stay `link`
  quote replies (appmsg type 57)                        = 110   -> `file` -> `text`
  merged chat records (appmsg type 19)                  =   3   -> `file` -> `text`
  other non-file appmsg subtypes                        =   1   -> `file` -> `text`
currently projected as `file`                           = 115
re-typed by this candidate                              = 113
voice messages in staging                               =   5   -> gain a media reference
```

Consequences that **must** be honoured by the next consumer live round:

```text
1. The re-emitted events land after EFB_CHECKPOINT (273844), so a next EFB live
   round entering at its old checkpoint replays all of them -- including events
   that are now deliverable, which would produce real external deliveries and
   pollute the round ledger.
2. Therefore the next EFB live round MUST fix its entry checkpoint at the
   post-deployment stream head, not at 273844.
3. Advancing any consumer checkpoint is itself a consumer-state mutation and
   REQUIRES ITS OWN SEPARATE AUTHORIZATION.  This taskbook does not grant it.
4. EFB's continuation point is the LOCAL `core-event-cursor.json`, not the Core
   checkpoint row (CursorStore.align_with_core only advances a missing or
   below-initial_cursor local value).  Both values must be pinned together.
```

### 5.6 Voice artifact limitation (disclosed, not a gate failure)

```text
VOICE_ORIGINAL_FORM          = SILK (WeChat voiceformat 4), lifted verbatim from
                               the decrypted VoiceInfo table
VOICE_TRANSCODE              = NOT PERFORMED  (no SILK decoder exists in the image)
VOICE_MIME_TYPE              = audio/silk
VOICE_CONSUMER_DELIVERABILITY = UNVERIFIED
```

The Core contract is satisfied — the original artifact exists and is retrievable
byte-for-byte, with `media_role=original` and `media_status=ready`. Whether the
downstream consumer can *deliver* a SILK container (Telegram voice notes require
OGG/Opus) was not verified offline and must be treated as a live-round risk, not as
a Core contract gap. If a live round fails on voice delivery, the correct fix
direction is a transcode step (add a SILK decoder to the image), not a change to the
media-reference contract.

---

## 6. Rollback

Rollback is a **second production Core recreate** and therefore also requires an
explicit operator authorization. It must not be improvised.

```text
ROLLBACK_OVERLAY        = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-media-contract-f3-candidate.yml
ROLLBACK_OVERLAY_SHA256 = 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d   (verified at seal time)
ROLLBACK_IMAGE_DIGEST   = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
ROLLBACK_IMAGE_PRESENT_ON_HOST = YES  (confirmed present in the host image list at seal time)

ROLLBACK_COMMAND = docker compose -f docker-compose.yml \
                     -f docker-compose.rc14-core-media-contract-f3-candidate.yml \
                     up -d --no-deps core
```

Older images remain on the host as further rollback material:

```text
sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f  (config 8add2212d7e2)  = 1e5eddd
sha256:7d9259a420d152706bca80a28c9757633e527fd0f681fa32d9883048878d3ab5  (config 661967daae8a)  = 08a4e74
```

**Never restore a consumer checkpoint to a lower value**, even during rollback.
**Never delete or rewrite the EFB effect ledger or its `MEDIA_FAILED` history.**

---

## 7. Prohibitions for the executing round

```text
DO_NOT  start EFB
DO_NOT  start the Agent
DO_NOT  run the EFB Functional Live Retry
DO_NOT  advance, rebootstrap or roll back any consumer checkpoint
DO_NOT  recreate, restart or start Console / Runtime / AgentWechat / Agent / EFB
DO_NOT  open the protected production Core DB set while Core is RUNNING
DO_NOT  snapshot the Core DB while Core is active
DO_NOT  modify this taskbook or any sealed result document
DO_NOT  deploy any digest other than the one in §2
```

Protected set (policy `docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md` §1.2) — the
only files this round may never open while Core is RUNNING:

```text
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-wal
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-shm
/mnt/disk3/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite
/app/runtime/core/wechat_core.sqlite
```

---

## 8. Required return block after execution

```text
CORE_IMAGE_AFTER              =
CORE_OCI_REVISION_AFTER       =
CORE_STATE_AFTER              =
CORE_RESTART_COUNT_AFTER      =
CORE_CONTAINER_ID_AFTER       =
AGENT_CHECKPOINT_AFTER        =
EFB_CHECKPOINT_AFTER          =
STREAM_HEAD_BEFORE            =
STREAM_HEAD_AFTER             =
SERVICE_RESTART_DELTA_EXCLUDING_CORE =
CHECKPOINT_PROTOCOL_REGRESSION =
NO_MESSAGE_PROJECTED_AS_FILE_WITHOUT_A_MEDIA_REFERENCE =
F3_MEDIA_PROJECTION_REGRESSION =
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS =
ACTIVE_CORE_RAW_SQLITE_READS         =
PRODUCTION_EFB_TOUCHED        =
PRODUCTION_AGENT_TOUCHED      =
ROLLBACK_PERFORMED            =
ACTION                        = STOP
```

---

## 9. Provenance of this document

```text
TASKBOOK_PATH   = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_TASKBOOK.md
ENGINEERING_RESULT = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_ENGINEERING_RESULT.md
```

Every digest, sha256 and byte count in this document was measured, not predicted.
The overlay sha256 in §4.2 was computed from the **actual** file on the host, which is
what makes the seal meaningful.
