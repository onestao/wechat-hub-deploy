# RC.14 EFB Functional — Reprojection Idempotency: Unknown Identity Hardening — RESULT

```text
ROUND                             = RC.14 EFB Reprojection Idempotency — Unknown Identity Hardening
ROUND_TYPE                        = ENGINEERING + OFFLINE_VERIFICATION
OPERATOR_RULING                   = §2 STRICT INTERPRETATION
PRODUCTION_LIVE                   = NOT_ENTERED
EFB_STARTED_BY_THIS_ROUND         = NO
CHECKPOINT_ADVANCED_BY_THIS_ROUND = NO
ACTION                            = STOP
```

Authority carried in (unchanged, not re-derived by this round):

```text
EFB_CHECKPOINT                = 273844
AGENT_CHECKPOINT              >= 195927
EFB                           = STOPPED
AGENT                         = STOPPED
CORE                          = RUNNING / HEALTHY
POST_F3_CHECKPOINT_ADVANCE    = REJECTED
CHECKPOINT_ADVANCE_SAFE       = NO
DECISION_CASE                 = C
EFB_CODE_CHANGE_REQUIRED      = YES
CHECKPOINT_CHANGE_REQUIRED    = NO
SURGICAL_FENCE_CANDIDATE      = NONE
```

Frozen intermediate candidate preserved as the base (not modified, not re-tagged):

```text
BASE_SOURCE = aa9407833d4c6ae54e1da6d830980e178cebd693
BASE_IMAGE  = sha256:f73965dd175de4c27019cb38d04299427638df3d676f9a1f4cb10127840af758
```

Historical results preserved, not re-derived and not overwritten:

```text
R14-EFB-R1                        = PASS
KNOWN_TERMINAL_EFFECT_SUPPRESSION = PASS
W1_DUPLICATE_EXTERNAL_DELIVERY    = 0
W1_NEW_MEDIA_FAILED_FROM_REPROJECTION = 0
W1_UNWANTED_PENDING_MEDIA         = 0
W2_DUPLICATE_EXTERNAL_DELIVERY    = 0
W2_NEW_MEDIA_FAILED_FROM_REPROJECTION = 0
W2_UNWANTED_PENDING_MEDIA         = 0
```

---

## 0. What the operator ruling changed

The previous round decided "is this a re-projection?" with a projection-generation
test:

```python
if current_status is None and event_type != "message.created":
    return          # R14-EFB-R2 as originally fixed
```

Section 2 of this round's instruction forbids that: `event_type == message.updated`
must not, by itself, be the basis for `duplicate` / `reprojection` / `historical
object`. The reason is a real semantic gap, not a style preference — Core emits
`message.updated` for **any** row it already holds whose digest changed, and that
includes objects created *after* this consumer subscribed that the consumer has
never delivered. Under the old rule those were silently dropped as "replays".

The hardening therefore replaces the event-type test with a three-fact decision:

```text
1. stable effect identity      (consumer_id, account_id, message_id, effect_kind)
2. durable subscription floor  (Core initial_cursor + bootstrap_at), persisted
3. Core authoritative business provenance (message created_at, or an immutable
   origin cursor if Core ever exposes one)
```

and `event_type` keeps only its routing role (which handler runs), never the
identity role.

---

## 1. Durable subscription provenance

```text
SUBSCRIPTION_FLOOR_DURABLE = YES
SUBSCRIPTION_FLOOR_SCOPE   = consumer_id + account_id
```

- New module `efb_wechat_comwechat_slave/Provenance.py`
  (`sha256 deb4620942045eb47358eb2296ca17445216b415d7ae99935dc6d2283fa93b3f`),
  `PROVENANCE_SCHEMA_VERSION = 1`.
- `SubscriptionFloorStore` persists one record per `(consumer_id, account_id)` to
  `core-subscription-floor.json` in the channel data directory, written
  tempfile + `os.fsync` + `os.replace`. It is **not** memory-only: a restart reads
  it back before any event is classified.
