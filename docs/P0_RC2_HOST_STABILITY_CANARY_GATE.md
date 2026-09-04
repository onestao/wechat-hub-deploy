# P0 rc.2 Host Stability Canary Gate

Date: 2026-09-04

Scope: `0.1.0-rc.2` single-account NAS canary only.

This gate supersedes any older H2/H3 or clipboard acceptance instructions until it passes. It is a **host-stability canary**, not a throughput benchmark and not a resource profiling exercise.

## 1. Hard prerequisites

Do not start the canary unless all items below are true:

1. `0.1.0-rc.1` remains immutable and blocked.
2. Runtime rc.2 is source-built by GitHub Actions from a commit containing the P0 follow-up fixes documented in `P0_SELKIES_XCLIP_INCIDENT_REPORT.md`.
3. The rc.2 Runtime image is referenced by immutable GHCR digest in the rc.2 manifest/production overlay.
4. CI has passed the Runtime regression suite and shell/static checks.
5. All pre-existing WeChat Hub containers remain stopped before the canary starts; no H2/H3 workload is running.
6. Only **one designated Beta test account** is started for the canary.
7. Clipboard stays hard-disabled. Do not set or test any clipboard-enable override in rc.2, including under HTTPS.
8. No `docker system prune`, `docker volume prune`, destructive data migration, or unrelated NAS operation is allowed.

## 2. Pre-start source/config verification

Before starting the canary, verify the effective production configuration contains:

```text
Runtime Manager       pids_limit = 200
AgentWechat primary   PidsLimit  = 256 (bounded source override)
Selkies companion     PidsLimit  = 100 (bounded source override)
Selkies companion     Memory     = 1024 MiB default
Selkies companion     NanoCpus   = 2.0 cores default
Selkies companion     Init       = true
```

The exact `100/256` PIDs values are **candidate limits**, not automatically production-safe. cgroup PIDs count Linux tasks/threads. The canary must measure normal `pids.current` headroom and confirm `pids.events max` does not increase.

The Runtime Manager's own LinuxServer Selkies environment and the on-demand companion must both have all clipboard paths disabled:

```text
SELKIES_CLIPBOARD_ENABLED=false|locked
SELKIES_CLIPBOARD_IN_ENABLED=false|locked
SELKIES_CLIPBOARD_OUT_ENABLED=false|locked
SELKIES_ENABLE_BINARY_CLIPBOARD=false|locked
SELKIES_UI_SIDEBAR_SHOW_CLIPBOARD=false|locked
```

The AgentWechat child and Selkies companion must have no Host `PortBindings` for internal service ports.

## 3. Host baseline before canary start

Record, do not tune:

```text
date/time
uptime + load average
free memory / swap state
ping latency/loss from the operator workstation
SSH command round-trip latency
current WeChat Hub container list/state
host-wide xclip count **with PID/cgroup/container ownership recorded**
```

There must be no pre-existing **WeChat Hub-owned** `xclip` process before starting. Unrelated NAS workloads may legitimately have their own xclip process; record those as the host baseline and do not touch them.

Do not use synthetic CPU/memory load, message throughput tests, or rapid container churn in this gate.

## 4. cgroup v2 PIDs sampling

For each live canary container, obtain its host PID:

```bash
docker inspect -f '{{.State.Pid}}' <container>
```

On a cgroup-v2 host, derive the container cgroup from the host process:

```bash
PID=<host-pid>
CG=$(awk -F: '$1=="0" {print $3}' /proc/$PID/cgroup)
cat /sys/fs/cgroup"$CG"/pids.current
cat /sys/fs/cgroup"$CG"/pids.max
cat /sys/fs/cgroup"$CG"/pids.events
```

Record `pids.current`, `pids.max`, and the `max` counter in `pids.events` at baseline and during the canary.

**Immediate FAIL** if the `pids.events max` counter increases. That means a task creation was rejected by the cgroup and the configured limit lacks safe headroom for the exercised workload.

## 5. 30-minute real canary protocol

Use low-frequency observation. Suggested cadence is once every 30–60 seconds; do not build a tight polling loop.

