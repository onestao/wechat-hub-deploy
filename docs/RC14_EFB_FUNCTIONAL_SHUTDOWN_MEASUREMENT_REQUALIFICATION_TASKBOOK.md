# RC.14 EFB Functional — Exact-Digest Shutdown Measurement Requalification Taskbook

> Status: **PROTOCOL FROZEN — SEALED BEFORE EXECUTION**
>
> Prepared: 2026-09-16
>
> This document is the pre-registered measurement protocol for the RC.14 EFB
> Functional exact-digest shutdown requalification. It defines the qualification
> criteria **before** any new container is started. It does not modify, supersede,
> or retroactively reinterpret
> `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md`
> (SHA256 `0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511`),
> which remains the historical record of the first shutdown gate.
>
> This is **not** a product code change and **not** a Production Preflight.
> No production EFB, production credential, production profile, production
> ledger, production checkpoint, or production mount is touched.

## 0. Frozen Candidate Identity (immutable)

```text
FUNCTIONAL_SOURCE_COMMIT_FULL = 91a69cef323d120f0e32196917a630d2cf3baa88
FUNCTIONAL_IMAGE_DIGEST       = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
FUNCTIONAL_OCI_REVISION       = 91a69cef323d120f0e32196917a630d2cf3baa88
```

Local image ID observed on the unraid host:
`sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a`.

Every container in this requalification is created from the digest above.
No tag reference without `@sha256:` may be used.

## 1. Hard Prohibitions

Abort immediately if any proposed action would:

- Modify Functional source at `91a69cef`.
- Rebuild, republish, retag, or re-push the Functional image.
- Modify image labels or any image byte.
- Start production EFB.
- Read, write, or reference production Telegram credentials.
- Read, write, or reference the production EFB profile.
- Read, write, or reference the production effect ledger.
- Read, write, or reference the production checkpoint (`272548`).
- Perform any Production Preflight step.
- Send or receive any real Telegram or WeChat message.
- Retroactively rewrite the previous gate result
  (`PREVIOUS_STRICT_WALL_GATE = 2/5 wall < 2.0s`) into a PASS.

Every container runs with `--network none`, an isolated temporary profile, an
isolated temporary data/ledger directory, the frozen in-process stub Core, no
production credential, and no production mount. The production EFB container
`wechat-hub-f-live-efb` is observed as `Exited` and is never started.

## 2. Why this requalification exists — the measurement defect

The first gate collapsed three different physical quantities into one number and
then applied the product criterion to the wrong one:

```text
T_CLI (docker stop command invocation -> docker stop CLI return)
```

was treated as *the* product shutdown latency, and because the unraid host has a
2.7–5.2 s CLI-inclusive baseline for even a trivial `sleep` container, the wall
criterion `< 2.0 s` was met only 2/5 — while the product-internal shutdown was
1.002–1.003 s on 5/5 with zero SIGKILL. The gate therefore reported a host
property as a product property.

This protocol separates the three quantities and pre-registers which one is
allowed to carry the product verdict.

## 3. The three times (normative definitions)

```text
T_PROCESS
    SIGTERM received
      -> application durable flush complete / process exit

T_CONTAINER_DIE
    docker stop invoked
      -> Docker die event / docker wait completion

T_CLI
    docker stop command invocation
      -> docker stop CLI return
```

Verdict authority:

| Quantity | Role | May carry product verdict |
| --- | --- | --- |
| `T_PROCESS` | product shutdown latency | **YES — primary** |
| `T_CONTAINER_DIE` | container death latency under the daemon | **YES — secondary** (if reliably measurable) |
| `T_CLI` | `HOST_DOCKER_CLI_OVERHEAD_EVIDENCE` | **NO — evidence only, never the sole criterion** |

`T_CLI` is recorded on every run and reported, but it is explicitly classified as
`HOST_DOCKER_CLI_OVERHEAD_EVIDENCE` and must never be used as the only product
shutdown criterion.

## 4. Pre-registered Gate Criteria