- The floor is resolved from Core's governed bootstrap read
  (`GET /v1/consumers/{id}/bootstrap` → `initial_cursor`, `bootstrap_at`,
  `bootstrap_mode`, `bootstrap_source`). When `bootstrap_at` is absent the store
  derives it from a bounded events-poll read, marks `floor_at_is_derived`, and
  biases the derivation toward suppression.
- Restart idempotence: an unchanged anchor preserves its original `recorded_at`,
  so the file is **byte-stable** across restarts
  (`test_floor_is_byte_stable_across_restarts`).
- Re-anchoring supersedes exactly one record per scoped account and keeps the
  superseded anchor in `history` (`test_floor_reanchors_on_rebootstrap_and_keeps_history`).
- Core unreachable at startup is not fatal: the durable local record is kept
  (`test_floor_survives_core_being_unreachable`).
- The scope is `consumer_id` + `account_id`. The effective consumer id is the
  derived `f"{consumer_base}:{channel_id}"` (production:
  `efb-linux-wechat:wechat.linux`), which is exactly the id Core keys on — see §11.

**Production-consumer initialisation is non-destructive.** Establishing the floor
adds one new file and touches nothing else:

```text
EffectLedger rows        = unchanged
mapping DB               = unchanged
checkpoint               = unchanged
```

asserted directly by
`test_floor_initialisation_does_not_touch_ledger_mapping_or_checkpoint`.

---

## 2. Unknown identity classification

```text
UNKNOWN_UPDATED_PRE_FLOOR_SUPPRESSED      = YES
UNKNOWN_UPDATED_POST_FLOOR_TREATED_AS_NEW = YES
UNKNOWN_UPDATED_AMBIGUOUS_FAIL_CLOSED     = YES
```

For an event whose effect identity is **absent** from the ledger:

| classification | condition | behaviour |
|---|---|---|
| `KNOWN_EFFECT` | identity already in the ledger | existing `EffectLedger` state machine |
| `REPROJECTION_OF_PREEXISTING_OBJECT` | business origin **<** durable floor | suppress — no ledger write, no external effect |
| `FIRST_BUSINESS_EFFECT` | business origin **>=** durable floor | normal handling |
| `INDETERMINATE` | provenance unavailable / ambiguous | fail closed / retryable — no external effect, no terminal `MEDIA_FAILED` fabrication |

A cursor origin is compared against the cursor floor, a timestamp origin against
the timestamp floor. An origin that is present but unparsable **fails closed**
rather than falling through to the weaker clock signal. An origin exactly equal to
the floor counts as **new** (the floor is the last-not-delivered boundary):
`test_origin_exactly_at_the_floor_is_treated_as_new`.

The final duplicate / re-projection conclusion therefore comes from stable identity
+ durable subscription provenance + Core authoritative business provenance — never
from `event_type`.

---

## 3. Event type controls routing, not identity

```text
EVENT_TYPE_USED_FOR_ROUTING_ONLY        = YES
EVENT_TYPE_USED_FOR_DUPLICATE_DECISION  = NO
```

`_handle_event` still routes on `event_type` (`message.created` / `message.updated`
→ message handler; `message.removed`, `chat.updated`, `send.updated`, `media.ready`,
`account.status` → their own handlers, with unknown types tolerated). That is the
whole of its authority.

The proof is a **two-way relabel** that no event-type-based implementation can
survive:

```text
TestEventTypeIsRoutingOnly
  test_real_new_business_is_recognised_under_a_flipped_event_type
      the 3 real new objects (274305/274306/274307), relabelled message.updated
      -> FIRST_BUSINESS_EFFECT = 3, deliveries = 2, 274307 = PENDING_MEDIA
  test_real_reprojection_is_suppressed_under_a_flipped_event_type
      the 387 pre-floor re-projections, relabelled message.created (the strongest
      possible relabel)
      -> REPROJECTION_OF_PREEXISTING_OBJECT = 387, deliveries = 0, ledger rows = 0
  test_post_floor_object_is_delivered_under_both_event_types
  test_pre_floor_object_is_suppressed_under_both_event_types
```

