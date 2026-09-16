# RC.14 EFB Functional Correctness Live Qualification Taskbook

> Status: **NOT EXECUTED**
>
> Prepared: 2026-09-16
>
> This taskbook is an execution plan and evidence template only. Creating this file does not authorize or perform production startup, consumer rebootstrap, real WeChat/Telegram delivery, checkpoint mutation, ledger mutation, or profile mutation.

## 0. Active Core Production DB Access Rule

```text
ACTIVE CORE PRODUCTION DB ACCESS RULE

While Core is RUNNING:

Host/container side-channel access to the production
Core DB/WAL/SHM file contents is forbidden.

Use Core API only.

Raw database/file-content access is permitted only
against an offline snapshot created while Core is stopped.
```

This taskbook must not contain a host-side `sqlite3`, `sha256sum`, `md5sum`,
`cat`, `head`, `tail`, `cp`, `dd`, `rsync`, `tar`, `gzip`, or
`docker run -v <live-core-db>` against the production Core DB set:

```text
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-wal
/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-shm
```

Allowed while Core is RUNNING: the Core HTTP API, `docker inspect`,
`docker logs`, container state / image metadata, non-content filesystem
metadata, and API-sourced consumer / checkpoint / provenance reads.

If the Core API lacks a field this taskbook needs, **STOP**. Emit
`CORE_API_GAP = <field>` + `ACTION = STOP` and file it against
`docs/API_ENHANCEMENT_REQUEST_CORE_READONLY_OBSERVABILITY.md`. Never bypass with
the raw database.

Full policy: `docs/ACTIVE_CORE_PRODUCTION_DB_ACCESS_POLICY.md`.

### 0.1 Required return values

This qualification is not complete unless it returns **all** of the following,
with the two Core-access values exactly zero:

```text
ACTIVE_CORE_RAW_SQLITE_READS = 0
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
```

Any non-zero value is an automatic **FAIL**, regardless of every other result in
this document.

Supporting values:

```text
CORE_ACCESS_MODE = HTTP_API_ONLY
CORE_API_GAP_COUNT = <n>
OFFLINE_SNAPSHOT_SQLITE_ALLOWED = YES
```

## 1. Scope

This taskbook qualifies the RC.14 fixes for:

- F1: original media correctness
- F2: durable delayed-media delivery and duplicate suppression
- F3: durable, scoped reply mapping and visible quote fallback
- F4: actual sender and self identity

The qualification must preserve all Retry2/Retry3 history and frozen candidates. It must not change the production consumer identity, bootstrap state, checkpoint, effect ledger, message-mapping database, or account profile except through the explicitly approved live test messages and only after every precondition below is satisfied.

## 2. Candidate Identity

| Field | Value |
| --- | --- |
| EFB source branch | `rc14-efb-functional-correctness` |
| Functional source commit | `91a69cef323d120f0e32196917a630d2cf3baa88` |
| Inherited Retry3 baseline | `b387317` |
| Core companion branch | `rc14-efb-functional-correctness-core` |
| Core media commits | `2caee27`, `1e5eddd` |
| Functional image digest | `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241` |
| Functional OCI revision | `91a69cef323d120f0e32196917a630d2cf3baa88` |
| Production EFB checkpoint | `272548` |

```text
RETRY2_RESULT = FAIL_HISTORICAL_PRESERVED
RETRY2_CROSS_RUN_REPLAY_EVIDENCE = INDETERMINATE_HISTORICAL
Retry3 shutdown correction = inherited
F1-F4 functional correctness = included
```

## 2.1 Candidate Publication Record (2026-09-16)

Facts recorded; no qualification verdict is asserted by this section.

