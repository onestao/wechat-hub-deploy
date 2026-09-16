# RC.14 EFB Functional Shutdown Requalification — Taskbook ERRATUM 1 (Pre-Gate)

> Status: **SEALED BEFORE THE GATE RUN**
>
> Prepared: 2026-09-16
>
> Amends: `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md`
> SHA256 `3b2587e49acf9aee26a1df815b202e2bea54cd4509b75cfbe1c095c80bc5a4c0`
>
> The amended taskbook is **not** modified. Its §4, §4.1, §5, §6, §7 text and its
> SHA256 seal remain exactly as committed at deploy commit
> `8b7c60ea710bdc305b902e14009b0e7e6a41f44b`. This erratum is a separate,
> separately sealed document.

## 0. Why this erratum exists

A one-container preflight of the sealed harness was executed **before** the gate
run in order to validate the instrument, not to produce a verdict. It returned no
qualification verdict and is not part of the gate. It revealed three instrument
defects and one measurement question that would have made the sealed §4.1
decision table fire incorrectly or uninformatively. All preflight raw evidence is
reproduced in §5.

**This erratum does not relax any acceptance criterion.** §3 states explicitly
which criteria are unchanged, and where the change is a *strengthening*.

## 1. ERRATUM-1 — `kill` event semantics (instrument correction, verdict-neutral)

### Observed

On this host (Docker 27.5.1), `docker stop -t 2` emits a `kill` event carrying
`Actor.Attributes.signal = "15"` when it delivers the stop signal, and emits a
second `kill` event carrying `signal = "9"` only if the grace period expires and
SIGKILL is used.

Preflight, EFB container, clean exit: exactly one `kill` event, `signal=15`,
`exit_code=0`, no `signal=9`.

Micro-probe, `sleep 600` as PID 1: `kill signal=15` at `+0.528 s`, then
`kill signal=9` at `+2.840 s`, `exit_code=137`.

### Defect

Sealed §4.1 lists "any Docker kill event" as a FAIL trigger and sealed §4 lists
"Docker kill event count == 0" as a PASS requirement. As written, that fires on
every successful run, including the host baseline, because the normal SIGTERM
delivery path itself produces a `kill` event. The literal criterion is
unsatisfiable by a correct product and is therefore mis-specified.

### Correction (verdict-neutral, SIGKILL detection strengthened)

```text
DOCKER_KILL_EVENT_COUNT        := number of kill events with signal == "9"
DOCKER_SIGTERM_EVENT_COUNT     := number of kill events with signal == "15"   (recorded, expected >= 1)
TOTAL_DOCKER_KILL_EVENT_COUNT  := all kill events                            (recorded)
```

FAIL trigger becomes: **any `kill` event with `signal == 9`**, i.e. any actual
SIGKILL. This is corroborated by two further independent signals that were already
in the sealed table and are unchanged:

```text
exit_code == 137        (unchanged FAIL trigger)
docker stop rc != 0     (unchanged per-run check)
```

The original criterion is preserved in this document and in the result document
as `SEALED_KILL_EVENT_CRITERION = "any kill event" -> UNSATISFIABLE_BY_CORRECT_PRODUCT`,
so nothing is hidden. No criterion is weakened: the pre-existing `exit_code == 137`
FAIL trigger already covered the SIGKILL outcome, and the corrected criterion now
identifies SIGKILL directly rather than by its proxy.

## 2. ERRATUM-2 — baseline container semantics (addition, verdict-neutral)

### Observed

A container whose PID 1 is `sleep 600` **does not exit on SIGTERM**. PID 1 has no
default signal actions inside a container, so `sleep` ignores SIGTERM, Docker's
2 s grace expires, and SIGKILL is used. Micro-probe result: `exit_code = 137`,
`docker stop` CLI wall `4.918 s`, `kill signal=9` at `+2.840 s`.

### Defect

Sealed §7 specifies the baseline as "the same image, entrypoint `sleep 600`" and
states its purpose as proving whether `T_CLI - T_CONTAINER_DIE` is dominated by
daemon/CLI cleanup. A SIGKILL-terminated baseline cannot serve as the clean-exit
comparator for a product that exits cleanly on SIGTERM.