---

## 4. The existing 417 ledger rows

```text
HISTORICAL_LEDGER_REWRITTEN = NO
LEDGER_RESET                = NO
REBOOTSTRAP                 = NO
CHECKPOINT_CHANGED          = NO
```

375 `DELIVERED` + 42 `MEDIA_FAILED` remain authoritative and are neither migrated
nor rewritten. The provenance feature is strictly **additive**: two new files
(`core-subscription-floor.json`, `core-provenance-deferrals.json`) plus the
already-sealed additive `effect_kind` column from the previous round. No effect
identity is rewritten.

```text
test_production_shaped_rows_survive_the_additive_migration
    rebuilds the pre-effect_kind table with raw sqlite3, runs the migration,
    asserts all 417 (account_id, message_id, status) triples and the historical
    effect_id encoding survive verbatim
test_hardened_code_keeps_the_production_row_count
    417 rows -> restart -> 417 rows, DELIVERED 375 / MEDIA_FAILED 42
```

---

## 5. Real fixture: W1 / NEW / W2 and the synthetic cases

Re-run over the real window with no checkpoint fence:

```text
W1  = 273845..274304   (460 events)
NEW = 274305..274307   (3 events)
W2  = 274308..274727   (420 events)
```

Six zero gates, measured as **phase deltas** so a pre-existing terminal or pending
row can never be mis-attributed to a re-projection:

```text
W1_DUPLICATE_EXTERNAL_DELIVERY        = 0
W1_NEW_MEDIA_FAILED_FROM_REPROJECTION = 0
W1_UNWANTED_PENDING_MEDIA             = 0
W2_DUPLICATE_EXTERNAL_DELIVERY        = 0
W2_NEW_MEDIA_FAILED_FROM_REPROJECTION = 0
W2_UNWANTED_PENDING_MEDIA             = 0
```

The three real new business objects are recognised from **business provenance**,
not because they happen to be `message.created`:

```text
274305_RECOGNIZED_AS_NEW = YES
274306_RECOGNIZED_AS_NEW = YES
274307_RECOGNIZED_AS_NEW = YES
```

`274305` (link) and `274306` (text) end `DELIVERED`; `274307` (file, `media_id`
empty) is **not** marked duplicate and is **not** swallowed — it is processed and
settles fail-safe at `PENDING_MEDIA` (see §8). No `media_id` was fabricated.

### 5.1 The declared most-important new regression

```text
FIRST_OBSERVED_EVENT = message.updated
business origin      AFTER subscription floor
effect identity      absent
-> RECOGNIZED_AS_NEW = YES          (test_unknown_update_after_floor_is_a_first_business_effect)
```

and its mirror:

```text
FIRST_OBSERVED_EVENT = message.updated
business origin      BEFORE subscription floor
-> RECOGNIZED_AS_REPROJECTION = YES
   EXTERNAL_EFFECT            = 0
   LEDGER_WRITE               = 0     (test_unknown_update_before_floor_is_a_reprojection)
```

These two are exactly the cases the previous event-type rule got wrong, and they
are the reason this round exists.

### 5.2 Ledger arithmetic

```text
417 seeded (375 DELIVERED + 42 MEDIA_FAILED)
+ 2 first deliveries (274305, 274306)
+ 1 fail-safe pending (274307, file / empty media_id)
= 420 rows  =  377 DELIVERED + 42 MEDIA_FAILED + 1 PENDING_MEDIA
```

---

## 6. Core lookup failure fails closed

```text
UNKNOWN_UPDATED_AMBIGUOUS_FAIL_CLOSED = YES
CLASSIFICATION                        = INDETERMINATE
EXTERNAL_EFFECT                       = 0
TERMINAL_LEDGER_WRITE                 = 0
RETRY_ALLOWED                         = YES
```

Named indeterminate reasons, each with a test:

```text
core_projection_absent
core_projection_has_no_created_at
core_projection_created_at_malformed
core_provenance_read_failed
core_provenance_read_returned_no_object
subscription_floor_unavailable
no_durable_effect_identity
```