Measured on the gate-carrying arm (Arm A, 10 runs). Written down before the first
container is started; not adjustable afterwards.

```text
PROCESS_EXIT_WITHIN_DOCKER_TIMEOUT = 5/5 PASS   (requalified to 10/10)
EXIT_CODE_0                        = 5/5        (requalified to 10/10)
SIGKILL_COUNT                      = 0
FINAL_DURABLE_FLUSH                = 5/5 PASS   (requalified to 10/10)
DELIVERY_SUPPRESSED                = 5/5 PASS   (requalified to 10/10)
ORPHAN_PROCESS_THREAD              = 0
```

and the quantitative criterion:

```text
T_PROCESS < 2.0 s   10/10
```

and, because Docker die timestamps are available at nanosecond resolution on this
host (`docker events --format '{{json .}}'` exposes `timeNano`):

```text
T_CONTAINER_DIE < 2.0 s   10/10
```

Supporting per-run checks that must all hold:

```text
state.ExitCode            == 0
state.OOMKilled           == false
state.Running             == false
state.Pid                 == 0
docker stop rc           == 0
docker wait rc           == 0
shutdown-evidence.exit_code              == 0
shutdown-evidence.repeated               == false
shutdown-evidence.delivery_suppressed    == true
shutdown-evidence.slave_drain[].ok       all true
shutdown-evidence.slave_drain[].detail.checkpoint_flushed        all true
shutdown-evidence.slave_drain[].detail.ledger_wal_checkpointed   all true
shutdown-evidence.slave_drain[].detail.checkpoint_cursor         all == 272548
core-evidence.checkpoint_requests[].processed_through_cursor     contains 272548
Docker kill event count  == 0
```

### 4.1 Pre-registered decision table

Evaluated only after all 10 Arm A runs complete. No partial-run pass is allowed.

```text
PASS
    T_PROCESS < 2.0s                10/10
    T_CONTAINER_DIE < 2.0s          10/10   (reliable timestamps proven)
    exit_code == 0                  10/10
    Docker kill events              0
    SIGKILL                         0
    final durable flush             PASS 10/10
    delivery_suppressed             PASS 10/10
    orphan_process_thread           0
    -> EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = PASS

FAIL
    any run has exit_code == 137
    OR any Docker kill event
    OR any SIGKILL
    OR any durable flush failure (checkpoint_flush / ledger_flush /
       delivery_suppressed / checkpoint cursor)
    OR any run has T_PROCESS >= 2.0 s
    -> EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = FAIL

INDETERMINATE
    T_PROCESS < 2.0s 10/10 and no FAIL trigger, but
    T_CONTAINER_DIE cannot be reliably proven < 2.0 s for all 10 runs
    (including the case where reliable measurement yields >= 2.0 s, which is
    not itself a FAIL trigger)
    -> EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = INDETERMINATE
```

Timestamp reliability for `T_CONTAINER_DIE` is established per run by requiring a
`die` event carrying a non-null `timeNano`, plus an independent
`docker wait <container>` completion observation, plus
`state.FinishedAt` agreement within a stated tolerance. If any of those is
missing for a run, `T_CONTAINER_DIE` is not proven for that run.

### 4.2 Historical results are preserved verbatim

```text
PREVIOUS_STRICT_WALL_GATE  = 2/5 wall < 2.0s   (FAIL_PRESERVED)
PREVIOUS_EXIT_CODES        = [0,0,0,0,0]       (PRESERVED)
PREVIOUS_SIGKILL           = 0                 (PRESERVED)
PREVIOUS_INTERNAL_SHUTDOWN = ~1.003s 5/5       (PRESERVED)
PREVIOUS_FINAL_FLUSH       = PASS 5/5          (PRESERVED)
```

This requalification adds a new, separately sealed protocol. It does not edit,
re-score, or re-label the earlier gate.

## 5. Measurement Method

### 5.1 Container isolation (per run, all arms)

