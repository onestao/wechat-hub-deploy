# RC.14 Core File / Voice Media Reference — Engineering Result

```text
RESULT_ID        = RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_ENGINEERING
WORK_PACKAGE     = RC.14 Core Media Reference Coverage — File / Voice Engineering
DATE             = 2026-09-17  (host UTC)
PHASE            = ENGINEERING / PRE-DEPLOYMENT
VERDICT          = ENGINEERING COMPLETE — AWAITING DEPLOYMENT AUTHORIZATION
ACTION           = STOP
```

## 0. Return block

```text
BASE_CORE_SOURCE                    = 6538f79a664a325543c19391cc14601d282e07a4
NEW_CORE_SOURCE_COMMIT              = 9434e915b78b2eb5471acf282d4e223c03e8d83a
NEW_CORE_IMAGE_DIGEST               = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
NEW_CORE_OCI_REVISION               = 9434e915b78b2eb5471acf282d4e223c03e8d83a
NEW_CORE_OCI_REVISION_EQUALS_SOURCE = YES

FILE_SOURCE_PATH_AVAILABLE          = YES
VOICE_SOURCE_PATH_AVAILABLE         = NO   (no voice file exists anywhere on disk; see §4)
FILE_ORIGINAL_BYTES_AVAILABLE       = YES
VOICE_ORIGINAL_BYTES_AVAILABLE      = YES  (SILK blob in the decrypted VoiceInfo table)

FILE_MEDIA_REFERENCE_FIX            = IMPLEMENTED
VOICE_MEDIA_REFERENCE_FIX           = IMPLEMENTED
FILE_MEDIA_READY_SEMANTICS          = ORIGINAL_COPIED_VERBATIM_SIZE_VERIFIED
VOICE_MEDIA_READY_SEMANTICS         = ORIGINAL_SILK_VERBATIM_LENGTH_VERIFIED_NO_TRANSCODE

274307_CLASSIFIED_AS_NEW_BUSINESS   = YES
274307_DUPLICATE                    = NO
274307_MEDIA_ID_RESOLVABLE          = NOT_PROVABLE_OFFLINE
274307_IS_A_GENUINE_FILE            = NO   (appmsg type 57, a quote reply)

EFB_FILE_MEDIA_CONTRACT_COMPATIBLE  = PASS
EFB_VOICE_MEDIA_CONTRACT_COMPATIBLE = PASS

IMAGE_STICKER_VIDEO_REGRESSION      = PASS
F3_MESSAGE_PROJECTION_REGRESSION    = PASS
THUMBNAIL_SAFETY_REGRESSION         = PASS

FULL_TESTS                          = Ran 268 tests / 0 FAIL / 0 ERROR   (CI, authoritative)
CI_RUN                              = 35215908801
PUBLISH_RUN                         = 35216281684

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0

PRODUCTION_CORE_MUTATION            = NO
PRODUCTION_EFB_TOUCHED              = NO
PRODUCTION_AGENT_TOUCHED            = NO

DEPLOYMENT_TASKBOOK_SHA256          = 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae

CORE_MEDIA_REFERENCE_ENGINEERING    = PASS
CORE_MEDIA_REFERENCE_CANDIDATE_READY = YES
CORE_MEDIA_REFERENCE_LIVE_AUTHORIZATION_READY = NO

ACTION = STOP
```

### 0.1 Historical facts preserved (not modified)

```text
FILE_MEDIA_REFERENCE_GAP_CONFIRMED = YES
CORE_FOLLOWUP_REQUIRED             = YES
REAL_EVENT_CURSOR                  = 274307
REAL_EVENT_TYPE                    = file
REAL_EVENT_MEDIA_ID                = empty
MEDIA_FAILED historical histogram  = image 18 / file 14 / sticker 9 / voice 1   (42 total)
```

These were **extended**, never rewritten. §7 adds the mechanism behind the historical
`file` count; the sealed census fixture was verified byte-identical
(`sha256 697c207f1ceb073c40fa63743efe53216f279a0974bd58af5078d3287373df3c`).

---

## 1. Root-cause audit

### 1.1 The filter is real — and it is not the whole cause

