# RC.14 — EFB Post-F3 Checkpoint Fence Reconciliation Result

**Round type:** STRICT READ-ONLY reconciliation (no production mutation)
**Host:** unraid `192.168.22.102` (root)
**Production stack:** `wechat-hub-f-live`
**Round window (host UTC):** `2026-09-17T03:18:18Z` … close
**Predecessor:** `docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_RESULT.md`
(`sha256 a6972063da916976a780f8802d5918a62b4b3f69cfc65eea08c178bb07614998`, verdict PASS)

---

## §0 Authorization and method

Authorized work package: determine whether the cursor range `273845..274727` can be safely
skipped by the EFB consumer, i.e. whether advancing the EFB checkpoint
`273844 → 274727` would lose any business event.

Explicit scope limits carried into this round:

- The checkpoint was **not** advanced. No consumer checkpoint, receipt, ack or event row was written.
- EFB was **not** started. Agent was **not** started.
- No EFB EffectLedger row was deleted, rewritten, reclassified or reset.
- No F1/F2 historical result was replayed, reset or cleaned.
- Every Core read went through the Core HTTP API on `127.0.0.1:18082`.
- The poll calls deliberately omitted `consumer_id`. Per `core/store.py::poll_events`, the
  consumer-registry check and the `consumer_checkpoints` lookup are both guarded by
  `if cid:`, so an empty `consumer_id` makes the call a pure `SELECT` over `events` that writes
  nothing. This is the reason the round can read the stream while remaining side-effect free.

Method note on the guard: the host command log for this round is
`tmp/rc14-fence/core_db_access_command_log.txt`, scanned with
`check_forbidden_live_core_db_access.py --mode both --json`. The guard's repository-wide CI form
also scans `.md` files, but it skips prose outside fenced code blocks, so the prohibition lists in
this document are prose, and the fenced blocks below contain only Core HTTP API reads.

---

## §1 Production state at round open and close

| Service | Container | State | RestartCount | StartedAt | Touched |
|---|---|---|---|---|---|
| Core | `wechat-hub-f-live-core` | `running (healthy)` | 0 | `2026-09-17T01:45:06.839931379Z` | no |
| Console | `wechat-hub-f-live-console` | `running (healthy)`, Up 3 days | — | — | no |
| Runtime | `wechat-hub-f-live-runtime` | `running (healthy)`, Up 5 days | — | — | no |
| AgentWechat A | `wechat-agent-f-live-a-faf35abb` | `running`, Up 5 days | — | — | no |
| AgentWechat B | `wechat-agent-testb-a7c4f6c8` | `running`, Up 5 days | — | — | no |
| Agent | `wechat-hub-f-live-agent` | `exited (0)` | 0 | `2026-09-16T07:31:50.371571612Z` | no |
| EFB | `wechat-hub-f-live-efb` | `exited (0)` | 0 | `2026-09-16T16:49:38.345169161Z` | no |

Core image identity is unchanged from the F3 deployment round:

```
Core container : e95ebb30e8581df5bc9455ef7420d3b3fa142b77f57e6a0f037e8a9f0fe794c9
Core image     : sha256:9061b9b3a986f70b9d77a9c0d5afd65e8e90808e735152f7a32d00d053407f31
               = ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3…0427   (revision 6538f79a)
```

`AGENT = STOPPED`, `EFB = STOPPED` held for the whole round.

Core `/health` at round open reported `ok:true`, `contract_version:1`, `accounts:2`,
`sync_worker.cycle_count:408`, `consecutive_failed_cycles:0`, `flush_error_count:0`.

### §1.1 Consumer state (Core HTTP API)

`GET /v1/events/checkpoint?consumer_id=efb-linux-wechat:wechat.linux`

```json
{"consumer_id":"efb-linux-wechat:wechat.linux","processed_through_cursor":273844,
 "last_event_id":"","subscription_account_id":"","updated_at":"2026-09-16T17:14:43Z"}
```

`GET /v1/consumers/efb-linux-wechat:wechat.linux/bootstrap`