A timeout, a 404, a malformed payload or a missing `created_at`/origin never
becomes a guess. The event is parked in a bounded deferral store
(`max_attempts = 5`, `max_entries = 512`), separate from `EffectLedger`, retried
each poll cycle and on `media.ready`. An indeterminate **media** event
specifically does **not** become `MEDIA_FAILED`
(`test_indeterminate_media_does_not_become_media_failed`). Observed log line:

```text
Indeterminate business provenance for f-live-a/indeterminate-media
(core_provenance_read_returned_no_object); failing closed
(attempt=1, no external effect, no terminal ledger write)
```

---

## 7. Restart regression

```text
RESTART_PROVENANCE_SAFE = YES
```

- The floor file is byte-stable across a restart (unchanged anchor ⇒ `recorded_at`
  preserved, file not rewritten).
- A post-restart replay of the same real fixture is still classified as a
  re-projection, and the ledger row count is unchanged at 420.
- Provenance counters are per-channel in-memory diagnostics and restart at zero by
  design; the guarantee asserted is the classification and the absence of
  duplicate external effects, not a counter value.
- `test_restart_preserves_floor_and_decision`,
  `test_restart_replays_the_real_fixture_without_duplicate_effects`.

---

## 8. Core `file` media reference gap stays separate

```text
FILE_MEDIA_REFERENCE_GAP_CONFIRMED = YES
CORE_FOLLOWUP_REQUIRED             = YES
```

`274307` (`type=file`, `media_id` empty) remains an independent Core follow-up.
No `media_id` was fabricated and no Core source, image or deployment was touched
this round. The consumer's fail-safe `PENDING_MEDIA` is the correct behaviour for
a capability gap.

---

## 9. Candidate publication

```text
NEW_SOURCE_COMMIT = 69a1f58e29177634b6790ed3b5ec688871ba590c
NEW_IMAGE_DIGEST  = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:6c8dc474298f42d7a3528902a0dd8398270f9b525f1d299e05d7f2e46bc16d00
NEW_OCI_REVISION  = 69a1f58e29177634b6790ed3b5ec688871ba590c
CI_RUN            = 35201298847   (success)
PUBLISH_RUN       = 35201725302   (failure — see 9.3)
```

Delta on top of the frozen base:

| commit | contents | size |
|---|---|---|
| `c650759` | the hardening (`ComWechat.py`, `Core.py`, new `Provenance.py`, 5 pre-existing test doubles + new hardening suite + provenance fixture) | 10 files, +2250 / −64 |
| `69a1f58` | Mock Core models the governed bootstrap read (`stack/mock-core/app.py`) | 1 file, +43 |

New fixture `tests/fixtures/rc14_unknown_identity_provenance.json`
(`sha256 89de9256bf983ce8385b2dfe8c384ec7e22bfccbded2f97f00a9dd797be9d047`)
carries the ledger census, the per-cursor business provenance and the production
floor; the sealed census, the ledger partition and the read-only Core capture are
all reproduced exactly (`test_fixture_matches_the_sealed_census`,
`test_provenance_census_matches_the_read_only_capture`).

### 9.1 CI

```text
CI_RUN 35201298847   head 69a1f58e29177634b6790ed3b5ec688871ba590c   conclusion success
  Ran 141 tests in 18.918s
  OK
```

`test_channel_mock_core` and `test_kettly_etm_compat` both green.

### 9.2 Host-side exact-digest pull (independent of CI)

```text
PULL_EXIT               = 0
config id               = sha256:93068fc0405c0b9233d796fed5ccfa083c4b48244124573500df398157494941
org.opencontainers.image.revision = 69a1f58e29177634b6790ed3b5ec688871ba590c
org.opencontainers.image.version  = 0.1.0-rc.14-efb-unknown-identity-hardening
Entrypoint              = ["ehforwarderbot"]
```

`OCI_REVISION == NEW_SOURCE_COMMIT`, enforced by the workflow **and** observed on
the host-pulled image.

