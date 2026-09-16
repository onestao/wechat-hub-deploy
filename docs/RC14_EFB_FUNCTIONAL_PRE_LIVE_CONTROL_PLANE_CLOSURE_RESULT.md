# RC.14 EFB Functional Correctness — Pre-Live Control-Plane Closure Result

> ## ⛔ `DOCUMENT_STATUS = STOPPED_BY_GATE_1`
>
> **This is NOT a completed closure.** The round halted at **§1 Concurrent Workload Gate**.
> **§2 – §9 were NOT executed.** No overlay was authored, no erratum was created, no Core API
> checkpoint read was performed, and no profile/ledger/mapping/Core state was touched.
>
> `PRE_LIVE_CONTROL_PLANE_CLOSURE = STOPPED_BY_GATE_1`
> `EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO`

- **Round:** Pre-Live Control-Plane Closure (not a Live Qualification)
- **Executed:** 2026-09-16, host UTC `13:26:29Z` – `13:27Z` (unraid `192.168.22.102`)
- **Stopped at:** §1, before any §2–§9 action
- **Predecessor:** `docs/RC14_EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT_RESULT.md`
  (`EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT = PASS`, `…_LIVE_AUTHORIZATION_READY = YES`)

---

## 1. Concurrent Workload Gate — FAILED

```text
CONCURRENT_AGENT_BENCHMARK = YES
```

Per the round protocol, the existence of a running agent benchmark requires an immediate STOP.
The benchmark was **not** killed — the protocol forbids terminating another workstream.

### 1.1 Evidence

Host observation at `2026-09-16T13:26:29Z`:

```text
root 2320222  1  0 21:17 ?  bash -c cd /root/rc14-v5 && setsid nohup bash /root/rc14-v5/repo/bench/run_v5_matrix.sh \
                            > /root/rc14-v5/matrix2.out 2>&1 < /dev/null & disown; sleep 4; echo LAUNCHED
root 2320223 2320222 0 21:17 ?  bash /root/rc14-v5/repo/bench/run_v5_matrix.sh
root 2335809 2320223 0 21:23 ?  docker run --rm --name v5-B1-run1 \
      -v <ROOT>/work:/work -v <ROOT>/bench-direct/B1-run1:/data \
      --entrypoint /usr/local/bin/python \
      ghcr.io/onestao/wechat-hub-agent@sha256:0eff09ff…c35492 \
      /work/replay_harness_v5.py --db /data/db.sqlite --workload /work/workload-forward.jsonl \
      --out /work/bench-B1-run1.jsonl --variant B1-run1 --consumer-id v5bench-B1-run1 \
      --batch 400 --events 6000 --core-mode sealed --instrument
```

```text
docker ps:  v5-B1-run1 | ghcr.io/onestao/wechat-hub-agent | Up 2 minutes | 3 minutes ago
```

Sweep script: `/root/rc14-v5/repo/bench/run_v5_matrix.sh` (5617 B, mtime `2026-09-16 21:17`).
Its own header describes it as:

> `# RC.14 Agent V5 - offline benchmark matrix (v2, order-balanced).`

and states it is an **agent** benchmark harness that
> `Never touches the production Agent/Core, their DB/WAL/SHM, or the production consumer id.
> Every arm writes to its own throwaway clone.`

It is nevertheless an **RC.14 qualification that continuously produces array I/O**, which is exactly
the class §1 gates on.

### 1.2 Sweep scope and remaining runtime

The script runs **20 arms**:

| Phase | Arms | Core mode |
| --- | --- | --- |
| Latin-square rounds 1–3 (sealed set) | 9 (`A/B/C` × 3 positions) | `sealed` |
| Latin-square rounds 1–3 (faithful set) | 9 (`A/B/C` × 3 positions) | `faithful` |
| Defect probe | 2 (`D4-v4`, `D5-v5`) | `faithful` |

Arms: `A` = V4 image + `/mnt/user` (FUSE shfs), `B` = V5 image + `/mnt/user`, `C` = V5 image + `/mnt/disk3` (direct XFS).

Observed progress in the current sweep's `matrix.log`:

```text
2026-09-16T13:26:34Z ARM_RC=0 label=B1-run1 array_after=[mdResyncAction=check P mdResyncPos=0 ] final_bytes=849993728
SUMMARY={… "variant": "B1-run1", "core_mode": "sealed", "TOTAL_EVENTS": 6000, "TOTAL_SECONDS": 108.335,
         "EVENTS_PER_SECOND": 55.384, "BATCH_P50_MS": 6662.1, "BATCH_P95_MS": 10178.5, …}
```

- Sweep started `2026-09-16T13:17Z`; 2 of 20 arms complete at `13:26:34Z` → ≈ 4.75 min per arm.
- `matrix.done` marker **absent** → the sweep is still in progress.
- **Estimated remaining runtime ≈ 85 minutes** (≈ 1 h 25 m) at the observed per-arm rate.
- Array state throughout: `{"action": "check P", "pos": 0, "size": 3907018532, "pct": 0.0, "resync": 0, "dt": 0, "active": false}` — degraded array, parity check paused, unchanged from the preflight.

### 1.3 Note on sweep re-launch

This is a **new** sweep instance. During the immediately preceding preflight the running sweep was
PID `2265125` writing `matrix.out`; it has since been replaced by PID `2320222` writing `matrix2.out`.
The sweep is therefore being re-launched, not merely finishing once — the gate will keep re-triggering
until the operator stops re-launching it.

### 1.4 Other host load (informational, not the gate)

The following running containers also produce host I/O but are **not** RC.14 qualifications and do not
by themselves trigger §1: `immich`, `acc-gateway-longtext-e2e`, `acc-ovms-longtext-e2e`, `ovms-server`,
`immich-machine-learning`, `transmission`, `PostgreSQL_Immich`, `Redis`, `CouchDB-v2.x`.
They are listed for operator awareness only.

```text
CONCURRENT_LIVE_QUALIFICATION = NO
```

No second consumer or live-qualification instance is attached to the production Core / Agent / EFB path.

---

## 2 – §9. NOT EXECUTED

| Section | Status | Reason |
| --- | --- | --- |
| §2 Core API authoritative checkpoints | **NOT EXECUTED** | Blocked by §1 STOP |
| §3 Frozen single-instance EFB overlay | **NOT EXECUTED** | Blocked by §1 STOP |
| §4 Static compose qualification | **NOT EXECUTED** | Blocked by §1 STOP |
| §5 Sealed taskbook erratum | **NOT EXECUTED** | Blocked by §1 STOP |
| §6 Profile activation plan audit | **NOT EXECUTED** | Blocked by §1 STOP |
| §7 Ledger / sidecar rule | **NOT EXECUTED** (no action was required or taken) | Blocked by §1 STOP |
| §8 Protected-service baseline refresh | **NOT EXECUTED** (metadata observed during §1 only) | Blocked by §1 STOP |
| §9 Final closure result | this document (STOP record only) | — |

Nothing was created, modified, or deleted under `release/`, `docs/`, or on the host.

---

## 10. Values observed incidentally during the §1 gate

These are the only values reported as observed. They come from the `docker ps` metadata snapshot taken
while checking the gate; **no new production read was issued** for them, and no `docker inspect` /
Core API / SQLite call was made this round.

| Service | Container | Image | State |
| --- | --- | --- | --- |
| Core | `wechat-hub-f-live-core` | `ghcr.io/onestao/wechat-hub-core` | `Up 22 hours (healthy)` |
| Console | `wechat-hub-f-live-console` | `ghcr.io/onestao/wechat-hub-console` | `Up 3 days (healthy)` |
| Runtime | `wechat-hub-f-live-runtime` | `ghcr.io/onestao/wechat-hub-runtime` | `Up 5 days (healthy)` |
| AgentWechat A | `wechat-agent-f-live-a-faf35abb` | `ghcr.io/onestao/wechat-hub-agent-wechat` | `Up 5 days` |
| AgentWechat B | `wechat-agent-testb-a7c4f6c8` | `ghcr.io/onestao/wechat-hub-agent-wechat` | `Up 5 days` |
| Agent | `wechat-hub-f-live-agent` | — | **not in `docker ps`** → STOPPED |
| EFB | `wechat-hub-f-live-efb` | — | **not in `docker ps`** → STOPPED |