```json
{"consumer_id":"efb-linux-wechat:wechat.linux","initial_cursor":272037,
 "processed_through_cursor":273844,"bootstrap_mode":"bounded_window",
 "bootstrap_source":"governed_rebootstrap","bootstrap_at":"2026-09-15T11:18:09Z",
 "stream_head_cursor":274760,"retention_floor_cursor":1,
 "audit_history":[{"action":"rebootstrap","previous_cursor":13181,
   "new_initial_cursor":272037,"new_bootstrap_mode":"bounded_window",
   "operator_token":"EFB_REBOOTSTRAP_REMEDIATION_QUAL_RETRY2",
   "created_at":"2026-09-15T11:18:09Z"}]}
```

`GET /v1/events/checkpoint?consumer_id=wechat-agent` → `processed_through_cursor: 195927`,
`updated_at: 2026-09-16T08:04:11Z` (unchanged, as expected while Agent is stopped).

**Two facts from this block drive the whole analysis:**

1. `PRE_EFB_CHECKPOINT = 273844`, last written `2026-09-16T17:14:43Z`.
2. EFB was admitted through a **governed bounded window** starting at `initial_cursor = 272037`
   (`2026-09-15T11:18:09Z`). Events with cursor `< 272037` were never in EFB's scope — an
   operator decision recorded in the audit history, not an accident.

Stream at round open: `stream_head_cursor = 274760`, `retention_floor_cursor = 1` (nothing trimmed;
the full history is addressable).

---

## §2 Full enumeration of the gap (no sampling)

The gap `273845..274727` was read end to end with five `GET /v1/events/poll` calls
(`limit=200`, the Core V1 hard cap), plus a ten-call control read of `272037..273844`.
No sampling, no extrapolation.

```
p1 after=273844 n=200 first=273845 next=274044
p2 after=274044 n=200 first=274045 next=274244
p3 after=274244 n=200 first=274245 next=274444
p4 after=274444 n=200 first=274445 next=274644
p5 after=274644 n=116 first=274645 next=274760
head=274760 floor=1
```

Filtered to the gap and verified contiguous:

```
GAP_TOTAL          = 883
GAP_UNIQUE_CURSORS = 883
GAP_MIN            = 273845
GAP_MAX            = 274727
span               = 274727 - 273845 + 1 = 883   ->  no holes, no duplicates
```

Event-type census of the whole gap:

| event_type | count |
|---|---|
| `account.status` | 39 |
| `media.ready` | 13 |
| `message.created` | 3 |
| `message.updated` | 828 |
| **total** | **883** |

Gap wall-clock span (from event `occurred_at`): `2026-09-16T17:21:40Z` … `2026-09-17T01:46:30Z`.
EFB's last checkpoint write was `2026-09-16T17:14:43Z`, so the gap opens ~7 minutes after EFB stopped
and closes at the F3 deployment. This is the whole "EFB was down" accumulation.

### §2.1 The gap is two distinct windows

| Window | Cursors | Events | Composition |
|---|---|---|---|
| **W1** | `273845..274307` | 463 | `account.status` 33, `media.ready` 13, `message.created` 3, `message.updated` 414 |
| **W2** | `274308..274727` | 420 | `account.status` 6, `message.updated` 414 |

W2 is exactly the window the F3 deployment result reported (420 events: 6 + 414). W1 was outside that
round's window and had not been enumerated before.

`message.updated` occurrence times:

```
W1 message.updated occurred_at : 2026-09-17T00:09:10Z .. 2026-09-17T00:09:18Z   (8 s burst)
W2 message.updated occurred_at : 2026-09-17T01:45:15Z .. 2026-09-17T01:45:22Z   (7 s burst)
```

W2 starts 9 seconds after the new Core container `StartedAt` (`01:45:06.839931379Z`) — the F3 sync
worker's first full re-read. W1 happened **1 h 36 min before** the F3 deployment, i.e. it was
produced by the **previous** Core.

---

## §3 The 828 `message.updated` — two re-projections of one 414-object set

