# RC.14 EFB Functional Correctness — Final Production Preflight Result

- **Document type:** Preflight result (read-only, no live traffic)
- **Executed:** 2026-09-16, host UTC window `13:03:57Z` – `13:06:xxZ` (unraid `192.168.22.102`)
- **Mode:** `READ_ONLY / NO_LIVE_TRAFFIC`
- **Frozen candidate:** source `91a69cef323d120f0e32196917a630d2cf3baa88`,
  image `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241`
- **Predecessor:** `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_RESULT.md`
  (`EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS`)

> This preflight did **not** start production EFB, did **not** start the production Agent,
> did **not** rebootstrap a consumer, and did **not** modify any checkpoint, ledger, mapping
> database, pending-media state, Telegram profile, or Core state. Every production read below
> is either an HTTP API call or non-content filesystem metadata.

---

## 0. Frozen candidate identity

| Item | Expected | Observed | Verdict |
| --- | --- | --- | --- |
| Source commit | `91a69cef323d120f0e32196917a630d2cf3baa88` | `91a69cef323d120f0e32196917a630d2cf3baa88` (OCI label `org.opencontainers.image.revision`) | MATCH |
| Image digest | `sha256:d45029d5…456241` | repoDigest `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241` | MATCH |
| Local image ID | — | `sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a` | RECORDED |
| Mutable-tag substitution | none permitted | image present as `<none>` tag, referenced **by digest only**; repoDigest identical to the frozen digest | NO SUBSTITUTION |

Evidence command:

```bash
docker image inspect ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d5…456241 \
  --format '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}|{{.RepoDigests}}'
```

```
sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a|91a69cef323d120f0e32196917a630d2cf3baa88|[ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241]
```

**`IMAGE_LINEAGE = PASS`**

Separately recorded (NOT the frozen candidate): the stopped `wechat-hub-f-live-efb` container still
references the historical Retry2 image `sha256:9e7bb215…` / digest `sha256:9c53faa4…` / OCI revision
`17641908e5d1c9ce71ebaf00903af4edccd87e60`. This is the preserved Retry2 artifact and is **not**
a candidate for the live window.

---

## 1. Historical evidence freeze

All previously sealed verdicts are preserved verbatim. Nothing in this document re-adjudicates them.

```text
RETRY2_RESULT = FAIL_HISTORICAL_PRESERVED
RETRY2_CROSS_RUN_REPLAY_EVIDENCE = INDETERMINATE_HISTORICAL
PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED
EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS
```

Sealed artifacts re-verified by SHA256 in this session:

| Artifact | SHA256 | Status |
| --- | --- | --- |
| `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md` | `0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511` | MATCH |
| `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_TASKBOOK.md` | `b4111f96654df2fed6f3ff25572770fe39020850af511c42f6d305f2d664da53` | MATCH |
| `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_RESULT.md` | `6172a2a1b33f8a0bd69a248e11d16548fe9d6f1a4bb65be153ee07b9f1337e20` | MATCH |

---

## 2. Live service state

Read via `docker ps -a` / `docker inspect` (metadata only, no DB content).

| Service | Container | Image (digest) | State | Restart count | Restart policy | Required | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Core | `wechat-hub-f-live-core` | `…wechat-hub-core@sha256:7d9259a4…8d3ab5` | `running` / `healthy` | 0 | `no` | RUNNING/HEALTHY | PASS |
| Agent | `wechat-hub-f-live-agent` | `…wechat-hub-agent@sha256:c9300742…3f463a` | `exited (0)` | 0 | `no` | STOPPED | PASS |
| EFB | `wechat-hub-f-live-efb` | `…efb-linux-wechat-slave@sha256:9c53faa4…f994a` (Retry2) | `exited (137)` | 0 | `no` | STOPPED | PASS |
| Console | `wechat-hub-f-live-console` | `…wechat-hub-console@sha256:8712f867…274dd` | `running` / `healthy` | 0 | `no` | — | OK |
| Runtime | `wechat-hub-f-live-runtime` | `…wechat-hub-runtime@sha256:5a2454a6…02158` | `running` / `healthy` | 0 | `no` | — | OK |
| AgentWechat bridge A | `wechat-agent-f-live-a-faf35abb` | `…agent-wechat@sha256:87b055e3…c85e4` | `running` | 0 | `unless-stopped` | — | OK |
| AgentWechat bridge B | `wechat-agent-testb-a7c4f6c8` | `…agent-wechat@sha256:87b055e3…c85e4` | `running` | 0 | `unless-stopped` | — | OK |

