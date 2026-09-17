# RC.14 Core Media Contract F3 — Production Deployment Taskbook

```text
TASKBOOK_ID                = RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT
REQUEST_ID                 = CORE_MEDIA_ROLE_CONTRACT_V1
ISSUED_AT                  = 2026-09-17T01:28:02Z  (host UTC)
ISSUED_BY                  = RC.14 release engineering
AUTHORIZATION_STATE        = PENDING_OPERATOR_APPROVAL
PREDECESSOR_TASKBOOK       = docs/RC14_CORE_MEDIA_ROLE_CONTRACT_PRODUCTION_DEPLOYMENT_TASKBOOK.md
PREDECESSOR_TASKBOOK_SHA256= dd305c5f0aef59f4a822e2844b7276dc381dd076d8d963d8f48e248924b02316
PREDECESSOR_RESULT         = docs/RC14_CORE_MEDIA_ROLE_CONTRACT_PRODUCTION_DEPLOYMENT_RESULT.md
PREDECESSOR_RESULT_SHA256  = c874a0f6c2f7086105a1d944d0b021fee6a80d111ba472f82f76ea666781bced
PREDECESSOR_VERDICT        = FAIL  (GATE_3 = FAIL, GATE_4 = FAIL)
```

> This taskbook is the **only** authorization surface for the next production Core
> mutation. It must be sealed (SHA256 recorded) before the deployment command in §8
> is executed, and it must never be edited after sealing. Corrections go into a
> separate erratum document.

---

## §1 Authorization and scope

The operator decision of 2026-09-17 is the governing instruction:

```text
KEEP_CURRENT_CORE      = YES
ROLLBACK_CURRENT_CORE  = NO            # 禁止任何 rollback
NEXT_STEP              = Core Media Contract F3 Completion
F3.DESCENDANT_OF       = 1e5eddd4b5504bad44409ab610767688e32ddca2
EFB                    = STOPPED
AGENT                  = STOPPED
EFB_FUNCTIONAL_LIVE_RETRY = NOT AUTHORIZED
```

F3 was authorized **only** to fix the projection/whitelist data loss. After F3
engineering, regression, immutable image and this sealed taskbook, the next
controlled Core recreate may be applied for. This taskbook records that the
engineering preconditions are met and defines the deployment that may be applied
**once the operator approves it**.

### §1.1 In-scope change surface (as executed)

| Surface | Status |
| --- | --- |
| `message.created` top-level `message.media_role` | FIXED |
| `message.created` top-level `message.media_status` | FIXED |
| `message.updated` same fields | FIXED |
| REST message projection same fields | FIXED |
| store / serialization path no longer drops normalized media-contract fields | FIXED |

### §1.2 Out-of-scope surfaces (attested untouched)

```text
EFB_MODIFICATION                       = NONE
AGENT_MODIFICATION                     = NONE
CHECKPOINT_PROTOCOL_MODIFICATION       = NONE
STORAGE_MIGRATION                      = NONE
ACCOUNT_STATUS_RECEIPT_REDESIGN        = NONE
UNRELATED_CORE_SCHEMA_REFACTOR         = NONE
MESSAGES_TABLE_SCHEMA_CHANGE           = NONE
```

---

## §2 Pinned identities

```text
CORE_F3_SOURCE_COMMIT_FULL   = 6538f79a664a325543c19391cc14601d282e07a4
CORE_F3_SOURCE_PARENT        = 1e5eddd4b5504bad44409ab610767688e32ddca2
CORE_F3_BRANCH               = rc14-core-media-f3  (origin/rc14-core-media-f3)
CORE_F3_IMAGE_REF            = ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
CORE_F3_IMAGE_DIGEST         = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
CORE_F3_IMAGE_CONFIG_ID      = sha256:9061b9b3a986f70b9d77a9c0d5afd65e8e90808e735152f7a32d00d053407f31
CORE_F3_IMAGE_CREATED        = 2026-09-17T01:23:37.472421668Z
CORE_F3_OCI_REVISION         = 6538f79a664a325543c19391cc14601d282e07a4
CORE_F3_OCI_VERSION          = 0.1.0-rc.14-core-media-contract-f3
OCI_REVISION_EQUALS_SOURCE_COMMIT = YES
CORE_F3_MUTABLE_TAG          = ghcr.io/onestao/wechat-hub-core:0.1.0-rc.14-core-media-contract-f3  (NOT a production identity)
DIGEST_PULL_PROOF            = PASS  (docker pull by digest returned rc 0, "Image is up to date")
```

