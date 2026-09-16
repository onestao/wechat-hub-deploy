# RC.14 EFB Functional Correctness — Production Live Qualification Result

> **STATUS: FAIL — STOP**
>
> **AUTHORIZATION:** `RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION`
>
> **RUN WINDOW (host UTC):** `2026-09-16T16:49:38Z` → `2026-09-16T17:21:18Z` (31 min 40 s)
> (host local `2026-09-17 00:49:38` → `01:21:18` +0800)
>
> **VERDICT:** the frozen candidate behaved **correctly** (it failed closed). The **system** fails
> the requirement, because the running production Core does not implement the media role/status
> contract that the frozen candidate consumes. Filed as
> `docs/API_ENHANCEMENT_REQUEST_CORE_MEDIA_ROLE_CONTRACT.md`.

```text
EFB_FUNCTIONAL_LIVE_QUALIFICATION = FAIL
EFB_PRODUCTION_PROMOTION_READY    = NO
CORE_API_GAP                      = media_role, media_status, X-Media-Role, X-Media-Status
ACTION                            = STOP
```

---

## 1. Executive verdict

The RC.14 EFB Functional Correctness candidate was started against live production infrastructure
under the frozen overlay, caught up the production backlog with zero duplicates, and was stopped
cleanly. It was **not** promoted, and no Agent was started.

The round **stopped on a Core API gap**, exactly as the sealed taskbook §0 directs:

> "If the Core API lacks a field this taskbook needs, **STOP**. Emit `CORE_API_GAP = <field>` +
> `ACTION = STOP` … Never bypass with the raw database."

What happened, in one paragraph: the frozen candidate requires every media artefact to declare
`media_role == "original"` and `media_status == "ready"` before it will send it to Telegram. The
deployed Core (`08a4e746…`) never declares either — not in `message.created` payloads, not in
`media.ready` events, and not as `X-Media-Role` / `X-Media-Status` response headers on
`GET /v1/media/{id}`. The candidate therefore rejected **every** resolvable media item as a
non-original artefact and recorded `MEDIA_FAILED`.

The important consequence — and the reason this is a *correct* failure rather than a *bad* one:

```text
THUMBNAIL_DELIVERED_AS_FINAL = NO      (proven live)
PLACEHOLDER_FINAL_DELIVERY   = 0       (proven live)
DUPLICATE_MEDIA_DELIVERY     = 0       (proven live)
```

The pre-fix Core's `normalize.py` resolves a media path from `media_path or thumb_path` and
publishes it with `status='ready'`, i.e. it **can** publish thumbnail bytes as though they were the
original. The candidate's role check is the only thing preventing that from reaching Telegram, and
it held. No original was delivered either — that is the gap.

---

## 2. Frozen inputs (all SHA256 / digest verified exact)

```text
TASKBOOK        docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md
                SHA256 = 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511   PASS
                MODIFIED_BY_THIS_ROUND = NO

ERRATUM         docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_EXECUTION_ERRATUM.md
                SHA256 = d81f2d35ce70b0394625a30495a19b47ba8d57db87146a6adb7c9915c3859dab   PASS
                MODIFIED_BY_THIS_ROUND = NO

OVERLAY         release/docker-compose.rc14-efb-functional-live.yml
                SHA256 = 8479fcdecf900ba58dc2751b78b5ce900356edcbbbca50f49c3e4a56c4d968dd   PASS
                (2397 B; transferred to host byte-exact; host copy re-hashed after decode)

FUNCTIONAL_SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST  = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION  = 91a69cef323d120f0e32196917a630d2cf3baa88
OCI_REVISION_EQ_SOURCE_COMMIT = YES
LOCAL_IMAGE_ID           = sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a
```

Erratum E3 was honoured: its precedence was applied **only** to candidate identity and the
execution overlay. Every gate, abort criterion and rollback step in the sealed taskbook remained in
force verbatim. The taskbook's stale `af3707d` precondition (§5) was not retroactively rewritten;
it is resolved for execution by E1 only.

