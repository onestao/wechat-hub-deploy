# RC.14 Core Media Contract F3 — Completion Result

```text
RESULT_ID        = RC14_CORE_MEDIA_CONTRACT_F3_COMPLETION
REQUEST_ID       = CORE_MEDIA_ROLE_CONTRACT_V1
DATE             = 2026-09-17  (host UTC)
PHASE            = ENGINEERING / PRE-DEPLOYMENT
VERDICT          = ENGINEERING COMPLETE — AWAITING DEPLOYMENT AUTHORIZATION
```

## 0. Return block

```text
F3_COMPLETION                              = DONE
F3_COMMIT                                  = 6538f79a664a325543c19391cc14601d282e07a4
F3_PARENT                                  = 1e5eddd4b5504bad44409ab610767688e32ddca2
F3_DESCENDANT_OF_1e5eddd                   = YES
F3_BRANCH                                  = rc14-core-media-f3  (origin/rc14-core-media-f3)
F3_DIFF_SCOPE                              = MINIMAL
F3_UNRELATED_PRODUCTION_CHANGES            = NONE
F3_FILES_CHANGED                           = 2  (core/store.py +29 ; core/tests/test_efb_media_functional_correctness.py +148)
F3_MESSAGES_SCHEMA_CHANGE                  = NO
F3_CORE_DB_SCHEMA_DESTRUCTIVE_CHANGE       = NO
F3_REGRESSION                              = PASS
F3_CI_RUN                                  = 35170072065  (Core CI, push, headSha 6538f79a…)
F3_CI_TESTS                                = Ran 248 tests in 133.907s / 241 ok / 0 FAIL / 0 ERROR
F3_PUBLISH_RUN                             = 35170328964  (Core Publish RC Image, workflow_dispatch)
F3_IMAGE_REF                               = ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
F3_IMAGE_DIGEST                            = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
F3_IMAGE_CONFIG_ID                         = sha256:9061b9b3a986f70b9d77a9c0d5afd65e8e90808e735152f7a32d00d053407f31
F3_OCI_REVISION                            = 6538f79a664a325543c19391cc14601d282e07a4
F3_OCI_REVISION_EQUALS_SOURCE_COMMIT       = YES
F3_DIGEST_PULL_PROOF                       = PASS  (rc 0)
F3_DEPLOY_OVERLAY                          = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-media-contract-f3-candidate.yml
F3_DEPLOY_OVERLAY_SHA256                   = 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d
F3_DEPLOY_OVERLAY_BYTES                    = 498
F3_RENDER_DIFF_CHANGED_LINES               = 1   (services.core.image only)
F3_DEPLOYMENT_TASKBOOK                     = docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md
F3_DEPLOYMENT_TASKBOOK_SHA256              = 85ba886feec2c4ed3504ac071ccd0466156d43ba47e090956b98851b5211dc7d
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS       = 0
ACTIVE_CORE_RAW_SQLITE_READS               = 0
CORE_DB_ACCESS_GUARD_SELFTEST              = PASS
CORE_DB_ACCESS_GUARD_FINDINGS              = []
CORE_SOURCE_COMMIT_CURRENT                 = 1e5eddd4b5504bad44409ab610767688e32ddca2
CORE_IMAGE_DIGEST_CURRENT                  = sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f
CORE_STATE_CURRENT                         = RUNNING / HEALTHY / RestartCount 0
AGENT_CHECKPOINT_CURRENT                   = 195927   (floor 195927)
EFB_CHECKPOINT_CURRENT                     = 273844   (floor 273844)
CORE_STREAM_HEAD_CURRENT                   = 274307
CHECKPOINT_REGRESSION                      = ZERO
AGENT_STATE_CURRENT                        = STOPPED
EFB_STATE_CURRENT                          = STOPPED
CORE_MEDIA_CONTRACT_F3                     = ENGINEERING_COMPLETE
EFB_FUNCTIONAL_REQUALIFICATION_PREREQUISITE = PENDING_DEPLOYMENT  (not yet re-evaluated)
CORE_RECREATE_REQUESTED                    = YES  (one controlled recreate, taskbook §8)
ACTION                                     = STOP — await operator authorization
```