**Mutable tags are never a production identity.** The overlay in §2.1 pins the
manifest digest only.

### §2.1 Deployment overlay (already created, inert)

```text
OVERLAY_PATH   = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-media-contract-f3-candidate.yml
OVERLAY_BYTES  = 498
OVERLAY_SHA256 = 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d
```

```yaml
# Core Candidate overlay for RC.14 Core Media Contract F3
# Pinned to immutable candidate digest: ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
# OCI revision: 6538f79a664a325543c19391cc14601d282e07a4
# Scope: CORE SERVICE ONLY. Untouched: runtime, console, agent, agentwechat, efb.
name: wechat-hub-f-live
services:
  core:
    image: ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
```

The file was written **before** this taskbook was sealed and verified byte-identical
to the locally generated expectation (498 B, SHA256 above). Writing it did not touch
any running service. The previously deployed overlay
`docker-compose.rc14-core-media-role-candidate.yml` (SHA256
`c20e5e259473da1f59df2b622a42f11faa9adfec0e7c2ffdea92ecdb1c702b5e`) is **preserved
unmodified** so it remains a byte-exact rollback artifact.

### §2.2 Render-diff proof (executed before sealing)

```text
docker compose -f docker-compose.yml -f docker-compose.rc14-core-media-role-candidate.yml      config > running
docker compose -f docker-compose.yml -f docker-compose.rc14-core-media-contract-f3-candidate.yml config > candidate
diff running candidate
```

```diff
81c81
<     image: ghcr.io/onestao/wechat-hub-core@sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f
---
>     image: ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
```

```text
RENDER_DIFF_CHANGED_LINES = 1        # services.core.image only
RENDER_DIFF_UNEXPECTED    = NONE
```

---

## §3 Production Core lineage

```text
LINEAGE_BEFORE_F1            = 08a4e746e66fe94cbe73f99f7284ae7f01963447  (governed bootstrap / SIGBUS-recovery lineage)
LINEAGE_F1                   = 2caee27b5ad273eaa829c77191f722559749ea73
LINEAGE_F2                   = 1e5eddd4b5504bad44409ab610767688e32ddca2
LINEAGE_F3                   = 6538f79a664a325543c19391cc14601d282e07a4
F3_PARENT                    = 1e5eddd4b5504bad44409ab610767688e32ddca2
F3_IS_STRICT_DESCENDANT      = YES   (git merge-base --is-ancestor 1e5eddd 6538f79)
CURRENT_PROD_SOURCE_COMMIT   = 1e5eddd4b5504bad44409ab610767688e32ddca2
CURRENT_PROD_IMAGE_DIGEST    = sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f
CURRENT_PROD_IMAGE_CONFIG_ID = sha256:8add2212d7e203bf22bc7d235da9220546969a10d69a981f3cc5ceca9a657715
```

The deployment in §8 moves Core from `1e5eddd` to its direct child `6538f79`, so the
consumer-bootstrap / required-consumer-governance / SIGBUS-recovery lineage is
preserved by construction (fast-forward within the same line).

---

## §4 Checkpoint floors (legal minimums — no rollback permitted)

```text
AGENT_CHECKPOINT_FLOOR = 195927
EFB_CHECKPOINT_FLOOR   = 273844
```

```text
AGENT_CHECKPOINT_BEFORE_DEPLOY = 195927     (wechat-agent)
EFB_CHECKPOINT_BEFORE_DEPLOY   = 273844     (efb-linux-wechat:wechat.linux)
CORE_STREAM_HEAD_BEFORE_DEPLOY = 274307
CORE_RETENTION_FLOOR           = 1
```

Forbidden under any circumstance: restoring `EFB -> 272548`, `Agent -> 129248`,
`Agent -> 95667`, or any checkpoint decrement. `273844` is the new legal EFB floor.

---

## §5 Red lines (unchanged from the predecessor taskbook)