---

## 3. §0 — Final Entry Gate: PASS

```text
CORE_STATE                          = RUNNING / HEALTHY
AGENT_STATE (entry)                 = STOPPED   (exited 0, FinishedAt 2026-09-16T08:04:18Z)
EFB_STATE (entry)                   = STOPPED   (exited 137, historical Retry2 exit)
CONCURRENT_AGENT_BENCHMARK          = NO
CONCURRENT_LIVE_QUALIFICATION       = NO
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS        = 0
```

Concurrency exclusion was established the hard way — zero `matrix` processes in `ps`, zero `v5-*`
containers in `docker ps`, and no `matrix.done` sentinel under the prior sweep root `/root/rc14-v5`.
No other workstream was killed (the protocol forbids it).

Core checkpoint evidence was read through the **HTTP API only**:

```text
CORE_API_AGENT_CHECKPOINT = 195927    (required >= 195927)   PASS
ENTRY_EFB_CHECKPOINT      = 272548    (required >= 272548)   PASS
ENTRY_CORE_STREAM_HEAD    = 273841    (read at 2026-09-16T15:24:15Z)
```

`CORE_STREAM_HEAD` is a moving value (`account.status` heartbeats advance it roughly every 5 s).
The entry value is timestamped above and was re-read before the run; it is never reused.

---

## 4. §1 — Protected-service baseline (entry)

| Service | Container | State | RestartCount | StartedAt |
| --- | --- | --- | --- | --- |
| Core | `wechat-hub-f-live-core` | running / healthy | 0 | `2026-09-15T14:58:48Z` |
| Console | `wechat-hub-f-live-console` | running / healthy | 0 | `2026-09-13T12:05:02Z` |
| Runtime | `wechat-hub-f-live-runtime` | running / healthy | 0 | `2026-09-11T06:45:48Z` |
| AgentWechat A | `wechat-agent-f-live-a-faf35abb` | running | 0 | `2026-09-11T05:12:55Z` |
| AgentWechat B | `wechat-agent-testb-a7c4f6c8` | running | 0 | `2026-09-11T05:12:57Z` |
| Agent | `wechat-hub-f-live-agent` | exited (0) → **STOPPED** | 0 | `2026-09-16T07:31:50Z` |
| EFB | `wechat-hub-f-live-efb` | exited (137) historical → **STOPPED** | 0 | created `2026-09-15T11:19:06Z` |

The Agent remained STOPPED for the entire window. Core, Console, Runtime and both AgentWechat
bridges were never restarted, recreated, or otherwise disturbed.

---

## 5. §2 — Telegram Master Activation: PASS

```text
MASTER_BEFORE  = efb_qual_master.QualMasterChannel   sha256 bce4475813602739583248f5c2a815c62a467b9c911943d085ead6aa1f747d75
SNAPSHOT       = config.yaml.pre_live_snap           sha256 bce4475813602739583248f5c2a815c62a467b9c911943d085ead6aa1f747d75
MASTER_AFTER   = blueset.telegram                    sha256 4eb096aac775bcf35a157acda7f25dc558414d782087ff93cc727002b0f520d7
TELEGRAM_CREDENTIAL_PRINTED = NO
CONSUMER_ID_CHANGED = NO   (efb-linux-wechat:wechat.linux, unchanged throughout)
ACCOUNT_SCOPE_CHANGED = NO (f-live-a, unchanged throughout)
```

The snapshot was taken with `cp -p` **before** the mutation, so the restore path is byte-exact
rather than reconstructed.

---

## 6. §3 — Candidate startup: PASS