### 0.1 Historical verdicts preserved (not modified by this phase)

```text
EFB_FUNCTIONAL_LIVE_QUALIFICATION          = FAIL
EFB_PRODUCTION_PROMOTION_READY             = NO
FAILURE_OWNER                              = CORE_MEDIA_CONTRACT
EFB_FUNCTIONAL_CANDIDATE_READY             = YES
EFB_CANDIDATE_CHANGE_REQUIRED              = NO
CORE_MEDIA_CONTRACT_PRODUCTION_DEPLOYMENT  = FAIL
EFB_FUNCTIONAL_REQUALIFICATION_PREREQUISITE = FAIL
GATE_1 = PASS   GATE_2 = PASS   GATE_3 = FAIL   GATE_4 = FAIL   GATE_5 = PASS   GATE_6 = PASS
```

The frozen FAIL result documents were verified byte-identical (`sha256sum -c`) and
were **not** touched:

```text
docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_RESULT.md   31aa1619…5788
docs/RC14_CORE_MEDIA_ROLE_CONTRACT_PRODUCTION_DEPLOYMENT_RESULT.md  c874a0f6…bced
docs/API_ENHANCEMENT_REQUEST_CORE_MEDIA_ROLE_CONTRACT.md            59f52624…6979
```

---

## 1. Root cause (restated precisely)

The predecessor deployment proved GATE_3 and GATE_4 still failed: in a 200-event
window after cursor 273700 there were **0** message events carrying a top-level
`media_role`, and
`GET /v1/accounts/f-live-a/chats/38808757431@chatroom/messages?limit=1` exposed only
`vendor_specific.media`, never the top-level fields.

Trace:

```text
core/normalize.py::_normalized_message()
    if media:
        normalized.update({"media_id":…, "filename":…, "mime_type":…,
                           "media_role": media["role"],      <-- produced
                           "media_status": media["status"]}) <-- produced
            ↓  (core/normalize.py:499  store.upsert_message(normalized))
core/store.py::CoreStore.upsert_message()
    value = { …explicit column whitelist… }        <-- media_role / media_status DROPPED
    value_digest = digest(value)
    INSERT INTO messages (…explicit column list…)   <-- no column, nothing to persist
    self._append_event(conn, account_id, event_type, {"message": value})   <-- payload lacks the fields
            ↓
core/store.py::CoreStore._message_row()
    optional = (("text",…),("media_id",…),("filename",…),("mime_type",…),("target_message_id",…))
                                                <-- media_role / media_status DROPPED
```

The frozen EFB candidate reads the contract at the **top level**:

```text
efb-linux-wechat-slave  CoreMessage.py:226-227
    media_role   = message.get("media_role")
    media_status = message.get("media_status")
    media_role   != "original"  ->  MediaPermanentError
    media_status != "ready"     ->  MediaPendingError
efb-linux-wechat-slave  ComWechat.py:1115
    raw_message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
```

so the predecessor deployment reproduced the identical historical `MediaPermanentError`
and could not close the Core API gap. The gap was a **projection / whitelist data
loss**, not a missing capability: F1 had already produced the fields.

---

## 2. Fix

Two additive hunks, both in `core/store.py`.

### 2.1 `upsert_message` — stop dropping the contract fields

```python
        value["source_message_table"] = str(value["vendor_specific"].get("source_message_table") or "")
+       # The normalizer records the media role/status contract on the message it
+       # hands to the store, and mirrors it into vendor_specific.media.  The
+       # explicit column whitelist above rebuilds the persisted value from
+       # scratch, so without this projection both fields would be silently
+       # dropped from the message object that the event payload and the REST
+       # projection expose.  The keys are only materialized for messages that
+       # actually carry media, so text-only messages keep their previous digest
+       # and are not re-emitted.
+       media_role = str(message.get("media_role") or "")
+       media_status = str(message.get("media_status") or "")
+       if not media_role or not media_status:
+           media = value["vendor_specific"].get("media")
+           if isinstance(media, dict):
+               media_role = media_role or str(media.get("role") or "")
+               media_status = media_status or str(media.get("status") or "")
+       if media_role:
+           value["media_role"] = media_role
+       if media_status:
+           value["media_status"] = media_status
```

