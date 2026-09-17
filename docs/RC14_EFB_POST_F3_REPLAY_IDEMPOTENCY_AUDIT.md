# RC.14 — EFB Post-F3 Replay / EffectLedger Idempotency Audit

**Round type:** STRICT READ-ONLY audit — no production mutation, no checkpoint advance, no consumer start
**Host:** unraid `192.168.22.102` (root)
**Production stack:** `wechat-hub-f-live`
**Round window (host UTC):** `2026-09-17T03:48:38Z` … `2026-09-17T03:56Z`
**Predecessors (sealed, unmodified):**

| Document | sha256 |
|---|---|
| `docs/RC14_EFB_POST_F3_CHECKPOINT_FENCE_RECONCILIATION_RESULT.md` | `19aba2b31ae60699e2263f286cf9c48bb08512a462116b8a4bc1cf93b99ce2cf` |
| `docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_RESULT.md` | `a6972063da916976a780f8802d5918a62b4b3f69cfc65eea08c178bb07614998` |

**Frozen EFB candidate under audit:** `SOURCE_COMMIT 91a69cef323d120f0e32196917a630d2cf3baa88`,
image digest `sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241`,
image `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave`, workdir `/opt/efb-linux-wechat-slave`.

**Headline verdict:** the replay of the F3 re-projection windows is **NOT idempotent** and **NOT
safely skippable**. A single-cursor checkpoint fence cannot fix it. The defect is at the
**event-identity level** inside the frozen EFB candidate, so
`EFB_CODE_CHANGE_REQUIRED = YES` (Case C). No checkpoint was advanced.

---

## §0 Authorization, scope and method

Authorized work package: determine (a) whether the cursor range `273845..274727` can be safely
skipped, and (b) whether the frozen EFB candidate is idempotent under replay of that range, using
the production EffectLedger as the authority for what has already been delivered.

Explicit scope limits carried into this round — all observed:

- No checkpoint, receipt, ack or event row was written. Every poll omitted `consumer_id`.
  Per `core/store.py::poll_events`, both the consumer-registry check and the
  `consumer_checkpoints` lookup are guarded by `if cid:`, so an empty `consumer_id` makes the call
  a pure `SELECT` over `events` that writes nothing.
- EFB was **not** started. Agent was **not** started. No Telegram or WeChat send was attempted.
- No `INSERT` / `UPDATE` / `DELETE` / `VACUUM` / `wal_checkpoint` / migration on the production
  EffectLedger. The production ledger file was **never** opened by `sqlite3`; all queries ran
  against a disposable `/dev/shm` copy of the main DB plus its `-wal`. No `-wal` / `-shm` sidecar
  was removed or rewritten.
- No EFB profile file (ledger, mapping store, cursor JSON, echo store) was written.
- No F1/F2 historical result was replayed, reset or reclassified. The historical
  `MEDIA_FAILED = 42` was preserved untouched.
- The frozen EFB Functional Candidate was **not** rebuilt, retagged or modified. It was read only
  as a read-only extraction of its image source tree.

Method: the entire event population of the range was re-enumerated with **no sampling** (5 Core
HTTP polls at `limit=200`), then joined against the production EffectLedger by the *exact* effect
identity taken from the frozen source, and finally classified by *re-executing the frozen
predicates* (`_is_media_message`, `CoreMessageBuilder.build()`, `_handle_message_event`) as
read-only decision logic over the captured JSON. No EFB process ran; no network egress to Telegram
or WeChat was possible.

Guard: host command log `tmp/rc14-idem/core_db_access_command_log.txt`, scanned with
`check_forbidden_live_core_db_access.py --mode both --json --no-docs` →
`findings: []`, `RAW_SQLITE_GUARD = PASS`, `GENERIC_FILE_OPEN_GUARD = PASS`,
`SCRATCH_GUARD = PASS`. The boundary controls live in a separate fixture,
`tmp/rc14-idem/guard_boundary_control.txt`, which contains one *intentional* positive-control
violation; its `FAIL` is the evidence that the guard is live, and its two negative controls
(EFB ledger copy, `sqlite3` on the RAM copy) are clean. `--selftest` →
`CI_POSITIVE_TESTS PASS`, `CI_NEGATIVE_TESTS PASS`.

---

## §1 Production state at round open and close

| Service | Container | State | Touched |
|---|---|---|---|
| Core | `wechat-hub-f-live-core` | `running (healthy)`, Up 2 hours | no |
| Console | `wechat-hub-f-live-console` | `running (healthy)`, Up 3 days | no |
| Runtime | `wechat-hub-f-live-runtime` | `running (healthy)`, Up 5 days | no |
| AgentWechat A | `wechat-agent-f-live-a-faf35abb` | `running`, Up 5 days | no |
| AgentWechat B | `wechat-agent-testb-a7c4f6c8` | `running`, Up 5 days | no |
| Agent | `wechat-hub-f-live-agent` | **absent from `docker ps`** ⇒ stopped | no |
| EFB | `wechat-hub-f-live-efb` | **absent from `docker ps`** ⇒ stopped | no |

Durable consumer state at open **and** at close (byte-identical, re-read twice):

```
checkpoint : {"consumer_id":"efb-linux-wechat:wechat.linux",
              "processed_through_cursor":273844,"last_event_id":"",
              "subscription_account_id":"","updated_at":"2026-09-16T17:14:43Z"}
local cursor file : {"cursor":"273844"}
stream_head_cursor : 274764   (open)  …  274764 (close)
```

