# RC.14 EFB Functional — Exact-Digest Shutdown Measurement Requalification RESULT

> Executed: 2026-09-16
>
> Protocol: `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md`
> + errata 1, 2, 3 (all sealed before the corresponding run)
>
> **Verdict: `EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = INDETERMINATE`**

## 0. Return block

```text
FUNCTIONAL_SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST  = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION  = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_UNCHANGED          = YES
                           (host image ID sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a
                            OCI revision label 91a69cef323d120f0e32196917a630d2cf3baa88, re-read after the run)

RUN_COUNT = 33   (10 gate arm A + 10 BASELINE_SLEEP + 10 BASELINE_CLEAN + 3 supplementary arm B)

PROCESS_SHUTDOWN_SEC_RUNS = 1.002628,1.002460,1.002575,1.002964,1.002526,1.002382,1.002578,1.002840,1.002502,1.002479
PROCESS_SHUTDOWN_MAX      = 1.002964
PROCESS_SHUTDOWN_P50      = 1.002551

CONTAINER_DIE_SEC_RUNS = 2.639504,1.707167,2.506627,2.634562,2.177599,5.037137,2.664360,1.609843,4.919283,1.873740
CONTAINER_DIE_MAX      = 5.037137
CONTAINER_DIE_P50      = 2.570595

CLI_RETURN_SEC_RUNS = 2.642038,1.577230,2.508624,2.398336,2.027104,5.039064,1.835065,1.501375,4.921641,1.631987
CLI_RETURN_MAX      = 5.039064
CLI_RETURN_P50      = 2.212720

BASELINE_CONTAINER_DIE_P50 = 1.390233   (BASELINE_CLEAN, primary comparator)
                             3.259544   (BASELINE_SLEEP, SIGKILL path, contrast only)
BASELINE_CLI_RETURN_P50    = 1.044680   (BASELINE_CLEAN)
                             3.028376   (BASELINE_SLEEP)

EXIT_CODES              = [0,0,0,0,0,0,0,0,0,0]
SIGKILL_COUNT           = 0
DOCKER_KILL_EVENT_COUNT = 0            (kill events carrying signal=9)
                          total kill events = 10, all carrying signal=15 (SIGTERM delivery, expected)

CHECKPOINT_FLUSH_PASS    = 10/10
LEDGER_FLUSH_PASS        = 10/10
DELIVERY_SUPPRESSED_PASS = 10/10
ORPHAN_COUNT             = 0

PREVIOUS_STRICT_WALL_GATE             = FAIL_PRESERVED
EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = INDETERMINATE

PRODUCTION_EFB_TOUCHED = NO
```

Authorization consequence, as pre-registered in taskbook §9:

```text
EFB_FUNCTIONAL_CANDIDATE_READY            = NOT_GRANTED  (PASS was not achieved)
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY   = NO
```

## 1. Verdict derivation

The sealed decision table (taskbook §4.1, as corrected only by erratum 1 §1) was
applied literally.

```text
PASS requires                                   RESULT        MET
  T_PROCESS < 2.0 s                 10/10        10/10         YES
  T_CONTAINER_DIE < 2.0 s           10/10         3/10         NO
  exit_code == 0                    10/10        10/10         YES
  Docker kill events (signal=9)          0            0        YES
  SIGKILL                                0            0        YES
  final durable flush               PASS 10/10   PASS 10/10     YES
  delivery_suppressed               PASS 10/10   PASS 10/10     YES
  orphan_process_thread                  0            0        YES
  -> PASS not achieved

FAIL triggers                                   RESULT
  any exit_code == 137                    none (all 0)
  any kill event with signal == 9         none
  any SIGKILL                             none
  any durable flush failure               none (checkpoint_flush, ledger_flush,
                                          delivery_suppressed, cursor 272548,
                                          core cursor 272548 all 10/10)
  any T_PROCESS >= 2.0 s                  none (max 1.002964)
  -> FAIL not triggered

INDETERMINATE (sealed wording)
  "T_PROCESS < 2.0s 10/10 and no FAIL trigger, but T_CONTAINER_DIE cannot be
   reliably proven < 2.0 s for all 10 runs (including the case where reliable
   measurement yields >= 2.0 s, which is not itself a FAIL trigger)"
  -> CONDITION MET

EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = INDETERMINATE
```