### 2.2 `_message_row` — same contract in the REST projection

```python
        if vendor:
            output["vendor_specific"] = vendor
+       # The media role/status contract is persisted inside vendor_specific.media
+       # (the messages table has no dedicated columns).  Consumers read the
+       # contract at the top level of the message object, so project it here as
+       # well and keep the REST view identical to the event payload view.
+       media = vendor.get("media") if isinstance(vendor, dict) else None
+       if isinstance(media, dict):
+           if media.get("role"):
+               output["media_role"] = media["role"]
+           if media.get("status"):
+               output["media_status"] = media["status"]
        return output
```

### 2.3 Design decisions and their justification

**No `messages` table schema change.** The contract values are already persisted
inside `vendor_json` as `vendor_specific.media.role` / `.status`. F3 derives the
top-level projection from that single source of truth at both serialization
boundaries, so no column, migration or backfill is needed — matching the operator's
"如无必要，不新增 messages 表 schema".

**Conditional materialization, not unconditional.** Adding the keys unconditionally
would give every media-less message two new keys and therefore a new digest, causing
the whole historical message table to re-emit as `message.updated`. The keys are
materialized only when they are non-empty, matching the existing
`source_local_id` precedent in the same function. This is asserted by
`test_f3_6_text_only_messages_are_not_perturbed` (second upsert must return
`unchanged`, and no `message.updated` may be emitted).

**Bounded, disclosed re-emission for media-bearing messages.** For messages that do
carry media, two new keys do change the digest, so each such message that the 5 s
sync worker re-reads emits one extra `message.updated`. The magnitude was measured
at the F1/F2 deployment of the same class of change: `message.updated 15` in the
observation window. This is disclosed in the taskbook §6.3 together with the
consequence that the next EFB round must fix its entry checkpoint at the
post-deployment stream head.

**Fallback to `vendor_specific.media`.** The store accepts `message` dicts from the
normalizer, which sets both shapes. The fallback guarantees the event payload and
the REST projection can never disagree if only one shape is present, and it is
covered by `test_f3_5_projection_falls_back_to_vendor_specific_media`.

---

## 3. Scope compliance

| Operator restriction | Attestation |
| --- | --- |
| fix `message.created` top-level `media_role` | DONE — §2.1 |
| fix `message.created` top-level `media_status` | DONE — §2.1 |
| fix `message.updated` same fields | DONE — same code path (`event_type` is chosen from `before is None`) |
| fix REST message projection same fields | DONE — §2.2 |
| store / serialization must not drop normalized contract fields | DONE — §2.1 |
| prefer fixing projection/whitelist rather than adding schema | DONE — no DDL |
| no `messages` table schema addition unless necessary | NOT NECESSARY → NONE ADDED |
| no EFB modification | NONE |
| no Agent modification | NONE |
| no checkpoint protocol modification | NONE |
| no storage migration | NONE |
| no `account.status` receipt redesign | NONE |
| no unrelated Core schema refactor | NONE |

Diff scope check:

```text
git diff --name-status 1e5eddd..6538f79
M  core/store.py
M  core/tests/test_efb_media_functional_correctness.py

git diff --stat 1e5eddd..6538f79
 core/store.py                                      |  29 ++++
 .../tests/test_efb_media_functional_correctness.py | 148 +++++++++++++++++++++
 2 files changed, 177 insertions(+)
```

Only one production file is touched, and every added line is inside the two
message-projection functions described in §2. `COMPANION_DIFF_SCOPE = MINIMAL`,
`UNRELATED_PRODUCTION_CHANGES = NONE`.

Descendant proof:

```text
git rev-parse 6538f79a664a325543c19391cc14601d282e07a4^
  -> 1e5eddd4b5504bad44409ab610767688e32ddca2
git merge-base --is-ancestor 1e5eddd4b5504bad44409ab610767688e32ddca2 6538f79a664a325543c19391cc14601d282e07a4
  -> DESCENDANT_OF_1e5eddd = YES
```

---

## 4. Regression evidence

### 4.1 New tests (7) added to the frozen F1/F2 suite