Confirmed at the deployed revision `6538f79`:

```python
# memory/media_sync.py::sync_media()
SELECT message_uid, chat_username, local_id, type_label, message_content
FROM messages
WHERE type_label IN ('image', 'sticker', 'video')
```

and the dispatcher had only `sync_image` / `sync_sticker` / `sync_video`. So no
`message_media` row was ever written for a `file` or `voice` message;
`core/normalize.py` attaches the media reference by joining that table, so
`media_id` was emitted empty and every consumer failed closed permanently.

### 1.2 The upstream label is over-broad

`link_or_file` is the staging label for WeChat local type **49**, which is *every*
`appmsg`: url shares (5), file transfers (6), merged chat records (19), quote replies
(57) and others. `core/normalize.py` mapped `link_or_file -> file` (a **media** type)
and only overrode to `link` when a url was present.

Measured on the production account staging store (`f-live-a`), by the **outer appmsg
`<type>`** and whether a non-empty `<url>` exists:

```text
appmsg type 57 (quote reply)          empty url   110
appmsg type 19 (merged chat records)  empty url     2
appmsg type 62 (other)                empty url     1
appmsg type  6 (file transfer)        empty url     2      <- the only genuine files
appmsg type  4 / 5 / 51 / 68 / 19     real url     19
                                          total    134
```

```text
currently projected as `file`  = 115
genuine file transfers within that set = 2
non-file appmsg subtypes projected as `file` = 113
```

So the observed production blocker was **not** only a missing media pipeline. 113 of
115 messages projected as `file` are not files at all: they were demanded to carry a
media reference that can never exist. That is the mechanism behind the historical
`MEDIA_FAILED file = 14`.

### 1.3 Required answers

```text
FILE_SOURCE_PATH_AVAILABLE              = YES
    <wechat_base_dir>/msg/file/<YYYY-MM>/<original filename>, readable from the
    Core container (config/ is mounted read-only at /app/config).
VOICE_SOURCE_PATH_AVAILABLE             = NO
    There is no voice file anywhere on disk: no msg/voice, no Voice/ directory
    under msg/attach/*/, and a filesystem search for *.silk/*.amr/*.aud/*.mp3/*.wav
    returned nothing. Voice exists only as a blob.

FILE_ORIGINAL_BYTES_AVAILABLE           = YES
    Confirmed end to end on a real message: appmsg type 6, title
    send_file_1788297195381_F-LIVE-20260901T210920Z-A-FILE.txt, declared totallen 32,
    and msg/file/2026-09/<same name> present at exactly 32 bytes.
VOICE_ORIGINAL_BYTES_AVAILABLE          = YES
    The decrypted shard message/media_0.db holds VoiceInfo with 4 rows and 40,084
    bytes of SILK payload (magic 02 23 21 53 49 4C 4B 5F = "\x02#!SILK_"). Each row's
    byte length matches the message's declared `length` attribute exactly
    (6196 / 16132 / 13234 / 4522), which is the integrity signal used in §4.

FILE_MEDIA_ID_CREATION_BLOCKED_BY_FILTER  = YES
VOICE_MEDIA_ID_CREATION_BLOCKED_BY_FILTER = YES
    Both were excluded by the SELECT above. For `file` the filter was additionally
    masked by the classification defect of §1.2.
```

The filter was **not** changed on historical inference alone; every value above was
measured on the production account staging store at the deployed revision.

---

## 2. Safety requirement — how "ready" is decided

A media row is published as `media_role = original` / `media_status = ready` **only**
when the genuine original artifact has been located, integrity-checked and
materialised. Concretely, for every new type:

| Prohibited | How it is prevented |
| --- | --- |
| thumbnail fallback posing as original | files and voice have **no** thumbnail path at all; only `msg/file/**` (files) and `VoiceInfo.voice_data` (voice) are ever consulted, and neither is a thumbnail cache |
| empty file posing as ready | a located file with `st_size == 0` is rejected (`missing_file`); an empty `voice_data` blob is rejected |
| temp path missing yet published ready | the artifact is written atomically and the **copy** is size-verified before the row is built; a failed copy yields `missing_file` |
| deciding ready from `type_label` alone | the decision needs the parsed appmsg subtype, the declared size, a located candidate, a matching size and a successful copy |
| inferring role from the filename | role is derived from `media_type` (file/voice are always `original`; video stays `thumbnail`), never from a name |
| fabricating a `media_id` for absent content | a not-ready row is never persisted into Core's `media` table, so `GET /v1/media/{id}` returns 404 and no bytes are served |