This is the central finding, and it corrects a number carried forward from the F3 round.

F3 fingerprint test (does the event's `payload.message` carry the top-level F3 keys?):

```
W1 message.updated total          = 414
  media_role present              = 0
  media_status present            = 0
  distinct message_id             = 414
W2 message.updated total          = 414
  media_role present              = 414
  media_status present            = 414
  distinct message_id             = 414
shared message_id across W1 ∩ W2  = 414
```

So the two windows are the **same 414 message identities**, emitted twice:

- **W1 (00:09Z, previous Core):** 414 updates with **no** `media_role` / `media_status` — the
  pre-F3 payload shape.
- **W2 (01:45Z, F3 Core):** the same 414 updates **with** `media_role` / `media_status` — the F3
  contract now materialised.

W2's field distribution:

```
media_role    : original 403, thumbnail 11
media_status  : original_pending 228, missing_metadata 89, missing_file 83, ready 13, decode_failed 1
                (228+89+83+13+1 = 414)
```

The status mix matches the media-scan statistics reported by `/health` for the same two accounts
(f-live-a: `original_pending 222, missing_metadata 89, missing_file 65, ready 10, decode_failed 1`;
testB: `original_pending 6, missing_file 16, ready 3`) to within a few rows of scan drift. That is the
signature of the **whole media-bearing message population** being re-projected because the F3 change
made `media_role` / `media_status` digest-participating keys — not of 414 fresh messages arriving.

The underlying business objects are old. `payload.message.created_at` across the 414:

```
min = 2026-09-01T06:22:51Z
max = 2026-09-16T13:09:47Z
```

Every one of the 414 predates the F3 deployment (`2026-09-17T01:45:06Z`) by at least 12 h 35 min, and
the oldest by more than two weeks.

### §3.1 Were these objects already in EFB's scope?

`message.created` for a message always precedes any `message.updated` for the same message (a row must
exist before it can be "changed"). Therefore the creation cursor of each of the 414 is either inside
the gap or before it. The gap contains only 3 `message.created`, and none of their message ids is in
the 414 set:

```
created_in_414 = 0
```

So every one of the 414 was created at cursor `<= 273844`. Splitting that against EFB's admitted
window (`272037..273844`, read in full as the control sample — 1808 events):

| Control window `272037..273844` | count |
|---|---|
| `account.status` | 1333 |
| `media.ready` | 44 |
| `message.created` | 417 (417 distinct) |
| `message.updated` | 6 (6 distinct) |
| `send.updated` | 8 |
| **total** | **1808** |
| `occurred_at` span | `2026-09-13T12:03:37Z` … `2026-09-16T16:40:19Z` |

```
ids414_created_in_pre        = 69     (creation inside EFB's consumed window)
ids414_created_before_pre    = 345    (creation before initial_cursor 272037)
```

**69** of the 414 had their `message.created` consumed by EFB, so replaying their updates is a
re-projection of objects EFB already processed. The other **345** were created before EFB's governed
bounded-window floor `272037`, so EFB was never scoped to them at all.

Either way, all 828 are `REGENERATED_EXISTING_OBJECT`. None is a new user message.

---

## §4 The 13 `media.ready`

```
MEDIA_READY_TOTAL = 13
```

| Cursors | Account | occurred_at | role | filename |
|---|---|---|---|---|
| 273876 | f-live-a | 2026-09-17T00:09:09Z | original | `cad14590f716f27b0ad275e16211ce60.png` |
| 273877–273885 (9) | f-live-a | 2026-09-17T00:09:09Z | thumbnail | `*_thumb.jpg` |
| 274273–274275 (3) | testB | 2026-09-17T00:09:18Z | original | `.png`, `.jpg`, `.jpg` |

All 13 fire inside the W1 burst window (`00:09:09Z`–`00:09:18Z`) — they are the media-scan
transitions that produced W1, not an independent event stream.

The `media.ready` payload carries **no message linkage** — only `account_id`, `media_id`, `role`,
`status`, `filename`, `mime_type`, `disposition`. Parent-message identity was therefore established
indirectly, from three independent identity/ordering facts:

1. No `message.created` exists anywhere in the gap for `testB`, so the three testB `media.ready`
   cannot belong to a message created inside the gap.
2. The ten f-live-a `media.ready` fire at `00:09:09Z`; the earliest f-live-a `message.created` in the
   gap is at `00:29:54Z`. A readiness transition cannot precede the ingestion of the message it
   belongs to, so these ten belong to messages created before the gap.
3. Cross-check against the control window: 3 of the 13 media ids also appear as `media.ready` in
   `272037..273844`, confirming those media objects pre-date the gap outright.

```
MEDIA_READY_TOTAL          = 13
MEDIA_READY_REGENERATED    = 13
MEDIA_READY_NEW_BUSINESS   = 0
```

---

## §5 The 3 `message.created` — the blocking finding

```
MESSAGE_CREATED_COUNT = 3
```

| Cursor | Account | Chat | created_at | type | media_role | media_status |
|---|---|---|---|---|---|---|
| 274305 | f-live-a | `38808757431@chatroom` | 2026-09-17T00:29:54Z | `link` | absent | absent |
| 274306 | f-live-a | `38808757431@chatroom` | 2026-09-17T00:30:06Z | `text` | absent | absent |
| 274307 | f-live-a | `38808757431@chatroom` | 2026-09-17T00:41:14Z | `file` | absent | absent |

These are the **first-ever events** for their message identities (event type is `message.created`,
which Core emits only when `before is None`), they are **not** members of the 414 re-projection set
(`created_in_414 = 0`), and their cursors `274305..274307` are **above** EFB's checkpoint `273844`.

They arrived at `00:29–00:41Z` on 2026-09-17. EFB stopped at `17:14:43Z` on 2026-09-16. EFB has never
had an opportunity to consume them. By identity — new message ids, first event, unconsumed cursor,
absent from every re-projection set — all three are `NEW_UNDELIVERED_BUSINESS_EVENT`.

The absent `media_role` / `media_status` on these three is expected, not a regression: they were
emitted by the **previous** Core at `00:29–00:41Z`, before the F3 deployment. Their absence is
`HISTORICAL_EVENT_IMMUTABLE` evidence and is not counted against the current F3 runtime — the F3
round's §6 rule applies unchanged.

---

## §6 The 39 `account.status`

`account.status` is a runtime-heartbeat projection of the account row. It carries no message, no
media and no outbound intent; nothing downstream of it can produce an external side effect.
Classified as neither regenerated business object nor new business event.

---

## §7 Classification summary

| Category | Events | Classification |
|---|---|---|
| `message.updated` (W1 + W2) | 828 | `REGENERATED_EXISTING_OBJECT` |
| `media.ready` | 13 | `REGENERATED_EXISTING_OBJECT` |
| `message.created` | 3 | `NEW_UNDELIVERED_BUSINESS_EVENT` |
| `account.status` | 39 | no external side effect |
| **total** | **883** | |

```
MESSAGE_UPDATED_TOTAL              = 828   (W1 414 + W2 414; 414 distinct identities)
MESSAGE_UPDATED_REGENERATED        = 828
MESSAGE_UPDATED_NEW_BUSINESS       = 0
MESSAGE_UPDATED_READY_STATUS_COUNT = 13    (all inside W2; W1 carries no status field)

MEDIA_READY_TOTAL                  = 13
MEDIA_READY_REGENERATED            = 13
MEDIA_READY_NEW_BUSINESS           = 0

MESSAGE_CREATED_NEW_BUSINESS       = 3

REGENERATED_EXISTING_EVENT_COUNT   = 828 + 13 = 841
NEW_UNDELIVERED_BUSINESS_EVENT_COUNT = 3
```

Answering the specific question put to this round: **yes**, the 13 `status = ready` updates are purely
the F3 media-role/status re-projection of pre-existing objects, not previously-undelivered new user
messages. But the gap is **not** a pure F3 artefact, and the fence question turns on something else
entirely — see §8.

---

## §8 Hard stop condition

```
NEW_UNDELIVERED_BUSINESS_EVENT_COUNT = 3  >  0
```

Per the authorized rule, this immediately yields:

```
CHECKPOINT_ADVANCE_SAFE = NO
```

No mutation authorization was created. No fence taskbook was authored
(`CHECKPOINT_TASKBOOK_SHA256 = NOT_CREATED`).

**Why this matters, concretely.** A single checkpoint is one cursor. Advancing EFB to `274727` would
skip `273845..274727` atomically, and that range contains the three genuine group-chat messages above.
The fence cannot be narrowed from the consumer side to spare them: the 3 new messages
(`274305..274307`) sit *inside* the same range as W1's 414 pre-F3 re-projections, and W2's 414 sit
immediately after them.

### §8.1 The fence is not a no-op even ignoring §5

Recorded for the next round's decision, not acted on here. The two candidate fence points have
different consequences:

- **Fence at `274727`** (the value this round was asked to test): skips W1 *and* W2. Drops the 3 new
  messages. Rejected by §8.
- **Fence at `274307`**: skips only W2, i.e. only the F3-generated burst, and preserves the 3 new
  messages. It does **not** protect against W1, whose 414 updates still carry the pre-F3 payload
  shape.

On W1 the payload shape is a live concern. The frozen EFB candidate
(`efb_wechat_comwechat_slave/CoreMessage.py:226-227`) reads the top-level fields and, per the sealed
contract document, treats a role that is not `"original"` as `MediaPermanentError` → `MEDIA_FAILED`
(the historical message text is `"…has role ''; thumbnail cannot be final"`, i.e. the absent field is
read as the empty string). Replaying W1 would therefore re-run the pre-F3 failure mode over the
media-bearing subset of those 414 events. Whether that merely re-records already-known failures or
writes new terminal ledger rows depends on EFB-side ledger semantics, which are **out of scope for
this read-only round and were not inspected**.

Also relevant: 10 of the 13 `ready` objects were created before EFB's `initial_cursor = 272037`
(§3.1), so an unfenced replay would attempt to push media as old as `2026-09-01` to Telegram. That is
the hazard the fence was conceived to prevent — and it is precisely why "skip the whole gap" and
"protect the new messages" are in direct conflict here.

Any future decision therefore needs an event-level mechanism (EFB-side effect identity / ledger
idempotency) rather than a single-cursor fence. That is an operator decision and is **not** made here.

---

## §9 Historical EFB evidence — preserved

```
HISTORICAL_MEDIA_FAILED_PRESERVED = YES
```

No EFB EffectLedger row was deleted. No `MEDIA_FAILED` row was rewritten to `DELIVERED`. No mapping
was reset. No F1/F2 result was replayed, reset or cleaned. `EFB checkpoint = 273844` stands unchanged.
This round performed no write of any kind against EFB or Core.

---

## §10 Active Core DB governance

`ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0`
`ACTIVE_CORE_RAW_SQLITE_READS = 0`

Guard self-test matrix: `CI_NEGATIVE_TESTS = PASS`, `CI_POSITIVE_TESTS = PASS`.
Guard scan of the round command log (`--mode both --json`):

```json
{"guard_version":"1.1.0","rule_id":"ACTIVE_CORE_HOST_PRODUCTION_DB_FILE_OPENS",
 "files_scanned":1,"findings":[],
 "RAW_SQLITE_GUARD":"PASS","GENERIC_FILE_OPEN_GUARD":"PASS","SCRATCH_GUARD":"PASS"}
```

Every Core read in this round was an HTTP call against `127.0.0.1:18082`. No host process opened,
copied, hashed, mounted or bound the production Core database, its `-wal` or its `-shm` — the
prohibition was observed even in its read-only forms, so no `-wal` / `-shm` sidecar was created and
there is nothing to disclose about sidecar residue.

Disposable scratch: the round's `/tmp/rc14fence` working set (15 raw poll captures plus 8 generated
jq programs, all in tmpfs/RAM) was deleted after the aggregates were recorded here, and the directory
was removed. Durable evidence and active references were verified absent before deletion.