```text
test_f3_1_message_created_event_exposes_media_contract_fields
test_f3_2_message_updated_event_exposes_media_contract_fields
test_f3_3_rest_message_projection_exposes_media_contract_fields
test_f3_4_thumbnail_role_is_exposed_and_never_reported_as_original
test_f3_5_projection_falls_back_to_vendor_specific_media
test_f3_6_text_only_messages_are_not_perturbed
test_f3_7_normalizer_to_store_contract_is_preserved_end_to_end
```

`test_f3_7` is the direct end-to-end closure of the reported root cause: it runs
`_normalized_message(..., media={"role": "original", "status": "ready"})` into
`CoreStore.upsert_message` and asserts that both the emitted `message.created`
payload and the REST `list_messages` row carry `media_role = "original"` and
`media_status = "ready"`.

### 4.2 CI (authoritative)

```text
RUN      35170072065  "Core CI"  event=push  headBranch=rc14-core-media-f3  headSha=6538f79a664a325543c19391cc14601d282e07a4
JOB      105039644228  test           -> success
JOB      105040129625  docker-build   -> success
RESULT   Ran 248 tests in 133.907s ; 241 "... ok" lines ; 0 FAIL ; 0 ERROR ; conclusion=success
```

The suite grew from 241 to 248 tests, i.e. exactly the 7 new F3 tests; no pre-existing
test was removed or renamed. Covered modules include `test_core`,
`test_rc14_required_consumer_governance`, `test_identity_v2`, `test_rc14_governed_bootstrap`,
`test_sync_worker_liveness`, `test_contacts_avatar_e`, `test_efb_media_functional_correctness`
and the media-sync numeric-chat family.

### 4.3 Local supplementary runs

```text
core.tests.test_efb_media_functional_correctness  ->  Ran 12 tests  OK   (F1 ×4 + F2 ×1 + F3 ×7)
core.tests.test_core                              ->  Ran 49 tests  OK   (0 sandbox guard blocks)
```

Note on local evidence discipline: a **full** local suite run is not admissible
evidence on this workstation, because the sandbox intercepts `shutil.rmtree` on
directories with ≥50 entries and emits `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]`,
which produces spurious `ERROR`s. The authoritative full-suite evidence is CI. The
two targeted local runs above are reported only as supporting signals.

### 4.4 Required regression answers

```text
CONSUMER_CHECKPOINT_REGRESSION  = ZERO   (wechat-agent 195927, efb 273844 unchanged across the phase)
CORE_DB_SCHEMA_DESTRUCTIVE_CHANGE = NO   (no DDL at all in F3)
MEDIA_NORMALIZATION_TESTS       = PASS
MEDIA_API_TESTS                 = PASS   (X-Media-Role / X-Media-Status legs re-confirmed live, §5)
HEALTH_REGRESSION               = PASS   (ok:true, contract_version 1, accounts 2)
EVENT_POLLING_REGRESSION        = PASS   (stream_head 274307, retention_floor 1, limit<=200 honoured)
```

---

## 5. Live production state at the end of this phase

Captured 2026-09-17T01:28:02Z (host UTC). **No service was mutated in this phase.**

| Service | Container ID | State | StartedAt | RestartCount |
| --- | --- | --- | --- | --- |
| core | `b93fa6a8bd6b1ed72323d249d2914cc4d5a054c0c29e1dd2ec0babf19a2663eb` | running / healthy | 2026-09-17T00:08:53Z | 0 |
| console | `cce13a59dad25fb8c10e741b6978b8c7b7e228ccc4259734a289cc439f22666a` | running | 2026-09-13T12:05:02Z | 0 |
| runtime | `d21960eef445e709a9e3fd06f30327682f3493cb7adc113bf99b5c67ec2eb852` | running | 2026-09-11T06:45:48Z | 0 |
| agent | `f4d2f2773e854f654c471200ed1530988c2655f62e8bd1b44796d90d3cddc096` | **exited (STOPPED)** | 2026-09-16T07:31:50Z | 0 |
| efb | `6023ad354c2616659e60e75ad95471718074584db3255f9c52d572546b8c8ea9` | **exited (STOPPED)** | 2026-09-16T16:49:38Z | 0 |
| agentwechat-a | `44559e58c4fefad872d07e353bbb6cfb340bff7bcfcd7ae9423aa2f4a155565d` | running | 2026-09-11T05:12:55Z | 0 |
| agentwechat-b | `a6c2e3ee61e1521828cd2e352e00847b16ff2e8841a3364b21147abd1a25ca51` | running | 2026-09-11T05:12:57Z | 0 |