```text
EFB_CONTAINER            = wechat-hub-f-live-efb  (id 6023ad354c26)
EFB_INSTANCE_COUNT       = 1                       (no second instance anywhere)
EFB_CREATED              = 2026-09-16T16:49:34Z
EFB_STARTED              = 2026-09-16T16:49:38.345169161Z
RESTART_POLICY           = no
PIDS_LIMIT               = 100
PUBLISHED_PORTS          = none
PROFILE_MOUNT            = /mnt/user/appdata/wechat-hub-f-live/efb-profile -> /root/.ehforwarderbot (rw)
NETWORK                  = internal
IMAGE_DIGEST_AT_RUNTIME  = matches frozen digest exactly
OCI_REVISION_AT_RUNTIME  = 91a69cef323d120f0e32196917a630d2cf3baa88
```

`docker compose config` was used to qualify the overlay statically **before** any container was
started: the merged render produced services `runtime, core, console, efb-multi`; a `diff` against
the base render showed **only** the `efb-multi` block added; published ports were identical (3/3);
the base compose contains zero `efb-multi` definitions; `efb-multi` itself publishes nothing.

No rebootstrap, no new consumer, no checkpoint reset, no ledger/mapping/pending deletion, no
mutable tag, no build.

---

## 7. §4 — Startup / Replay Safety Gate: PASS

The candidate resumed the **existing** consumer state and caught up the backlog monotonically:

```text
ENTRY_EFB_CHECKPOINT = 272548
FINAL_EFB_CHECKPOINT = 273844        (== stream head at the time of catch-up)
CHECKPOINT_REGRESSION = 0
MONOTONIC             = YES
CATCH_UP_ADVANCE      = +1296 events
CONVERGED_AT          = 2026-09-16T17:18:24Z (watcher: cursor == head, unresolved == 0)
```

Replay safety, all verified against the live ledger:

```text
HISTORICAL_DELIVERED_PRESERVED = 274   (rows with created_at < 2026-09-16: exactly 274, untouched)
HISTORICAL_DELIVERED_REPLAYED  = 0     (no historical effect re-sent to Telegram)
DUPLICATE_TELEGRAM_DELIVERY    = 0
RESERVED_UNRESOLVED            = 0
UNCERTAIN_UNRESOLVED           = 0
```

`DELIVERED = 274` from the Retry2 round was **not** re-delivered. The 274 historical rows retain
their original `created_at` values and were never mutated.

---

## 8. §5–§8 — Functional gates

### 8.1 F1 / LQ-01 — Original image: **FAIL**

The candidate resolved real image messages from the live stream and rejected every one of them:

```text
MEDIA_FAILED  f-live-a:be065d8c…  "image media be065d8c… has role ''; thumbnail cannot be final"   permanent=true
MEDIA_FAILED  f-live-a:8015346c…  "image media 8015346c… has role ''; thumbnail cannot be final"   permanent=true
```

Root cause, re-confirmed live at `2026-09-16T17:25:59Z` against a different media id:

```text
GET /v1/media/bfec71c0c0753a84b18f11c9ca65f327d98f265198f4624a033a12af513dec2e?account_id=f-live-a
HTTP/1.0 200 OK
Content-Type: image/jpeg
Content-Length: 5701
Content-Disposition: inline; filename="e505d4e740ff62450cf797f04df67567.jpg"
X-Media-Id: bfec71c0…
                                  <-- no X-Media-Role, no X-Media-Status
```

and `GET /v1/accounts/f-live-a/chats/38808757431@chatroom/messages?limit=5` returns
`media_role = NULL`, `media_status = NULL` on every message. `media.ready` events carry no `role`.

```text
MEDIA_ROLE_OBSERVED        = ''   (empty / absent)
MEDIA_STATUS_OBSERVED      = (absent)
TELEGRAM_MEDIA_IS_ORIGINAL = N/A  (nothing was sent)
THUMBNAIL_DELIVERED_AS_FINAL = NO
F1_VERDICT                 = FAIL
```

The failure is **not** attributable to the candidate. The candidate did the right thing.

### 8.2 F2 / LQ-02 — Delayed media / sticker: **FAIL**

Pending media never becomes ready, because readiness can never be established without
`media_status`:

```text
PENDING_MEDIA -> RESERVED -> DELIVERED   = never reached
media retry deadline exceeded            = 34 occurrences
PLACEHOLDER_FINAL_DELIVERY               = 0   (correct: nothing was sent as a placeholder)
DUPLICATE_MEDIA_DELIVERY                 = 0
F2_VERDICT                               = FAIL
```

`MEDIA_FAILED` breakdown by event type: `message.created` 8, `message.updated` 34. By reason:
34 × *media retry deadline exceeded*, 8 × *role `''`; thumbnail cannot be final*. By artefact type:
image 18, file 14, sticker 9, voice 1. By chat: `38808757431@chatroom` 38, `50421966048@chatroom` 4.

### 8.3 F3 / LQ-03 — Telegram reply visible fallback: **NOT EXECUTED**

Requires an operator-driven Telegram Reply action against a message synced in this window. The
round had already reached its STOP condition (F1/F2), and the taskbook §9 directs that the
candidate be stopped immediately on abort criteria. No human action node was reached, so no Reply
was attempted. `WECHAT_NATIVE_REPLY_SUPPORTED = NO` is carried from the frozen capability
contract, not re-measured here.

### 8.4 F4 / LQ-04 — Sender / self identity: **NOT EXECUTED**

Same reason. Observation only (from the event payloads consumed during catch-up, no Telegram-side
rendering was validated): group authors were observed as `self` (`is_self: true`), the chatroom id
itself (`is_self: false`, e.g. display `自己的小队-RB003-2205`), and real member ids such as
`wxid_yx40oh06ya1322` (display `茄子QieZhi`), `wxid_z44j7f8lrchv21` (display `劼`),
`wxid_rpfflqtdz4a22` (display `糯米鸡冻奶`). Payloads carry a top-level `author` block with
`display_name` / `is_self` / `member_id` plus `vendor_specific.direction_inferred_from`. **No
identity verdict is claimed** — that requires the Telegram-side rendering check.

### 8.5 §9 Mapping Restart Gate: **NOT EXECUTED**

No reply mapping was established (F3 not executed), so the controlled-restart mapping gate could
not be exercised. The candidate was restarted zero times during the window. The mapping database
was observed intact and correctly scoped at the end of the round:

```text
core-message-mapping.sqlite3 rows   = 101
distinct consumer_id                = efb-linux-wechat:wechat.linux   (exactly 1)
distinct account_id                 = f-live-a                       (exactly 1)
distinct chat_id                    = 2
MAPPING_RESTART_SAFE                = NOT_EXECUTED
```

### 8.6 §10 — EffectLedger final safety: **PASS**

```text
DELIVERED       = 375      (274 historical + 101 new; all 101 new are MsgType.Text)
MEDIA_FAILED    = 42       (each with a recorded media_failure_reason; see 8.2)
RESERVED        = 0
UNCERTAIN       = 0
PENDING_MEDIA   = 0
LEDGER_ROWS     = 417
LEDGER_CONSUMERS= 1
LEDGER_DELETED  = NO  (no row was deleted, truncated or rewritten by this round)
```

All 42 `MEDIA_FAILED` rows are explained above; none is an unexplained or spurious failure. Every
`DELIVERED` row corresponds to exactly one committed external effect. Because
`(consumer_id, effect_id)` is the primary key and there is a single consumer, no source event can
hold two committed effects.

The decisive shape of this round's traffic:

```text
NEW_DELIVERED_THIS_ROUND = 101   → 100% MsgType.Text, 0% media
```

Zero media reached Telegram. That is simultaneously the proof that fail-closed works and the proof
that F1/F2 cannot pass.

---

## 9. §11 — Core / Agent governance: PASS

- The Agent stayed STOPPED from entry to exit. It was never started.
- No host-side raw access to the protected production Core SQLite was performed at any point
  (no `sqlite3 -readonly`, `cat`, `cp`, `dd`, `sha256sum` against
  `…/core-data/core/wechat_core.sqlite` or its `-wal`/`-shm`).