### 9.3 Disclosed: `HARNESS_INFRA_DEVIATION` in the publish workflow

`PUBLISH_RUN = 35201725302` concluded `failure`, and the failure is **not** in the
product:

```text
Run final source regression                    = success   (Ran 141 tests in 14.117s -> OK)
Compile-check package and qualification harness = success
Build and push RC image                         = success
Pull immutable image and verify OCI revision    = success
Run exact-digest isolated shutdown gate         = FAILURE
```

```json
{"error": "[Errno 1] Operation not permitted: '/tmp/rc14-shutdown-1-jzdvdqt3/da
ta'", "gate": "FAIL",
 "image": "ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:6c8dc474298f42d7a3528902a0dd8398270f9b525f1d299e05d7f2e46bc16d00",
 "runs": []}
```

This is the **same** defect already recorded for the frozen candidate
(`PUBLISH_RUN = 35183987421`, `[Errno 1] Operation not permitted:
'/tmp/rc14-shutdown-1-oprxd48z/data'`): the embedded runner cannot clean up a
host temp directory that the root-running container created inside the bind mount,
and it aborts before executing a single run. It is classified
`HARNESS_INFRA_DEVIATION` — a runner-side filesystem defect, **not** a product
shutdown failure, and it is **not** reported as one. The product shutdown verdict
is taken from the independent gate in §10.2.

### 9.4 Disclosed: Mock Core test-double gap fixed (not a product defect)

CI run `35199306935` on the first hardening commit failed with:

```text
test_poll_once_converts_text_and_image_and_persists_cursor
    [Text, Image] != []
test_send_updated_reconciles_echo_reply_recall_and_restart
    IndexError: list index out of range
```

Cause: `stack/mock-core/app.py` never modelled
`GET /v1/consumers/{id}/bootstrap`, so the floor was unavailable and every unknown
identity correctly failed closed — i.e. nothing was delivered. Real Core always
answers that read, and the in-suite Core doubles already answered it. The shared
HTTP double now answers it too (`initial_cursor = 0`, `bootstrap_mode = at_head`,
`bootstrap_at = 2026-01-01T00:00:00Z`), modelling a fresh consumer whose whole
retained stream is new business. Additive only: no product code, no assertion and
no existing route was changed. This was a test-double deficiency that CI correctly
exposed, and fixing it is the reason `NEW_SOURCE_COMMIT != c650759`.

---

## 10. Exact-image isolated qualification

All in containers created with `--network none` and no production volume, against
the published digest. `PRODUCTION_EFB_TOUCHED = NO`.

```text
EXACT_IMAGE_SMOKE      = PASS
EXACT_IMAGE_REGRESSION = 140/141 PASS   (1 pre-existing, disclosed in 10.1)
SHUTDOWN_PRODUCT_GATE  = PASS
```

### 10.1 Smoke and in-image regression

Smoke, inside the exact image:

```json
{"channel": "LinuxWeChatChannel", "efb_version": "2.1.1", "etm_loaded": true,
 "product_package": "/opt/efb-linux-wechat-slave/efb_wechat_comwechat_slave/__init__.py",
 "provenance_schema_version": 1, "slave_version": "2.0.0a1"}
```

`provenance_schema_version = 1` proves the hardening module is the one shipped in
the image, loaded from the image's own copy of the repository.

The full suite was executed **inside the exact image** in seven chunks (the whole
discovery in one container was abandoned after it was killed mid-run; see 10.3).
Chunk totals sum to the CI total exactly:

| chunk | scope | result |
|---|---|---|
| c1 | mock-core integration, cross-run replay sentinel, UID | 23 tests, **OK** |
| c2 | EffectLedger replay safety, Kettly ETM compat | 21 tests, 1 failure (10.1.1) |
| c3 | F1 media selection, F2 pending media, F3 reply mapping, F4 self identity | 20 tests, **OK** |
| c4 | reprojection idempotency (W1 → real events → W2 fixture, restart) | 21 tests, **OK** |
| c5a | durable floor, unknown-identity classification, routing-only, primitives | 22 tests, **OK** |
| c5b | historical ledger compatibility, indeterminate fail-closed, restart provenance | 13 tests, **OK** |
| c6 | shutdown determinism | 21 tests, **OK** |
| | **total** | **141 tests, 140 PASS** |