When the original is unavailable the status is a truthful non-ready value from the
existing frozen vocabulary (`missing_file`, `missing_metadata`) and the role remains
`original` — a *pending original*, which is exactly the F2 contract already used for
images, never a thumbnail substitute.

---

## 3. File semantics

| Item | Value |
| --- | --- |
| original path source | `<wechat_base_dir>/msg/file/<YYYY-MM>/<filename>`, month derived from the message timestamp (`0 / -31 / +31` days), with a bounded walk of `msg/file` as fallback |
| filename | `appmsg/title`, accepted only after a strict safety check (§3.1) |
| size | `appattach/totallen`; the located candidate must match it exactly when present |
| MIME / content type | `mimetypes.guess_type(filename)`, falling back to `application/octet-stream` |
| `media_id` assignment time | at projection: `media_id` is the message's stable `message_uid`, materialised only once the row is `ready` |
| ready transition | first cycle in which a size-verified original is located and copied |
| `/v1/media/{id}` semantics | unchanged: serves the bytes with `Content-Type`, `X-Media-Id`, `X-Media-Role: original`, `X-Media-Status: ready` |

Target behaviour, now satisfied:

```text
message.media_id     != empty
message.media_role   =  original
message.media_status =  ready
GET /v1/media/{id}   -> original bytes, X-Media-Role: original, X-Media-Status: ready
```

### 3.1 Filename safety

The title comes from message XML controlled by the remote party. A value containing a
path separator, `..`, a drive qualifier, a control character, or exceeding 200
characters is **refused** (`missing_metadata`) rather than silently reduced to its
basename: a renamed file could otherwise match a different artifact sharing the
basename. Verified against `../../etc/passwd`, `..\..\evil.txt`, `C:evil.txt`,
`a/b.txt` and whitespace-only titles.

---

## 4. Voice semantics

Audited, not assumed:

| Item | Finding |
| --- | --- |
| source / path | none on disk. The original is a BLOB column, `VoiceInfo.voice_data`, in the **decrypted** shard `decrypted/message/media_0.db` |
| codec / container | SILK, `voicemsg voiceformat="4"`; blob magic `\x02#!SILK_V3` |
| extension | none upstream; the artifact is materialised as `<media_id>.silk` |
| bytes availability | 4 rows, 40,084 bytes total, each length-equal to the message's declared `length` |
| ready lifecycle | keyed on `(chat_username, create_time, local_id)` resolved through `Name2Id`; ready only when the blob exists **and** its length equals the declared length |

```text
VOICE_MEDIA_SUPPORT          = POSSIBLE  (the upstream does hold readable originals)
VOICE_MEDIA_READY_SEMANTICS  = ORIGINAL_SILK_VERBATIM_LENGTH_VERIFIED_NO_TRANSCODE
VOICE_MIME_TYPE              = audio/silk
VOICE_TRANSCODE              = NOT PERFORMED
```

**Disclosed limitation.** The image installs only `pycryptodome`, `zstandard` and
`Pillow`; there is no SILK decoder (no `pysilk`/`ffmpeg`), and the frozen EFB
candidate contains no transcode path either. The Core contract is satisfied — the
genuine original is retrievable byte-for-byte — but whether the downstream consumer
can *deliver* a SILK container (Telegram voice notes require OGG/Opus) was **not**
verified offline. This is a live-round risk, not a Core contract gap. If a live round
fails on voice, the correct fix direction is a transcode step in the image, not a
change to the media-reference contract.

Voice was **not** reported as `NOT_CURRENTLY_POSSIBLE`: that verdict is reserved for
the case where the upstream holds no readable voice original, which is not the case
here.

---

## 5. Minimal scope — what actually changed