- All Core state was read through the HTTP API: `/health`, `/v1/events/checkpoint`,
  `/v1/events/poll`, `/v1/accounts/{id}/chats/{chat}/messages`, `/v1/media/{id}`.
- The guard was re-run over the **complete** host-command log for the round:

```text
scripts/forensics/check_forbidden_live_core_db_access.py --json tmp/rc14-efb-live/live_round_core_db_access_command_log.txt

guard_version 1.1.0   rule ACTIVE_CORE_HOST_PRODUCTION_DB_FILE_OPENS
files_scanned 1  findings []  scratch_findings []
RAW_SQLITE_GUARD        = PASS
GENERIC_FILE_OPEN_GUARD = PASS
SCRATCH_GUARD           = PASS
```

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

The SQLite reads performed in this round were all against **EFB-owned** stores
(`core-effect-ledger.sqlite3`, `core-message-mapping.sqlite3`, `tgdata.db`) inside the EFB profile
directory. Those are not in the protected set. No `/dev/shm` snapshot was created, so the
disposable-snapshot lifecycle policy had nothing to clean up.

---

## 10. §12 — Graceful Shutdown Gate: PASS (with one instrumentation disclosure)

```text
COMMAND                     = docker stop -t 2 wechat-hub-f-live-efb
STOP_ISSUED_AT              = 2026-09-16T17:21:15Z
CONTAINER_FINISHED_AT       = 2026-09-16T17:21:18.798200824Z
DOCKER_STOP_CLI_WALL_SEC    = 6.007   (host CLI overhead; see disclosure D3)
GRACEFUL_STOP_EXIT_CODE     = 0       PASS
SIGKILL                     = 0       PASS   (OOMKilled=false; a SIGKILL would report 137)
CHECKPOINT_FLUSH            = PASS
LEDGER_FLUSH                = PASS
DELIVERY_SUPPRESSED         = PASS
```

Evidence for each sub-gate, since the in-process evidence line was not capturable (D2 below):

**`SIGKILL = 0`** — `State.ExitCode = 0`. A container killed by `docker stop`'s SIGKILL reports
`137` (128+9). This is the exact failure mode the historical Retry2 round hit (5.732 s, exit 137),
caused by `blueset.telegram`'s `stop_polling()` blocking ~5.5 s. Under the frozen candidate the
bounded master stop is capped at 1.0 s and the process exits with `0` — which is the only way to
reach exit code `0` inside a 2 s grace window. The candidate's coordinated shutdown therefore
**ran**; the historical defect is closed for this run.

**`CHECKPOINT_FLUSH = PASS`** — the durable checkpoint equals both the final local cursor and the
stream head at the moment catch-up completed; there is no gap to lose:

```text
CORE_API processed_through_cursor = 273844
local core-event-cursor.json      = {"cursor":"273844"}
stream head at convergence        = 273844
```

**`LEDGER_FLUSH = PASS`** — the ledger is fully checkpointed and row-identical across the stop:

```text
core-effect-ledger.sqlite3 mtime        = 2026-09-17 01:18:21 +0800 (unchanged by shutdown)
ledger -wal                             = absent   (no unflushed frames)
ledger directory mtime                  = 2026-09-17 01:21:17 +0800
                                          (inside the shutdown window: 01:21:18.798 finished)
ledger counts pre-stop == post-stop     = DELIVERED 375 / MEDIA_FAILED 42 / 417 rows
```

The ledger directory was touched during the shutdown window while the ledger main file was not —
the signature of a `checkpoint_wal()` open→checkpoint→close cycle with zero new frames. No row was
added, changed or deleted by the shutdown.

**`DELIVERY_SUPPRESSED = PASS`** — the last outbound Telegram row predates the stop by ~7 minutes,
and nothing was emitted during or after shutdown:

```text
tgdata.db msglog rows     = 377
msglog max(time)          = 2026-09-16 17:14:09   (stop at 17:21:18)
post-stop deliveries      = 0
```

### Disclosures