#### 10.1.1 The single failure — pre-existing and image-layout dependent

```text
test_etm_is_loaded_from_locked_editable_source (test_kettly_etm_compat)
AssertionError: False is not true :
  (PosixPath('/opt/efb-telegram-master/efb_telegram_master/__init__.py'),
   PosixPath('/opt/efb-linux-wechat-slave/upstream/efb-telegram-master-kettly'))
```

The Dockerfile installs the ETM fork at `/opt/efb-telegram-master` while the test
asserts the CI checkout path `upstream/efb-telegram-master-kettly`. It passes in CI
and fails inside any image built from this Dockerfile. Recorded as a
**baseline-equivalent deviation** — identical to the failure the previous round
measured on the frozen candidate. Neither the test nor the Dockerfile's ETM path
was touched.

### 10.2 Shutdown product-semantics gate

Judged on **container-internal evidence**, per the documented policy that `T_CLI`
on this host is a Docker-CLI artefact and never product shutdown latency.

```text
gate                = PASS
runs                = 5/5
failed_runs         = 0
shutdown_exit_codes = [0, 0, 0, 0, 0]
sigkill_count       = 0
t_process_max_sec   = 1.005094        (container-internal T_PROCESS)
t_cli_min/p50/max   = 1795 / 2094 / 4138 ms   (informational only)
final_durable_flush = PASS
orphan_process_thread = 0
```

All ten evidence checks are `true` on all five runs:

```text
exit_code_zero  not_running  pid_zero  not_oom_killed  shutdown_exit_code_zero
delivery_suppressed  drain_ok  checkpoint_flushed  ledger_wal_checkpointed
checkpoint_272548
```

Representative container-internal evidence:

```text
trigger                    = signal:15
exit_code                  = 0
delivery_suppressed        = true
hard_exit                  = true, repeated = false
master_stop_bounded_out    = true
phases: slave_drain 0.00334 s | suppress_dispatch 1.1e-05 s | master_stop_bounded 1.000451 s
slave_drain[0].detail: checkpoint_flushed true, ledger_wal_checkpointed true,
                       core_session_closed true, delivery_suppressed true,
                       poll_stopped true, checkpoint_cursor 272548
core checkpoint_requests[0].processed_through_cursor = 272548
```

`ExitCode = 0` (never `137` = 128+9) on every run is the authoritative proof that
the process was **not** SIGKILLed: it completed its bounded drain inside the grace
window. The new durable floor file (`data/core-subscription-floor.json`) is present
in each run's data directory, confirming the hardening initialises cleanly on a
real container start.

**Harness execution deviation, disclosed.** The frozen Python runner
(`run_image_shutdown_gate.py`) cannot execute on this host (no `python3`) nor in CI
(§9.3). The gate was therefore driven by a host shell script issuing **the same
`docker run` invocation with the same image, entrypoint and arguments** as the
frozen runner, validating the same ten evidence checks with `jq`. The evidence
files (`shutdown-evidence.json`, `core-evidence.json`) are produced by the
unmodified in-image probe and are the actual basis of the verdict.

**Self-correction disclosed.** The first gate attempt reported `PASS` with empty
evidence checks — a jq `--slurpfile` indexing error (`$insp[0]` is the
`docker inspect` array, so `State` had to be read as `$insp[0][0].State`) meant the
filter produced nothing and a fallback made the verdict vacuous. That result was
**discarded**, the filter was fixed, and the gate was made to fail loudly whenever
the evidence filter produces no checks. The verdict reported above is from the
corrected run; the discarded attempt is recorded here rather than hidden.

### 10.3 Disclosed: in-image full-discovery run abandoned

