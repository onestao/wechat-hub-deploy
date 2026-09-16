# RC.14 EFB Functional Shutdown Requalification — Taskbook ERRATUM 2 (Pre-Gate, Attempt 2)

> Status: **SEALED BEFORE THE GATE RUN (ATTEMPT 2)**
>
> Prepared: 2026-09-16
>
> Amends: `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK.md`
> (`3b2587e4…`) via
> `docs/RC14_EFB_FUNCTIONAL_SHUTDOWN_MEASUREMENT_REQUALIFICATION_TASKBOOK_ERRATUM_1.md`
> (`3f0f35b0…`).
>
> Neither earlier document is modified. This erratum records an aborted harness
> execution and the corrected harness pins.

## 1. Attempt 1 — ABORTED, NO VERDICT, DISCARDED

`requal_v2.sh` was launched as the gate run and reached all 10 arm-`a` containers
before being stopped. It produced **no qualification verdict** and is discarded
wholesale.

### Defect

The per-run event extraction used

```bash
jq -r '[.[] | select(...) | .timeNano] | first // empty' events.jsonl
```

on a JSONL stream. Without `-s`/`--slurp`, `jq` parses each line as an independent
input document, so `.[]` iterates the *values of one event object* rather than the
list of events. Every event-derived field therefore came back `null`:

```text
sigterm_event_sec = null
sigkill_event_sec = null
die_event_sec     = null
```

The run also silently continued instead of failing, because no null-guard existed
on those fields.

### Consequence

`T_CONTAINER_DIE` and the SIGTERM/SIGKILL event split were unavailable for
attempt 1. `T_PROCESS`, `T_FINISHED_AT`, `T_CLI` and all frozen-evidence checks
were unaffected, but a partial dataset cannot carry the pre-registered decision
table, so attempt 1 is **not** used for any verdict, aggregate, or percentile.

### Retained, not deleted

```text
/root/rc14-requal/attempt1_requal_v2.log     full attempt-1 stdout
/root/rc14-requal/attempt1/                  raw per-run shutdown + core evidence (20 files)
```

Attempt-1 `process_shutdown_sec` values are reproduced here **only** as a
consistency cross-check against attempt 2, with no verdict weight:

```text
a run 1  1.002234     a run 6  1.002497
a run 2  1.002513     a run 7  1.002372
a run 3  1.002594     a run 8  1.002781
a run 4  1.002636     a run 9  1.002945
a run 5  1.002601     a run 10 not reached
```

### Secondary defect (cosmetic)

The aggregate print block escaped double quotes inside single-quoted `jq`
programs (`join(\",\")`), producing `jq: 1 compile error` on the summary lines.
This affected only the console summary, never the stored JSON, and is fixed.

## 2. Harness correction (v3)

```text
ATTEMPT_1_HARNESS (defective, superseded):
  tmp/rc14-requal/requal_v2.sh  b78adcdca67bc786c882993e6c0d54a9f2d644f6eac14d78cbf8691cd5c12654
  tmp/rc14-requal/arm_b_v2.sh   f0d5aef53b7b816867f637ded25b992075021c78d75f5358d8b0a6990d19135f

GATE_RUN_HARNESS_PINS (v3):
  tmp/rc14-requal/requal_v3.sh  f4ffe7d20990fc9a22c9831953c7576118461ee5c41d9d70bb5ebf0900d40926
  tmp/rc14-requal/arm_b_v3.sh   5d956f465f80401a7380ff09e17fab3ebc23afbea7db76e4a32ab1f89aaa7f66
  tmp/rc14-requal/marks_fixture.py
                                04945c4d52a52971df8b9da659f28e0b00ce5787a5d960cf4e0f0bc59cc414cd
                                (UNCHANGED — taskbook §5.5 pin still valid)
```

v3 changes, exhaustively:

1. `off()` now uses `jq -sr` (slurp) so the events stream is iterated as a list.
2. Hard null-guards: the run aborts with `REQUAL_V3_FAIL` if no `die` event, no
   `FinishedAt`, no SIGTERM(15) event, or an empty events stream is captured.
3. Raw `events.jsonl` retained per arm-`a` run at
   `/root/rc14-requal/evidence/a-run<i>-events.jsonl`.
4. Aggregate print quoting fixed.
5. Output filenames renamed `requal_v3.json` / `armB_v3.json` so attempt-1 and
   attempt-2 evidence cannot be confused.

Nothing else changed. The measurement method (taskbook §5), the container
isolation, the run plan (taskbook §6), the baseline (taskbook §7 + erratum 1 §2),
the per-run record (erratum 1 §6), the PASS/FAIL/INDETERMINATE decision table
(taskbook §4.1), and the return block (taskbook §9) are **unchanged**.

Host SHA256 verification before the run:

```text
requal_v3.sh        f4ffe7d20990fc9a22c9831953c7576118461ee5c41d9d70bb5ebf0900d40926
arm_b_v3.sh         5d956f465f80401a7380ff09e17fab3ebc23afbea7db76e4a32ab1f89aaa7f66
marks/marks_fixture.py  04945c4d52a52971df8b9da659f28e0b00ce5787a5d960cf4e0f0bc59cc414cd
```

## 3. Single-container smoke validation of v3 (no verdict)

One arm-`a` container was run with `N_A=1 N_BS=0 N_BC=0` to confirm the corrected
instrument. It returned a complete record:

```text
arm=a run=1
process_shutdown_sec   1.002780
sigterm_event_sec      0.208456
sigkill_event_sec      null
die_event_sec          2.726242
stop_event_sec         2.726305
destroy_event_sec      3.441616
finished_at_sec        1.214157
cli_return_sec         2.728216
waiter_return_sec      2.730192
exit_code              0
checkpoint_flush       true
ledger_flush           true
delivery_suppressed    true
checkpoint_cursor      272548
core_cursor            272548
repeated               false
checks_failed          (empty)
```

This is the same qualitative pattern as the erratum-1 preflight: the Docker `die`
event lands ~1.5 s after `State.FinishedAt`, i.e. after the container process has
already exited. The smoke run carries no verdict and is not part of any aggregate.

## 4. Seal

Committed and SHA256-sealed before attempt 2. Any change to §1–§2 after attempt 2
invalidates the requalification.