```text
git diff --stat 6538f79..9434e91
 core/normalize.py                                  |  27 +++-
 memory/media_sync.py                               | 332 ++++++++++++++++++++-
 memory/message_parse.py                            |  12 ++
 core/tests/test_rc14_file_voice_media_reference.py | new  (20 tests)
 core/tests/fixtures/rc14_sealed_274307.json        | new  (sealed fixture)
```

Four production-surface files, all inside the declared scope:

1. `memory/media_sync.py` — type coverage, extraction/indexing, ready transition.
2. `memory/message_parse.py` — expose the appmsg subtype discriminator (additive key).
3. `core/normalize.py` — classification driven by the appmsg subtype; explicit
   `file`/`voice` media role.
4. tests + fixture.

The filter alone was provably insufficient (§1.2), so the **minimal necessary
adapter** was implemented rather than only widening the SQL predicate — which is what
§5 of the request authorizes when widening is not sufficient.

### 5.1 Scope compliance

| Prohibition | Attestation |
| --- | --- |
| EFB not modified | NONE — the frozen candidate was read only |
| Agent not modified | NONE |
| consumer checkpoint protocol not modified | NONE |
| Core consumer bootstrap not modified | NONE |
| unrelated schema not modified | NONE — **zero DDL** |
| storage paths not modified | NONE — new artifacts go under the existing `runtime/media` |
| not only a SQL filter change | correct: the classification adapter is required |

### 5.2 Disclosed contract-visible change

Changing the projected `type` of non-file `appmsg` messages from `file` to `text`
(and of genuine files with a url from `link` to `file`) is a **contract-visible**
change affecting 113 existing messages on the current account. It is required for
correctness — without it the observed blocker is not closed — and it converts 113
currently-undeliverable messages into deliverable ones. Bounded re-emission is
quantified in §9.

---

## 6. Real regression fixtures — FMR-1 .. FMR-8

New module `core/tests/test_rc14_file_voice_media_reference.py` (20 tests).

| ID | Requirement | Test | Result |
| --- | --- | --- | --- |
| FMR-1 | file + original exists → `media_id` populated, role original, status ready, bytes retrievable | `test_fmr_1_file_with_original_is_published_as_ready_original`, `test_fmr_1_file_media_row_is_served_with_original_role_and_ready_status` | PASS |
| FMR-2 | file + original unavailable → not falsely ready, no thumbnail substitution | `test_fmr_2_missing_original_is_never_ready_and_never_uses_a_thumbnail`, `..._size_mismatch_is_not_ready`, `..._zero_byte_local_copy_is_not_ready`, `..._unsafe_filename_is_rejected_without_escaping_the_media_dir` | PASS |
| FMR-3 | file becomes available later → pending → ready, `media.ready` exactly once | `test_fmr_3_pending_then_ready_emits_media_ready_exactly_once` | PASS |
| FMR-4 | voice original exists → `media_id` populated, role/status correct, bytes retrievable | `test_fmr_4_voice_original_is_published_as_ready_original` | PASS |
| FMR-5 | voice unavailable → fail-safe, never falsely ready | `test_fmr_5_voice_without_original_is_fail_safe`, `..._length_mismatch_is_fail_safe`, `..._without_decrypted_store_is_fail_safe` | PASS |
| FMR-6 | image/sticker/video behaviour unchanged | `test_fmr_6_dispatch_preserves_image_sticker_video_and_adds_file_voice`, `test_fmr_6_video_projection_still_reports_a_thumbnail` | PASS |
| FMR-7 | F3 message projection regression — top-level `media_role`/`media_status` preserved | `test_fmr_7_file_message_keeps_top_level_media_contract_in_event_and_rest` | PASS |
| FMR-8 | `THUMBNAIL_REPORTED_AS_ORIGINAL_READY = NO` | `test_fmr_8_no_thumbnail_is_ever_reported_as_an_ready_original`, `test_fmr_8_role_derivation_never_marks_a_pending_file_as_a_thumbnail` | PASS |

```text
THUMBNAIL_REPORTED_AS_ORIGINAL_READY = NO
```