```text
Core image (running) = sha256:8add2212d7e203bf22bc7d235da9220546969a10d69a981f3cc5ceca9a657715
                     = ghcr.io/onestao/wechat-hub-core@sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f
Core OCI revision    = 1e5eddd4b5504bad44409ab610767688e32ddca2
wechat-agent         checkpoint 195927   updated_at 2026-09-16T08:04:11Z
efb-linux-wechat:wechat.linux checkpoint 273844  updated_at 2026-09-16T17:14:43Z
wechat-console       checkpoint 274307   updated_at 2026-09-17T00:41:35Z
stream_head 274307 ; retention_floor 1
```

`KEEP_CURRENT_CORE = YES` is honoured: production Core is still `1e5eddd`, healthy,
`RestartCount 0`, and no rollback was performed. `AGENT_CHECKPOINT = 195927` and
`EFB_CHECKPOINT = 273844` are at or above their legal floors and were not touched.

---

## 6. Zero-DB-access attestation

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

Guard: `scripts/forensics/check_forbidden_live_core_db_access.py` (guard version
`1.1.0`, rule `ACTIVE_CORE_HOST_PRODUCTION_DB_FILE_OPENS`, superseding
`ACTIVE_CORE_HOST_RAW_SQLITE_READS`).

```text
--selftest          -> CI_NEGATIVE_TESTS = PASS ; CI_POSITIVE_TESTS = PASS
--mode both --json tmp/rc14-coremedia-f3/core_db_access_command_log.txt
                    -> files_scanned 1 ; findings [] ;
                       RAW_SQLITE_GUARD = PASS ;
                       GENERIC_FILE_OPEN_GUARD = PASS ;
                       SCRATCH_GUARD = PASS
```

Every host command executed while Core was RUNNING is enumerated in
`tmp/rc14-coremedia-f3/core_db_access_command_log.txt`. All Core state and checkpoint
reads went through `http://127.0.0.1:18082` (`/health`, `/v1/events/checkpoint`,
`/v1/events/poll` without `consumer_id`, i.e. a pure `SELECT` that writes no receipt).
No `sqlite3`, no `sha256sum`/`cat`/`cp`/`dd`/`tar` against `core-data/**`, no
`/dev/shm` snapshot, no `docker exec`, no sidecar-bind open. One attempted inline
`python3 -c` one-liner was refused by the approval gate and replaced with `jq`; it
never executed and is recorded as such in the log.

---

## 7. Immutable candidate identity

```text
SOURCE_COMMIT_FULL  = 6538f79a664a325543c19391cc14601d282e07a4
IMAGE_DIGEST        = sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
OCI_REVISION        = 6538f79a664a325543c19391cc14601d282e07a4
OCI_REVISION == SOURCE_COMMIT_FULL  ->  YES
```

Host-side extraction (`/root/rc14-coremedia-f3-pull.sh`, md5
`87acad9f7e7d6584f69a377a4f6a3f0e`, 815 B, verified byte-identical after transfer):

```text
docker pull ghcr.io/onestao/wechat-hub-core:0.1.0-rc.14-core-media-contract-f3
  PULL_RC = 0
  CONFIG_ID     = sha256:9061b9b3a986f70b9d77a9c0d5afd65e8e90808e735152f7a32d00d053407f31
  OCI_REVISION  = 6538f79a664a325543c19391cc14601d282e07a4
  OCI_VERSION   = 0.1.0-rc.14-core-media-contract-f3
  IMAGE_CREATED = 2026-09-17T01:23:37.472421668Z
  REPO_DIGESTS  = ["ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427"]
  size          501 MB

docker pull ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3…0427
  DIGEST_PULL_RC = 0   ("Image is up to date")
```