### Correction (addition only)

The sealed `BASELINE_SLEEP` arm is **kept and executed unchanged** (10 runs), and
is reported as `BASELINE_SLEEP` with the explicit annotation
`BASELINE_SLEEP_EXIT_PATH = SIGKILL_AFTER_GRACE`.

A second baseline is added:

```text
BASELINE_CLEAN
    same image, no product logic
    entrypoint: python -c 'import signal,sys,time;
                 signal.signal(signal.SIGTERM, lambda *a: sys.exit(0));
                 time.sleep(600)'
    exits 0 on SIGTERM, i.e. the same exit path class as the product
    10 runs, docker stop -t 2
```

`BASELINE_CONTAINER_DIE_P50` and `BASELINE_CLI_RETURN_P50` in the sealed §9 return
block are reported for **both** baselines; `BASELINE_CLEAN` is designated the
primary comparator because it matches the product's exit path.

Neither baseline may be subtracted from product latency. Sealed §7 stands.

## 3. ERRATUM-3 — added `FinishedAt` triangulation (no criterion change)

### Observed

The Docker `die` **event** timestamp is not the container's death instant on this
host. EFB preflight:

```text
kill(signal=15) event          1789556148.290614
container State.FinishedAt     1789556149.297893507   (= kill(15) + 1.007279 s)
die event                      1789556150.485671700   (= FinishedAt + 1.187778 s)
stop event                     1789556150.485738200
docker stop CLI return         T0 + 2.591280 s
docker wait completion         T0 + 2.593117 s
product elapsed_sec            1.002651 s
```

So the `die` event is emitted ~1.19 s **after** the container process has already
exited, and `docker wait` returns after that cleanup too. The delay is daemon
post-mortem cleanup (container teardown / unmount of a 1.05 GB layered image on
the degraded HDD array), not product work.

### Correction (triangulation, criterion unchanged)

Three death-related timestamps are now recorded and reported for every run:

```text
T_DIE_EVENT      = die event timeNano  - T0      (sealed definition)
T_WAIT_RETURN    = docker wait completion - T0   (sealed definition)
T_FINISHED_AT    = State.FinishedAt    - T0      (daemon-recorded process death)
```

The sealed §4.1 PASS requirement and INDETERMINATE rule are evaluated **against
the sealed definition** (`T_DIE_EVENT`, corroborated by `T_WAIT_RETURN`).
`T_FINISHED_AT` is reported as additional evidence and does **not** substitute for
it. Concretely, the sealed rule is applied literally:

```text
if T_DIE_EVENT < 2.0s for all 10 runs and all other PASS requirements hold
      -> PASS
if T_PROCESS < 2.0s 10/10 and no FAIL trigger, but T_DIE_EVENT is not < 2.0s
      for every run
      -> INDETERMINATE
```

`T_FINISHED_AT` exists so the result can state *where* the excess lives. It cannot
convert an INDETERMINATE into a PASS. This erratum therefore adds information and
removes none.

## 4. ERRATUM-4 — harness supersede (pins)

The sealed v1 harnesses are **not** modified; they stay byte-identical on the host
so the taskbook §5.6 pins remain verifiable. v2 harnesses are used for the gate run
and are pinned here.

```text
SUPERSEDED_BY_PREFLIGHT:
  tmp/rc14-requal/arm_a.sh      4b641359c83e95e76b35aa40d1513737450d451b08ef7f45ea2ec03794657355
  tmp/rc14-requal/baseline.sh   7c94241c74f90efa570fa71cff470d28f62b69943196ba6e33e501306f43a0c0
  tmp/rc14-requal/arm_b.sh      0d748ee04b171ed16b2eae2b73bd6df1d4a517606b6d08f49c658deba390c87c

GATE_RUN_HARNESS_PINS:
  tmp/rc14-requal/requal_v2.sh  b78adcdca67bc786c882993e6c0d54a9f2d644f6eac14d78cbf8691cd5c12654
  tmp/rc14-requal/arm_b_v2.sh   f0d5aef53b7b816867f637ded25b992075021c78d75f5358d8b0a6990d19135f
  tmp/rc14-requal/marks_fixture.py
                                04945c4d52a52971df8b9da659f28e0b00ce5787a5d960cf4e0f0bc59cc414cd
                                (UNCHANGED from taskbook §5.5)
```