Note the two AgentWechat containers are the per-account WeChat bridges. The production consumer
`wechat-hub-f-live-agent` is **not** running; `AGENT = STOPPED` is confirmed by container absence,
not inferred.

---

## §2 §B1 — Frozen ranges, head, and boundary reconciliation

**Current head.** `stream_head_cursor` was `274764` at open and `274764` at close of this round.
The head is a **moving value** and must never be used as a checkpoint target — see §11.

**Full re-enumeration (no sampling).** 5 polls at `limit=200` from `after=273844` captured 920
events spanning cursors `273845..274764`:

```
captured total         = 920
distinct cursors       = 920     (distinct == total  ⇒ no duplicates)
min / max cursor       = 273845 / 274764
span (max-min+1)       = 920     (== total          ⇒ no holes, contiguous)
```

**The requested range `273845..274727`:**

```
GAP_N = 883   (contiguous; min 273845, max 274727, span 883)
GAP_TYPES = account.status 39 | media.ready 13 | message.created 3 | message.updated 828
```

**Boundary reconciliation against the sealed predecessor.** The sealed reconciliation document
partitioned the range as `W1 = 273845..274307` (463) and `W2 = 274308..274727` (420). This round's
instruction re-partitions it as `W1 = 273845..274304`, `NEW_BUSINESS_1 = 274305..274307`,
`W2 = 274308..274727`.

**Off-by-one correction (explicit, as required):** the sealed `W1` upper bound `274307` is
**inclusive of the 3 new `message.created` events**. The correct separation is

```
W1_sealed (273845..274307, 463)  =  W1_this_round (273845..274304, 460)  ∪  NEW_BUSINESS_1 (274305..274307, 3)
```

No numeric result in the sealed document is wrong — the 463 = 33 + 13 + 3 + 414 arithmetic is
correct, and the document's §8.1 already treats `274305..274307` separately. Only the *label*
boundary needs the correction, and this round adopts the finer partition:

| Window | Range | Events | Composition |
|---|---|---|---|
| **W1** | `273845..274304` | **460** | `account.status` 33, `media.ready` 13, `message.updated` 414 |
| **NEW_BUSINESS_1** | `274305..274307` | **3** | `message.created` 3 |
| **W2** | `274308..274727` | **420** | `account.status` 6, `message.updated` 414 |
| | | **883** | |

All 414 W1 `message.updated` events lie at cursors `≤ 274304`, so the message-level findings below
are identical under either partition. The re-read also reproduces the sealed figures exactly:
`message.updated` total **828**, W1 **414**, W2 **414**, shared identity set **414**, disjoint
identity set **0** (`IDS_IN_BOTH_W1_W2 = 414`, `IDS_NOT_BOTH = 0`).

**Timing.** W1's `message.updated` burst `2026-09-17T00:09:10Z .. 00:09:18Z`; W2's
`2026-09-17T01:45:15Z .. 01:45:22Z` — W2 begins 9 s after the F3 Core container's `StartedAt`
(`2026-09-17T01:45:06.839931379Z`). All 414 `created_at` values fall in
`2026-09-01T06:22:51Z .. 2026-09-16T13:09:47Z`, i.e. at least **12 h 35 min before the F3 container
existed**. `created_in_414 = 0`.

**Payload fingerprint (re-confirmed this round).**

- W1 (`273845..274304`, previous Core): `media_role` and `media_status` are **absent from the
  top level entirely** — `0/414` carry them. The values survive only nested inside
  `vendor_specific.media` (`{"original_media_id":…,"role":"original","status":"original_pending",
  "thumbnail_media_id":""}`). This is the exact F3 defect signature: `_normalized_message()`
  produced the fields but `upsert_message()`'s explicit column whitelist dropped them.
  `media_id` **is** present on all media-typed events (`empty_media_id = 0`).
- W2 (`274308..274727`, F3 Core): top-level `media_role` / `media_status` present on **414/414**.