FMR-8 reports a **contingency table**, not a single sample: every persisted
`message_media` row is walked, the artifact's own filename suffix (`_thumb`, `.tmp`)
is correlated against `(media_type, status)`, and no row may claim
`ready` without a materialised artifact.

---

## 7. The 274307 fixture — and what it actually is

Built from the sealed census row (copied verbatim, not modified) plus the structural
facts read once, read-only, from the account staging store. The message body is
deliberately **not** reproduced: the census itself excludes message text and author
identity. Fixture: `core/tests/fixtures/rc14_sealed_274307.json`.

The sealed payload is:

```text
cursor=274307  event_type=message.created  account_id=f-live-a
chat_id=38808757431@chatroom
message_id=8745c1a931013b8941a0736d6fb890f1a4129129bd03b2b4842d09f7d5995d79
type=file  direction=incoming  media_id=''  media_role=''  media_status=''
```

Its real structure:

```text
upstream type_label          = link_or_file
outer appmsg type            = 57          -> a QUOTE REPLY, not a file transfer
refermsg present             = YES         -> it quotes another type-49 appmsg
appattach element present    = YES
appattach attachment payload = NO          -> only empty cdnthumbaeskey/aeskey, no totallen/attachid
```

```text
274307_IS_A_GENUINE_FILE   = NO
274307_MEDIA_ID_RESOLVABLE = NOT_PROVABLE_OFFLINE
```

`NOT_PROVABLE_OFFLINE` is not a limitation here — it is the **correct** outcome. The
message is a quote reply carrying no attachment, so no media artifact exists to
freeze into a fixture. Nothing was fabricated to make it resolvable.

After the fix, the message is projected as `text` (not `file`), receives no media
reference, and is deliverable as ordinary text. The test asserts the sealed census
value (`type=file`) is preserved as the *pre-fix* record and never overwritten.

---

## 8. EFB compatibility simulation (offline)

Frozen candidate `69a1f58e29177634b6790ed3b5ec688871ba590c`, run from a detached
worktree with the repository's own `tests/stub_ehforwarderbot.py`. No Core, no
Telegram, no production host, and **no EFB source modification**. Script:
`tmp/rc14-filevoice/efb_media_contract_simulation.py`.

```text
EFB_FILE_MEDIA_CONTRACT_COMPATIBLE  = PASS   effect DELIVERED, 1 delivery, 1 media call
EFB_VOICE_MEDIA_CONTRACT_COMPATIBLE = PASS   effect DELIVERED, 1 delivery, 1 media call
PRE_FIX_CONTROL_FAILS_CLOSED        = PASS   PENDING_MEDIA -> MEDIA_FAILED, 0 deliveries
SEALED_274307_CLASSIFICATION        = PASS   FIRST_BUSINESS_EFFECT (both origin routes)
```

The third line is the discriminating control: fed the **pre-fix** Core projection (a
`file` message with no media reference) the same frozen candidate still parks in
`PENDING_MEDIA` and settles as `MEDIA_FAILED`. The two PASS lines are therefore not
vacuous.

For 274307 the frozen candidate's durable-provenance classifier returns
`FIRST_BUSINESS_EFFECT` both via the authoritative projection timestamp and via the
cursor floor, so:

```text
274307_CLASSIFIED_AS_NEW_BUSINESS = YES
274307_DUPLICATE                  = NO
```

(`KNOWN_EFFECT` would require a durable effect identity; a message that was never
delivered has none.)

---

## 9. Full Core regression

Authoritative evidence is CI (local full-suite runs are contaminated by the
workstation sandbox):

```text
CI_RUN           = 35215908801   "Core CI"  event=push  headSha=9434e915b78b2eb5471acf282d4e223c03e8d83a
JOB 105184218086 test          -> success   Ran 268 tests in 147.343s ; 0 FAIL ; 0 ERROR
JOB 105184992777 docker-build  -> success
SUITE_DELTA      = 248 (F3) -> 268  =  +20, exactly the new FMR module; no test removed or renamed
```

Local supplementary runs (supporting evidence only):