The `T_CONTAINER_DIE` timestamps were measured reliably (every run produced a
non-null `die` event `timeNano`, an independent `docker wait` completion, and a
non-null `State.FinishedAt`). The result is therefore a **measured** `>= 2.0 s`
on 7 of 10 runs, not an inability to measure. It is not a FAIL trigger, and it is
not a PASS. It is INDETERMINATE, exactly as the protocol pre-registered.

## 2. Why — the host decomposition

The requalification's purpose was to stop conflating three times. Measured
per-run, on the exact digest, the three times decompose as follows
(medians of the 10 gate runs; `SIGTERM` here is the daemon's `kill(signal=15)`
event timestamp, which agrees with `SIGTERM + T_PROCESS = FinishedAt` to
2.8–4.0 ms on every run):

```text
T0  docker stop invoked
 |  0.268 s   P50 (min 0.132 / max 2.304)   CLI + daemon + signal delivery
SIGTERM delivered
 |  1.003 s   P50 (min 1.002382 / max 1.002964)   T_PROCESS (product)
process exited  ==  State.FinishedAt
 |  1.137 s   P50 (min 0.457 / max 3.365)   daemon post-mortem cleanup
Docker die event
 |  -0.119 s  P50                            CLI already returned before this
docker stop CLI returned
```

So the two host-side overhead terms are:

1. **`docker stop` invocation → SIGTERM delivery**: P50 0.268 s
   (the CLI process fork/exec + API round trip + daemon signal dispatch).
2. **process exit → Docker `die` event**: P50 1.137 s
   (container teardown / unmount of a 1.05 GB layered image on the degraded HDD
   array).

And the quantity the original gate blamed is neither:

```text
T_CLI - T_CONTAINER_DIE  per run, gate arm A
  0.002534, -0.129937, 0.001997, -0.236226, -0.150495,
  0.001927, -0.829295, -0.108468, 0.002358, -0.241753
  P50 = -0.119 s
```

**`T_CLI - T_CONTAINER_DIE` is not a cleanup term at all — it is negative on
6 of 10 runs.** `docker stop`'s CLI returns *before* the daemon emits the `die`
event. The two are asynchronous host-side notifications, not an ordered
before/after pair, so their difference cannot be attributed to "daemon/CLI
cleanup" in the way the baseline question assumed. The host overhead lives
entirely inside `docker stop invoked → die event`, split between the two terms
above.

### 2.1 The baseline proves the criterion is host-dominated

`BASELINE_CLEAN` is a container with **zero product logic** — `python` idling,
exiting 0 immediately on SIGTERM. Its only job is to show the host floor.

```text
BASELINE_CLEAN (10 runs, no product logic at all)
  finished_at_sec   min 0.137570  P50 0.241401  max 1.828117
  die_event_sec     min 0.562848  P50 1.390233  max 4.139681     <- 8/10 < 2.0 s
  cli_return_sec    min 0.465369  P50 1.044680  max 3.697078
  exit_codes        all 0, no signal-9 kill event
  die_event - finished_at  P50 1.028678 s
```

A container that does nothing but exit cleanly already fails
`T_CONTAINER_DIE < 2.0 s` on 2 of 10 runs and sits at a P50 of 1.39 s, i.e.
within 0.61 s of the threshold, purely from daemon cleanup. The gate arm's
3/10 pass rate is the same phenomenon with a 1.003 s product term added on top.

`BASELINE_SLEEP` (the sealed baseline) is reported for completeness but is a
different exit path: `sleep` as PID 1 has no default signal action, so SIGTERM is
ignored, Docker's 2 s grace expires, and SIGKILL is used.

```text
BASELINE_SLEEP (10 runs)
  exit_codes        all 137
  kill signal=9     10/10
  sigkill_event_sec P50 2.455959
  finished_at_sec   P50 2.456771
  die_event_sec     P50 3.259544
  cli_return_sec    P50 3.028376
```

Neither baseline is subtracted from product latency, per taskbook §7.

## 3. The product result, stated cleanly

