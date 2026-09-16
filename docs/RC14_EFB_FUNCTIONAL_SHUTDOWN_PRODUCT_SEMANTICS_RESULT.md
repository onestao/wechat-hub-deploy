# RC.14 EFB Functional — Exact-Digest Shutdown Product-Semantics Requalification RESULT

> Executed: 2026-09-16
>
> Protocol: `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_TASKBOOK.md`
> (sealed before execution)
>
> **Verdict: `EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS`**

## 0. Return block

```text
SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_DIGEST  = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
OCI_REVISION  = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_UNCHANGED = YES
                  (host image ID sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a,
                   OCI revision label 91a69cef323d120f0e32196917a630d2cf3baa88,
                   both re-read after the run and identical to the pre-run values)

RUN_COUNT = 20

PROCESS_SHUTDOWN_RUNS = 1.002487,1.002571,1.002721,1.003129,1.002934,1.003489,1.003984,1.002870,1.002711,1.002217,1.003018,1.002745,1.002478,1.002797,1.002577,1.002843,1.002701,1.002112,1.003462,1.002510
PROCESS_SHUTDOWN_MAX  = 1.003984
PROCESS_SHUTDOWN_P50  = 1.002733

FLUSH_TIME_RUNS = 0.002146,0.002180,0.002359,0.002769,0.002542,0.003110,0.003541,0.002570,0.002297,0.001881,0.002682,0.002374,0.002099,0.002404,0.002189,0.002511,0.002348,0.001857,0.002996,0.002175
FLUSH_TIME_MAX  = 0.003541

EXIT_CODES = 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
SIGKILL_COUNT = 0
SIGNAL9_EVENT_COUNT = 0
EXIT137_COUNT = 0

CHECKPOINT_FLUSH_PASS = 20/20
LEDGER_FLUSH_PASS = 20/20
DELIVERY_SUPPRESSED_PASS = 20/20
ORPHAN_COUNT = 0

DIE_EVENT_TIMES_INFORMATIONAL = 2.758764,1.709039,3.220182,3.413539,4.742455,2.038541,2.850909,2.792451,1.659120,2.416403,3.336510,3.104302,2.644300,3.017451,2.041749,2.665815,2.560993,1.867194,2.984136,1.984135
CLI_TIMES_INFORMATIONAL = 2.761117,1.600519,3.222658,3.416173,4.744788,1.892158,2.852862,2.795040,1.550040,2.088585,3.338553,3.106377,2.646822,3.019736,1.923168,2.379238,2.078583,1.749474,2.531031,1.742552

PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED

EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS
EFB_FUNCTIONAL_CANDIDATE_READY = YES
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO

PRODUCTION_EFB_TOUCHED = NO
```

Authorization consequence, as pre-registered in taskbook §10:

```text
EFB_FUNCTIONAL_CANDIDATE_READY          = YES
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO
    (Production Preflight has not been executed)
-> STOP. Production Preflight was NOT entered.
```

## 1. Verdict derivation

The sealed decision table (taskbook §5.2) was applied literally. There is no
INDETERMINATE branch in this protocol, and none was needed.

```text
PASS requires                                   RESULT      MET
  20/20 T_PROCESS < 2.0 s           max 1.003984   20/20     YES
  20/20 T_FLUSH   < 2.0 s           max 0.003541   20/20     YES
  20/20 exit code == 0                            20/20     YES
  SIGKILL == 0                                        0     YES
  signal 9 event == 0                                 0     YES
  20/20 durable flush PASS                        20/20     YES
  20/20 delivery suppressed PASS                  20/20     YES
  orphan process/thread == 0                          0     YES
  -> EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS

FAIL triggers                                   RESULT
  any exit_code == 137                            none (all 0)
  any signal 9 event                              none
  any SIGKILL                                     none
  any durable flush failure                       none
  any T_PROCESS >= 2.0 s                          none (max 1.003984)
  any T_FLUSH >= 2.0 s                            none (max 0.003541)
  -> FAIL not triggered
```

No sealed evidence artifact was missing or corrupt, so the INDETERMINATE escape
clause (taskbook §5.2) was not reached. Every run produced a parseable
`shutdown-evidence.json`, a parseable `core-evidence.json`, a non-null `die`
event `timeNano`, a non-null `State.FinishedAt`, and a non-null `kill(signal=15)`
event. The harness's hard null-guards never fired.

## 2. The product result, stated cleanly

```text
PRODUCT SHUTDOWN, exact digest, 20/20
  T_PROCESS   min 1.002112  P50 1.002733  max 1.003984   -> 20/20 < 2.0 s
  T_FLUSH     min 0.001857  P50 0.002366  max 0.003541   -> 20/20 < 2.0 s
  exit_code 0                                            -> 20/20
  SIGKILL / kill(signal=9) / exit 137                    -> 0 / 0 / 0
  checkpoint_flushed / ledger_wal_checkpointed            -> 20/20 / 20/20
  delivery_suppressed                                     -> 20/20
  checkpoint cursor 272548 (local and Core-acked)          -> 20/20
  repeated == false                                       -> 20/20
  orphan process/thread/container                          -> 0
```