```text
core.tests.test_rc14_file_voice_media_reference       Ran 20 tests  OK
core.tests.test_efb_media_functional_correctness      } Ran 88 tests  87 ok, 1 error
core.tests.test_media_sync_numeric_chat               }   the single error is
core.tests.test_memory_ingest_numeric_chat            }   test_core.CoreHttpTest.
core.tests.test_core                                  }   test_runtime_management_api_reloads_registry_immediately
                                                          (TimeoutError), which reproduces
                                                          identically on the UNMODIFIED baseline
                                                          worktree at 6538f79 -> pre-existing
                                                          local-environment failure, not a regression
```

```text
CHECKPOINT_PROTOCOL_REGRESSION      = ZERO
CORE_DB_DESTRUCTIVE_SCHEMA_CHANGE   = NO    (no DDL at all)
HEALTH_REGRESSION                   = PASS  (ok:true, contract_version 1, accounts 2)
EVENT_POLLING_REGRESSION            = PASS  (stream head read without consumer_id; limit<=200 honoured)
MEDIA_API_TESTS                     = PASS  (X-Media-Role / X-Media-Status legs exercised)
F3_MEDIA_PROJECTION_REGRESSION      = PASS  (FMR-7)
SIGBUS_GOVERNANCE_STATIC_GUARDS     = PASS  (guard selftest: CI_NEGATIVE_TESTS / CI_POSITIVE_TESTS both PASS)
```

### 9.1 Bounded re-emission (disclosed)

Messages whose persisted digest changes are re-emitted by the 5 s sync worker as one
`message.updated`, landing **after** the current consumer checkpoints.

```text
messages re-typed by this candidate (file -> text)   = 113
genuine file messages gaining a media reference      =   2
voice messages gaining a media reference             =   5
```

Consequence, pinned in the taskbook §5.5: the next EFB live round must fix its entry
checkpoint at the **post-deployment stream head**, not at 273844, or it will replay
stale re-emissions — including newly deliverable ones — and pollute the round ledger.
Advancing a consumer checkpoint is itself a consumer-state mutation needing its own
authorization.

---

## 10. Production governance

```text
PRODUCTION_CORE_MUTATION    = NO
PRODUCTION_EFB_TOUCHED      = NO
PRODUCTION_AGENT_TOUCHED    = NO
CORE_RECREATE_COUNT         = 0   (this round)
CORE_STATE_AT_ROUND_END     = running / healthy / RestartCount 0 / StartedAt 2026-09-17T01:45:06.839931379Z (unchanged)
AGENT_STATE_AT_ROUND_END    = STOPPED   (exited 0)
EFB_STATE_AT_ROUND_END      = STOPPED   (exited 0)
```

Guard: `scripts/forensics/check_forbidden_live_core_db_access.py`
(sha256 `a81015cc953a1fc5376f4a005221c57d0172026daa2ed9ab0d8829657933dfe1`);
selftest `CI_NEGATIVE_TESTS = PASS` / `CI_POSITIVE_TESTS = PASS`.

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

### 10.1 Disclosed guard/policy divergence — read this

Running the guard over the round's full command log
(`tmp/rc14-filevoice/core_db_access_command_log.txt`) returns
`RAW_SQLITE_GUARD = FAIL (5 findings)` while `GENERIC_FILE_OPEN_GUARD = PASS` and
`SCRATCH_GUARD = PASS`.

The findings are **not** protected-set accesses. The guard's
`PRODUCTION_CORE_PATH_PATTERNS[0]` is `wechat-hub-f-live[/\\]+core-data`, which
matches the *entire* `core-data` subtree, whereas policy
`docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md` §1.2 defines the protected set as
exactly the Core DB set and adds: *"Out of scope (must stay out of scope — do not
over-block)"*. The account staging store and the decrypted WeChat shards live under
`core-data/accounts/<account_id>/` and are not in that list.

Boundary control (`tmp/rc14-filevoice/guard_boundary_control.sh`), run with
`--command`:

```text
P1 sqlite3  .../core-data/core/wechat_core.sqlite          expect FAIL -> FAIL   OK
P2 sha256sum .../core-data/core/wechat_core.sqlite-wal     expect FAIL -> FAIL   OK
P3 cat      .../core-data/core/wechat_core.sqlite-shm      expect FAIL -> FAIL   OK
P4 cp       .../core-data/core/wechat_core.sqlite /tmp/x   expect FAIL -> FAIL   OK
N1 curl http://127.0.0.1:18082/health                      expect PASS -> PASS   OK
N2 ls -la .../core-data/core/                              expect PASS -> PASS   OK
N3 docker inspect wechat-hub-f-live-core                   expect PASS -> PASS   OK
N4 docker ps -a                                            expect PASS -> PASS   OK
B1 sqlite3 .../core-data/accounts/.../wechat_memory.sqlite expect PASS -> FAIL   DIVERGENCE
B2 sqlite3 .../core-data/accounts/.../media_0.db           expect PASS -> FAIL   DIVERGENCE
B3 sqlite3 .../agent-data/wechat-agent.sqlite              expect PASS -> PASS   OK
M1 echo 'wechat_core.sqlite'                               expect FAIL -> PASS   OK
```

The four protected-set controls fail exactly as required and the `agent-data` control
is correctly exempt, so the guard is discriminating; B1/B2 show the over-block. The
over-block is a property of the guard pattern, not of this round's behaviour, and is
reported here for the operator to reconcile.

Measured on the log:

```text
commands naming the protected basename in operand position  = 0
sqlite3 invocations total                                   = 13
  against the protected set                                 = 0
  against account staging / decrypted stores                = 13
ACTIVE_CORE_HOST_NON_CORE_STAGING_DB_READS = 13   (disclosed; policy §1.2 out of scope)
```

**Sidecar disclosure.** A read-only SQLite open of a WAL-mode database creates
`-shm`/`-wal` sidecars. After the reads, the decrypted shard directory holds
`media_0.db` (73728 B, mtime unchanged), `media_0.db-shm` (32768 B, created) and
`media_0.db-wal` (0 B, created — zero bytes means no pending frames). **No sidecar was
created on the protected set** (its directory listing shows no live
`wechat_core.sqlite-wal`/`-shm`, only renamed historical `*.rollback-*` copies). The
staging sidecars are left in place, not deleted: deleting them would itself be a
modification, and Core's `refresh_decrypted()` removes residual `-wal`/`-shm` after
each decrypt cycle anyway. Core's health, `consecutive_failed_cycles = 0` and
`RestartCount 0` confirm no operational impact.

All Core state and checkpoint evidence came from the read-only HTTP API
(`/health`, `/v1/events/checkpoint`, `/v1/events/poll` without `consumer_id`, i.e. a
pure `SELECT` that writes no receipt) and `docker inspect`.

---

## 11. Immutable candidate

```text
CORE_MEDIA_REF_SOURCE_COMMIT = 9434e915b78b2eb5471acf282d4e223c03e8d83a
CORE_MEDIA_REF_IMAGE_DIGEST  = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
CORE_MEDIA_REF_OCI_REVISION  = 9434e915b78b2eb5471acf282d4e223c03e8d83a
OCI_REVISION == SOURCE_COMMIT = YES
CI_RUN                       = 35215908801
PUBLISH_RUN                  = 35216281684
```

Host-side extraction (`/root/rc14-filevoice-pull.sh`, md5
`b43b96da925a62e9f6be81be8bcef9ac`, 850 B, verified byte-identical after transfer):

```text
docker pull ghcr.io/onestao/wechat-hub-core:0.1.0-rc.14-core-filevoice-media-ref
  PULL_RC       = 0
  CONFIG_ID     = sha256:a11731dafc06a93631a5726e1549e479462165efd1b0abd7377dbd877237e165
  OCI_REVISION  = 9434e915b78b2eb5471acf282d4e223c03e8d83a
  OCI_VERSION   = 0.1.0-rc.14-core-filevoice-media-ref
  IMAGE_CREATED = 2026-09-17T11:33:40.35797917Z
  REPO_DIGESTS  = ["ghcr.io/onestao/wechat-hub-core@sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47"]
  size          500,804,144 B

docker pull ghcr.io/onestao/wechat-hub-core@sha256:a0d4f70b...02e47
  DIGEST_PULL_RC = 0   ("Image is up to date")
```