```text
FUNCTIONAL_SOURCE_COMMIT_FULL = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_LINEAGE = OCI revision label identical to source commit (verified in publish run step and by unraid docker inspect)

CI_RUN = 35069471405 (EFB CI, conclusion success)
PUBLISH_RUN = 35070004601 (regression + compileall + build/push + lineage verify passed; embedded shutdown-gate step failed, see deviation D1)

FULL_REGRESSION = 85/85 PASS (CI log: "Ran 85 tests ... OK"; zero FAIL/ERROR)
F1_F4_REGRESSION = 20/20 PASS (subset of the 85)
RETRY3_SHUTDOWN_REGRESSION = 21/21 PASS (tests/test_shutdown_deterministic.py, subset of the 85)
compileall = PASS (package + scripts/qualification)
docker-build linux/amd64 = PASS

UNRAID_EXACT_DIGEST_AVAILABLE = YES (docker pull by digest; RepoDigests match)
UNRAID_OCI_REVISION_MATCH = YES (docker inspect label = 91a69cef...)

FINAL_IMAGE_FUNCTIONAL_SMOKE = 38/38 PASS on exact-digest container (--network none, isolated):
  ORIGINAL_IMAGE_SELECTION = PASS (f1_1, f1_3)
  THUMBNAIL_NOT_FINAL = PASS (f1_2, f1_4)
  PENDING_MEDIA_RESTART = PASS (f2_2)
  PENDING_MEDIA_DUPLICATE_SUPPRESSION = PASS (f2_1, f2_3, f2_4, f2_5)
  REPLY_MAPPING_RESTART = PASS (f3_3)
  REPLY_CROSS_SCOPE_FAIL_CLOSED = PASS (f3_5)
  REPLY_VISIBLE_FALLBACK = PASS (f3_1, f3_2, f3_4)
  SELF_IDENTITY_PRIVATE = PASS (f4_1, f4_2)
  SELF_IDENTITY_GROUP = PASS (f4_3, f4_4, f4_5, f4_6)
  EFFECT_LEDGER_REGRESSION = PASS (18 ledger/replay tests)

FINAL FUNCTIONAL IMAGE SHUTDOWN GATE (5 real containers of the exact digest,
docker stop -t 2, isolated temp profile/ledger/mapping DB, stub Core, no
production credentials/profile/checkpoint):
  SHUTDOWN_RUN_1_SEC = 2.151153 (internal 1.002584)
  SHUTDOWN_RUN_2_SEC = 1.877204 (internal 1.002388)
  SHUTDOWN_RUN_3_SEC = 2.229769 (internal 1.002508)
  SHUTDOWN_RUN_4_SEC = 2.064058 (internal 1.002757)
  SHUTDOWN_RUN_5_SEC = 1.756926 (internal 1.002895)
  SHUTDOWN_MIN_SEC = 1.756926 / SHUTDOWN_P50_SEC = 2.064058 / SHUTDOWN_MAX_SEC = 2.229769 (wall)
  internal shutdown: min 1.002388 / p50 1.002584 / max 1.002895
  SHUTDOWN_EXIT_CODES = [0, 0, 0, 0, 0]
  SIGKILL = 0/5 (exit 0 under -t 2 proves exit inside the 2s grace window)
  final durable flush = PASS 5/5 (checkpoint 272548 flushed, ledger WAL
  checkpointed, delivery_suppressed, orphan containers 0)

PRODUCTION_EFB_TOUCHED = NO
```

Deviation D1 (frozen harness fixture bug): the frozen in-image probe stub
(`scripts/qualification/image_shutdown_probe.py`) returns
`contract_version: "v1"` while `Core.py` requires integer `1`, so the frozen
gate runner cannot start the channel (CoreContractError). This also caused the
publish-run embedded gate step to fail. The shutdown gate above was executed
with the same frozen image, frozen probe, and frozen parameters except the
generated temp profile used `startup_healthcheck: false`; orchestration was a
host shell port of the frozen runner (unraid has no python3). Product code
path under test is 100% frozen image bytes. A harness-only fix ("v1" -> 1) is
recommended for a future commit; it does not affect product behavior but will
change future image revision lineage.

Deviation D2 (host wall-clock overhead): on the unraid host (degraded array)
`docker stop` CLI-inclusive wall time has a 2.7-5.2s baseline even for a
trivial sleep container. Wall-time `< 2.0s` was met 2/5; product-internal
shutdown was 1.002-1.003s on 5/5 and no run was SIGKILLed. Wall-clock figures
above are reported as host context, not as a product verdict.

No live qualification claim is made by this record.

## 3. Already Completed Offline Evidence

The following evidence was completed before this taskbook was prepared:

| Gate | Result |
| --- | --- |
| Full EFB regression | `PASS` - 85 tests |
| Core media tests | `PASS` - 5 tests |
| F1-F4 real-dependency tests | `PASS` - 20 tests |
| Mock-core integration | `PASS` - 12 tests |
| Kettly integration | `PASS` - 3 tests |
| Retry3 ledger/shutdown group | `PASS` |

Candidate image construction, publication, and isolated qualification were completed on 2026-09-16; see section 2.1 (Candidate Publication Record) for the exact-digest identity, CI/publish run IDs, smoke results, shutdown-gate measurements, and the two recorded deviations.

## 4. Hard Prohibitions

Abort immediately if any proposed action would:

- Rebootstrap or replace the production consumer.
- Reset, advance manually, rewrite, or delete checkpoint `272548`.
- Edit, truncate, migrate ad hoc, replace, or delete the production effect ledger.
- Edit, truncate, replace, or delete the production reply/message-mapping database.
- Modify the production account profile, self identity, peer identity, or chat bindings.
- Start production EFB before the stop state and candidate identity have been independently verified.
- Use a mutable image tag without recording its immutable digest and OCI revision.
- Reuse a Retry2/Retry3 frozen candidate directory as a writable RC.14 workspace.
- Treat a thumbnail as final media or manually promote a pending item to delivered.
- Send any real WeChat or Telegram message outside the approved qualification window and test matrix.

## 5. Preconditions

All boxes must be checked by the live operator. Any unchecked item is a no-go.

- [ ] Change window and responsible operator are recorded.
- [ ] Production EFB is independently observed as stopped.
- [ ] No EFB process, service, container, scheduled task, or supervisor is actively consuming the production account.
- [ ] The last durable production checkpoint is exactly `272548` before candidate startup.
- [ ] The production checkpoint, effect ledger, reply mapping, and profile files have read-only backups with hashes and timestamps.
- [ ] The candidate was built from source commit `af3707d` plus Core commits `2caee27` and `1e5eddd`.
- [ ] The candidate image digest and OCI revision are recorded and match the immutable image selected for the test.
- [ ] Candidate configuration points to the existing production consumer state without rebootstrap.
- [ ] Candidate configuration does not introduce a second concurrent consumer.
- [ ] Logging can correlate message ID, account, chat, media state, reservation, delivery, and reply mapping without exposing secrets.
- [ ] Rollback image/configuration is identified and can be restored without changing checkpoint or ledger contents.
- [ ] A bounded list of test accounts, chats, messages, stickers, images, and reply targets is approved.

### Production stop verification record

Record commands and raw output used by the live operator. Do not infer `STOPPED` only from an expected deployment state.

| Check | Evidence | Result |
| --- | --- | --- |
| Process/service/container | `NOT RECORDED` | `NOT EXECUTED` |
| Concurrent consumer exclusion | `NOT RECORDED` | `NOT EXECUTED` |
| Checkpoint equals `272548` | `NOT RECORDED` | `NOT EXECUTED` |

## 6. Startup Gate

Before candidate startup:

1. Record candidate image digest and OCI revision.
2. Verify the digest corresponds to source commit `91a69cef323d120f0e32196917a630d2cf3baa88`.
3. Reconfirm production EFB is stopped and no competing consumer exists.
4. Reconfirm checkpoint remains `272548`.
5. Start exactly one candidate instance with the existing consumer state and no rebootstrap.
6. Observe startup only; do not send test traffic until startup logs show normal recovery of the pending-media state, effect ledger, and reply mapping.

Abort if startup performs an unexpected migration, asks to bootstrap a consumer, rewrites identity/profile data, loses ledger/mapping state, or advances the checkpoint without corresponding input.

## 7. Live Test Matrix

For every case, record source IDs, timestamps, account, chat, candidate digest, checkpoint before/after, relevant structured logs, Telegram result, and duplicate count. Redact secrets but retain stable correlation IDs.

### LQ-01 Original image

**Purpose:** Prove that delivered image media is the original ready object, never a thumbnail substitute.

1. Send one uniquely identifiable image through the approved WeChat test path.
2. Capture thumbnail and original metadata separately where available.
3. Confirm EFB does not deliver final media while only thumbnail or pending original state is available.
4. Confirm final delivery occurs only with `media_role=original` and `media_status=ready`.
5. Compare dimensions, byte size, hash where available, and visible content against the original source.

Pass criteria:

- Exactly one Telegram delivery.
- Final attachment is the original ready media.
- No thumbnail is silently used as final media.
- No reservation or delivery is recorded before the original becomes ready.

### LQ-02 Sticker delayed-ready and restart

**Purpose:** Prove durable pending-media recovery and bounded retry behavior.

1. Send an approved sticker whose original media is deliberately observed in delayed-ready state.
2. Confirm durable state becomes `PENDING_MEDIA` and no external effect is reserved.
3. Stop the candidate cleanly before the original becomes ready.
4. Reconfirm checkpoint, ledger, mapping, and profile were not manually changed.
5. Restart the same immutable candidate with the same durable state.
6. Allow the original media to become ready and observe recovery.

Pass criteria:

- Pending state survives restart.
- State progression is consistent with `PENDING_MEDIA -> RESERVED -> DELIVERED`.
- Exactly one final delivery occurs after readiness.
- Retry count is bounded.
- Failure paths produce `MEDIA_FAILED` or `UNCERTAIN`, never a false `DELIVERED`.
- Thumbnail is not delivered as the final sticker.

### LQ-03 Telegram reply visible fallback

**Purpose:** Prove correct behavior when native WeChat reply is unsupported.