`T_PROCESS` spread across 20 runs is **1.872 ms**; `T_FLUSH` spread is
**1.684 ms**. Both are far below the 2.0 s threshold — the margin on
`T_PROCESS` is 0.996 s (99.8 % of the budget unused), on `T_FLUSH` 1.996 s.

### 2.1 The bound is structural, not lucky

`ShutdownCoordinator` bounds the shutdown by construction:

```text
worst-case T_PROCESS
  = slave_drain budget (shutdown_slave_drain_budget_sec = 0.75)
  + master stop budget (shutdown_master_budget_sec      = 1.0)
  = 1.75 s  <  2.0 s
```

The fixture installs a master whose `stop_polling` blocks for 12 s, so the bounded
branch is exercised on every run. Confirmed on all 20 runs:

```text
master_stop_bounded_out = true     20/20
master_stop_completed   = false    20/20
master_stop_elapsed_sec ~ 1.0003 s 20/20   (the 1.0 s budget, not the 12 s master,
                                            is what ends the phase)
phases[0].phase == "slave_drain"   20/20
sum(phases[].elapsed_sec) - elapsed_sec  = -12 us .. -20 us   (20/20, i.e. the
                                            phase ledger closes to within 20 us)
trigger == "signal:15"             20/20
hard_exit == true                  20/20
poll_stopped == true               20/20
core_session_closed == true        20/20
```

So `T_PROCESS < 2.0 s` holds because the two budgets sum below the threshold. The
observed 1.0027 s median is the `master_stop_bounded` budget plus a real
2.0–3.5 ms durable drain.

## 3. Why `T_FLUSH` is 0.002 s and not 1.0 s

`T_FLUSH` measures `SIGTERM_RECEIVED -> FINAL_DURABLE_FLUSH_COMPLETE`, which is
phase 0 (`slave_drain`). That phase quiesces the Core poll loop, flushes the
checkpoint cursor, and checkpoints the effect ledger — it is deliberately ordered
**before** the master stop precisely so durable state is safe regardless of what
the master does afterwards. It therefore completes in ~2–4 ms while the bounded
master stop consumes the remaining ~1.0 s.

This is the property the protocol was written to measure: durable state is safe
long before the grace period expires, and the process exits on its own well inside
it.

## 4. Docker evidence (per run)

```text
docker stop timeout           = 2 s exactly          20/20 (unique value 2)
docker stop rc                = 0                    20/20
docker wait rc                = 0                    20/20
state.ExitCode                = 0                    20/20
state.OOMKilled               = false                20/20
state.Running                 = false                20/20
state.Pid                     = 0                    20/20
Docker kill events signal=15  = 20/20   (SIGTERM delivery, expected on the
                                         normal docker stop path)
Docker kill events signal=9   = 0/20
exitCode 137                  = 0/20
```

`exit_code == 0` together with `SIGKILL == 0` and `kill(signal=9) == 0` is the
external proof required by taskbook §5: the candidate did **not** exhaust Docker's
2 s grace period and get force-killed.

### 4.1 Informational timings (not part of the verdict)

Recorded per taskbook §6, and explicitly excluded from the product decision:

```text
T_DIE_INFORMATIONAL   min 1.659120  P50 2.712290  max 4.742455   ( 4/20 < 2.0 s)
T_CLI_INFORMATIONAL   min 1.550040  P50 2.588927  max 4.744788
State.FinishedAt      min 1.119792  P50 1.334732  max 1.815948
SIGTERM delivery      min 0.113426  P50 0.322457  max 0.810763
```

These numbers are the empirical justification for §3 of the taskbook: the `die`
event reaches a P50 of 2.71 s and breaches 2.0 s on 16 of 20 runs on a product
whose internal shutdown is 1.0027 s. It is host/daemon-dominated, exactly as the
pre-registered rationale states, and it correctly carries no verdict weight here.

## 5. Historical results, preserved

Nothing in this requalification edits, re-scores, or re-labels any earlier gate.

```text
PREVIOUS_STRICT_WALL_GATE     = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL   = INDETERMINATE_PRESERVED
```

The earlier protocols' own seals are unchanged:

```text
RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md
    sha256 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511
RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md
    sha256 3b2587e49acf9aee26a1df815b202e2bea54cd4509b75cfbe1c095c80bc5a4c0
    + errata 3f0f35b0… / b90f86c0… / 7fa26e4a…
```

The three-time decomposition measured in the previous round (`T_PROCESS`
1.002382–1.002964 s, 10/10 < 2.0 s) is reproduced here on a different sample
(`T_PROCESS` 1.002112–1.003984 s, 20/20 < 2.0 s), which is a consistency check,
not a re-adjudication.

## 6. Protocol deviations and defects, disclosed

All were sealed before the run they affected. No acceptance criterion was relaxed
at any point.