```text
--network none
--label rc14.requal.arm=<a|b|baseline>
--volume <fresh mktemp dir>:/qualification     (isolated temp profile,
                                                isolated ledger,
                                                isolated mapping DB,
                                                isolated cursor store)
--entrypoint python
image = FUNCTIONAL_IMAGE_DIGEST (exact digest)
```

Stub Core: the frozen in-image probe starts its own in-process HTTP stub Core on
`127.0.0.1:<ephemeral>` and rewrites `core.base_url` to it. No host-side Core, no
production Core, no production network. `--network none` still permits loopback.

No production credential, no production profile, no production mount, no
production checkpoint file is mounted or read.

### 5.2 Host-side anchors (per run)

```text
T0 = host CLOCK_REALTIME nanoseconds, taken immediately before docker stop
T1 = host CLOCK_REALTIME nanoseconds, taken immediately after docker stop returns
T0m/T1m = host CLOCK_MONOTONIC via /proc/uptime, same two instants
docker wait <container> is started as an independent waiter BEFORE docker stop
docker events --filter container=<name> --format '{{json .}}'
    captures: stop, kill (if any), die, destroy
    T_CONTAINER_DIE = (die.timeNano - T0) / 1e9
    T_CLI           = (T1 - T0) / 1e9
```

`docker events.timeNano` and `date +%s%N` are the same CLOCK_REALTIME domain, so
the subtraction is valid. `T_CLI` is additionally computed from the host monotonic
clock (`T1m - T0m`) as an independent cross-check.

`docker stop -t 2` is used on every run. Docker's own grace-period expiry is the
mechanism that would produce a `kill` event and `exit 137`; either is a FAIL
trigger.

### 5.3 Container-internal shutdown evidence

The frozen image already emits shutdown evidence through the product's own
`ShutdownCoordinator`, which is the authority for `T_PROCESS`:

```text
<mount>/shutdown-evidence.json
    .elapsed_sec                 = coordinator clock at end of run()
                                   measured from signal-triggered run() start
    .trigger                     = "signal:15"
    .phases[]                    = slave_drain / suppress_dispatch /
                                   master_stop_bounded, each with elapsed_sec
    .slave_drain[].detail        = poll_stopped, core_session_closed,
                                   checkpoint_flushed, checkpoint_cursor,
                                   ledger_wal_checkpointed, poll_thread_joined,
                                   delivery_suppressed, elapsed_sec
    .delivery_suppressed         = true
    .exit_code                   = 0
<mount>/core-evidence.json
    .checkpoint_requests[]       = consumer_id + processed_through_cursor
```

The frozen evidence exposes **relative** elapsed values, not absolute monotonic
stamps. The five required marks are therefore handled in two ways:

**(a) Primary — consumed from frozen evidence as offsets from signal receipt.**
The coordinator's clock is started at the first statement of the signal-triggered
`run()`, so offsets from it are offsets from signal receipt:

```text
CONTAINER_MONOTONIC_MARKS = DERIVED_OFFSETS_FROM_SIGNAL_RECEIPT

signal_received_monotonic          := 0.000000  (coordinator clock origin)
delivery_suppressed_monotonic      := cumulative offset at end of phase
                                      slave_drain step 4 / phase suppress_dispatch
checkpoint_flush_completed_monotonic := cumulative offset at end of phase
                                      slave_drain (detail.checkpoint_flushed)
ledger_flush_completed_monotonic   := cumulative offset at end of phase
                                      slave_drain (detail.ledger_wal_checkpointed)
exit_requested_monotonic           := evidence.elapsed_sec
```

Cumulative offset of phase *k* = sum of `phases[0..k].elapsed_sec`.

**(b) Secondary — absolute monotonic marks from the Arm B instrument fixture.**
Arm B obtains genuine absolute `time.monotonic()` marks so the derivation in (a)
can be falsified rather than assumed. Arm B is supplementary and carries no gate
verdict.

### 5.4 Arm B — host-side monotonic mark fixture (supplementary)

Arm B runs the same frozen image, same frozen probe module, same frozen gate-runner
profile, with a host-side fixture as the entrypoint. The fixture:

- imports the frozen in-image probe module **verbatim** from
  `/opt/efb-linux-wechat-slave/scripts/qualification/image_shutdown_probe.py`;
- corrects the frozen `/health` contract literal in host memory only
  (`"v1"` → `1`), which allows the frozen gate-runner profile
  (`startup_healthcheck: true`) to be used with **zero parameter deviation**;
- attaches read-only observation wrappers on documented seams
  (`ShutdownCoordinator._clock`, `ShutdownCoordinator._exit_func`,
  `channel.drain_for_shutdown`, `channel.suppress_external_dispatch`,
  `channel._flush_final_checkpoint`, `effect_ledger.checkpoint_wal`),
  each of which only reads `time.monotonic()` around the original callable;
- writes the absolute marks to `<mount>/marks.json` with a buffered write +
  close (no fsync) immediately before the controlled exit, so the mark write
  does not inflate `T_CONTAINER_DIE`.

Arm B additionally measures the tail the frozen evidence cannot show, because
`elapsed_sec` is captured **before** the evidence file is written:

```text
post_exit_request_to_die_sec = die.timeNano - realtime(exit_requested_monotonic)
```

### 5.5 Arm B fixture pin (frozen before execution)

```text
ARM_B_FIXTURE_PATH   = tmp/rc14-requal/marks_fixture.py
ARM_B_FIXTURE_SHA256 = 04945c4d52a52971df8b9da659f28e0b00ce5787a5d960cf4e0f0bc59cc414cd
ARM_B_FIXTURE_MOUNTS = <run temp dir>/marks/marks_fixture.py -> /qualification/marks/marks_fixture.py
```

The fixture is host-side only. It is never copied into, or baked into, the
candidate image.

### 5.6 Harness pins (frozen before execution)

```text
ARM_A_HARNESS      = tmp/rc14-requal/arm_a.sh
ARM_A_HARNESS_SHA256 = 4b641359c83e95e76b35aa40d1513737450d451b08ef7f45ea2ec03794657355
ARM_B_HARNESS      = tmp/rc14-requal/arm_b.sh
ARM_B_HARNESS_SHA256 = 0d748ee04b171ed16b2eae2b73bd6df1d4a517606b6d08f49c658deba390c87c
BASELINE_HARNESS      = tmp/rc14-requal/baseline.sh
BASELINE_HARNESS_SHA256 = 7c94241c74f90efa570fa71cff470d28f62b69943196ba6e33e501306f43a0c0
```

Each harness is uploaded to `/root/rc14-requal/` on the unraid host and its
SHA256 is re-verified on the host **before** the first run.

## 6. Run Plan

| Arm | Containers | Profile | Carries gate verdict |
| --- | --- | --- | --- |
| A | **10** | frozen gate-runner profile, single deviation `startup_healthcheck: false` | **YES** |
| B | 3 | frozen gate-runner profile verbatim (`startup_healthcheck: true`) | no (supplementary) |
| BASELINE | **10** | minimal container, no product logic | no (evidence only) |

Per run, the following are recorded:

```text
PROCESS_SHUTDOWN_SEC
CONTAINER_DIE_SEC
CLI_RETURN_SEC
EXIT_CODE
KILL_EVENT
SIGKILL
CHECKPOINT_FLUSH
LEDGER_FLUSH
DELIVERY_SUPPRESSED
ORPHAN_COUNT
```

`ORPHAN_COUNT` is evaluated at the end of each arm as
`docker ps -aq --filter label=rc14.requal.arm=<arm> | wc -l` plus the count of
containers in `status=dead`; both must be 0.

Percentiles: `P50` is the median (`n` even → mean of the two central values);
`MIN`/`MAX` are the extremes of the 10 values. Per the standing project
discipline, no single run is evidence; min/median/max are always reported.

## 7. Host Baseline (evidence only)

A minimal container with **no product logic** (the same image, entrypoint
`sleep 600`) is stopped 10 times under the same daemon with the same
`docker stop -t 2`.

Purpose, and only purpose:

```text
prove whether (T_CLI - T_CONTAINER_DIE) is dominated by daemon/CLI cleanup
```

```text
BASELINE_CONTAINER_DIE_P50
BASELINE_CLI_RETURN_P50
```

The baseline is **never** subtracted from, or used to discount, product latency.
A slow host CLI does not make the product slower, and a fast host CLI does not
make the product faster.

## 8. Frozen Probe Bug (preserved)

History: the frozen in-image qualification stub answers
`GET /health` with `contract_version: "v1"` (string) while `Core.py` requires the
integer `1` (`CONTRACT_VERSION`), so the frozen gate runner raises
`CoreContractError` and the publish-run embedded gate step failed.

```text
FROZEN_GATE_FIXTURE_BUG = PRESERVED
```

This round must not change the image. Handling:

- Arm A keeps the frozen probe unmodified and therefore keeps the single
  documented parameter deviation `startup_healthcheck: false`. This is a
  qualification-profile parameter, not a product behaviour: the health check is a
  startup probe, it is not on the shutdown path, and every shutdown assertion is
  still evaluated.
- Arm B carries the correction as a **host-side fixture** whose content SHA256 is
  pinned in §5.5, and which is never written into the candidate.
- No production Core is contacted by either arm.

Both deviations and the fixture patch are disclosed in the result document and
must appear in any downstream citation of this requalification.

## 9. Evidence and Return Values

Output:

```text
docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_RESULT.md
docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_RESULT.md.sha256
```

Raw per-run evidence is retained on the unraid host under
`/root/rc14-requal/evidence/` and `/root/rc14-requal/{armA,armB,baseline}.json`.

Required return block:

```text
FUNCTIONAL_SOURCE_COMMIT =
FUNCTIONAL_IMAGE_DIGEST =
FUNCTIONAL_OCI_REVISION =
IMAGE_UNCHANGED =

RUN_COUNT =

PROCESS_SHUTDOWN_SEC_RUNS =
PROCESS_SHUTDOWN_MAX =
PROCESS_SHUTDOWN_P50 =

CONTAINER_DIE_SEC_RUNS =
CONTAINER_DIE_MAX =
CONTAINER_DIE_P50 =

CLI_RETURN_SEC_RUNS =
CLI_RETURN_MAX =
CLI_RETURN_P50 =

BASELINE_CONTAINER_DIE_P50 =
BASELINE_CLI_RETURN_P50 =

EXIT_CODES =
SIGKILL_COUNT =
DOCKER_KILL_EVENT_COUNT =

CHECKPOINT_FLUSH_PASS =
LEDGER_FLUSH_PASS =
DELIVERY_SUPPRESSED_PASS =
ORPHAN_COUNT =

PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
EXACT_DIGEST_SHUTDOWN_REQUALIFICATION = PASS / FAIL / INDETERMINATE

PRODUCTION_EFB_TOUCHED = NO
```

Authorization consequence, pre-registered:

```text
if PASS:
    EFB_FUNCTIONAL_CANDIDATE_READY = YES
    EFB_FUNCTIONAL_LIVE_AUTHORIZATION_READY = NO
        (Production Preflight has not been executed)
then STOP.
```

## 10. Structural note carried into the result

The bounded shutdown path is bounded **by construction**, not by luck:

```text
worst-case T_PROCESS
  = slave_drain budget (shutdown_slave_drain_budget_sec = 0.75)
  + master stop budget (shutdown_master_budget_sec = 1.0)
  = 1.75 s  <  2.0 s
```

The fixture deliberately installs a master whose `stop_polling` blocks for 12 s,
which exercises the bounded branch; the observed `master_stop_bounded_out = true`
confirms the budget, not the master, is what ends that phase. The result document
must state whether this invariant held in all 10 runs.

## 11. Seal

This protocol is committed and SHA256-sealed **before** execution. The seal
commit and the SHA256 of this file are recorded in the result document. Any
post-hoc change to §4, §4.1, §5, §6, or §7 invalidates the requalification.