As in the predecessor round, the digest printed by the `docker/build-push-action`
build log is **not** the pullable manifest digest. The authoritative identity is the
one extracted above from `docker image inspect <config-id> .RepoDigests` and then
proved pullable by digest. The mutable tag
`0.1.0-rc.14-core-media-contract-f3` is **not** used as a production identity; the
deployment overlay pins the manifest digest only.

Previous images remain on the host, so rollback material is intact:

```text
sha256:c42822f4…5819f  (config 8add2212…)  = 1e5eddd  — current production
sha256:7d9259a4…8d3ab5 (config 661967da…)  = 08a4e74  — predecessor production
```

---

## 8. Deployment readiness

```text
OVERLAY_PATH   = /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-core-media-contract-f3-candidate.yml
OVERLAY_BYTES  = 498
OVERLAY_SHA256 = 8409245628c22d30ff36289efedd78a176f241b205a7c913a614609aa1d1da4d
```

Byte-identical to the locally generated expectation, verified on the host. Creating
it touched no running service.

Render-diff proof (`docker compose config` is a static render):

```diff
81c81
<     image: ghcr.io/onestao/wechat-hub-core@sha256:c42822f4ff534bc7a44b656b022fdd9877d9ebacbf53da42207ada65e885819f
---
>     image: ghcr.io/onestao/wechat-hub-core@sha256:77ec49f3b913bb9199ad2629d7caf6c28e34e41aa856edb11c042fce0bbb0427
```

```text
RENDER_DIFF_CHANGED_LINES = 1     (services.core.image only)
RENDER_DIFF_UNEXPECTED    = NONE
```

The predecessor overlay `docker-compose.rc14-core-media-role-candidate.yml`
(SHA256 `c20e5e259473da1f59df2b622a42f11faa9adfec0e7c2ffdea92ecdb1c702b5e`) is preserved
unmodified as the byte-exact rollback artifact.

The exact deployment command, its constraints, the post-deployment gate, and the
rollback criteria are pinned in
`docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md`
(SHA256 `85ba886feec2c4ed3504ac071ccd0466156d43ba47e090956b98851b5211dc7d`).

---

## 9. Disclosures and residual risks

1. **Bounded re-emission of media-bearing messages.** Adding the two keys changes the
   stored digest for media-bearing messages only, so each such message re-read by the
   5 s sync worker emits one additional `message.updated`. Magnitude measured at the
   F1/F2 deployment of the same class of change: `message.updated 15` in the window.
   Media-less messages are unaffected (asserted). Consequence recorded in the taskbook
   §6.3: the next EFB Functional Live round must fix its entry checkpoint at the
   post-deployment stream head, otherwise it will replay stale media re-emissions.

2. **F1's `role='original'` migration default is unchanged and still unprovable from
   the API.** The additive `media.role` column defaults to `'original'` for pre-existing
   rows; rows never re-upserted as `ready` keep that default. No live counterexample
   exists (all resolvable media ids are non-`_thumb`), but the API cannot prove the
   byte provenance of historical media. F3 neither widens nor narrows this.

3. **`media_status` semantics are carried verbatim.** F3 projects whatever the
   normalizer produced (`ready`, `original_pending`, …). It does not reinterpret
   `original_pending` as a terminal state; the frozen EFB candidate already maps a
   non-`ready` status to `MediaPendingError` and will keep doing so.

4. **Local full-suite runs are not evidence.** See §4.3.

5. **No new schema, so no migration risk** — but also no persisted top-level column:
   the contract remains derived from `vendor_json`. If a future phase wants to filter
   or index on media role/status in SQL, a column would then be required; that is
   explicitly out of scope here.

---

## 10. Next step

```text
ACTION = STOP
```

The engineering phase is complete. The single permitted next action is the controlled
Core recreate defined in
`docs/RC14_CORE_MEDIA_CONTRACT_F3_PRODUCTION_DEPLOYMENT_TASKBOOK.md` §8, and it
requires explicit operator authorization first.

Until that authorization is granted:

```text
EFB   = STOPPED      (do not start)
AGENT = STOPPED      (do not start)
EFB_FUNCTIONAL_LIVE_RETRY = NOT AUTHORIZED  (do not run)
ROLLBACK                  = NOT PERFORMED   (KEEP_CURRENT_CORE = YES)
```