Notes:

- `EFB exit 137` is the **pre-existing historical stop state** (finished `2026-09-15T11:59:31Z`), unchanged
  before and after this preflight. The container is not running and consumes nothing. This is distinct from
  the product-semantics shutdown gate, which is a separate sealed PASS.
- `AGENT exit 0` — clean historical stop, finished `2026-09-16T08:04:18Z`.
- No second EFB/agent consumer instance exists.

**`CONCURRENT_LIVE_QUALIFICATION = NO`**

Definition used: no second consumer or qualification instance attached to the **production**
Core / Agent / EFB path.

Disclosed concurrent host activity (see §12 D2): the host is currently running the leftover V5
catch-up benchmark sweep `run_v5_matrix.sh` (host PID `2265125`), which at observation time had
`v5-C1-run1` running. That container:

- uses `--core-mode sealed` against `MOCK_CORE=http://127.0.0.1:36513` (not the production Core),
- uses its own private `/data/db.sqlite` (`--consumer-id v5bench-C1-run1`),
- mounts no EFB profile, no EFB ledger, no mapping DB, and no production agent DB.

It therefore cannot consume production events and does not attach to the production EFB path, but it
**is** a heavy host-I/O workload. It is listed as a mandatory pre-live condition (§11 R6) and was
deliberately **not** stopped by this read-only preflight.

---

## 3. Core consumer state (HTTP API only)

**`CORE_ACCESS_MODE = HTTP_API_ONLY`**

Core `/health` (2026-09-16T13:03:57Z):

```json
{"ok":true,"service":"wechat-core","contract_version":1,"accounts":2,
 "sync":{"enabled":true,"ok":true,"worker_alive":true,"consecutive_failures":0},
 "registry":{"source":"/app/config/wechat-runtime/accounts.json","hot_reload":true,"accounts":2,"ok":true}}
```

`/v1/accounts` reports both accounts `online`, `runtime_health=healthy`, `sender_driver=agent_wechat`,
`native_reply=false`.

| Value | Source | Observed |
| --- | --- | --- |
| `EFB_CURRENT_CHECKPOINT` | live `…/wechat.linux/core-event-cursor.json` (content read of a **non-Core** consumer state file) | `272548` |
| `AGENT_CURRENT_CHECKPOINT` | `agent_meta.core_cursor` in the agent's own SQLite, read while the agent container was **STOPPED** | `195927` |
| `CORE_STREAM_HEAD` | Core API `GET /v1/events/poll` → `stream_head_cursor` | `273428` @ `2026-09-16T13:05:13Z` |
| `retention_floor_cursor` | same response | `1` |

- `EFB_CURRENT_CHECKPOINT = 272548` **≥ 272548** — requirement satisfied. The value was read from the live
  file on disk, **not** hardcoded from historical context.
- `AGENT_CURRENT_CHECKPOINT = 195927` is **recorded only**; nothing was modified.
- `CORE_STREAM_HEAD` is a moving value: it advances by one `account.status` heartbeat roughly every 5 s
  (273403 → 273428 across the session). The number above is a timestamped snapshot, not a constant.

### 3.1 Active-Core production DB access gate

| Gate | Required | Observed |
| --- | --- | --- |
| `ACTIVE_CORE_RAW_SQLITE_READS` | `0` | `0` |
| `ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS` | `0` | `0` |

Evidence: the full host-command log for this preflight is pinned at
`tmp/rc14-preflight/preflight_core_db_access_command_log.txt` and was scanned with the project guard:

```bash
python scripts/forensics/check_forbidden_live_core_db_access.py --selftest
python scripts/forensics/check_forbidden_live_core_db_access.py --json \
  tmp/rc14-preflight/preflight_core_db_access_command_log.txt
```