---

## §11 Disclosures

1. **The 828 figure corrects a number carried out of the F3 round.** The F3 result reported 414
   re-emitted `message.updated`. That was correct for its window (`274308..274727`) but understates
   the gap, which contains 828 — the *same* 414 objects re-projected twice: once by the previous Core
   at `00:09Z` without the F3 fields, once by the F3 Core at `01:45Z` with them. The F3 verdict
   (`CORE_MEDIA_CONTRACT_F3_DEPLOYMENT = PASS`) is unaffected: the F3 fingerprint (fields present on
   414/414) is unambiguous, and W1 is dated before the F3 container existed.
2. **The gap is not a pure F3 artefact.** It contains 3 genuine new incoming messages (§5). This is
   the reason the fence is unsafe, and it was not visible from the F3 round's window.
3. **The `274727` fence value is a historical cursor, not the head.** At round close
   `stream_head_cursor = 274760`, and cursor `274728` is itself a new `message.created`
   (`f-live-a`, `2026-09-17T02:29:36Z`). Any future round must re-pin against the head it actually
   faces rather than reusing `274727`.
4. **`media.ready` carries no message linkage.** Parent-message identity had to be inferred from
   ordering plus the absence of any same-account `message.created` in the gap. A future Core revision
   that put `message_id` / `chat_id` on the `media` payload would make this classification direct
   instead of inferential.