```text
PRODUCT SHUTDOWN, exact digest, 10/10
  T_PROCESS  min 1.002382  P50 1.002551  max 1.002964   -> 10/10 < 2.0 s
  exit_code 0                                             -> 10/10
  SIGKILL / kill(signal=9)                                -> 0
  checkpoint_flushed / ledger_wal_checkpointed            -> 10/10
  delivery_suppressed                                     -> 10/10
  checkpoint cursor 272548 (local + Core-acked)           -> 10/10
  repeated == false                                       -> 10/10
  orphan process/thread/container                         -> 0
```

The product exits on SIGTERM in 1.0024–1.0030 s, on 10 of 10 runs, with a
0.0006 s spread. Every frozen-evidence assertion passed on every run.

### 3.1 The bound is structural, not lucky

`ShutdownCoordinator` bounds the shutdown by construction:

```text
worst-case T_PROCESS
  = slave_drain budget (shutdown_slave_drain_budget_sec = 0.75)
  + master stop budget (shutdown_master_budget_sec   = 1.0)
  = 1.75 s  <  2.0 s
```

The qualification fixture installs a master whose `stop_polling` blocks for 12 s,
so the bounded branch is exercised on every run. Confirmed on all 10 gate runs:

```text
master_stop_bounded_out = true     10/10
master_stop_completed   = false    10/10
master_stop_elapsed_sec ~ 1.0003 s 10/10   (the budget, not the 12 s master, ends it)
phases: slave_drain 0.002015-0.002558 (P50 0.002219) /
        suppress_dispatch 0.000005-0.000007 /
        master_stop_bounded 1.000267-1.000382
sum(phases) == elapsed_sec within 18 microseconds on every run
```

So `T_PROCESS < 2.0 s` holds because the two budgets sum below the threshold, not
because the fixture happens to be fast. The observed 1.0026 s is the
`master_stop_bounded` budget plus the real 2.0–2.6 ms drain (P50 2.22 ms).

## 4. Container-internal shutdown evidence — the five marks

The frozen in-image instrument emits **relative** elapsed values, not absolute
monotonic stamps, so the five required marks are reported two ways.

### 4.1 Primary — consumed from frozen evidence as offsets from signal receipt

The coordinator's clock starts at the first statement of the signal-triggered
`run()`, so offsets from it are offsets from signal receipt (taskbook §5.3).
Gate arm A, 10/10:

```text
signal_received_monotonic            := 0.000000  (reference, by definition)
delivery_suppressed_monotonic        := 0.000006  P50 (end of phase suppress_dispatch;
                                                   0.000005-0.000007 across runs)
checkpoint_flush_completed_monotonic := 0.002219  P50 (end of phase slave_drain;
                                                   0.002015-0.002558 across runs)
ledger_flush_completed_monotonic     := 0.002219  P50 (same drain call, ledger step
                                                   inside it, bounded by drain end)
exit_requested_monotonic             := 1.002551  P50 (= evidence.elapsed_sec)
```

`CONTAINER_MONOTONIC_MARKS = DERIVED_OFFSETS_FROM_SIGNAL_RECEIPT`.

### 4.2 Secondary — absolute monotonic marks from the Arm B instrument (3 runs)

Arm B attaches read-only observation wrappers on the product's own injection
seams and records genuine absolute `time.monotonic()` values. Run 1, raw:

```text
signal_received_monotonic             453957.371353129
coordinator_run_start_monotonic       453957.371518543   (+0.000165)
delivery_suppressed_monotonic         453957.371531527   (+0.000178)
checkpoint_flush_completed_monotonic  453957.373388413   (+0.002035)
ledger_flush_completed_monotonic      453957.373760199   (+0.002407)
exit_requested_monotonic              453958.374547477   (+1.003194)
```

All three runs, as offsets from `signal_received_monotonic`:

```text
run   suppressed   checkpoint_flush   ledger_flush   exit_requested
1     0.000178     0.002035           0.002407       1.003194
2     0.000186     0.002031           0.002329       1.002956
3     0.000432     0.006713           0.007719       1.008930
```

### 4.3 The derivation in §4.1 is validated, and conservative