**D1 — `docker stop -t 2` is a thin margin on this host.** The frozen shutdown gate measures
*product-internal* elapsed time (min 1.002388 / p50 1.002584 / max 1.002895 s across 5 runs) and
proves exit-inside-grace by exit code `0` under `-t 2`. On this degraded-array host the CLI-inclusive
wall time carries a documented 2.7–5.2 s baseline (taskbook §2.1 Deviation D2); this run measured
6.007 s. The product-side result is correct (`exit 0`, no SIGKILL), but the *wall-clock* margin is
thin and should not be read as a performance measurement.

**D2 — Instrumentation gap: `EFB_SHUTDOWN_EVIDENCE` was not emitted to the container log.** The
frozen image's console log handler emitted **only** ERROR-level records for the entire window
(42 of 42 records are `[ERROR]`; the container log is 98 lines total and ends at `17:18:21`). The
coordinator's evidence line is logged at INFO (`ComWechat.drain_for_shutdown`, `ComWechat.py:293`)
and is therefore dropped by the live entrypoint. The `--shutdown-evidence <path>` file sink exists
in `ShutdownCoordinator` but is wired by the requalification harness, not by the production
entrypoint (`ENTRYPOINT ["ehforwarderbot"]`). Consequently
`SHUTDOWN_INTERNAL_ELAPSED_SEC = UNMEASURED` for this run and the three flush sub-gates were
verified from independent host-side artefacts instead. **Recommended for the next candidate:** have
the production entrypoint always write the evidence JSON to a path inside the profile volume, so a
live window is self-attesting.

**D3 — The candidate overlay was left in place.** `/root/rc14-efb-live/docker-compose.rc14-efb-functional-live.yml`
is retained so the stopped container's compose provenance stays resolvable. Retry2's withdrawal of
its own overlay is what produced the missing-compose-file gap recorded as preflight D4; leaving it
avoids repeating that. It is inert while the container is stopped.

**D4 — Historical Retry2 deliveries included media.** The 274 preserved historical `DELIVERED` rows
include 28 `MsgType.Image`. They were produced by the *previous* candidate (`17641908…`), which had
no media-role check, against the same pre-fix Core that can publish thumbnail bytes as the
original. Whether any of those 28 reached Telegram as a thumbnail is **not** re-litigated here and
is **not** claimed either way — it is recorded because it is the live counterpart of the F1 defect.

---

## 11. §13 — Restore Pre-Live Master: PASS

```text
RESTORE_COMMAND  = cp -p <profile>/config.yaml.pre_live_snap <profile>/config.yaml
MASTER_RESTORED  = efb_qual_master.QualMasterChannel
POST_RESTORE_SHA256 = bce4475813602739583248f5c2a815c62a467b9c911943d085ead6aa1f747d75
SNAPSHOT_SHA256     = bce4475813602739583248f5c2a815c62a467b9c911943d085ead6aa1f747d75
BYTE_FOR_BYTE_EQUAL = YES
FINAL_EFB_STATE     = STOPPED
```

Restore is byte-for-byte identical to the pre-live snapshot, not merely semantically equivalent.

---

## 12. §14 — Protected-Service Reconciliation: PASS

| Service | Container | RestartCount (entry → final) | StartedAt (entry → final) | Restart delta |
| --- | --- | --- | --- | --- |
| Core | `wechat-hub-f-live-core` | 0 → 0 | `2026-09-15T14:58:48Z` → unchanged | **0** |
| Console | `wechat-hub-f-live-console` | 0 → 0 | `2026-09-13T12:05:02Z` → unchanged | **0** |
| Runtime | `wechat-hub-f-live-runtime` | 0 → 0 | `2026-09-11T06:45:48Z` → unchanged | **0** |
| AgentWechat A | `wechat-agent-f-live-a-faf35abb` | 0 → 0 | `2026-09-11T05:12:55Z` → unchanged | **0** |
| AgentWechat B | `wechat-agent-testb-a7c4f6c8` | 0 → 0 | `2026-09-11T05:12:57Z` → unchanged | **0** |
| Agent | `wechat-hub-f-live-agent` | 0 → 0 | `2026-09-16T07:31:50Z` → unchanged | **0** |
| EFB | `wechat-hub-f-live-efb` | 0 → 0 | `2026-09-16T16:49:38Z` → `FinishedAt 17:21:18Z` | **0** |