5. **W1's pre-F3 payload shape is an open EFB-side question**, not resolved here: whether replaying
   pre-F3 events produces fresh terminal `MEDIA_FAILED` rows or only re-records known failures depends
   on ledger semantics that this read-only round did not inspect.
6. **The 3 new messages are reported by identity only.** Whether EFB's own configuration would
   actually forward the chat `38808757431@chatroom` to Telegram was not determined — EFB-side
   configuration is out of scope here. The classification follows the authorized rule (judge by
   stable identity, never by content).
7. **This document is a new, uncommitted docs-only artifact.** It was not requested by name and is
   deliberately **not** part of the authorized F3 docs commit. It is untracked pending instruction.

---

## §12 Return block

```
PRE_EFB_CHECKPOINT = 273844
TARGET_EFB_CHECKPOINT = 274727

GAP_EVENT_COUNT = 883

ACCOUNT_STATUS_COUNT = 39
MESSAGE_CREATED_COUNT = 3
MESSAGE_UPDATED_COUNT = 828
MEDIA_READY_COUNT = 13
OTHER_COUNT = 0

MESSAGE_UPDATED_READY_STATUS_COUNT = 13

REGENERATED_EXISTING_EVENT_COUNT = 841
NEW_UNDELIVERED_BUSINESS_EVENT_COUNT = 3

MESSAGE_CREATED_NEW_BUSINESS = 3
MESSAGE_UPDATED_NEW_BUSINESS = 0
MEDIA_READY_NEW_BUSINESS = 0

HISTORICAL_MEDIA_FAILED_PRESERVED = YES

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS = 0

CHECKPOINT_ADVANCE_SAFE = NO

CHECKPOINT_TASKBOOK_SHA256 = NOT_CREATED

CHECKPOINT_MUTATION_PERFORMED = NO

AGENT_STATE = STOPPED
EFB_STATE = STOPPED

ACTION = STOP
```

---

## §13 STOP

The authorized work package ends here.

- The EFB checkpoint was **not** advanced: `273844 → 274727` did **not** happen. Closing re-read
  returned `processed_through_cursor = 273844`, `updated_at = 2026-09-16T17:14:43Z` — byte-identical
  to the opening read.
- EFB was **not** started. Agent was **not** started.
- No mutation authorization was created.
- No checkpoint-fence taskbook was authored, because the gate it depends on did not hold.
- No production object of any kind was modified. Core image, container id and `RestartCount` are
  unchanged from the F3 deployment; Console, Runtime, AgentWechat A/B, Agent and EFB were not
  restarted, recreated or reconfigured.