While Core is ACTIVE:

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0     (required)
ACTIVE_CORE_RAW_SQLITE_READS         = 0     (required)
```

Forbidden against the production Core DB (`.../core-data/core/wechat_core.sqlite`,
including `-wal`/`-shm`): `sqlite3`, Python `sqlite3`, `sha256sum`, `cat`/`head`/`tail`,
`cp`/`dd`/`rsync`/`tar`/`gzip`, any sidecar-bind open. All Core state and checkpoint
reads go through the Core HTTP API (`http://127.0.0.1:18082`) or the in-container VFS.

Forbidden actions during this deployment:

```text
START_EFB                        = FORBIDDEN
START_AGENT                      = FORBIDDEN
REAL_TELEGRAM_SEND               = FORBIDDEN
REAL_WECHAT_SEND                 = FORBIDDEN
CONSUMER_REBOOTSTRAP             = FORBIDDEN
CHECKPOINT_ROLLBACK              = FORBIDDEN
DELETE_EFFECT_LEDGER             = FORBIDDEN
DELETE_42_MEDIA_FAILED_ROWS      = FORBIDDEN
MODIFY_EFB_FUNCTIONAL_IMAGE      = FORBIDDEN
MODIFY_EFB_PROFILE               = FORBIDDEN
STORAGE_MIGRATION                = FORBIDDEN
RECREATE_CONSOLE                 = FORBIDDEN
RECREATE_RUNTIME                 = FORBIDDEN
RECREATE_AGENTWECHAT             = FORBIDDEN
```

`/dev/shm` must never be used as a persistent snapshot store. No file-level DB
snapshot is required for this deployment: the change is an additive application
projection and no schema migration is involved (see §6.2).

---

## §6 Change character

### §6.1 Diff scope

```text
DIFF 1e5eddd..6538f79
core/store.py                                          | +29
core/tests/test_efb_media_functional_correctness.py    | +148
2 files changed, 177 insertions(+), 0 deletions(-)
```

Both hunks in `core/store.py` are additive and confined to message projection:

1. `CoreStore.upsert_message()` — after the existing `source_local_id` /
   `source_message_table` handling, materialize `value["media_role"]` and
   `value["media_status"]` from the normalizer output (falling back to
   `vendor_specific.media`). These keys reach the persisted value, the digest, and
   the `{"message": value}` event payload.
2. `CoreStore._message_row()` — after the existing `vendor_specific` projection,
   lift `vendor_specific.media.role` / `.status` to the top level of the REST
   message row.

### §6.2 Schema impact

```text
CORE_DB_SCHEMA_DESTRUCTIVE_CHANGE = NO
MESSAGES_TABLE_SCHEMA_CHANGE      = NONE
MEDIA_TABLE_SCHEMA_CHANGE         = NONE   (the additive `media.role` column was introduced by F1 and is already live)
```

F3 adds **no** DDL. The new fields are derived from the already-persisted
`vendor_json`, so no migration, no backfill, and no offline snapshot are required.

### §6.3 Expected event-stream consequence (disclosed)

`media_role` / `media_status` are projections of `vendor_specific.media`, which
already participates in the stored message digest. Materializing them as explicit
keys changes the digest **only for messages that carry media**, so each
media-bearing message that the 5 s sync worker re-reads emits one additional
`message.updated`. Media-less messages keep their previous digest and are not
re-emitted (asserted by `test_f3_6_text_only_messages_are_not_perturbed`).

Bounded expectation, measured at the F1/F2 deployment of the same class of change:

```text
EXPECTED_EXTRA_MESSAGE_UPDATED   = order 10-30 events, media-bearing messages only
EXPECTED_ACCOUNT_STATUS_TRAFFIC  = unchanged (heartbeat ~5 s)
CONSUMER_CHECKPOINT_IMPACT       = NONE
```

This re-emission lands **after** the current EFB checkpoint `273844`, so the next
EFB Functional Live round would replay it. The next round's taskbook must therefore
fix its entry checkpoint at the post-deployment stream head (or otherwise account
for stale media re-emissions) — this is a **round-design obligation recorded here**,
not a defect of the F3 change.

---

## §7 Protected service baseline (captured 2026-09-17T01:28:02Z, host UTC)