```text
derived (frozen evidence.elapsed_sec)  -  instrumented (absolute marks)
  run 1  -0.000469 s
  run 2  -0.000409 s
  run 3  -0.000597 s
```

The frozen-derived `T_PROCESS` is accurate to within **0.6 ms**, and it errs
**conservative**: it understates the true signal→exit-request interval by
0.4–0.6 ms, because Arm B's signal handler stamps `signal_received_monotonic`
one handler dispatch before the coordinator's clock starts. The frozen evidence
never flatters the product.

### 4.4 The tail the frozen evidence cannot see

`evidence.elapsed_sec` is captured *before* the evidence file is written, so the
frozen record structurally cannot bound the final write/flush/exit tail. Arm B
measures it:

```text
post_exit_request_to_die_sec   0.492527   1.038063   1.755949   (3 runs)
```

This tail is host-side (evidence-file write + `os._exit` + daemon teardown), not
product work. It is the reason `T_CONTAINER_DIE` and `T_CLI` cannot serve as
product measurements on this host.

## 5. Historical results, preserved

Nothing in this requalification edits, re-scores, or re-labels the earlier gate.

```text
PREVIOUS_STRICT_WALL_GATE  = 2/5 wall < 2.0s   -> FAIL_PRESERVED
PREVIOUS_EXIT_CODES        = [0,0,0,0,0]       -> PRESERVED
PREVIOUS_SIGKILL           = 0                 -> PRESERVED
PREVIOUS_INTERNAL_SHUTDOWN = ~1.003s 5/5       -> PRESERVED
PREVIOUS_FINAL_FLUSH       = PASS 5/5          -> PRESERVED
```

The new protocol is a separate, separately sealed document. The earlier gate's
own taskbook SHA256 `0f7624cc…4ff511` is unchanged.

## 6. Protocol deviations and defects, disclosed

All were sealed before the run they affected. No acceptance criterion was
relaxed at any point.

| ID | Sealed in | Nature | Effect on verdict |
| --- | --- | --- | --- |
| D1 | taskbook §8 | Arm A profile uses `startup_healthcheck: false` because the frozen in-image stub returns `contract_version: "v1"` while `Core.py` requires integer `1`. `FROZEN_GATE_FIXTURE_BUG = PRESERVED`; image bytes untouched. | none — healthcheck is a startup probe, not on the shutdown path |
| E1-1 | erratum 1 §1 | `docker stop` emits `kill(signal=15)` on the normal path, so the sealed "any kill event" criterion was unsatisfiable by a correct product. Corrected to `kill(signal=9)`. `exit_code == 137` FAIL trigger unchanged. | verdict-neutral; SIGKILL detection strengthened |
| E1-2 | erratum 1 §2 | `sleep 600` as PID 1 ignores SIGTERM (no default signal action for PID 1), so the sealed baseline is SIGKILL-terminated. Sealed `BASELINE_SLEEP` kept and executed; `BASELINE_CLEAN` added as the clean-exit comparator. | none — baseline is evidence only |
| E1-3 | erratum 1 §3 | `FinishedAt` triangulation added. Verdict still evaluated on the sealed `T_DIE_EVENT` definition; `T_FINISHED_AT` cannot convert INDETERMINATE into PASS. | none — adds information only |
| E2 | erratum 2 | Attempt 1 (`requal_v2.sh`) produced no verdict and is discarded: `jq` without `-s` cannot iterate a JSONL events stream, so every event-derived field was `null`. Raw attempt-1 evidence retained. | none — attempt 1 contributed no data |
| E3 | erratum 3 | Arm B fixture had a Python `global` scoping syntax error; aborted before run 1. One line moved. | none — Arm B is supplementary and non-verdict-bearing |

Arm A's harness pins were verified by `sha256sum` on the host immediately before
the gate run:

```text
requal_v3.sh             f4ffe7d20990fc9a22c9831953c7576118461ee5c41d9d70bb5ebf0900d40926
arm_b_v3.sh              5d956f465f80401a7380ff09e17fab3ebc23afbea7db76e4a32ab1f89aaa7f66
marks/marks_fixture.py   2ff2e53e2706cd70bde3f45e7d9453223a58f7626cb7c78103cbd982bf28f5f9
```

## 7. Governance seals