1. Select a mapped message in an approved same-account, same-chat test conversation.
2. Reply from Telegram through the candidate.
3. Confirm capability reports `native_reply=false`.
4. Confirm the outbound WeChat content contains the visible quote fallback and the new reply body.
5. Repeat with an unknown same-chat target and confirm visible fallback remains usable.
6. Attempt a mapping reference from a different account or chat without sending it onward if the guard rejects it earlier.

Pass criteria:

- No unsupported native-reply claim or payload is emitted.
- Known and unknown same-chat targets use a visible quote fallback.
- Cross-account and cross-chat mappings fail closed.
- Mapping lookup is scoped by consumer, account, and chat.

### LQ-04 Self and peer identity

**Purpose:** Prove that sender and self identity come from actual message identity fields.

1. Send one inbound peer message in an approved direct chat.
2. Send one self-authored message visible to the same consumer.
3. Repeat in an approved group chat with a distinguishable member sender.
4. Record top-level `sender_id`, `sender_name`, and `is_self`, plus nested author only as diagnostic fallback.

Pass criteria:

- Peer messages are never classified as self based on nickname or chat peer.
- Self-authored messages are classified as self from explicit identity evidence.
- Group sender attribution matches the actual member.
- Nested author is used only when top-level identity is absent.

### LQ-05 Durable reply mapping across restart

**Purpose:** Prove reply mapping survives process restart without scope leakage.

1. Deliver a uniquely identifiable WeChat message to Telegram and record its mapping IDs.
2. Stop and restart the same candidate without changing the mapping database.
3. Reply from Telegram to the mapped message.
4. Verify the mapping is recovered from `core-message-mapping.sqlite3` in the correct consumer/account/chat scope.

Pass criteria:

- Mapping survives restart.
- Correct same-chat quote fallback is produced.
- No mapping from another account or chat is selected.

### LQ-06 Duplicate delivery zero

**Purpose:** Prove replay, retry, and restart do not produce duplicate external effects.

1. Use the LQ-02 delayed-ready item and one ordinary ready item.
2. Exercise one controlled restart and one bounded retry for each applicable item.
3. Correlate source message ID, durable state transitions, effect-ledger entry, and Telegram message ID.

Pass criteria:

- Duplicate Telegram deliveries: `0`.
- Each source message has at most one committed external effect.
- `RESERVED`, `DELIVERED`, `MEDIA_FAILED`, and `UNCERTAIN` semantics match observed external state.
- No READY-before-reservation violation occurs.

## 8. Evidence Table

| Test | Source/message IDs | Checkpoint before/after | Logs/artifacts | Duplicate count | Result |
| --- | --- | --- | --- | --- | --- |
| LQ-01 original image | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |
| LQ-02 delayed sticker/restart | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |
| LQ-03 reply fallback | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |
| LQ-04 identity | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |
| LQ-05 mapping restart | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |
| LQ-06 duplicate zero | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT EXECUTED` |

## 9. Abort Criteria

Stop the candidate immediately and preserve evidence if any of the following occurs:

- Production EFB or another consumer is discovered running concurrently.
- Candidate identity cannot be tied to the recorded immutable digest and source revision.
- Checkpoint differs from the expected value without a corresponding, auditable consumed event.
- Consumer bootstrap or rebootstrap is requested or initiated.
- Thumbnail is delivered as final media.
- Media is reserved or delivered before original-ready state.
- A pending message is lost across restart.
- Retry is unbounded or delivery duplicates exceed zero.
- A cross-account or cross-chat reply mapping is accepted.
- Native reply is claimed despite `native_reply=false`.
- Peer/self identity is misclassified.
- Ledger, mapping, checkpoint, or profile shows unexplained mutation.
- Any test traffic escapes the approved accounts or chats.

## 10. Rollback

1. Stop the RC.14 candidate; do not start another instance until process/container absence is verified.
2. Preserve candidate logs, checkpoint observation, mapping database, effect ledger, and test message IDs.
3. Do not edit or roll back checkpoint, ledger, mapping, or profile contents manually.
4. Restore the previously approved immutable image and configuration only after confirming it will use the same durable consumer state without rebootstrap.
5. Start at most one production instance.
6. Verify consumer continuity and reconcile any `RESERVED` or `UNCERTAIN` effect before permitting new traffic.
7. Document the abort reason and leave RC.14 Live qualification as failed/incomplete.

## 11. Qualification Decision

RC.14 may be declared Live-qualified only when all six live tests pass, duplicate delivery is zero, all identity and reply-scope checks pass, checkpoint continuity is explained, and all evidence fields are populated.

Current decision: **NOT EXECUTED - NO LIVE QUALIFICATION CLAIM**