```
CI_NEGATIVE_TESTS = PASS
CI_POSITIVE_TESTS = PASS
…
"findings": [],
"RAW_SQLITE_GUARD": "PASS",
"GENERIC_FILE_OPEN_GUARD": "PASS",
"SCRATCH_GUARD": "PASS"
```

The only raw SQLite reads in this preflight targeted:

1. the **agent's own** database (`…/agent-data/wechat-agent.sqlite`), which is **not** part of the
   protected Core set, read read-only while the agent was stopped; and
2. a **RAM snapshot** of the EFB effect ledger at `/dev/shm/ledger-probe.sqlite` (per
   `docs/DEV_SHM_DISPOSABLE_SNAPSHOT_LIFECYCLE_POLICY`), deleted afterwards with `/dev/shm` verified
   empty (`count=0`).

`CORE_API_GAP = NONE` — every Core-side value this preflight needed was available through the API
(`stream_head_cursor` and `retention_floor_cursor` are both exposed). `AGENT_CURRENT_CHECKPOINT` is
agent-local durable state, not a Core observability field, so its absence from the Core API is not a
`CORE_API_GAP`. No raw Core DB access was used as a substitute for any Core field.

---

## 4. Telegram credential readiness

| Check | Result |
| --- | --- |
| File exists | YES — `…/blueset.telegram/config.yaml` (78 B) |
| Token non-empty | YES — 48 characters |
| Token shape | 1 colon, 10 leading digits before the colon → valid BotFather bot-token shape |
| Admin configured | YES — `admins: [407680985]` |
| Owner / mode | `root:root`, mode `600` |
| Runtime-readable | YES — the EFB container runs as root and binds `…/efb-profile` → `/root/.ehforwarderbot` |
| Token printed to logs | **NO** — always emitted as `<REDACTED>` |
| Telegram API called | **NO** |

**`CREDENTIAL_READY = YES`**

---

## 5. Production profile / master-channel gate

`profiles/default/config.yaml`:

```yaml
master_channel: efb_qual_master.QualMasterChannel
slave_channels:
  - wechat.linux
middlewares: []
```

- `PRE_AUTH_MASTER_CHANNEL = efb_qual_master.QualMasterChannel`
  — a **qualification** master (`modules/efb_qual_master.py`, 6816 B), **not** `blueset.telegram`.
- `profiles/default/config.yaml` is byte-identical to `profiles/default/config.yaml.pre_live_snap`
  (both 100 B, mtime `2026-09-14T17:27`).
- Profile mtimes are all pre-dating this preflight: `config.yaml` `2026-09-14T17:27`,
  `wechat.linux/config.yaml` `2026-09-14T17:27`, `blueset.telegram/config.yaml` `2026-09-15T17:26`.
  **No profile file was modified.**
- Consequence: with a qualification master armed and `native_reply=false`, the profile as it stands
  **cannot** deliver to a real Telegram chat. The real Telegram credential exists but is not wired.

**`PROFILE_STATE_SAFE = YES`** (pre-live state, no armed production delivery path)

---

## 6. EffectLedger preservation (strict read-only forensics)

Forensics were run against a RAM snapshot; the production file was never opened for write.

```sql
PRAGMA user_version;    -- 0
PRAGMA journal_mode;    -- wal
PRAGMA quick_check;     -- ok
PRAGMA integrity_check; -- ok
```

Schema (live) — byte-identical to the frozen `EffectLedger._init_db()` DDL, no extra/missing columns:

```sql
CREATE TABLE effect_ledger (
  consumer_id TEXT NOT NULL, effect_id TEXT NOT NULL, account_id TEXT NOT NULL,
  message_id TEXT NOT NULL, efb_uid TEXT NOT NULL DEFAULT '',
  event_type TEXT NOT NULL DEFAULT 'message.created',
  status TEXT NOT NULL DEFAULT 'RESERVED',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  details_json TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (consumer_id, effect_id));
CREATE INDEX idx_effect_ledger_status ON effect_ledger(consumer_id, status);
CREATE INDEX idx_effect_ledger_account_msg ON effect_ledger(account_id, message_id);
```

State histogram:

| Field | Value | Count |
| --- | --- | --- |
| `status` | `DELIVERED` | 274 |
| `status` | `RESERVED` | 0 |
| `status` | `UNCERTAIN` | 0 |
| `status` | `PENDING_MEDIA` | 0 |
| `status` | `MEDIA_FAILED` | 0 |
| `consumer_id` | `efb-linux-wechat:wechat.linux` | 274 |
| `account_id` | `f-live-a` | 274 |
| `event_type` | `message.created` | 274 |

Non-destruction evidence:

| Check | Result |
| --- | --- |
| `rm` / `truncate` / `VACUUM` / `VACUUM INTO` | NOT performed |
| Schema migration / `ALTER TABLE` | NOT performed |
| Table recreate / journal reset | NOT performed |
| Main DB size | `208896` B |
| Main DB `mtime` / `ctime` | `2026-09-15 19:55:20.851585019 +0800` — **unchanged during this preflight** |
| Row count | `274` (matches the pre-preflight baseline) |

**`SCHEMA_PREPARATION_REQUIRED = NO`**

Reason: `PENDING_MEDIA`, `MEDIA_FAILED`, and `UNCERTAIN` are **values of the existing `status TEXT`
column**, not new columns or new tables. The frozen source declares them as constants
(`EffectLedger.py:41-44`) and reads/writes them through the existing column
(`mark_media_pending`, `reserve_pending_effect`, `mark_media_failed`, `pending_media`,
`mark_uncertain`). The live schema therefore already fully represents every state the frozen
candidate can produce — **no migration is required, and none was attempted**.

**`EFFECT_LEDGER_PRESERVED = YES`**

---

## 7. Durable message mapping (`core-message-mapping.sqlite3`)

`core-message-mapping.sqlite3` **does not exist on disk** at
`…/wechat.linux/`. Per the preflight protocol this is **not** automatically a FAIL, provided the
frozen initialisation is atomic, non-destructive, and fail-closed — which it is:

| Requirement | Evidence from frozen source | Verdict |
| --- | --- | --- |
| Initialisation strategy non-destructive | `MessageMapping.py:48` `CREATE TABLE IF NOT EXISTS message_mapping (…)`; `:67` / `:79` `CREATE INDEX IF NOT EXISTS` — idempotent, no `DROP`, no `DELETE`, no migration step | PASS |
| Explicit consumer / account / chat scope | PK `(consumer_id, account_id, chat_id, efb_uid)`; index on `(consumer_id, account_id, chat_id, core_message_id)`; second index on `(consumer_id, telegram_chat_id, telegram_message_id)`. Reply resolution is scoped by consumer+account+chat, so no cross-account / cross-chat guess is possible | PASS |
| Restart-safe | `record()` is an `INSERT … ON CONFLICT … DO UPDATE` where each column keeps its stored value unless the incoming value is non-empty (`CASE WHEN excluded.x != '' THEN excluded.x ELSE message_mapping.x END`). A restart cannot blank previously persisted fields | PASS |
| Cannot overwrite existing ledger / profile | Separate database file (`core-message-mapping.sqlite3`) created under `resolved_data_path`; it never opens `core-effect-ledger.sqlite3`, `core-event-cursor.json`, or any profile file | PASS |
| Safe first-start empty creation | `__init__` → `Path.mkdir(parents=True, exist_ok=True)` then `_init_db()`; a missing file is created empty and immediately usable | PASS |
| Fail-closed on bad input | `record()` returns `False` when `consumer_id`, `account_id`, `chat_id`, or `efb_uid` is empty — it refuses rather than writing an unscoped row | PASS |
| Historical cleanup required | none — no historical data exists to reconcile | **NO** |

**`MAPPING_DB_PRESENT = NO` (expected, safe) · `MAPPING_INIT_NON_DESTRUCTIVE = YES` ·
`MAPPING_SCOPE_EXPLICIT = YES` · `MAPPING_RESTART_SAFE = YES` ·
`MAPPING_FIRST_START_SAFE_EMPTY_CREATE = YES` · `MAPPING_HISTORICAL_CLEANUP_REQUIRED = NO`**

---