| ID | Sealed in | Nature | Effect on verdict |
| --- | --- | --- | --- |
| D1 | taskbook §7 | The harness uses `startup_healthcheck: false` because the frozen in-image stub answers `/health` with `contract_version: "v1"` while `Core.py` requires the integer `1`. `FROZEN_GATE_FIXTURE_BUG = PRESERVED`; image bytes untouched. | none — a startup probe, not on the shutdown path; every shutdown assertion still evaluated |
| H1 | harness (sealed, unpatchable post-seal) | The harness's final *reporting* block calls `docker ps -aq --filter "status=stopped"`, which is not a valid Docker status filter; the daemon returned `invalid filter 'status=stopped'`. The line printed `residual_status_stopped=0` from an empty stdout. | none — the call sits in the post-verdict reporting block, does not call the harness `fail()` path, and touches no acceptance criterion. Disclosed rather than patched, because editing a sealed harness would invalidate the seal. |

Two observations worth recording explicitly, neither of which is a defect:

- **`residual_status_created=5`** is a host-wide count, not requalification
  residue. The five `created` containers are pre-existing production Unraid
  containers (`ollama`, `new-api`, `iptv-api`, `image-api`, `obsidian`), created
  2025-11-01 through 2026-09-16, unrelated to this image and this run. The
  requalification's own orphan filters
  (`label=rc14.prodsem.arm=p` and `status=dead`) both returned 0.
- **`poll_thread_joined = false` on 20/20 runs** is a product design property of
  the `hard_exit` path, not an orphan. The Core poll thread is quiesced
  (`poll_stopped = true`, `core_session_closed = true`) and the process then calls
  `os._exit(0)`, which destroys the whole address space including that thread.
  An orphan would be a process or thread *surviving* the container; the container
  PID namespace is destroyed on exit and the post-run host check found 0
  `image_shutdown_probe` processes. `ORPHAN_COUNT = 0` is therefore correct.

Harness pin verified **on the host** both before and after the run:

```text
prodsem_v1.sh   sha256 e04d6f5a19c3b2408f28c06e0814874ebe77fbf4cfaefa602d4d43f26cff3cd4
                11921 bytes, LF, bash -n clean
```

## 7. Governance seals

```text
TASKBOOK   docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_TASKBOOK.md
           sha256 b4111f96654df2fed6f3ff25572770fe39020850af511c42f6d305f2d664da53
           deploy commit c117ab0b5beaab5a4f8f7751c6b0820bcac2335b
           (commit contains exactly this taskbook + its .sha256)

RESULT     docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_RESULT.md
           (+ .sha256)

HARNESS    tmp/rc14-prodsem/prodsem_v1.sh
           sha256 e04d6f5a19c3b2408f28c06e0814874ebe77fbf4cfaefa602d4d43f26cff3cd4
```

Raw evidence retained on the unraid host:

```text
/root/rc14-prodsem/prodsem_v1.json     all 20 runs, machine-readable
/root/rc14-prodsem/prodsem_v1.log      gate stdout, per-run lines + aggregates
/root/rc14-prodsem/evidence/           60 files: per-run shutdown / core / events
/root/rc14-prodsem/prodsem_v1.sh       harness (sha re-verified post-run)
```

## 8. Production safety

```text
PRODUCTION_EFB_TOUCHED = NO
```

- Production EFB container `wechat-hub-f-live-efb` was observed
  `Exited (137) 24 hours ago` both **before** and **after** the run. It was never
  started.
- No production credential, profile, ledger, checkpoint, or mount was read or
  written. Every container ran `--network none` with a fresh temporary profile, a
  temporary data/ledger directory, an isolated mapping store, and the frozen
  in-process stub Core.
- No real Telegram or WeChat message was sent or received.
- No Production Preflight step was performed.
- Final state: 0 requalification containers, 0 containers in `status=dead`,
  0 host probe processes, `/dev/shm` empty (0 entries).
- Candidate image unchanged: ID `sha256:bc6efcb7…1d444a`, OCI revision label
  `91a69cef…3baa88`, identical before and after.

## 9. Conclusion

On the exact frozen digest, the product satisfies the requirement as stated in
taskbook §2, on 20 of 20 runs:

> EFB completes durable shutdown and exits normally on its own within the
> SIGTERM grace period of Docker `stop -t 2`, and does not depend on SIGKILL.

```text
T_PROCESS  1.002112 - 1.003984 s   20/20 < 2.0 s
T_FLUSH    0.001857 - 0.003541 s   20/20 < 2.0 s
exit 0, zero SIGKILL, zero signal-9, zero exit-137,
durable flush complete (checkpoint + ledger), delivery suppressed,
checkpoint 272548 durably flushed and Core-acked, zero orphans   20/20
```

```text
EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS
EFB_FUNCTIONAL_CANDIDATE_READY     = YES
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO
```

`EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY` remains **NO** because the Production
Preflight has not been executed. Per the sealed protocol, execution stops here.

```text
STOPPED BEFORE PRODUCTION PREFLIGHT.
```