```text
CORE_RESTART_DELTA       = 0
CONSOLE_RESTART_DELTA    = 0
RUNTIME_RESTART_DELTA    = 0
AGENTWECHAT_RESTART_DELTA = 0
AGENT_RESTART_DELTA      = 0
CORE_HEALTH              = PASS
FINAL_AGENT_STATE        = STOPPED
FINAL_EFB_STATE          = STOPPED
```

Every protected service's `StartedAt` is unchanged from the entry baseline, so nothing was
recreated or restarted. The only container that changed state is the EFB candidate itself.

---

## 13. §15 — Stop-on-Failure assessment

The round reached its STOP condition at F1/F2. It did **not** trigger any of the *other* §15
stop conditions:

| Stop condition | Observed |
| --- | --- |
| Checkpoint regression | `0` — monotonic `272548 → 273844` |
| Historical duplicate delivery | `0` — 274 historical rows preserved and not re-sent |
| Wrong / cross-scope reply mapping | not reachable (F3 not executed) |
| Thumbnail as final | `NO` — proven live |
| Placeholder sticker as final | `0` |
| Duplicate delayed media | `0` |
| Wrong self attribution | not reachable (F4 not executed) |
| SIGKILL | `0` — exit code `0` |
| Unresolved `UNCERTAIN` | `0` |
| Core unhealthy | Core healthy throughout |
| Agent unexpectedly started | never started |
| Protected-service restart | all deltas `0` |
| Active Core DB file-open violation | `0` (guard PASS) |

Already-passing sub-gates are preserved as measured; nothing was re-run, and the production
checkpoint was **not** reset to reproduce any failure.

---

## 14. §16 — Return block