## 8. Pending-media forward compatibility

| Check | Result |
| --- | --- |
| Separate pending-media store | none — pending media is a ledger `status` value (`PENDING_MEDIA`), retried via `_retry_pending_media()` → `EffectLedger.pending_media()` |
| Terminal failure state representable | YES — `MEDIA_FAILED` |
| Crash/failure state representable | YES — `UNCERTAIN` (fail-closed `BLOCKED_UNCERTAIN_EFFECT`) |
| Live rows needing conversion | 0 (`PENDING_MEDIA = 0`, `MEDIA_FAILED = 0`) |
| Schema change needed for the live window | none |

**`PENDING_MEDIA_SCHEMA_READY = YES` · `DESTRUCTIVE_MIGRATION_REQUIRED = NO`**

---

## 9. Live qualification taskbook seal

| Item | Expected | Observed |
| --- | --- | --- |
| `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md` SHA256 | `0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511` | `0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511` |
| Pinned source commit (§2/§2.1/§6) | `91a69cef323d120f0e32196917a630d2cf3baa88` | matches frozen candidate |
| Pinned image digest (§2/§2.1) | `sha256:d45029d5…456241` | matches frozen candidate |
| Pinned OCI revision | `91a69cef…` | matches frozen candidate |
| Pinned production EFB checkpoint | `272548` | matches live value |

**`TASKBOOK_SEAL = MATCH` · `TASKBOOK_IMAGE_PIN = MATCH`**

---

## 10. Protected-service baseline

Recorded before the live window. Any change to these values between now and live start is an abort signal.

| Service | Container ID | Image ID | RepoDigest | Restart count | State |
| --- | --- | --- | --- | --- | --- |
| Core | `bbff02b4ae5b` | `sha256:661967daae8ad445ff52433561f490b43f6f4bbc1fc5a545ec3a2c125de1c1aa` | `…wechat-hub-core@sha256:7d9259a420d152706bca80a28c9757633e527fd0f681fa32d9883048878d3ab5` | 0 | running / healthy |
| Console | `cce13a59dad2` | `sha256:fcd9749d4944e5d9f8b99730f3b5e55b12359566a5c41b691d35fe43774fd282` | `…wechat-hub-console@sha256:8712f8675b41959c600cee2a57f6434854134afb37a81f7ae026c19ba31274dd` | 0 | running / healthy |
| Runtime | `d21960eef445` | `sha256:1c43c1e314dce64d1cac9e8eab802811b926f5e8ae0ed830653fa8519b5a6e2b` | `…wechat-hub-runtime@sha256:5a2454a6a772852a7c38b0e4321345db1fcb5bd6eb038f018d3067d40dd02158` | 0 | running / healthy |
| AgentWechat A | `44559e58c4fe` | `sha256:b177fedfc241e8ad8b7f493ae95b8632948e6c018338cfddc31c23f4a00f2dca` | `…agent-wechat@sha256:87b055e3ed2b9b5091421b15ed802c3e9f36e0029d11ea1f12a727bb5f3c85e4` | 0 | running |
| AgentWechat B | `a6c2e3ee61e1` | `sha256:b177fedfc241e8ad8b7f493ae95b8632948e6c018338cfddc31c23f4a00f2dca` | `…agent-wechat@sha256:87b055e3ed2b9b5091421b15ed802c3e9f36e0029d11ea1f12a727bb5f3c85e4` | 0 | running |
| Agent | `f4d2f2773e85` | `sha256:ee986b4e45ccaa8f0d232e752aa1eb9724662839dc19b3ddfcfafff8c15eed58` | `…wechat-hub-agent@sha256:c93007426738733c3bb9c3021e43edfd724c7c5455a2b7cf7a7b9101733f463a` | 0 | exited (0) |
| EFB | `2d73f4c1a496` | `sha256:9e7bb21506ce0c65be36f9e338521c8e6ef87037cb922a888ed31108adffbe81` | `…efb-linux-wechat-slave@sha256:9c53faa4680fbbbac3e0993169595eb8d14a55bf4fd1c88461d1f2956c5f994a` | 0 | exited (137) |

Additional recorded EFB container facts (needed to reconstruct the live start):