| Service | Container ID | Image | State | StartedAt | RestartCount |
| --- | --- | --- | --- | --- | --- |
| core | `b93fa6a8bd6b1ed72323d249d2914cc4d5a054c0c29e1dd2ec0babf19a2663eb` | `sha256:8add2212d7e203bf22bc7d235da9220546969a10d69a981f3cc5ceca9a657715` | running / healthy | 2026-09-17T00:08:53.357960218Z | 0 |
| console | `cce13a59dad25fb8c10e741b6978b8c7b7e228ccc4259734a289cc439f22666a` | `sha256:fcd9749d4944e5d9f8b99730f3b5e55b12359566a5c41b691d35fe43774fd282` | running | 2026-09-13T12:05:02.973659468Z | 0 |
| runtime | `d21960eef445e709a9e3fd06f30327682f3493cb7adc113bf99b5c67ec2eb852` | `sha256:1c43c1e314dce64d1cac9e8eab802811b926f5e8ae0ed830653fa8519b5a6e2b` | running | 2026-09-11T06:45:48.455808964Z | 0 |
| agent | `f4d2f2773e854f654c471200ed1530988c2655f62e8bd1b44796d90d3cddc096` | `sha256:ee986b4e45ccaa8f0d232e752aa1eb9724662839dc19b3ddfcfafff8c15eed58` | **exited (STOPPED)** | 2026-09-16T07:31:50.371571612Z | 0 |
| efb | `6023ad354c2616659e60e75ad95471718074584db3255f9c52d572546b8c8ea9` | `sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a` | **exited (STOPPED)** | 2026-09-16T16:49:38.345169161Z | 0 |
| agentwechat-a | `44559e58c4fefad872d07e353bbb6cfb340bff7bcfcd7ae9423aa2f4a155565d` | — | running | 2026-09-11T05:12:55.911370452Z | 0 |
| agentwechat-b | `a6c2e3ee61e1521828cd2e352e00847b16ff2e8841a3364b21147abd1a25ca51` | — | running | 2026-09-11T05:12:57.593190942Z | 0 |

Only the **core** row may change. Every other row must have `RestartCount` delta 0
and an unchanged `StartedAt` after the deployment.

Concurrent-workstream check before the window: 0 matrix/benchmark processes, 0
`v5-*` containers.

---

## §8 Deployment procedure (the single permitted mutation)

Preconditions, all re-verified immediately before execution:

```text
1. Core RUNNING and HEALTHY, RestartCount 0, image = sha256:8add2212d7e2...
2. Agent STOPPED, EFB STOPPED (exited, RestartCount 0)
3. AGENT_CHECKPOINT >= 195927 ; EFB_CHECKPOINT >= 273844
4. No concurrent benchmark workstream
5. CORE_F3_IMAGE_DIGEST present on the host and digest-pull proof still valid
6. OVERLAY_SHA256 == 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d
7. THIS_TASKBOOK_SHA256 verified against its .sha256 seal
8. Core DB guard clean for the whole round (findings: [])
```

Execution — exactly one command, `core` only:

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose \
  -f docker-compose.yml \
  -f docker-compose.rc14-core-media-contract-f3-candidate.yml \
  up -d --no-deps core
```

Mandatory constraints on that command:

```text
--no-deps            REQUIRED
--remove-orphans     FORBIDDEN   (would touch the stopped EFB/Agent containers)
service list         core ONLY
```

**Core max one controlled recreate.** If the command must be re-run for any reason,
stop and escalate instead of re-running — a second recreate requires a new taskbook
and a new operator authorization.

No `docker compose down`, no `--force-recreate` on any other service, no image
pruning, no `docker system prune`.

---

## §9 Post-deployment qualification gate

All of the following must hold; any failure is a STOP, not a retry.

```text
CORE_HEALTH                    = PASS      (container healthy, /health ok:true, contract_version 1, accounts 2)
CORE_RESTART_COUNT             = 0
CORE_IMAGE_DIGEST_AFTER        = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
CORE_OCI_REVISION_AFTER        = 6538f79a664a325543c19391cc14601d282e07a4
AGENT_CHECKPOINT_POST          >= 195927
EFB_CHECKPOINT_POST            >= 273844
CHECKPOINT_REGRESSION          = ZERO
AGENT_STATE_POST               = STOPPED
EFB_STATE_POST                 = STOPPED
PROTECTED_SERVICE_DELTA        = ALL ZERO  (console, runtime, agent, efb, agentwechat-a, agentwechat-b)
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