Running all 141 tests in a single container was abandoned after the container and
its driving shell both died ~10 minutes in, mid-`test_hardened_code_keeps_the_production_row_count`,
with no summary line. No OOM was recorded in `dmesg`; the container was observed
alive but at ~0.1 % CPU (I/O-blocked on the degraded array, where the test performs
417 individual `synchronous=FULL` ledger commits). The suite was re-run in the
seven chunks of 10.1, which completed with 0 real failures. The chunked result is
the evidence; the abandoned run is not counted.

---

## 11. Production untouched

```text
PRODUCTION_EFB_TOUCHED   = NO
PRODUCTION_AGENT_TOUCHED = NO
EFB_CHECKPOINT           = 273844
EFB_CHECKPOINT_MUTATION  = 0
```

Containers, at `2026-09-17T09:1xZ` on the host:

```text
wechat-hub-f-live-core         Up 8 hours (healthy)
wechat-hub-f-live-efb          Exited (0) 16 hours ago
wechat-hub-f-live-agent        Exited (0) 25 hours ago
wechat-hub-f-live-console      Up 3 days (healthy)
wechat-hub-f-live-runtime      Up 6 days (healthy)
wechat-agent-f-live-a-faf35abb Up 6 days
wechat-agent-testb-a7c4f6c8    Up 6 days
```

```text
EFB   StartedAt = 2026-09-16T16:49:38Z   FinishedAt = 2026-09-16T17:21:18Z   ExitCode 0   Restarts 0
AGENT StartedAt = 2026-09-16T07:31:50Z   FinishedAt = 2026-09-16T08:04:18Z   ExitCode 0   Restarts 0
```

Neither container has been started since the previous round.

**Checkpoint read, read-only HTTP only.** No Core SQLite file was opened, read,
copied, hashed or executed against — the standing prohibition is respected in full.

```text
GET http://127.0.0.1:18082/v1/consumers/efb-linux-wechat%3Awechat.linux/bootstrap

consumer_id             = efb-linux-wechat:wechat.linux
initial_cursor          = 272037
processed_through_cursor= 273844      <- the EFB checkpoint
bootstrap_mode          = bounded_window
bootstrap_source        = governed_rebootstrap
bootstrap_at            = 2026-09-15T11:18:09Z
stream_head_cursor      = 274782
retention_floor_cursor  = 1
```

Note `GET /v1/consumers/efb-linux-wechat/bootstrap` returns
`bootstrap_not_found`: the effective consumer id is the derived
`{consumer_base}:{channel_id}`, which is exactly what the hardening's
`consumer_id` derivation and the floor scope use. This read also independently
confirms that the hardening fixture's production floor
(`272037` / `2026-09-15T11:18:09Z` / `bounded_window` / `governed_rebootstrap`)
matches production reality.

Corroborating local state, all read-only, with mtimes that predate this round:

```text
core-event-cursor.json            = {"cursor":"273844"}     mtime 2026-09-17 01:14:42 +0800
core-effect-ledger.sqlite3        size 380928               mtime 2026-09-17 01:18:21 +0800
core-effect-ledger.sqlite3-wal    size 0 (no pending frames) mtime 2026-09-17 01:24:20 +0800
core-message-mapping.sqlite3      size 86016                mtime 2026-09-17 01:14:09 +0800
```

Every EFB state file was last written during the previous round's shutdown window
(container `FinishedAt` 2026-09-16T17:21:18Z). Nothing has written to them since,
and the ledger WAL holds zero frames. The EFB consumer was never started, no
checkpoint was advanced, and no Telegram or WeChat message was sent.

The Core-DB forensics guard (`scripts/forensics/check_forbidden_live_core_db_access.py`)
lives in the Core repository and is not part of this EFB worktree; it was therefore
not invoked here. No command in this round referenced a Core database path — all
Core reads went through the read-only HTTP GET above.

---

## 12. Return block