Host paths: `/root/rc14-requal/requal_v2.sh`, `/root/rc14-requal/arm_b_v2.sh`,
`/root/rc14-requal/marks/marks_fixture.py`. Each is re-verified by `sha256sum` on
the host before the first run.

`requal_v2.sh` performs all three container arms in one pass:

| Arm | Containers | Exit path |
| --- | --- | --- |
| `a` | 10 | frozen probe, SIGTERM → clean exit 0 |
| `bs` | 10 | `sleep 600` PID 1 → SIGKILL after grace |
| `bc` | 10 | python idle → clean exit 0 on SIGTERM |

`arm_b_v2.sh` performs the 3 supplementary instrument runs. The gate verdict comes
from arm `a` only.

## 5. Preflight evidence (raw)

All preflight containers ran with `--network none`, isolated temp mounts, the
exact digest
`ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241`,
and no production mount, credential, profile, ledger, or checkpoint.

### 5.1 EFB container (frozen probe), 1 run

```text
process_shutdown_sec (frozen evidence .elapsed_sec) = 1.002651
shutdown evidence  = trigger signal:15, exit_code 0, delivery_suppressed true,
                     phases [slave_drain 0.002312, suppress_dispatch 0.000007,
                     master_stop_bounded 1.000314],
                     slave_drain detail {checkpoint_flushed true,
                     ledger_wal_checkpointed true, checkpoint_cursor 272548,
                     core_session_closed true, poll_stopped true,
                     delivery_suppressed true, poll_thread_joined false}
core evidence      = checkpoint_requests[0].processed_through_cursor 272548
docker events      = kill(signal 15) 1789556148290614000
                     die             1789556150485671700
                     stop            1789556150485738200
state              = ExitCode 0, OOMKilled false, Running false, Pid 0
                     FinishedAt 2026-09-16T10:55:49.297893507Z
docker stop rc     = 0 ;  docker wait rc = 0
```

### 5.2 Micro-probe, `sleep 600` as PID 1 (1 run)

```text
docker events = kill(signal 15) +0.528 s
                kill(signal 9)  +2.840 s
state         = ExitCode 137, FinishedAt 2026-09-16T10:56:27.862771966Z
docker stop CLI wall = 4.918 s ; docker wait = 4.919 s
```

### 5.3 Micro-probe, python idle with SIGTERM → exit 0 (1 run)

```text
docker events = kill(signal 15) 1789556271802480600
                stop            1789556272209676000
                die             1789556272375491300
state         = ExitCode 0, FinishedAt 2026-09-16T10:57:51.807306591Z
docker stop rc = 0 ; docker wait rc = 0
docker stop CLI wall = 0.588 s ; docker wait = 0.589 s
```

### 5.4 Derived host-side floor (clean-exit idle)

Using `T0 ≈ die_event − T_CLI`:

```text
T0 -> SIGTERM delivery            ~0.013 s
SIGTERM -> process exit           ~0.005 s
process exit -> die event         ~0.568 s
die event -> CLI return           ~0.002 s
```

## 6. Amended per-run record

```text
arm, run
process_shutdown_sec        (arm a only, frozen evidence)
sigterm_event_sec           kill signal 15 offset
sigkill_event_sec           kill signal 9 offset (null when absent)
die_event_sec               sealed T_CONTAINER_DIE definition
stop_event_sec
destroy_event_sec           destroy event captured after docker rm -f
finished_at_sec             State.FinishedAt offset (added triangulation)
cli_return_sec              T_CLI
cli_return_monotonic_sec    T_CLI on the host monotonic clock
waiter_return_sec           docker wait completion offset
exit_code, oom_killed, running, pid, stop_rc, wait_rc
checkpoint_flush, ledger_flush, delivery_suppressed, checkpoint_cursor,
core_cursor, repeated            (arm a only)
checks_failed
```

## 7. Seal

This erratum is committed and SHA256-sealed before the gate run. The seal commit
and this file's SHA256 are recorded in the result document. Any change to §1–§4
after the gate run invalidates the requalification.