`RestartCount` was **not** refreshed this round (would require a §8 `docker inspect` pass).

### Ledger / sidecar

No ledger read and no ledger mutation occurred this round. The production effect ledger and its
zero-byte `-wal` / `-shm` sidecars remain exactly as sealed by the preflight.

```text
LEDGER_NEW_READ_THIS_ROUND = NO
LEDGER_MUTATION_THIS_ROUND = NO
```

### Active-Core production DB access gate

The full host-command log for this round is pinned at
`tmp/rc14-preflight/closure_round1_core_db_access_command_log.txt` and was scanned with the project guard:

```bash
python scripts/forensics/check_forbidden_live_core_db_access.py --json \
  tmp/rc14-preflight/closure_round1_core_db_access_command_log.txt
```

```
"findings": [],
"RAW_SQLITE_GUARD": "PASS",
"GENERIC_FILE_OPEN_GUARD": "PASS",
"SCRATCH_GUARD": "PASS"
```

```text
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS = 0
```

### Original sealed taskbook

Re-hashed locally (read-only) this round:

```text
ORIGINAL_TASKBOOK_SHA256 = 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511
ORIGINAL_TASKBOOK_MODIFIED = NO
```

---

## 11. Return block

```text
FUNCTIONAL_SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_LINEAGE = PASS

CORE_API_AGENT_CHECKPOINT = NOT_EVALUATED
CORE_API_EFB_CHECKPOINT = NOT_EVALUATED
CORE_STREAM_HEAD = NOT_EVALUATED

CONCURRENT_AGENT_BENCHMARK = YES
CONCURRENT_LIVE_QUALIFICATION = NO

FUNCTIONAL_LIVE_OVERLAY = NOT_CREATED
FUNCTIONAL_LIVE_OVERLAY_SHA256 = NOT_CREATED
EFB_IMAGE_EXACT_DIGEST = NOT_EVALUATED
EFB_INSTANCE_COUNT = NOT_EVALUATED
NO_PROTECTED_SERVICE_OVERRIDE = NOT_EVALUATED
NO_NEW_HOST_PORT = NOT_EVALUATED
PRODUCTION_PROFILE_MOUNT = NOT_EVALUATED
CORE_NETWORK_PATH = NOT_EVALUATED

ORIGINAL_TASKBOOK_SHA256 = 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511
ORIGINAL_TASKBOOK_MODIFIED = NO

LIVE_EXECUTION_ERRATUM_SHA256 = NOT_CREATED
TASKBOOK_LINEAGE_CONFLICT_RESOLVED = NOT_RESOLVED_THIS_ROUND

TELEGRAM_MASTER_ACTIVATION_PLAN = NOT_EVALUATED
TELEGRAM_MASTER_RESTORE_PLAN = NOT_EVALUATED

LEDGER_NEW_READ_THIS_ROUND = NO
LEDGER_MUTATION_THIS_ROUND = NO

CORE_HEALTH = PASS
AGENT_STATE = STOPPED
EFB_STATE = STOPPED

ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS = 0

PRE_LIVE_CONTROL_PLANE_CLOSURE = STOPPED_BY_GATE_1
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO
```

`IMAGE_LINEAGE = PASS` is carried from the frozen preflight verification
(`docs/RC14_EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT_RESULT.md` §0); the candidate image was **not**
re-inspected this round.

---

## 12. Unblock condition

The round may be re-run once all of the following hold:

```text
CONCURRENT_AGENT_BENCHMARK = NO
CONCURRENT_LIVE_QUALIFICATION = NO
```

Concretely: the `run_v5_matrix.sh` sweep must have reached its `MATRIX_DONE` / `matrix.done` marker
(estimated ≈ 1 h 25 m from `2026-09-16T13:26Z`) **and must not be re-launched**. Per the round protocol
this agent did **not** terminate the sweep; stopping or deferring it is an operator decision.

After the sweep has cleared, re-run §1–§9 from the top; the frozen candidate identity, the sealed
preflight evidence, and every historical verdict remain unchanged and valid.

**`ACTION = STOP` — Production Live was not executed.**