```text
FUNCTIONAL_SOURCE_COMMIT   = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST    = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION    = 91a69cef323d120f0e32196917a630d2cf3baa88
OCI_REVISION_EQ_SOURCE_COMMIT = YES
EFB_IMAGE_EXACT_DIGEST     = PASS
EFB_INSTANCE_COUNT         = 1

TASKBOOK_SHA256            = 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511
LIVE_EXECUTION_ERRATUM_SHA256 = d81f2d35ce70b0394625a30495a19b47ba8d57db87146a6adb7c9915c3859dab
FUNCTIONAL_LIVE_OVERLAY_SHA256 = 8479fcdecf900ba58dc2751b78b5ce900356edcbbbca50f49c3e4a56c4d968dd
ORIGINAL_TASKBOOK_MODIFIED = NO

ENTRY_EFB_CHECKPOINT       = 272548
FINAL_EFB_CHECKPOINT       = 273844
CHECKPOINT_REGRESSION      = 0
CORE_API_AGENT_CHECKPOINT  = 195927
FINAL_CORE_STREAM_HEAD     = 273854      (read at 2026-09-16T17:25:49Z; moving value)
RETENTION_FLOOR_CURSOR     = 1

F1_ORIGINAL_IMAGE          = FAIL
F2_DELAYED_MEDIA_STICKER   = FAIL
F3_TELEGRAM_REPLY_MAPPING  = NOT_EXECUTED
F4_SENDER_SELF_IDENTITY    = NOT_EXECUTED
THUMBNAIL_DELIVERED_AS_FINAL = NO
PLACEHOLDER_FINAL_DELIVERY = 0
DUPLICATE_MEDIA_DELIVERY   = 0

MAPPING_RESTART_SAFE       = NOT_EXECUTED
MAPPING_DB_ROWS            = 101
MAPPING_DB_SCOPE           = 1 consumer / 1 account / 2 chats

DUPLICATE_TELEGRAM_DELIVERY = 0
CROSS_RUN_REPLAY_DUPLICATE  = 0
HISTORICAL_DELIVERED_PRESERVED = 274
HISTORICAL_DELIVERED_REPLAYED  = 0

LEDGER_DELIVERED           = 375
LEDGER_MEDIA_FAILED        = 42
LEDGER_RESERVED            = 0
LEDGER_UNCERTAIN           = 0
LEDGER_PENDING_MEDIA       = 0
LEDGER_ROWS                = 417
LEDGER_MUTATION_THIS_ROUND = NO

GRACEFUL_STOP              = PASS
GRACEFUL_STOP_EXIT_CODE    = 0
SIGKILL                    = 0
FINAL_FLUSH_CHECKPOINT     = PASS
FINAL_FLUSH_LEDGER         = PASS
FINAL_FLUSH_DELIVERY_SUPPRESSED = PASS

MASTER_RESTORE             = PASS
MASTER_RESTORED_TO         = efb_qual_master.QualMasterChannel
MASTER_RESTORE_SHA256      = bce4475813602739583248f5c2a815c62a467b9c911943d085ead6aa1f747d75
MASTER_RESTORE_BYTE_EXACT  = YES
FINAL_EFB_STATE            = STOPPED
FINAL_AGENT_STATE          = STOPPED

CORE_RESTART_DELTA         = 0
CONSOLE_RESTART_DELTA      = 0
RUNTIME_RESTART_DELTA      = 0
AGENTWECHAT_RESTART_DELTA  = 0
AGENT_RESTART_DELTA        = 0
CORE_HEALTH                = PASS

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0

CORE_API_GAP               = media_role, media_status, X-Media-Role, X-Media-Status
CORE_RUNNING_REVISION      = 08a4e746e66fe94cbe73f99f7284ae7f01963447
CORE_REQUIRED_REVISION     = 1e5eddd4b5504bad44409ab610767688e32ddca2
CORE_API_GAP_FILED_AS      = docs/API_ENHANCEMENT_REQUEST_CORE_MEDIA_ROLE_CONTRACT.md

EFB_FUNCTIONAL_LIVE_QUALIFICATION = FAIL
EFB_PRODUCTION_PROMOTION_READY    = NO
ACTION                            = STOP
```

`EFB_FUNCTIONAL_LIVE_QUALIFICATION = FAIL` is the honest reading of the conjunction: the
qualification requires all six live tests to pass, and two of them (LQ-01, LQ-02) cannot pass while
the Core lacks the media role/status contract. `EFB_PRODUCTION_PROMOTION_READY = NO` follows
directly. The candidate itself is **not** the defect; the candidate is what makes the defect
survivable.

---

## 15. Post-condition

```text
ACTION = STOP
```

- Production EFB: **STOPPED**, configuration restored to `efb_qual_master.QualMasterChannel`
  byte-for-byte.
- Production Agent: **STOPPED**, untouched.
- Core, Console, Runtime, both AgentWechat bridges: untouched, healthy, `RestartCount` deltas all 0.
- Agent V5 Production Live: **not started**.
- No follow-on round was begun.

The next round must not start until a Core image built from `1e5eddd4b5504bad44409ab610767688e32ddca2`
(or a descendant) is deployed and this document's sibling enhancement request §6 acceptance
criteria are demonstrable through the Core HTTP API alone.

---

## 16. Related

- `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md` (sealed, unmodified)
- `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_EXECUTION_ERRATUM.md` (E1–E4)
- `docs/RC14_EFB_FUNCTIONAL_PRE_LIVE_CONTROL_PLANE_CLOSURE_RESULT.md` (predecessor, PASS)
- `docs/RC14_EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT_RESULT.md` (R1–R6, D3–D6)
- `docs/API_ENHANCEMENT_REQUEST_CORE_MEDIA_ROLE_CONTRACT.md` (the filed gap)
- `docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md`
- `docs/DEV_SHM_DISPOSABLE_SNAPSHOT_LIFECYCLE_POLICY.md`
