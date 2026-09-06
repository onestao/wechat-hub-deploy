# WeChat Hub RC.5 — RB-003 Core Final Artifact Report (Integration-RB3-Build)

- **Role**: Integration-RB3-Build (Section 5 of `docs/FLASH_RC5_RB003_FINAL_CLOSURE_TASKBOOK.md`)
- **Date**: 2026-09-06
- **Inputs**: Flash-RB3-D `docs/RC5_RB003_SYNC_WORKER_LIVENESS_FIX.md`,
  Flash-RB3-E `docs/RC5_RB003_RELEASE_LINEAGE_PROVENANCE_PORT.md`,
  Flash-RB3-F `docs/RC5_RB003_FRESHNESS_OBSERVABILITY_FIX.md` (all `READY_FOR_INTEGRATION`)
- **Verdict**:

```text
RB-003 CORE FINAL ARTIFACT = READY_FOR_LIVE_VALIDATION
```

Phase B scope only: integrate, test, build, publish, update manifest/validator evidence.
**No NAS apply, no Hub send/outbox, no H2, no Production, no A/B/Runtime/Core restart.**

---

## 1. Artifact identity (immutable)

```text
Image      ghcr.io/onestao/wechat-hub-core
Tag        0.1.0-rc.5-rb003          (secondary: sha-6f12932, pushed by the same run)
Digest     sha256:5f63366963c6ede7e8ceb9de89c17e9c36b7044ae1b9816df70952a6d0b4fc23
Platform   linux/amd64
Source     rc5/rb003-final-core @ 6f1293286d5ec348dcbdc7db014235257cbabe72
Base       1b797cad4305f9e3e3b746bbad1f9957a4f21f41  (exact deployed Core revision)
Replaces   ghcr.io/onestao/wechat-hub-core@sha256:40dea31b7b28e67e53e9f570334b488d68e3314703381dd1f59b32b22bbde453
```

## 2. Provenance chain (source revision == OCI revision == registry digest)

| Link | Value | Evidence |
|---|---|---|
| Source commit (local == origin tip) | `6f129328…` | `git rev-parse HEAD` == `git ls-remote origin rc5/rb003-final-core` |
| Publish run HEAD | `6f129328…` | `gh run view 34032239949` → `headSha` |
| Docker build-arg `OCI_REVISION` | `${{ github.sha }}` = `6f129328…` | `publish-image.yml` + run log (`DOCKER_METADATA_OUTPUT_JSON` revision) |
| OCI label in published artifact | `org.opencontainers.image.revision = 6f129328…` | config blob `sha256:a10cb79a…` read from GHCR (verify run 34032553342) |
| Tag → digest in registry | `0.1.0-rc.5-rb003` → `sha256:5f6336…` | GHCR manifest fetch (Docker-Content-Digest) == build output digest |
| Version label | `0.1.0-rc.5-rb003` | config blob |

Workflow runs (repo `onestao/wechat-hub-core`):

| Run | Purpose | Result |
|---|---|---|
| 34032188102 | Fail-closed tag-absence preflight (credentialed GHCR check) | `HTTP 404` → TAG_UNUSED, PASS |
| 34032239949 | `publish-image.yml` workflow_dispatch, `rc_tag=0.1.0-rc.5-rb003`, ref `rc5/rb003-final-core` | success |
| 34032553342 | Published-artifact verify (tag digest + OCI labels from registry) | `VERIFY_OK` |

Fail-closed notes:

- The tag `0.1.0-rc.5-rb003` was chosen unused; the registry check treats HTTP != 404
  (including indeterminate auth/network results) as fatal, so an existing tag could never
  be overwritten. Published tags were never overwritten; `0.1.0-rc.1` (= deployed 40dea31)
  is untouched.
- The core publish workflow has no built-in tag guard, so the preflight was supplied as a
  temporary credentialed workflow (added to and removed from the default branch; see §7).

## 3. Integration lineage (exact diff surface vs deployed revision `1b797cad`)

```text
$ git diff --stat 1b797cad..6f12932
 core/account_worker.py                        | 322 +++++++++-
 core/app.py                                   | 119 ++++-
 core/key_extract.py                           |  21 +-
 core/normalize.py                             |  27 +
 core/runtime_bridge.py                        |  81 ++-
 core/source_provenance.py                     | 68 +++   (new, taskbook-sanctioned local helper)
 core/store.py                                 |  57 +-
 core/tests/test_rc5_rb003_freshness_observability.py | 387 +++ (new)
 core/tests/test_source_provenance.py          | 502 +++  (new)
 core/tests/test_sync_worker_liveness.py       | 592 +++  (new)
 10 files changed, 2134 insertions(+), 42 deletions(-)
```

