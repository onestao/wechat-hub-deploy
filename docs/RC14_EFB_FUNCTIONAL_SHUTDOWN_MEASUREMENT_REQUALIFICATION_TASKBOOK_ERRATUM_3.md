# RC.14 EFB Functional Shutdown Requalification — Taskbook ERRATUM 3 (Pre-Arm-B)

> Status: **SEALED BEFORE THE ARM B INSTRUMENT RUN**
>
> Prepared: 2026-09-16
>
> Amends: taskbook `3b2587e4…` via erratum 1 `3f0f35b0…` and erratum 2 `b90f86c0…`.

## 1. Scope

This erratum concerns **only the supplementary Arm B instrument fixture**. Arm A
(the gate-carrying arm) had already completed all 10 runs when this defect was
found; no Arm A measurement, criterion, or verdict is affected.

## 2. Fixture defect

`tmp/rc14-requal/marks_fixture.py` used the module global `MARKS` as an
`argparse` default before declaring `global MARKS` in the same function:

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marks", default=MARKS)   # reads MARKS here
    ...
    global MARKS                                    # SyntaxError
    MARKS = str(known.marks)
```

Python rejects this at compile time:

```text
File "/qualification/marks/marks_fixture.py", line 150
    global MARKS
    ^^^^^^^^^^^^
SyntaxError: name 'MARKS' is used prior to global declaration
```

Arm B run 1 aborted before `ready.json` and the harness correctly reported
`ARM_B_V2_FAIL: exited before ready run 1`. No Arm B data was produced.

## 3. Correction

`global MARKS` moved to the first statement of `main()`. One line moved; no logic
changed. Verified with `ast.parse` and re-hashed.

```text
ARM_B_FIXTURE_PREVIOUS (taskbook §5.5 pin, DEFECTIVE)
  04945c4d52a52971df8b9da659f28e0b00ce5787a5d960cf4e0f0bc59cc414cd

ARM_B_FIXTURE_CORRECTED (this erratum)
  2ff2e53e2706cd70bde3f45e7d9453223a58f7626cb7c78103cbd982bf28f5f9
```

Host path `/root/rc14-requal/marks/marks_fixture.py` re-verified by `sha256sum`
before the Arm B run. The defective bytes are preserved at
`/root/rc14-requal/marks/marks_fixture.py.pre`.

## 4. Unchanged

Arm B remains supplementary and carries **no** gate verdict (taskbook §5.4,
erratum 1 §3). Arm A's harness pins, measurement method, run plan, baseline,
decision table, and return block are untouched. The five absolute monotonic marks
that Arm B exists to supply are unchanged in definition.

## 5. Seal

Committed and SHA256-sealed before the Arm B run.