W2 `type × media_role × media_status` matrix (this round's authoritative read):

| type | media_role | media_status | count |
|---|---|---|---|
| image | original | original_pending | 228 |
| image | original | missing_metadata | 87 |
| sticker | original | missing_file | 58 |
| image | original | missing_file | 23 |
| video | thumbnail | ready | 9 |
| image | original | ready | 4 |
| video | thumbnail | missing_metadata | 2 |
| system | original | missing_file | 2 |
| image | original | decode_failed | 1 |
| | | **total** | **414** |

Marginals: `media_role` = original 403 / thumbnail 11; `media_status` = original_pending 228,
missing_metadata 89, missing_file 83, ready 13, decode_failed 1. W1 has the same type marginal
(image 343, sticker 58, video 11, **system 2**) with empty role/status.

**The 2 `system` events matter.** They are `revokemsg` system notices from account `testB`
(chat `49017533139@chatroom`). They carry a populated `media_id` + `media_role = "original"` +
`media_status = "missing_file"`, so the F3 re-projection swept them in — but their `type` is
`system`, which is **not** in EFB's media predicate. They are therefore handled on the *text* path
and, critically, receive **no EffectLedger protection at all** (see §6 and §7).

---

## §3 §B2 — `poll(after=N)` contract and the two checkpoint questions

**Contract.** `poll(after=N)` returns strictly `cursor > N`, clipped to the current stream head.
Evidence, three independent sources:

1. Core source `core/store.py::poll_events`:
   `statement = "SELECT * FROM events WHERE cursor>? AND cursor<=?"` with
   `args = [cursor, stream_head_cursor]` — strict `>` on the lower bound.
2. Frozen EFB client `Core.py::CoreClient.poll_events` passes `after` straight through as the
   `after` query parameter, with `limit = max(1, min(int(limit), 200))` (a hard cap, not a hint).
3. Empirical: `poll(after=273844&limit=200)` returned `min(cursor) = 273845`; the whole capture is
   contiguous from `273845`.

Because the upper bound is the **live** head, the final page can overshoot the requested range —
observed here (the `after=274644` page returned up to `274764`).

**Answers:**

```
CHECKPOINT_274304_PRESERVES_274305_274307 = YES
CHECKPOINT_274307_PRESERVES_274305_274307 = NO
```

`274304` as a resume point means the next poll starts at `274305`, so all three new business
events are preserved. `274307` as a resume point means the next poll starts at `274308`, so
`274305`, `274306` and `274307` are all **skipped and lost**.

**Critical caveat — the Core checkpoint row is not the resume point.** `CursorStore.align_with_core`
(`Core.py`) reads the **local** `core-event-cursor.json` and returns it unchanged whenever
`local_cursor >= core initial_cursor`; it only advances the local cursor when it is *missing* or
*below* Core's `initial_cursor`. `poll_once()` likewise seeds from
`self.cursor_store.load()`, never from the checkpoint API. The Core
`consumer_checkpoints.processed_through_cursor` row is written by EFB but **never read back for
resumption**.

Consequence: moving the Core checkpoint row alone would **not** change where EFB resumes. A real
fence would require moving the local cursor file — which this round did not do, and which is not
authorized. Any future fence taskbook must pin **both** values, not just the checkpoint.

---

## §4 §B3 — Production EffectLedger read-only evidence

Access path: `cp` of the main DB and its `-wal` into `/dev/shm/efbaudit/`, then `sqlite3` against
the copy only. The `-shm` sidecar was deliberately **not** copied.

```
ledger file  : <EFB_PROFILE>/profiles/default/wechat.linux/core-effect-ledger.sqlite3
size         : 380928 bytes
mtime        : 2026-09-17 01:18 (local, UTC+8)  ==  2026-09-16T17:18Z
-wal         : 0 bytes  (no pending frames, before and after)
-shm         : 32768 bytes (preserved, untouched)
```

**Identity, pre-read and post-read — byte-identical:**

```
sha256 (pre-read)  = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd
sha256 (post-read) = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd
```

**Row census (read-only):**

```
total rows        = 417
status histogram  = DELIVERED 375 | MEDIA_FAILED 42 | RESERVED 0 | UNCERTAIN 0 | PENDING_MEDIA 0
updated_at range  = 2026-09-15T11:19:46Z .. 2026-09-16T17:18:20Z
consumer_id       = efb-linux-wechat:wechat.linux   (single consumer)
```

The historical `MEDIA_FAILED = 42` is **intact**. There is **no** `RESERVED` or `UNCERTAIN` row,
so no `BLOCKED_UNCERTAIN_EFFECT` fail-closed state is pending. There are **zero** `PENDING_MEDIA`
rows, which is decisive for §9.

```
EFB_LEDGER_MUTATION = 0
```

---

## §5 §B4 — Exact effect identity (taken from frozen source, not inferred)

From `/tmp/efbsrc/efb_wechat_comwechat_slave/EffectLedger.py`:

```python
@staticmethod
def compute_effect_id(account_id: str, message_id: str, event_type: str = "message.created") -> str:
    acc = str(account_id or "").strip()
    msg = str(message_id or "").strip()
    if not acc or not msg:
        raise ValueError(...)
    return f"{acc}:{msg}"
```

and the table definition:

```sql
CREATE TABLE IF NOT EXISTS effect_ledger (
    consumer_id TEXT NOT NULL, effect_id TEXT NOT NULL,
    account_id TEXT NOT NULL, message_id TEXT NOT NULL,
    efb_uid TEXT NOT NULL DEFAULT '', event_type TEXT NOT NULL DEFAULT 'message.created',
    status TEXT NOT NULL DEFAULT 'RESERVED',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (consumer_id, effect_id)
);
```

```
EFFECT_IDENTITY_SCHEMA                 = "{account_id}:{message_id}"   (PK: consumer_id, effect_id)
EFFECT_IDENTITY_INCLUDES_EVENT_CURSOR  = NO
EFFECT_IDENTITY_INCLUDES_MESSAGE_ID    = YES
EFFECT_IDENTITY_INCLUDES_MEDIA_ID      = NO
EFFECT_IDENTITY_INCLUDES_CHAT_SCOPE    = NO
```

Two notes that matter downstream:

- `compute_effect_id()` accepts an `event_type` argument and **ignores it**. The signature is
  misleading: `message.created` and `message.updated` for the same message collide on one key by
  design.
- `account_id` is not a chat-scoped key, and the `message_id` namespace is already account-scoped
  in practice, so cross-chat collision is not a concern here.

**Are the W1, W2 and historical-delivered identities for the same message identical?**

```
W1 / W2 / historical-delivered identity equality = YES
```

All three resolve to the same `f"{account_id}:{message_id}"`. The W1 re-projection at
`273845..274304`, the W2 re-projection at `274308..274727`, and the original delivery recorded in
the ledger therefore land on **exactly the same ledger row**. This is why the ledger is able to
suppress W1/W2 for the 69 messages EFB already acted on — and why it is *unable* to suppress
anything for the other 345 (see §7).

---

## §6 §B5 — Ledger dedupe vs media validation ordering (Path A / Path B)

**Answer: Path A.** The ledger dedupe runs **before** media validation.

```
LEDGER_DEDUPE_BEFORE_MEDIA_VALIDATION = YES
MEDIA_VALIDATION_BEFORE_LEDGER_DEDUPE = NO
```

**Code locations** — `efb_wechat_comwechat_slave/ComWechat.py`, `_handle_message_event()`
(defined at L893), in execution order:

| Line | Statement | Role |
|---|---|---|
| 792 | `def _is_media_message(...)` → `type in {"image","sticker","voice","video","file"}` | the `is_media` predicate |
| 922 | `self.effect_ledger.compute_effect_id(account_id, core_message_id)` | effect identity |
| 927 | `self.effect_ledger.get_effect_status(self.consumer_id, effect_id)` | ledger lookup |
| **932** | `if current_status == STATE_DELIVERED and (event_type == "message.created" or is_media): … return` | **DELIVERED suppression** |
| 936 | `if current_status in {STATE_RESERVED, STATE_UNCERTAIN}: … return` | fail-closed suppression |
| **943** | `if current_status == STATE_MEDIA_FAILED: … return` | **MEDIA_FAILED suppression** |
| **948** | `efb_msg = self.message_builder.build(message, chat)` | **media validation happens HERE** |
| 962 | `reserve_pending_effect(...)` | PENDING_MEDIA → RESERVED |
| 968 | `reserve_effect(...)` | first reservation |
| 996 | `efb_msg.edit = event_type == "message.updated" and current_status != STATE_PENDING_MEDIA` | edit flag |
| 999 | `self._deliver_message(efb_msg)` | **external side effect** |
| 1040 | `mark_delivered(...)` | ledger finalisation |
| 1048 | `def _retry_pending_media(...)` | media.ready / timer promotion |

`MediaPendingError` / `MediaPermanentError` can only be raised inside
`CoreMessageBuilder.build()` (`CoreMessage.py`), which is invoked at L948 — strictly after all
three ledger suppression branches. Therefore an already-`DELIVERED` effect never reaches media
validation, and a W1 payload missing `media_role`/`media_status` cannot produce a spurious
`MediaPermanentError` for a message that was already delivered.

**The two pre-conditions that break idempotency** — both are visible in the same function:

1. **L932 is gated on `(event_type == "message.created" or is_media)`.** For a
   `message.updated` whose `type` is not in the media set (here: the 2 `system` events), the
   `DELIVERED` branch **does not fire**. Execution falls through to L948, L996 sets `edit = True`,
   and L999 delivers again. There is no other guard.
2. **There is no "have I seen this identity before?" check for an unknown identity.** For a
   `message.updated` with `current_status is None`, all three suppression branches are skipped and
   the event is processed exactly like a first delivery. A re-projection of a message EFB never
   delivered is indistinguishable from a genuine first projection.

---

## §7 §B6 — Offline dry classification of W1 and W2

Method: each of the 828 `message.updated` events was replayed through the frozen decision logic
(read-only), with the **production ledger** as the authority for `current_status`. Classification
uses stable identity only — never message text, time proximity or content similarity.

### §7.1 Fine-grained buckets (`message.updated` only)

| Bucket | W1 `273845..274304` | W2 `274308..274727` |
|---|---|---|
| `SUPPRESSED_ALREADY_DELIVERED` (ledger `DELIVERED`) | 42 | 42 |
| `SUPPRESSED_MEDIA_FAILED` (ledger `MEDIA_FAILED`) | 27 | 27 |
| `SUPPRESSED_FAILCLOSED` (ledger `RESERVED`/`UNCERTAIN`) | 0 | 0 |
| `SUPPRESSED_OUTGOING_ECHO` | 0 | 0 |
| `WOULD_NEW_DELIVERY` | 2 | 6 |
| `WOULD_MEDIA_FAILED` | 343 | 9 |
| `WOULD_PENDING_MEDIA` | 0 | 330 |
| `UNKNOWN` | 0 | 0 |
| **total** | **414** | **414** |

### §7.2 Mapped onto the requested taxonomy (including §9's `media.ready`)

| Bucket | W1 | W2 |
|---|---|---|
| `SUPPRESSED_ALREADY_DELIVERED` | 42 | 42 |
| `NO_EXTERNAL_EFFECT` | 40 | 27 |
| `WOULD_NEW_DELIVERY` | 2 | 6 |
| `WOULD_MEDIA_FAILED` | 343 | 9 |
| `WOULD_PENDING_MEDIA` | 0 | 330 |
| `UNKNOWN` | 0 | 0 |
| **total** | **427** | **414** |

`NO_EXTERNAL_EFFECT(W1) = 27` (`MEDIA_FAILED`-suppressed) `+ 13` (the `media.ready` no-ops of §9).
`NO_EXTERNAL_EFFECT(W2) = 27`. W1's total is `414 + 13 = 427` because all 13 `media.ready` events
fall in W1; W2 contains none.

### §7.3 Identity join against the production ledger

```
LEDGER_ROWS                 = 417
W1: TOTAL 414  IN_LEDGER 69  NOT_IN_LEDGER 345
W2: TOTAL 414  IN_LEDGER 69  NOT_IN_LEDGER 345
IN_LEDGER status split      = 42 DELIVERED / 27 MEDIA_FAILED   (identical in W1 and W2)
NEW3_IN_LEDGER              = (empty — none of 274305/274306/274307 has any ledger row)
NONMEDIA_NOLEDGER           = 2 per window (the two `system` events)
```

The arithmetic closes exactly, which is an independent check on the classifier:

```
W2 ledger-absent 345  = 343 media  +  2 system
W2 media ledger-absent 343 = 4 (image|original|ready)  +  9 (thumbnail ∪ decode_failed)  +  330 (pending group)
W2 ledger-present   69 = 0 (ready group)  +  3 (thumbnail ∪ decode_failed)  +  66 (pending group)
```

### §7.4 Why W1 and W2 fail differently

**W1 fails loudly.** Every one of the 412 media-typed W1 events carries `media_id` but **no**
`media_role`. `CoreMessageBuilder.build()` evaluates
`if media_role != "original": raise MediaPermanentError(...)` with `media_role == ""`, so the
pre-F3 payload shape converts 343 ledger-absent media updates directly into
`mark_media_failed()` writes. This is the pre-F3 failure mode being re-run, and it is the exact
question the sealed predecessor left open at its §11 disclosure #5 — **now resolved: the answer is
that replaying W1 writes new `MEDIA_FAILED` rows.**

**W2 fails quietly and more broadly.** W2's payloads are well-formed (F3 fields present), so the
330 pending-group events take the `MediaPendingError` path into `_defer_media()` →
`mark_media_pending()`, **inserting 330 new `PENDING_MEDIA` rows** and enrolling 330 historical
messages into the retry machinery — for messages whose `created_at` predates EFB's governed
`initial_cursor = 272037` by days. The 9 thumbnail/decode_failed events become `MEDIA_FAILED`, and
6 events would produce genuine external deliveries.

**Sequential replay (the realistic scenario).** Because W1 shadows W2 on the same identities:

| Step | Effect |
|---|---|
| 1. W1 (460 events) | **+343 `MEDIA_FAILED` rows**; **2 external deliveries** (the two `system` revoke notices); 13 `media.ready` no-ops |
| 2. NEW_BUSINESS_1 (3) | **2 deliveries** (274305, 274306); 274307 → **+1 `PENDING_MEDIA` row** (§8) |
| 3. W2 (420 events) | the 343 media now read `MEDIA_FAILED` ⇒ suppressed; the 2 `system` have still **no** ledger row ⇒ **2 duplicate deliveries**; 0 new pending rows |

Net sequential outcome: **344 new ledger rows**, **6 external Telegram deliveries**, of which
**2 are duplicates** of messages delivered seconds earlier in the same replay.

---

## §8 §B7 — The three new business events

All three are genuine first-ever projections of their identities, at cursors **above** the
checkpoint `273844`, arriving after EFB stopped.

```
CREATED 274305  key=f-live-a:786c0fb7…b063  type=link  in_414=0
CREATED 274306  key=f-live-a:48139a58…b65df type=text  in_414=0
CREATED 274307  key=f-live-a:8745c1a9…95d79 type=file  in_414=0
```

`in_414 = 0` for all three: none belongs to the 414-identity re-projection set. `NEW3_IN_LEDGER`
is empty: no ledger row exists for any of them. `NEW_BUSINESS_EVENT = YES` for all three.

| Cursor | Account / chat | `created_at` | type | `media_id` | EFB dry-run outcome |
|---|---|---|---|---|---|
| 274305 | f-live-a / `38808757431@chatroom` | `2026-09-17T00:29:54Z` | link | `""` | not media → `MsgType.Link` → delivered |
| 274306 | f-live-a / `38808757431@chatroom` | `2026-09-17T00:30:06Z` | text | `""` | not media → `MsgType.Text` → delivered |
| 274307 | f-live-a / `38808757431@chatroom` | `2026-09-17T00:41:14Z` | **file** | **`""`** | **is media** → `MediaPendingError` |

```
274305_WOULD_DELIVER = YES
274306_WOULD_DELIVER = YES
274307_WOULD_DELIVER = NO      (deferred as PENDING_MEDIA, never deliverable)
```

`274307` is a quoted-message payload typed `file` whose `media_id` is empty. In
`CoreMessageBuilder.build()` the media block raises
`MediaPendingError(f"{msg_type} original media reference is not available")` on
`if not media_id:` — evaluated **before** the `media_role` check. `_handle_message_event`
therefore routes it to `_defer_media()` and writes a `PENDING_MEDIA` row. The scheduled retry
cannot succeed either, because `_retry_pending_media()` re-injects the same payload with an empty
`media_id`; after `media_retry_max_attempts` (20) or the 300 s deadline it transitions to
`MEDIA_FAILED`. This is EFB's designed fail-closed behaviour, **not** a replay artifact — but it
is a genuine Core-side data gap (a `file`-typed message published with no media reference) that
deserves its own work item. It does not change the fence decision: `274307` is real new business
and must **not** be skipped.

**No replay suppression rule misjudges any of the three.** They have no ledger row, so they hit
none of the suppression branches; `_is_media_message` is evaluated on their own `type`. They are
indistinguishable from a normal first delivery, which is the correct behaviour for them — and
simultaneously the reason the fence at `274727` is unusable (§10).

---

## §9 §B8 — The 13 `media.ready` events

All 13 fall in **W1**; W2 contains none.

| Cursor | Account | role | status | occurred_at |
|---|---|---|---|---|
| 273876 | f-live-a | original | ready | `2026-09-17T00:09:09Z` |
| 273877–273885 | f-live-a | thumbnail ×9 | ready | `2026-09-17T00:09:09Z` |
| 274273 | testB | original | ready | `2026-09-17T00:09:18Z` |
| 274274 | testB | original | ready | `2026-09-17T00:09:18Z` |
| 274275 | testB | original | ready | `2026-09-17T00:09:18Z` |

(10 f-live-a = 1 original + 9 thumbnail, plus 3 testB original. All 13 sit inside the W1 burst
window `00:09:09Z–00:09:18Z` — the sealed predecessor's statement on this is confirmed correct.)

**Handling path.** `_handle_event` routes `media.ready` to
`_retry_pending_media(account_id=…, ready_media=media)`, which calls
`self.effect_ledger.pending_media(consumer_id, due_before=None, media_id=<media_id>)`. It acts only
on rows already in `PENDING_MEDIA` for that `media_id`. **The production ledger has zero
`PENDING_MEDIA` rows** (§4), so every lookup returns an empty list and the handler is a no-op.

The `media.ready` payload also carries **no message linkage** — the raw shape is
`{"media":{"account_id","disposition","filename","media_id","mime_type","role","status"}}`, with no
`message_id` and no `chat_id` — so a `media.ready` event cannot itself create pending state; it can
only promote an existing pending row.

```
W1_MEDIA_READY_TOTAL                  = 13
W1_MEDIA_READY_SUPPRESSED             = 13
W1_MEDIA_READY_WOULD_EXTERNAL_EFFECT  = 0
W1_MEDIA_READY_WOULD_MUTATE_PENDING_STATE = 0
W2_MEDIA_READY_TOTAL                  = 0
W2_MEDIA_READY_WOULD_EXTERNAL_EFFECT  = 0
W2_MEDIA_READY_WOULD_MUTATE_PENDING_STATE = 0
```

**Would skipping W1 break real pending-media state? NO.** Three independent reasons:

1. There are zero `PENDING_MEDIA` rows in the production ledger, so no effect is waiting on a
   promotion that W1 could supply.
2. `media.ready` cannot create pending state — it only promotes it.
3. `poll_once()` calls `_retry_pending_media()` unconditionally at the top of every poll with
   `due_before=now`, so pending media is retried on a timer regardless of `media.ready`. Skipping
   W1's `media.ready` events would forgo only the *immediate* promotion, never the eventual retry.

---

## §10 §B9 — Three-way decision

```
DECISION_CASE                  = C
CHECKPOINT_MUTATION_PERFORMED  = NO
CHECKPOINT_CHANGE_REQUIRED     = NO
SURGICAL_FENCE_CANDIDATE       = NONE
EFB_CODE_CHANGE_REQUIRED       = YES
```

**Case A is excluded.** The current checkpoint `273844` is **not** already safe. W1 alone would
write 343 new `MEDIA_FAILED` rows and emit 2 external deliveries; W2 would write 330 new
`PENDING_MEDIA` rows and 9 `MEDIA_FAILED` rows and emit 6 deliveries. The next round may **not**
simply start from `273844`.

**Case B is excluded.** `SURGICAL_FENCE_CANDIDATE = 274304` would isolate W1 correctly and preserve
`274305..274307` — but W2 is **also** unsafe, so fencing only W1 does not make the range safe. The
candidate value is therefore reported as `NONE` rather than `274304`.

**Case C applies, and the reasoning is structural, not incidental.** The range cannot be made safe
by choosing a checkpoint value:

- Any resume point `≤ 274304` includes W1 → unsafe.
- Any resume point `∈ [274308, 274727]` includes W2 → unsafe.
- Any resume point `> 274727` skips **both** the re-projections *and* the 3 new business events at
  `274305..274307` — i.e. it buys safety by silently dropping real user messages. That is exactly
  the failure mode the instruction forbids: *checkpoint-skipping must not be used to dodge a code
  problem, and real new business must not be skipped to avoid Telegram re-sends.*
- `274305..274307` and `274308..274727` are adjacent and must be treated oppositely, so **no single
  cursor separates them**.

Because the non-idempotent events (`message.updated` at cursors above the checkpoint) must be
consumed by any future EFB run in normal operation anyway, the only correct remedy is **event-level
idempotency inside EFB**. This round does not implement it and does not authorize it; it is
recorded as a required, separately-authorized code change.

**Minimal defect statement for the fix round** (findings only — nothing implemented):

1. **Unknown-identity `message.updated` is treated as a first delivery.** There is no
   "have I already projected this identity?" record. The ledger's identity is
   `account_id:message_id` with no event-type or cursor component, so a re-projection of an
   *undelivered* message is indistinguishable from a first projection. A candidate guard: a
   `message.updated` for an identity with no prior ledger/mapping record should be recorded as a
   projection-only observation rather than dispatched — consistent with `efb_msg.edit = True`,
   which already presupposes the message is known to the master.
2. **The `DELIVERED` suppression is gated on `is_media`** (ComWechat.py L932), leaving non-media
   `message.updated` events entirely unprotected. Removing the
   `(event_type == "message.created" or is_media)` gate would make the 2 `system` events
   idempotent.
3. **Core-side option worth considering:** an explicit re-projection marker on re-emitted events
   (e.g. `reprojection: true` / `origin_cursor`) would let any consumer distinguish a
   re-projection from a first projection without inference. This would have prevented the whole
   class of defect at the producer.

---

## §11 §B10 — `274728 .. current head`

```
range scanned                  = 274728 .. 274764   (37 events)
POST_274727_NEW_BUSINESS_EVENT_COUNT = 37
POST_274727_NEW_BUSINESS_EVENT_TYPES = message.created 37   (nothing else)
POST_274727_ACCOUNT               = f-live-a, all direction=incoming
POST_274727_CREATED_AT_RANGE      = 2026-09-17T02:29:20Z .. 2026-09-17T03:28:34Z
```

Composition by type: **32 `text`, 3 `file` (`274737`, `274739`, `274750`), 2 `image` (`274732`,
`274747`)** — all `message.created`. The two image events carry `media_role = original`,
`media_status = original_pending` with a populated `media_id`, i.e. normal in-flight media.

Classification: every one of the 37 is `FUTURE_NORMAL_CONSUMPTION`. They are genuine new business
arriving while EFB is stopped, and they are **not** an advance target, **not** a fence candidate and
**not** a reason to move any checkpoint.

The head advanced from `274760` (previous round) to `274764` during this round and continues to
advance. **The head must never again be used as a checkpoint target** — it is a moving value, and
any checkpoint pinned to a sampled head value will silently skip whatever arrives next.

---

## §12 §B11 — Governance counters

```
ACTIVE_CORE_RAW_SQLITE_READS                 = 0
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS         = 0
CORE_MUTATION                                = 0
CORE_CHECKPOINT_MUTATION                     = 0
CORE_RECEIPT_ACK_EVENT_WRITES                = 0
EFB_LEDGER_MUTATION                          = 0
EFB_CHECKPOINT_MUTATION                      = 0
EFB_MAPPING_MUTATION                         = 0
EFB_CURSOR_FILE_MUTATION                     = 0
EFB_EFFECTLEDGER_SIDECAR_DELETIONS           = 0
EFB_STARTED                                  = NO
AGENT_STARTED                                = NO
PRODUCTION_SERVICE_RESTART                   = 0
TELEGRAM_SEND                                = 0
WECHAT_SEND                                  = 0
HISTORICAL_MEDIA_FAILED_ROWS                 = 42   (unchanged)
HISTORICAL_MEDIA_FAILED_ROWS_REWRITTEN       = 0
F1_F2_RESULT_REPLAY_OR_RESET                 = 0
EFB_FUNCTIONAL_CANDIDATE_CHANGED             = NO

GUARD_HOST_COMMAND_LOG                       = PASS  (findings: [], all three guards PASS)
GUARD_CONTROL_FIXTURE                        = 1 expected finding (positive control only)
GUARD_SELFTEST                               = CI_POSITIVE_TESTS PASS / CI_NEGATIVE_TESTS PASS

CHECKPOINT_PRE                               = 273844
CHECKPOINT_POST                              = 273844   (byte-identical, updated_at unchanged)
EFB_LEDGER_SHA256_PRE                        = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd
EFB_LEDGER_SHA256_POST                       = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd
EFB_LEDGER_WAL_BYTES                         = 0   (pre and post)

SCRATCH_RESIDUE                              = 0
  /dev/shm/efbaudit  removed, /dev/shm entry count = 0
  /tmp/efbaudit      removed
  /tmp/efbchk        removed
  /tmp/efbv          removed
  /tmp/efbsrc        RETAINED (read-only extraction of the frozen candidate source tree;
                     contains no production data; re-creatable via docker cp)
```

---

## §13 §B12 — Return block

```
ROUND                                     = RC.14 EFB Post-F3 Replay / EffectLedger Idempotency Audit
ROUND_TYPE                                = STRICT READ-ONLY
CORE                                      = RUNNING / HEALTHY
AGENT                                     = STOPPED
EFB                                       = STOPPED
FROZEN_EFB_SOURCE_COMMIT                  = 91a69cef323d120f0e32196917a630d2cf3baa88
FROZEN_EFB_IMAGE_DIGEST                   = sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241

CURRENT_EFB_CHECKPOINT                    = 273844
CURRENT_HEAD_AT_OPEN                      = 274764
CURRENT_HEAD_AT_CLOSE                     = 274764
GAP_RANGE                                 = 273845..274727
GAP_TOTAL_EVENTS                          = 883
GAP_CONTIGUOUS                            = YES
W1_RANGE                                  = 273845..274304
W1_TOTAL                                  = 460
NEW_BUSINESS_1_RANGE                      = 274305..274307
NEW_BUSINESS_1_TOTAL                      = 3
W2_RANGE                                  = 274308..274727
W2_TOTAL                                  = 420
BOUNDARY_OFF_BY_ONE_CORRECTION            = YES  (sealed W1 273845..274307 == W1_this_round ∪ NEW_BUSINESS_1)
MESSAGE_UPDATED_TOTAL                     = 828   (W1 414 + W2 414; 414 distinct identities)

CHECKPOINT_274304_PRESERVES_274305_274307 = YES
CHECKPOINT_274307_PRESERVES_274305_274307 = NO
RESUME_POINT_IS_LOCAL_CURSOR_FILE         = YES  (Core checkpoint row is never read for resumption)

EFB_LEDGER_ROWS                           = 417
EFB_LEDGER_STATUS                         = DELIVERED 375 | MEDIA_FAILED 42 | RESERVED 0 | UNCERTAIN 0 | PENDING_MEDIA 0
EFB_LEDGER_HISTORICAL_MEDIA_FAILED        = 42   (preserved)
EFB_LEDGER_MUTATION                       = 0
EFB_LEDGER_SHA256_PRE                     = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd
EFB_LEDGER_SHA256_POST                    = 3e0853fb1e74463fd51420870022c93116a651678093f02c548adc8adaaa0fcd

EFFECT_IDENTITY_SCHEMA                    = "{account_id}:{message_id}"  PK (consumer_id, effect_id)
EFFECT_IDENTITY_INCLUDES_EVENT_CURSOR     = NO
EFFECT_IDENTITY_INCLUDES_MESSAGE_ID       = YES
EFFECT_IDENTITY_INCLUDES_MEDIA_ID         = NO
EFFECT_IDENTITY_INCLUDES_CHAT_SCOPE       = NO
W1_W2_HISTORICAL_IDENTITY_EQUALITY        = YES

LEDGER_DEDUPE_BEFORE_MEDIA_VALIDATION     = YES
MEDIA_VALIDATION_BEFORE_LEDGER_DEDUPE     = NO
SUPPRESSION_PATH                          = PATH_A
CODE_LOCATIONS                            = ComWechat.py L922 compute_effect_id / L927 get_effect_status /
                                            L932 DELIVERED-suppress / L936 fail-closed /
                                            L943 MEDIA_FAILED-suppress / L948 build() (media validation) /
                                            L962 reserve_pending_effect / L968 reserve_effect /
                                            L996 edit flag / L999 deliver / L1040 mark_delivered

W1_SUPPRESSED_ALREADY_DELIVERED           = 42
W1_SUPPRESSED_MEDIA_FAILED                = 27
W1_NO_EXTERNAL_EFFECT                     = 40
W1_WOULD_NEW_DELIVERY                     = 2
W1_WOULD_MEDIA_FAILED                     = 343
W1_WOULD_PENDING_MEDIA                    = 0
W1_UNKNOWN                                = 0
W2_SUPPRESSED_ALREADY_DELIVERED           = 42
W2_SUPPRESSED_MEDIA_FAILED                = 27
W2_NO_EXTERNAL_EFFECT                     = 27
W2_WOULD_NEW_DELIVERY                     = 6
W2_WOULD_MEDIA_FAILED                     = 9
W2_WOULD_PENDING_MEDIA                    = 330
W2_UNKNOWN                                = 0
W1_IN_LEDGER                              = 69
W1_NOT_IN_LEDGER                          = 345
W2_IN_LEDGER                              = 69
W2_NOT_IN_LEDGER                          = 345
SEQUENTIAL_REPLAY_NEW_LEDGER_ROWS         = 344
SEQUENTIAL_REPLAY_EXTERNAL_DELIVERIES     = 6
SEQUENTIAL_REPLAY_DUPLICATE_DELIVERIES    = 2

NEW_BUSINESS_EVENT_274305                 = YES
NEW_BUSINESS_EVENT_274306                 = YES
NEW_BUSINESS_EVENT_274307                 = YES
274305_WOULD_DELIVER                      = YES
274306_WOULD_DELIVER                      = YES
274307_WOULD_DELIVER                      = NO   (type=file with empty media_id -> MediaPendingError)
NEW3_IN_LEDGER                            = (empty)
NEW3_MISJUDGED_AS_DUPLICATE               = 0

W1_MEDIA_READY_TOTAL                      = 13
W1_MEDIA_READY_SUPPRESSED                 = 13
W1_MEDIA_READY_WOULD_EXTERNAL_EFFECT      = 0
W1_MEDIA_READY_WOULD_MUTATE_PENDING_STATE = 0
W2_MEDIA_READY_TOTAL                      = 0
SKIPPING_W1_BREAKS_PENDING_MEDIA_STATE    = NO

DECISION_CASE                             = C
CHECKPOINT_MUTATION_PERFORMED             = NO
CHECKPOINT_CHANGE_REQUIRED                = NO
SURGICAL_FENCE_CANDIDATE                  = NONE
EFB_CODE_CHANGE_REQUIRED                  = YES
CHECKPOINT_ADVANCE_SAFE                   = NO

POST_274727_NEW_BUSINESS_EVENT_COUNT      = 37
POST_274727_TREATMENT                     = FUTURE_NORMAL_CONSUMPTION
HEAD_USED_AS_CHECKPOINT_TARGET            = NO

ACTIVE_CORE_RAW_SQLITE_READS              = 0
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS      = 0
PRODUCTION_SERVICE_RESTART                = 0
TELEGRAM_SEND                             = 0
WECHAT_SEND                               = 0
EFB_STARTED                               = NO
AGENT_STARTED                             = NO
SCRATCH_RESIDUE                           = 0
GUARD                                     = PASS

ACTION                                    = STOP
```

---

## §14 STOP

This round ends here.

- No checkpoint was advanced. `273844` is byte-identical at open and close.
- EFB was **not** started. Agent was **not** started.
- No Telegram or WeChat send occurred. No Core, ledger, mapping or cursor file was mutated.
- No F1/F2 historical result was replayed, reset or cleaned. The 42 historical `MEDIA_FAILED` rows
  are intact.
- No taskbook authorizing a checkpoint advance was produced, because no advance is safe
  (`CHECKPOINT_ADVANCE_SAFE = NO`).
- The required remedy is an **event-level idempotency guard inside EFB** (Case C). That change is
  not implemented here and is not authorized by this round; it requires its own taskbook and
  Operator authorization.