The mutable tag is **not** used as a production identity; the deployment overlay pins
the manifest digest only. Unraid performed exact-digest `pull`/`inspect` only — the
candidate was **not deployed**.

Rollback material verified present on the host:

```text
sha256:77ec49f3…0427  (config 9061b9b3a986)  = 6538f79  — current production, intact
sha256:c42822f4…5819f (config 8add2212d7e2)  = 1e5eddd
sha256:7d9259a4…8d3ab5 (config 661967daae8a) = 08a4e74
```

---

## 12. Deployment taskbook

```text
TASKBOOK        = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_TASKBOOK.md
DEPLOYMENT_TASKBOOK_SHA256 = 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae
TASKBOOK_POLICY_GATE = PASS  (present in the gate's forward-taskbook set; the gate's 8 pre-existing
                             failures are sealed historical taskbooks that cannot be re-sealed)
```

It pins:

```text
current production Core = 6538f79a664a325543c19391cc14601d282e07a4
                          sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
new source commit       = 9434e915b78b2eb5471acf282d4e223c03e8d83a
new exact image digest  = sha256:a0d4f70bff2263518c2d0c0f6e3e6e8ece5945829c2585ac5307965bfca02e47
OCI revision            = 9434e915b78b2eb5471acf282d4e223c03e8d83a
Agent checkpoint floor  >= 195927
EFB checkpoint floor    >= 273844
```

Deployment readiness artefacts, all measured on the host:

```text
OVERLAY_PATH   = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-filevoice-media-ref-candidate.yml
OVERLAY_SHA256 = a46b318f579bcf9c36b0cdb909b97639bd4f5c702f7dc7a1376f3147542afc9e
OVERLAY_BYTES  = 313      (byte-identical to the locally generated file)
RENDER_DIFF_CHANGED_LINES = 1   (services.core.image only)
RENDER_DIFF_UNEXPECTED    = NONE
```

The overlay is inert — it touches no running service and was written during
engineering. The predecessor F3 overlay
(`8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d`) is preserved
byte-exact as the rollback artifact.

### 12.1 Recreate budget — EXHAUSTED

```text
CORE_RECREATE_COUNT_USED            = 1   (spent by the F3 deployment)
CORE_RECREATE_BUDGET_REMAINING      = 0
REQUIRES_NEW_OPERATOR_AUTHORIZATION = YES
PRIOR_AUTHORIZATION_INHERITABLE     = NO
```

The next production Core recreate requires a **new, explicit operator authorization
naming this work package, this taskbook and this exact image digest**. The F3
authorization must not be inherited or reused.

---

## 13. Next step

```text
ACTION = STOP
```

Engineering is complete and the candidate is immutable and pullable. The single
permitted next action is the controlled Core recreate defined in the taskbook, and it
requires a new explicit operator authorization first.

Until that authorization is granted:

```text
CORE  = RUNNING  (unchanged; do not recreate)
EFB   = STOPPED  (do not start)
AGENT = STOPPED  (do not start)
EFB_FUNCTIONAL_LIVE_RETRY = NOT AUTHORIZED  (do not run)
ROLLBACK                  = NOT PERFORMED
```

### 13.1 Residual risks and follow-ups

1. **Voice delivery container.** The original is published as SILK with no transcode.
   Core's contract is satisfied; downstream deliverability is unverified (§4). Fix
   direction if a live round fails on voice: add a SILK decoder/transcode to the
   image — a separate work package, not a contract change.
2. **Re-emission entry checkpoint.** The next EFB live round must enter at the
   post-deployment stream head (§9.1), and that checkpoint advance needs its own
   authorization.
3. **Guard over-block.** `PRODUCTION_CORE_PATH_PATTERNS[0]` should be narrowed to
   `core-data/core/` to match policy §1.2 (§10.1). Until then, any round that reads a
   derived store under `core-data/accounts/` will produce guard findings that the
   policy does not require, and those findings must be disclosed rather than
   suppressed.
4. **Media-role default for historical rows.** Unchanged from F1/F2: the additive
   `media.role` column defaults to `'original'` for pre-existing rows, and the API
   cannot prove byte provenance for historical media. This round neither widens nor
   narrows that.
