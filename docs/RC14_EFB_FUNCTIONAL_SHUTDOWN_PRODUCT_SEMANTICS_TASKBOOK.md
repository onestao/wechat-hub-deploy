# RC.14 EFB Functional — Exact-Digest Shutdown Product-Semantics Requalification Taskbook

> Status: **PROTOCOL FROZEN — SEALED BEFORE EXECUTION**
>
> Prepared: 2026-09-16
>
> This document is the pre-registered measurement protocol for the RC.14 EFB
> Functional **product-semantics** shutdown requalification. It defines the
> qualification criteria **before** any container is started.
>
> It does not modify, supersede, or retroactively reinterpret:
>
> ```text
> docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md
>     sha256 0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511
>     -> PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
>
> docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md
> (+ errata 1, 2, 3)
>     -> PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED
> ```
>
> This is **not** a product code change, **not** a Production Preflight, and
> **not** an authorization to touch production EFB.

## 0. Frozen Candidate Identity (immutable)

```text
SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_DIGEST  = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
OCI_REVISION  = 91a69cef323d120f0e32196917a630d2cf3baa88
```

Local image ID observed on the unraid host:
`sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a`.

Every container in this requalification is created from the digest above. No tag
reference without `@sha256:` may be used.

```text
IMAGE_UNCHANGED = YES    (re-verified after the run; image bytes never touched)
```

## 1. Hard Prohibitions

Abort immediately if any proposed action would:

- Modify Functional source at `91a69cef`.
- Rebuild, republish, retag, or re-push the Functional image.
- Modify image labels, or any image byte, including to add instrumentation.
- Start production EFB.
- Read, write, or reference production Telegram credentials.
- Read, write, or reference the production EFB profile.
- Read, write, or reference the production effect ledger.
- Read, write, or reference the production checkpoint (`272548`).
- Perform any Production Preflight step.
- Send or receive any real Telegram or WeChat message.
- Retroactively rewrite either historical conclusion:
  `PREVIOUS_STRICT_WALL_GATE` or `PREVIOUS_DIE_EVENT_PROTOCOL`.

Every container runs with `--network none`, an isolated temporary profile, an
isolated temporary data/ledger directory, an isolated mapping store, the frozen
in-process stub Core, no production credential, and no production mount. The
production EFB container `wechat-hub-f-live-efb` is observed as `Exited` and is
never started.

## 2. The product requirement (normative)

> EFB must complete durable shutdown and exit normally on its own within the
> SIGTERM grace period of Docker `stop -t 2`. It must not depend on SIGKILL.

Stated as a measurable property:

```text
within the 2 s SIGTERM grace period:
    durable state is flushed
    the process exits on its own with exit code 0
    no SIGKILL is required, and none is delivered
```

## 3. Why the product gate does not use the Docker `die` event

This is pre-registered **before** the run, and it is the entire reason this
protocol exists.

The `die` event timestamp has been independently proven, on this exact digest and
on this exact host, to include **daemon / event-delivery latency** that is not
application process lifetime. Specifically, from the sealed measurement
requalification (2026-09-16, 10 gate runs + 10 clean-exit baseline runs):

```text
- Docker emits the die event AFTER container teardown. die lagged the daemon's
  own State.FinishedAt by 0.46 - 3.36 s (P50 1.137 s).
- A container with ZERO product logic (python idle, exits 0 on SIGTERM) already
  reached a die-event P50 of 1.390 s and breached 2.0 s on 2 of 10 runs, purely
  from daemon cleanup on the degraded HDD array.
- (T_CLI - T_CONTAINER_DIE) was NEGATIVE on 6 of 10 runs (P50 -0.119 s): the
  stop CLI returns before the daemon emits die. They are asynchronous host-side
  notifications, not an ordered before/after pair.
- The product's own T_PROCESS was 1.002382 - 1.002964 s, 10/10 below 2.0 s, with
  a 0.6 ms spread.
```

Therefore:

```text
DOCKER_DIE_EVENT_LATENCY = NOT_APPLICATION_PROCESS_LIFETIME
```

The `die` timestamp and the `docker stop` CLI wall time are recorded on every run
for traceability, and are classified **informational only**. They must never
participate in the product PASS/FAIL decision.

## 4. Normative timing definitions

```text
T_PROCESS
    SIGTERM_RECEIVED
      -> EXIT_REQUESTED

T_FLUSH
    SIGTERM_RECEIVED
      -> FINAL_DURABLE_FLUSH_COMPLETE

T_DIE_INFORMATIONAL
    docker stop invoked -> Docker die event          INFORMATIONAL ONLY

T_CLI_INFORMATIONAL
    docker stop command invocation -> stop CLI return  INFORMATIONAL ONLY
```

Verdict authority:

| Quantity | Role | May carry product verdict |
| --- | --- | --- |
| `T_PROCESS` | product shutdown latency | **YES** |
| `T_FLUSH` | product durable-flush latency | **YES** |
| `T_DIE_INFORMATIONAL` | daemon/event-delivery evidence | **NO** |
| `T_CLI_INFORMATIONAL` | `HOST_DOCKER_CLI_OVERHEAD_EVIDENCE` | **NO** |

### 4.1 Derivation from the frozen shutdown evidence

No instrumentation is added to the image. The frozen image already emits its own
shutdown evidence through the product's `ShutdownCoordinator`, whose clock is
started at the first statement of the signal-triggered `run()`:

```text
ShutdownCoordinator.run():
    started = clock()                       <- clock origin == signal receipt
    ... phase "slave_drain"   (checkpoint flush + ledger WAL checkpoint)
    ... phase "suppress_dispatch"
    ... phase "master_stop_bounded"
    evidence["phases"] = phases
    evidence["elapsed_sec"] = clock() - started   <- captured at EXIT_REQUESTED
    emit(evidence)
    os._exit(0)
```

Therefore, from `<mount>/shutdown-evidence.json`:

```text
SIGTERM_RECEIVED              := 0.000000  (coordinator clock origin, by definition)
FINAL_DURABLE_FLUSH_COMPLETE  := cumulative offset at end of phase "slave_drain"
                                 = phases[0].elapsed_sec, requiring
                                   phases[0].phase == "slave_drain"
EXIT_REQUESTED                := evidence.elapsed_sec

T_PROCESS = EXIT_REQUESTED             - 0 = evidence.elapsed_sec
T_FLUSH   = FINAL_DURABLE_FLUSH_COMPLETE - 0 = phases[0].elapsed_sec
```

`slave_drain` is required to be phase 0: it starts at the clock origin, so its
`elapsed_sec` **is** the cumulative offset from signal receipt to the completion
of the durable flush. A run whose phase 0 is not `slave_drain` is a harness
error and aborts the run (not scored).

The durable flush is the phase that produces
`detail.checkpoint_flushed`, `detail.ledger_wal_checkpointed`, and
`detail.checkpoint_cursor`.

## 5. Hard criteria — frozen before execution

```text
RUN_COUNT = 20
```

All 20/20 must satisfy:

```text
T_PROCESS < 2.0 s
T_FLUSH   < 2.0 s
exit code = 0

SIGKILL = 0
Docker kill signal 9 event = 0
exit code 137 count = 0

checkpoint flush = PASS
ledger flush = PASS
delivery_suppressed = PASS

orphan process/thread = 0
```

Additionally:

```text
docker stop timeout = exactly 2 s
```

`exit_code == 0` combined with `SIGKILL == 0` and `kill(signal=9) == 0` is the
external proof that the candidate did not exhaust Docker's 2 s grace period and
get force-killed.

### 5.1 Per-run supporting checks (all must hold)

```text
state.ExitCode            == 0
state.OOMKilled           == false
state.Running             == false
state.Pid                 == 0
docker stop rc            == 0
docker wait rc            == 0
shutdown-evidence.exit_code            == 0
shutdown-evidence.repeated             == false
shutdown-evidence.delivery_suppressed  == true
shutdown-evidence.slave_drain[].ok     all true
  ...detail.checkpoint_flushed         all true
  ...detail.ledger_wal_checkpointed    all true
  ...detail.checkpoint_cursor          all == 272548
core-evidence.checkpoint_requests[].processed_through_cursor contains 272548
```

### 5.2 Decision table

Evaluated only after all 20 runs complete. No partial-run pass is allowed.

```text
PASS
    20/20 T_PROCESS < 2.0 s
    20/20 T_FLUSH   < 2.0 s
    20/20 exit code == 0
    SIGKILL == 0
    signal 9 event == 0
    20/20 durable flush PASS
    20/20 delivery suppressed PASS
    orphan process/thread == 0
    -> EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS

FAIL
    any of the above not met
    -> EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = FAIL
```

```text
There is NO INDETERMINATE branch, except when the sealed evidence itself is
missing or corrupt.
```

A missing/corrupt sealed evidence artifact is an infrastructure fault, not a
product result, and must be reported as such rather than scored. Any such
occurrence must be disclosed explicitly in the result document.

## 6. Docker evidence (per run)

Each run records:

```text
docker events                      (stop / kill / die / destroy)
docker inspect final state         (ExitCode, OOMKilled, Running, Pid, FinishedAt)
exit code
OOMKilled
FinishedAt
```

Scanned explicitly for:

```text
signal=9
exitCode=137
```

Any occurrence is a FAIL.

The `die` timestamp and the CLI wall time continue to be recorded, but strictly as:

```text
T_DIE_INFORMATIONAL
T_CLI_INFORMATIONAL
```

and must not participate in the product PASS/FAIL decision.

## 7. Fixture

The sealed host-side fixture remains permitted.