Commits:

| Commit | Content | Source lane |
|---|---|---|
| `2f57eb9` | Bounded SQLite-lock resilience + `SyncLiveness` + GET-poll write skip (port of `27611a8`) | Flash-RB3-D |
| `a4c0c22` | Source-provenance binding + fail-closed + local helper (port of `a00da4c`) | Flash-RB3-E |
| `f0e1381` | Freshness completeness/SLO + `/health` sync node (port of `9d4fb2d`, conflict-resolved) | Flash-RB3-F |
| `6f12932` | Test-fixture contract fix (see §4) | integration |

### 3.1 Conflict resolution (semantic merge of three lanes)

- `core/account_worker.py` — D and F both rewrote `AccountSyncLoop`. Merged: D's
  `SyncLiveness` skeleton (record/flush/backoff, bounded `MAX_FAILURE_BACKOFF_SECONDS=60`)
  retained as the loop body; F's telemetry attributes (`last_run_at`, `last_run_ok`,
  `last_error`, `consecutive_failures`, `is_alive()`) updated on BOTH the exception path
  (D's last-resort `except Exception` boundary) and the completed-cycle path. Account-level
  degradation keeps normal cadence (D semantics) while incrementing F's failure streak, with
  `last_error` summarizing per-account errors. Import conflict resolved to
  `CoreStore, parse_rfc3339` + the E provenance imports.
- `core/app.py` — D and F both changed `/health`, `main()`, and `_apply_runtime_status`:
  - `/health` now exposes both `sync_worker` (D's top-level liveness snapshot, additive when
    sync enabled) and `sync` (F's aggregate: `enabled/ok/worker_alive/slo_seconds/
    consecutive_failures/last_run_at/last_error/stale_accounts/degraded_accounts`).
  - `main()` passes `liveness_path=…/sync_liveness.json` (D) and binds
    `service.sync_loop` (F).
  - `_apply_runtime_status` keeps BOTH semantics coherently: F's anti-masking guard
    (logged_in may not flip a `degraded`/failed-sync account back to `online`) is computed
    first, then D's unchanged-projection write-skip compares the projected row — steady-state
    GET polls remain non-writers and cannot mask degradation.
- D+E merged textually in `run_account`; reviewed: `resolve_runtime_account()` and
  `_assert_source_provenance()` sit inside the account-scoped `try` (E), the final
  `upsert_account` is guarded (D), F's freshness/`sync_ok` computation precedes the state
  decision, and `SourceIdentityError` → `state="error"` + `source_provenance` status block.

### 3.2 Integration fix: test-fixture contract (commit `6f12932`)

Full-suite run exposed one failure (`test_source_provenance.test_06`): E's fixtures mocked
`refresh_decrypted` as `{"failed": 0}`, while the real pipeline returns list-valued
`updated/skipped/missing_key/failed` (`memory/decrypt_sync.py:165`) and F's freshness
telemetry (correctly) consumes those lists — `len(0)` raised `TypeError` and B's cycle
recorded `ok=false`. Fixed by aligning both mocks to the production shape; test intent
unchanged (A fail-closed, peer completes). No production code was altered for this.

## 4. Identity-v2 isolation check (taskbook 5.3)

- Diff surface is exactly the 10 `core/` files above; no schema, no API shape change, no
  compose/sender/outbox/memory/web/console changes, no `core/identity.py`, no store schema
  additions, no Identity-v2 branch content.
- Vocabulary scan of the full diff for `identity_v2|IdentityError|binding_state|
  identity_binding|instance_id` matched only the taskbook-sanctioned local
  `core/source_provenance.py` helper (`SourceIdentityError`, `valid_wxid`,
  `wechat_data_dir_name`) and docstrings.
- The build tree is the clean integration worktree; the dirty `feat/identity-v2-core`
  working tree (modified `key_extract.py`, `normalize.py`, `runtime_bridge.py`) was never
  used. `feat/multi-account-core` tip `a5a37b0` (1 commit ahead of the deployed revision)
  was also not used — base is exactly `1b797cad`.

## 5. Tests

Environment: Python 3.12.0, `pycryptodome==3.23.0 zstandard==0.25.0 Pillow==11.3.0`
(identical to the image/CI pins), Windows dev host, no containers involved.

```text
$ python -m unittest discover -s core/tests -p 'test_*.py'
Ran 84 tests in 103.357s — OK
  (49 pre-existing Core + 18 D liveness + 8 E provenance + 9 F freshness)

$ python -m compileall -q core memory web ai status agent_console tools
OK  (only the pre-existing upstream SyntaxWarning in tools/wechat-decrypt/find_wxwork_keys.py)
```

Coverage of the mandatory regression list: D §2 (lock non-lethality, bounded degradation,
recovery, peer isolation, no duplicate events on retry, 5 s cadence preserved), E §3
(all 8 provenance scenarios incl. testB `rpff…` vs `yx40…`), F §4 (missing_key → degraded,
SLO staleness, anti-masking, no destructive deletion, worker liveness) — all green on the
merged tree, plus the D+E+F interaction tests above.

## 6. Manifest / overlay / validator

- `release/manifest-0.1.0-rc.5.yaml`: `images.core` → `sha256:5f6336…`; added
  `release_sources.core` (source_commit == oci_revision == `6f129328…`); added
  `rb003_core_artifact` provenance section with run IDs; canary comment records that the
  existing PASS ran against the previous digest and that the exact-final-artifact canary
  (L7, >=1800 s, with sync-freshness assertion) is REQUIRED before RB-003 closure.
- `release/docker-compose.production.yml`: `wechat-core.image` → new digest (pids_limit 100
  unchanged).
- `python scripts/release/validate_release.py --manifest release/manifest-0.1.0-rc.5.yaml
  --overlay release/docker-compose.production.yml --base-ref HEAD` → **RELEASE VALIDATION: PASS**
- `python -m pytest tests/release/test_validate_release.py -q` → **10 passed**
- Historical manifests rc.1–rc.4 verified byte-identical to HEAD (validator history check).

## 7. Resource cleanup / garbage check

```text
resource cleanup: PASS
```

Removed:

| Resource | Disposition |
|---|---|
| Remote branch `rc5/rb003-tag-preflight` | deleted (evidence lives in run logs 34032188102/34032553342) |
| Local branches `rc5/rb003-tag-preflight`, `rb3-preflight-default` | deleted |
| Temp worktree `work/core/.worktrees/rb3-preflight-tmp` | deleted (dir fully removed) |
| Temp debug harness `core/.tmp/rb3int_debug_test06.py` | deleted (`core/.tmp` removed; recreated only transiently by the suite itself) |
| Temp preflight workflow on default branch | added as `7440a84`, removed by `082dd8c` on `feat/multi-account-core` (audit-trail pair, no content remains) |
| Temp index file for plumbing commit | deleted |

Intentionally preserved:

| Resource | Owner | Reason | Removed by |
|---|---|---|---|
| Worktree `work/core/.worktrees/rb3-final` + branch `rc5/rb003-final-core` (local+origin) | Integration-RB3-Build / RC.5 release | published artifact's exact source lineage; audit anchor for the digest | operator after RC.5 closure |
| Patch branches `rc5/flash-rb3-d` (`27611a8`), `rc5/rb003-provenance-port` (`a00da4c`), `rc5/flash-rb3-f` (`9d4fb2d`) + their worktrees | Flash-RB3-D/E/F | original evidence commits cited in the three lane reports (not ancestors of the integration branch after cherry-pick) | operator after RC.5 closure |
| GHCR tag `0.1.0-rc.5-rb003` | release | immutable artifact, consumed by Integration-RB3-Live L1 | never |

No containers, volumes, NAS paths, secrets, or prune operations were involved in this task.
Live NAS resources (A/B, Runtime, Console, Core service, canary leftovers) were untouched.

## 8. Handoff to Integration-RB3-Live (Phase C)

1. L1 pulls exactly `ghcr.io/onestao/wechat-hub-core@sha256:5f63366963c6ede7e8ceb9de89c17e9c36b7044ae1b9816df70952a6d0b4fc23`
   (already pinned in the production overlay); effective compose diff must show only this
   Core image change.
2. New runtime artifact to expect: `runtime/core/sync_liveness.json` (inside the Core data
   root, atomic tmp+replace, managed by Core) — L2 can gate on `/health` → `sync_worker`
   and `sync` nodes, or the file mirror.
3. `/health` gains additive `sync_worker` + `sync` objects when `--sync-interval > 0`;
   `GET /v1/accounts` gains per-account `sync.stale/staleness_seconds/slo_seconds` and
   `degraded` states per F. No other API contract change.
4. L7 canary MUST be re-run on this exact manifest (the recorded PASS predates the Core
   change) with the additional sync-freshness assertion before RB-003 closure.
5. After closure, Sending remains suspended pending operator authorization; H2 and
   Production remain suspended/blocked per taskbook.