Live Core media-contract probe (EFB and Agent STOPPED, no new WeChat/Telegram
messages generated by the operator):

```text
CORE_MEDIA_ROLE_HEADER_SUPPORTED        = (re-confirm PASS)
CORE_MEDIA_STATUS_HEADER_SUPPORTED      = (re-confirm PASS)
CORE_MEDIA_READY_EVENT_HAS_ROLE         = (re-confirm PASS)
CORE_NEVER_PUBLISHES_THUMBNAIL_AS_ORIGINAL = (re-confirm PASS)
MESSAGE_PAYLOAD_HAS_MEDIA_ROLE          = evidence from GET /v1/accounts/{id}/chats/{chat_id}/messages
MESSAGE_PAYLOAD_HAS_MEDIA_STATUS        = evidence from the same REST projection
MESSAGE_CREATED_MEDIA_ROLE_PRESENT      = live event stream, if a media-bearing message event occurs in the window
MESSAGE_CREATED_MEDIA_STATUS_PRESENT    = live event stream, same condition
THUMBNAIL_REPORTED_AS_ORIGINAL_READY    = NO
```

If no media-bearing message event occurs naturally in the observation window, the
event-payload leg is recorded as `HISTORICAL_MEDIA_RUNTIME_PROBE = NOT_AVAILABLE`
with the deterministic REST projection as the compensating evidence. The production
DB must never be modified to manufacture evidence.

---

## §10 Rollback criteria and procedure

Rollback is **not** the default. It requires an explicit operator authorization and
a new taskbook, because §8 caps Core at one controlled recreate.

### §10.1 Rollback trigger conditions (any one)

```text
T1  Core fails to become healthy within 120 s of the recreate
T2  Core crash-loops (RestartCount > 0 or repeated non-zero exit)
T3  /health returns ok:false, or contract_version != 1, or accounts != 2
T4  AGENT_CHECKPOINT_POST < 195927  OR  EFB_CHECKPOINT_POST < 273844
T5  CHECKPOINT_REGRESSION != ZERO
T6  Any protected service shows a non-zero RestartCount delta or a changed StartedAt
T7  A forbidden DB-access finding appears in the round's host command log
T8  Event stream head moves backwards, or retention floor regresses
```

None of these fired during the predecessor deployment; if none fires here either,
rollback is **not** indicated and the current Core stays.

### §10.2 Rollback procedure (only if §10.1 fires)

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose \
  -f docker-compose.yml \
  -f docker-compose.rc14-core-media-role-candidate.yml \
  up -d --no-deps core
```

This restores Core to `sha256:c42822f4…5819f` / OCI revision `1e5eddd`. The overlay
file is preserved byte-identical for exactly this purpose. A rollback is itself a
Core recreate and therefore also consumes the one-recreate budget: escalate before
executing it.

---

## §11 Evidence artifacts to be produced

```text
docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_RESULT.md   (+ .sha256)
docs/RC14_CORE_MEDIA_CONTRACT_F3_COMPLETION_RESULT.md              (+ .sha256)  # engineering phase
tmp/rc14-coremedia-f3/core_db_access_command_log.txt               # whole-round host command log
tmp/rc14-coremedia/ci_test_log_f3.txt                              # CI job 105039644228
tmp/rc14-coremedia/f3-pull.sh                                      # host pull script (md5 87acad9f7e7d6584f69a377a4f6a3f0e)
```

---

## §12 Sealing

```text
TASKBOOK_PATH   = docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md
TASKBOOK_SHA256 = recorded in docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md.sha256
SEAL_AT         = 2026-09-17
```

Once sealed, this document is immutable. Any deviation discovered during execution
is recorded in a separate erratum; it must never be edited in place.

---

## §13 Requested operator authorization

```text
F3_ENGINEERING_COMPLETE              = YES
F3_REGRESSION                        = PASS
F3_IMMUTABLE_IMAGE_READY             = YES
F3_DEPLOYMENT_TASKBOOK_SEALED        = YES
REQUESTED_ACTION                     = AUTHORIZE ONE CONTROLLED CORE RECREATE (taskbook §8)
CURRENTLY_BLOCKED_UNTIL_APPROVAL     = the §8 deployment command
EFB                                  = STOPPED
AGENT                                = STOPPED
```

Nothing in §8 will be executed before the operator grants that authorization.