```text
--network none
SHA pinned
no production Telegram credential
no production profile
isolated ledger
isolated mapping
stub Core
```

History preserved, image not modified:

```text
FROZEN_GATE_FIXTURE_BUG = PRESERVED
```

The frozen in-image qualification stub answers `GET /health` with
`contract_version: "v1"` (string) while `Core.py` requires the integer `1`, so the
frozen gate-runner profile would raise `CoreContractError`. The single documented
deviation is the qualification-profile parameter `startup_healthcheck: false`.
This is a startup probe, not on the shutdown path, and every shutdown assertion is
still evaluated. The image is **not** changed to accommodate it.

### 7.1 Harness pin (frozen before execution)

```text
HARNESS              = tmp/rc14-prodsem/prodsem_v1.sh
HARNESS_SHA256       = e04d6f5a19c3b2408f28c06e0814874ebe77fbf4cfaefa602d4d43f26cff3cd4
HARNESS_BYTES        = 11921
HARNESS_LINE_ENDINGS = LF
```

The harness is uploaded to `/root/rc14-prodsem/` on the unraid host and its
SHA256 is re-verified **on the host** before the first run. Any post-seal change
to the harness invalidates this requalification.

## 8. Run plan

| Arm | Containers | Profile | Carries gate verdict |
| --- | --- | --- | --- |
| p (product-semantics) | **20** | frozen gate-runner profile, single deviation `startup_healthcheck: false` | **YES** |

Per run, recorded:

```text
T_PROCESS
T_FLUSH
EXIT_CODE
SIGKILL
SIGNAL9_EVENT
EXIT137
CHECKPOINT_FLUSH
LEDGER_FLUSH
DELIVERY_SUPPRESSED
T_DIE_INFORMATIONAL
T_CLI_INFORMATIONAL
```

`ORPHAN_COUNT` is evaluated at the end as
`docker ps -aq --filter label=rc14.prodsem.arm=p | wc -l` plus the count of
containers in `status=dead`; both must be 0.

Percentiles: `P50` is the median (`n` even → mean of the two central values);
`MIN`/`MAX` are the extremes of the 20 values. Per standing project discipline,
no single run is evidence; min/median/max are always reported.

## 9. Historical results preserved verbatim

```text
PREVIOUS_STRICT_WALL_GATE     = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL   = INDETERMINATE_PRESERVED
```

Neither is edited, re-scored, or re-labelled. This is a new, separately sealed
protocol. The earlier protocols' own SHA256 seals remain unchanged.

## 10. Evidence and return values

Output:

```text
docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_RESULT.md
docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_PRODUCT_SEMANTICS_RESULT.md.sha256
```

Raw per-run evidence is retained on the unraid host under
`/root/rc14-prodsem/evidence/` and `/root/rc14-prodsem/prodsem_v1.json`.

Required return block:

```text
SOURCE_COMMIT =
IMAGE_DIGEST =
OCI_REVISION =
IMAGE_UNCHANGED =

RUN_COUNT = 20

PROCESS_SHUTDOWN_RUNS =
PROCESS_SHUTDOWN_MAX =
PROCESS_SHUTDOWN_P50 =

FLUSH_TIME_RUNS =
FLUSH_TIME_MAX =

EXIT_CODES =
SIGKILL_COUNT =
SIGNAL9_EVENT_COUNT =
EXIT137_COUNT =

CHECKPOINT_FLUSH_PASS =
LEDGER_FLUSH_PASS =
DELIVERY_SUPPRESSED_PASS =
ORPHAN_COUNT =

DIE_EVENT_TIMES_INFORMATIONAL =
CLI_TIMES_INFORMATIONAL =

PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED

EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE =
EFB_FUNCTIONAL_CANDIDATE_READY =
EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO

PRODUCTION_EFB_TOUCHED = NO
```

Authorization consequence, pre-registered:

```text
if PASS:
    EFB_FUNCTIONAL_CANDIDATE_READY = YES
    EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO
        (Production Preflight has not been executed)
then STOP. Do not enter Production Preflight.
```

## 11. Structural note carried into the result

The bounded shutdown path is bounded **by construction**, not by luck:

```text
worst-case T_PROCESS
  = slave_drain budget (shutdown_slave_drain_budget_sec = 0.75)
  + master stop budget (shutdown_master_budget_sec   = 1.0)
  = 1.75 s  <  2.0 s
```

The fixture installs a master whose `stop_polling` blocks for 12 s, which
exercises the bounded branch. The result document must state whether
`master_stop_bounded_out = true` held in all 20 runs, and whether
`sum(phases) == elapsed_sec` within the recording resolution.

## 12. Seal

This protocol is committed and SHA256-sealed **before** execution. The seal commit
and the SHA256 of this file are recorded in the result document. Any post-hoc
change to §4, §5, §5.2, §6, §7, or §8 invalidates the requalification.