```text
compose project        = wechat-hub-f-live
compose service        = efb-multi
compose config files   = /mnt/disk3/appdata/wechat-hub-f-live/docker-compose.yml,
                         /mnt/user/appdata/wechat-hub-f-live/docker-compose.rc14-optional-efb-retry2-candidate.yml
network mode           = wechat-hub-f-live-internal
entrypoint / args      = ehforwarderbot -p default
mount                  = /mnt/user/appdata/wechat-hub-f-live/efb-profile -> /root/.ehforwarderbot (rw)
restart policy         = no
```

---

## 11. Live-window readiness items

**Functional gates carried by the sealed live taskbook §1 / §7 (must all pass, all six `LQ-01…LQ-06`):**

- **F1** — original media correctness (deliver the original ready object, never a thumbnail).
- **F2** — durable delayed-media delivery and duplicate suppression.
- **F3** — durable, scoped reply mapping and visible quote fallback.
- **F4** — actual sender and self identity.
- `LQ-01` original image · `LQ-02` sticker delayed-ready and restart · `LQ-03` Telegram reply visible
  fallback · `LQ-04` self and peer identity · `LQ-05` durable reply mapping across restart ·
  `LQ-06` duplicate delivery zero.

**Mapping restart:** `LQ-05` must show that `core-message-mapping.sqlite3` survives a candidate restart,
that reply resolution stays scoped to `(consumer_id, account_id, chat_id)`, and that no cross-account or
cross-chat mapping is ever accepted. First-start creation of the empty mapping DB is expected and must be
recorded as such, not treated as an anomaly.

**Replay zero-duplicate:** `LQ-06` must show `duplicate Telegram deliveries = 0`, that each source message
has at most one committed external effect, and that `RESERVED` / `DELIVERED` / `MEDIA_FAILED` / `UNCERTAIN`
semantics match observed external state with no READY-before-reservation violation.

**Operational pre-live conditions identified by this preflight:**

- **R1** — Re-read `EFB_CURRENT_CHECKPOINT` immediately before start; it must still be exactly `272548`.
- **R2** — Re-confirm `wechat-hub-f-live-efb` is absent/stopped and that no second consumer exists.
- **R3** — Start exactly **one** instance pinned to `sha256:d45029d5…456241`; no rebootstrap.
- **R4** — **Reconstruct the candidate compose overlay.** The EFB container's recorded config files list
  `docker-compose.rc14-optional-efb-retry2-candidate.yml`, which **no longer exists on disk**; the live
  base `docker-compose.yml` contains only `runtime`, `core`, `console` (no `efb-multi`). The operator must
  author and pin a new candidate overlay that starts one `efb-multi` instance on network
  `wechat-hub-f-live-internal` with the existing `efb-profile` mount and no rebootstrap.
- **R5** — Switch `master_channel` from `efb_qual_master.QualMasterChannel` to `blueset.telegram` **only**
  inside the approved live window, and revert afterwards (`config.yaml.pre_live_snap` is the restore point).
- **R6** — Confirm the host is free of concurrent benchmarks before the live window: the leftover
  `run_v5_matrix.sh` sweep (host PID `2265125`, currently running `v5-C1-run1`) must have finished or been
  stopped, so that delayed-media timing observations are not contaminated by unrelated host I/O.

---

## 12. Result