```text
TASKBOOK        docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md
                sha256 3b2587e49acf9aee26a1df815b202e2bea54cd4509b75cfbe1c095c80bc5a4c0
                deploy commit 8b7c60ea710bdc305b902e14009b0e7e6a41f44b

ERRATUM 1       ..._TASKBOOK_ERRATUM_1.md
                sha256 3f0f35b0d721f817235c939e4eac87b9810dd5446abfb2870121ca4c05a76541
                deploy commit a5cf5b35945591c3d44c0184c2b43d3e6cd95b16

ERRATUM 2       ..._TASKBOOK_ERRATUM_2.md
                sha256 b90f86c04a8510f7c7243f5e8df5ca633033f90c8fa7da4308dcbf117ef3da79
                deploy commit 5279719fe08d2dc306695bf6abda6fa6edd66a6f

ERRATUM 3       ..._TASKBOOK_ERRATUM_3.md
                sha256 7fa26e4a03b951113c939a14e50e97856aa9e757d44c2142330de6b2570682de
                deploy commit 0a2148049c3cb61792f129150d2df8343afb8542
```

Raw evidence retained on the unraid host:

```text
/root/rc14-requal/requal_v3.json           all 30 container runs (arm a / bs / bc)
/root/rc14-requal/armB_v3.json             3 supplementary instrument runs
/root/rc14-requal/requal_v3.log            gate run stdout, per-run lines
/root/rc14-requal/armB_v3.log              Arm B stdout
/root/rc14-requal/evidence/                per-run shutdown / core / marks / events
/root/rc14-requal/attempt1/                attempt-1 raw evidence (discarded, retained)
/root/rc14-requal/attempt1_requal_v2.log   attempt-1 stdout
```

## 8. Production safety

```text
PRODUCTION_EFB_TOUCHED = NO
```

- Production EFB container `wechat-hub-f-live-efb` was observed `Exited (137)`
  before the run and `Exited (137) 23 hours ago` after it. It was never started.
- No production credential, profile, ledger, checkpoint, or mount was read or
  written. Every container ran `--network none` with a fresh temporary profile,
  temporary data/ledger directory, and the frozen in-process stub Core.
- No real Telegram or WeChat message was sent or received.
- No Production Preflight step was performed.
- Final state: 0 requalification containers, 0 containers in `status=dead`,
  0 orphans.
- Candidate image unchanged: ID `sha256:bc6efcb7…1d444a`, OCI revision label
  `91a69cef…3baa88`, identical before and after.

## 9. Conclusion

The product's shutdown is **not** the thing that failed the earlier gate.

```text
PRODUCT SHUTDOWN (T_PROCESS)          1.002382 - 1.002964 s   10/10 < 2.0 s
  exit 0, zero SIGKILL, durable flush complete, delivery suppressed,
  checkpoint 272548 durably flushed and Core-acked, zero orphans   10/10
```

What failed is the **measurement definition**. `T_CONTAINER_DIE`, taken as the
Docker `die` event, is emitted 0.46–3.36 s *after* the container process has
already exited (P50 1.14 s), because the daemon emits it after container
teardown. A container with no product logic at all already reaches a
`T_CONTAINER_DIE` P50 of 1.39 s and breaches 2.0 s on 2 of 10 runs. On this host,
neither `T_CLI` nor `T_CONTAINER_DIE` is a product measurement.

The pre-registered consequence of that fact is INDETERMINATE, and INDETERMINATE
is what is returned. It is not a product failure, and it is not a PASS.

## 10. What would close this

To convert INDETERMINATE into PASS, the protocol would need a
`T_CONTAINER_DIE` definition that is not host-cleanup-dominated — for example
`State.FinishedAt` (daemon-recorded process death), which on these 10 runs is
**9/10 below 2.0 s** (P50 1.274606, max 3.309624 on the one noisy run). That is a
protocol change, so it must be pre-registered and sealed in a new taskbook before
being run; it cannot be applied retroactively to this one.

Separately, if the intent is to bound the *host's* container-stop latency rather
than the product's, the honest targets are the two host terms identified in §2 —
`docker stop` invocation → SIGTERM delivery, and process exit → `die` event —
neither of which the product controls.