```text
BASE_SOURCE                              = aa9407833d4c6ae54e1da6d830980e178cebd693
NEW_SOURCE_COMMIT                        = 69a1f58e29177634b6790ed3b5ec688871ba590c
NEW_IMAGE_DIGEST                         = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:6c8dc474298f42d7a3528902a0dd8398270f9b525f1d299e05d7f2e46bc16d00
NEW_OCI_REVISION                         = 69a1f58e29177634b6790ed3b5ec688871ba590c
FINAL_EFFECT_IDENTITY_SCHEMA             = (consumer_id, account_id, message_id, effect_kind)
SUBSCRIPTION_FLOOR_DURABLE               = YES
SUBSCRIPTION_FLOOR_SCOPE                 = consumer_id + account_id
EVENT_TYPE_USED_FOR_ROUTING_ONLY         = YES
EVENT_TYPE_USED_FOR_DUPLICATE_DECISION   = NO
UNKNOWN_UPDATED_PRE_FLOOR_SUPPRESSED     = YES
UNKNOWN_UPDATED_POST_FLOOR_TREATED_AS_NEW= YES
UNKNOWN_UPDATED_AMBIGUOUS_FAIL_CLOSED    = YES
W1_DUPLICATE_EXTERNAL_DELIVERY           = 0
W1_NEW_MEDIA_FAILED_FROM_REPROJECTION    = 0
W1_UNWANTED_PENDING_MEDIA                = 0
W2_DUPLICATE_EXTERNAL_DELIVERY           = 0
W2_NEW_MEDIA_FAILED_FROM_REPROJECTION    = 0
W2_UNWANTED_PENDING_MEDIA                = 0
274305_RECOGNIZED_AS_NEW                 = YES
274306_RECOGNIZED_AS_NEW                 = YES
274307_RECOGNIZED_AS_NEW                 = YES
RESTART_PROVENANCE_SAFE                  = YES
EXACT_IMAGE_SMOKE                        = PASS
SHUTDOWN_PRODUCT_GATE                    = PASS
PRODUCTION_EFB_TOUCHED                   = NO
PRODUCTION_AGENT_TOUCHED                 = NO
EFB_CHECKPOINT                           = 273844
EFB_CHECKPOINT_MUTATION                  = 0
UNKNOWN_IDENTITY_HARDENING               = PASS
EFB_REPROJECTION_IDEMPOTENCY_ENGINEERING = PASS
NEW_EFB_CANDIDATE_READY                  = YES
EFB_LIVE_AUTHORIZATION_READY             = NO
ACTION                                   = STOP
```

### Disclosures attached to the return block

1. **`PUBLISH_RUN = 35201725302` concluded `failure`.** The image built, pushed and
   revision-verified; only the workflow's embedded exact-digest shutdown gate step
   failed with the same host-side `[Errno 1] Operation not permitted` that already
   affects the frozen candidate. Classified `HARNESS_INFRA_DEVIATION`, not a product
   failure. See §9.3.
2. **`EXACT_IMAGE_SMOKE = PASS` is 140/141.** The one failure
   (`test_etm_is_loaded_from_locked_editable_source`) is a pre-existing
   Dockerfile-vs-CI path-layout assertion, identical on the frozen candidate.
   See §10.1.1.
3. **The shutdown gate was driven by a host shell replication** of the frozen
   runner's container invocation, because the runner cannot execute on this host or
   in CI. The evidence files it validates come from the unmodified in-image probe.
   See §10.2.
4. **One discarded gate attempt and one abandoned in-image discovery run** are
   recorded in §10.2 and §10.3 rather than omitted.
5. **`FILE_MEDIA_REFERENCE_GAP_CONFIRMED = YES` / `CORE_FOLLOWUP_REQUIRED = YES`** —
   the `274307` file/empty-`media_id` gap is deliberately **not** fixed in this
   package. See §8.
6. **`EFB_LIVE_AUTHORIZATION_READY = NO`** — a live round additionally requires an
   explicit checkpoint-advance authorization, which remains rejected
   (`CHECKPOINT_ADVANCE_SAFE = NO`) and was not requested.

---

```text
ACTION = STOP
```

No EFB start. No checkpoint advance. No Production Live. No Telegram. No WeChat.