### Phase A — primary only, 5 minutes

Start only the designated account's Runtime/AgentWechat primary.

Verify and record:

- account reaches expected healthy/login state;
- actual main WeChat process count is unchanged from the one-client architecture;
- Runtime and primary task counts establish a stable baseline;
- WeChat Hub Runtime/primary `xclip` count is `0`; any unrelated host baseline xclip remains separately attributed;
- host load/SSH/Ping remain normal;
- no `pids.events max` increment.

### Phase B — one Selkies desktop session, 10 minutes

Open one desktop session through the normal WeChat Hub Desktop Gateway.

Verify:

- exactly one account-scoped Selkies companion is created;
- companion `PidsLimit`, Memory, NanoCpus and `Init=true` match the rc.2 source policy;
- no Host port is published by the companion;
- Runtime Manager and companion native clipboard environment is hard-disabled;
- real `xclip` count inside all WeChat Hub canary cgroups remains exactly `0` for the entire phase; host-wide xclip has no unexplained growth relative to the recorded baseline;
- `pids.current` remains bounded with meaningful headroom below `pids.max`;
- `pids.events max` remains unchanged;
- Chinese IME, mouse, keyboard, file upload/download and resize may be smoke-tested, but **clipboard must not be tested or enabled**;
- host load, SSH responsiveness and Ping remain normal.

### Phase C — lifecycle churn, 10 minutes

Perform **at most 5** deliberate open/close cycles with normal human pacing. Do not run an automated rapid churn loop.

For every cycle:

1. Open one desktop session.
2. Confirm one companion exists.
3. Close the browser desktop.
4. Wait `WECHAT_SELKIES_IDLE_TTL_SECONDS` plus a small grace period.
5. Confirm the companion is removed.
6. Confirm no WeChat Hub-owned `xclip`, zombie, or orphan helper remains.
7. Confirm `pids.events max` did not increase.

### Phase D — post-close observation, 5 minutes

Leave the account primary running with no desktop session.

Confirm:

- companion remains absent;
- WeChat Hub-owned `xclip == 0` and host-wide xclip has returned to its attributed pre-canary baseline;
- no monotonic task growth;
- Runtime/primary health remains normal;
- host responsiveness remains normal.

Then stop the canary WeChat Hub containers normally and preserve all persistent data.

## 6. Mandatory FAIL conditions

Any one of the following is an immediate P0 Canary **FAIL**:

- any real `xclip` process appears in a WeChat Hub Runtime/primary/companion cgroup, or host-wide xclip grows without attribution to a pre-existing unrelated workload;
- `pids.events max` increases for any canary container;
- task count grows monotonically across samples without returning to baseline;
- Selkies companion remains after idle TTL + grace;
- zombie/orphan helper count grows across open/close cycles;
- a container loses required PIDs/Memory/CPU/Init limits;
- Runtime or companion clipboard settings are not hard-disabled;
- Host load rises abnormally and remains elevated;
- SSH command latency or Ping loss/latency degrades materially from baseline;
- unrelated NAS workloads become sluggish/unresponsive;
- account isolation or the one-WeChat-client invariant is violated.

On FAIL:

1. Stop only the WeChat Hub canary containers.
2. Set/keep their restart policy disabled while investigating.
3. Preserve volumes, databases, logs and process/cgroup evidence.
4. Do not prune.
5. Keep H2/H3 suspended.

## 7. PASS criteria

The gate passes only if the complete 30-minute real-host protocol finishes with:

```text
WeChat Hub-owned real xclip count        0 throughout
unexplained host-wide xclip growth       0
pids.events max increments              0
monotonic task leak                      none
companion lifecycle cleanup             100% for exercised cycles
orphan/zombie helper growth              none
Runtime native clipboard                hard-disabled
companion clipboard                     hard-disabled
Host responsiveness regression           none observed
single-account data/login integrity      intact
one real WeChat client for the account   preserved
```

The report must include raw before/during/after samples rather than only a final PASS statement.

Only after this gate passes may the project unblock H3 NAS Acceptance and resume H2 resource profiling as separate activities.