```text
RC14_EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT_RESULT

IMAGE_LINEAGE = PASS
SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_DIGEST = sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
OCI_REVISION = 91a69cef323d120f0e32196917a630d2cf3baa88

RETRY2_RESULT = FAIL_HISTORICAL_PRESERVED
RETRY2_CROSS_RUN_REPLAY_EVIDENCE = INDETERMINATE_HISTORICAL
PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED
EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS

CORE = RUNNING_HEALTHY
AGENT = STOPPED
EFB = STOPPED
CONSOLE = RUNNING_HEALTHY
RUNTIME = RUNNING_HEALTHY
AGENTWECHAT = RUNNING
CONCURRENT_LIVE_QUALIFICATION = NO

CORE_ACCESS_MODE = HTTP_API_ONLY
ACTIVE_CORE_RAW_SQLITE_READS = 0
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
CORE_API_GAP = NONE
EFB_CURRENT_CHECKPOINT = 272548
AGENT_CURRENT_CHECKPOINT = 195927
CORE_STREAM_HEAD = 273428

CREDENTIAL_READY = YES
PROFILE_STATE_SAFE = YES
PRE_AUTH_MASTER_CHANNEL = efb_qual_master.QualMasterChannel

EFFECT_LEDGER_PRESERVED = YES
SCHEMA_PREPARATION_REQUIRED = NO
LEDGER_DELIVERED = 274
LEDGER_RESERVED = 0
LEDGER_UNCERTAIN = 0
LEDGER_PENDING_MEDIA = 0
LEDGER_MEDIA_FAILED = 0

MAPPING_DB_PRESENT = NO
MAPPING_INIT_NON_DESTRUCTIVE = YES
MAPPING_SCOPE_EXPLICIT = YES
MAPPING_RESTART_SAFE = YES
MAPPING_HISTORICAL_CLEANUP_REQUIRED = NO

PENDING_MEDIA_SCHEMA_READY = YES
DESTRUCTIVE_MIGRATION_REQUIRED = NO

TASKBOOK_SEAL = MATCH
TASKBOOK_IMAGE_PIN = MATCH

EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT = PASS
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = YES

ACTION = STOP
```

### Disclosures

- **D1 — EFB container exit 137 is historical.** `wechat-hub-f-live-efb` is in the preserved
  `exited (137)` state left by the Retry2 teardown (`2026-09-15T11:59:31Z`), identical before and after
  this preflight. It is not a running process and does not affect the product-semantics shutdown gate.
- **D2 — Concurrent host benchmark.** The leftover V5 sweep `run_v5_matrix.sh` (PID `2265125`) is
  running `v5-C1-run1` on the same host. It uses a sealed mock Core and a private `/data` volume, touches
  no production resource, and was **not** stopped (this preflight is read-only). It is carried forward as
  condition **R6**. `CONCURRENT_LIVE_QUALIFICATION` is reported `NO` on the strict reading
  "a second consumer attached to the production Core/Agent/EFB path"; the raw fact is stated in full in §2.
- **D3 — Read-only forensics created ledger sidecar files.** After the preflight's read-only ledger
  forensics, `core-effect-ledger.sqlite3-wal` (0 bytes) and `core-effect-ledger.sqlite3-shm` (32768 bytes)
  carry `mtime/ctime 2026-09-16 21:00:59–21:01:06 +0800`. The main database file is untouched
  (`mtime/ctime 2026-09-15 19:55:20`, 208896 B, 274 rows, `quick_check ok`). A zero-length `-wal` carries
  no frames, so no data was written and none can be replayed. No process holds the file. The sidecars are
  inert and were left in place deliberately — removing them would itself be a filesystem modification.
- **D4 — Candidate compose overlay missing.** See **R4**. The overlay recorded in the EFB container's
  compose labels (`docker-compose.rc14-optional-efb-retry2-candidate.yml`) no longer exists, and the live
  base compose has no `efb-multi` service. The live window cannot start the candidate until a pinned
  overlay is authored. This is a start-procedure gap, not a candidate defect.
- **D5 — Sealed taskbook internal inconsistency (preserved, not edited).** The sealed live taskbook §5
  precondition still cites the Retry2 source lineage (`af3707d` + Core `2caee27` / `1e5eddd`), while §2/§2.1
  and §6 pin the functional candidate at `91a69cef…`. §6 governs candidate startup, so the preflight used
  `91a69cef…`. The taskbook is sealed and was **not** modified; the operator should treat the §5 line as
  a stale historical precondition.
- **D6 — `AGENT_CURRENT_CHECKPOINT` read method.** It was read from the agent's own SQLite
  (`agent_meta.core_cursor`) while the agent container was stopped. That database is **not** part of the
  protected production-Core set (`…/core-data/core/wechat_core.sqlite` + `-wal`/`-shm`), and no Core field
  was obtained this way. `CORE_API_GAP = NONE`.

**`ACTION = STOP` — Production Live was not executed.**
