# Post-F Release Status

Date: 2026-09-04
Status: 0.1.0-rc.3 IMMUTABLE ARTIFACT NAS CANARY PASSED — P0 HOST STABILITY RESOLVED

## Current Incident & Blocking Status

### P0 HOST STABILITY INCIDENT: BLOCKED

- **Release Affected**: `0.1.0-rc.1`
- **NAS Acceptance (H3)**: `MAY RESUME` (Canary PASS: 60/60 rounds, 30 min)
- **Resource Profiling (H2)**: `SUSPENDED` (Do NOT auto-resume without explicit authorization)
- **Incident Summary**: During Selkies Desktop activation on Unraid, >7,000 hanging `xclip -selection clipboard -o -t TARGETS` processes accumulated without a container PID boundary (`HostConfig.PidsLimit=<nil>`), coincident with load average `277.11, 281.70, 240.95` and loss of SSH/ping responsiveness. The subprocess leak and host-wide resource starvation are confirmed; exact runnable/D-state distribution, scheduler-lock mechanics, and the precise upstream reaping defect remain inferred unless reproduced with tracing.
- **Host Recovery**: Unraid NAS recovered cleanly after physical reboot. All WeChat Hub containers have been set to `restart=no` and safely stopped. Zero data loss: all `/data`, `/home/wechat`, database volumes, and NAS services remain completely intact. No prune operations were executed.

### P0 Remediation Implemented (Candidate for 0.1.0-rc.2)

1. **Clipboard Hard-Disabled for rc.2**: AgentWechat companion clipboard (in/out/binary/text/image) is locked off in `_selkies_attach_env()` and cannot be re-enabled by environment override in rc.2. Independent review also found that the Runtime image itself inherits LinuxServer `baseimage-selkies`, whose native clipboard defaults to enabled. The follow-up source patch therefore hard-disables the native `SELKIES_CLIPBOARD_*` settings in the Runtime Dockerfile and all deployment paths as well. HTTPS alone is not treated as a safety proof for xclip. Chinese IME, mouse, keyboard, resize, DPI, and file transfer remain enabled in source configuration but still require rc.2 live canary verification.
2. **Strict Cgroup PidsLimit**: Companion container hard-capped at `PidsLimit = 100` (`WECHAT_SELKIES_PIDS_LIMIT`). Primary AgentWechat container hard-capped at `PidsLimit = 256` (`AGENT_WECHAT_PIDS_LIMIT`). Compose services capped at 100-200.
3. **Session Lifecycle Auto-Reaping**: `desktop_gateway.py` schedules idle companion cleanup upon last WebSocket / session disconnect (10s TTL). Independent review found the first shell trap was invalidated by a later `exec`; rc.2 follow-up source now keeps a Bash PID1 supervisor alive, monitors Selkies + internal gateway with `wait -n`, cleans both on either-child exit, and relies on Docker stop/remove as the final whole-cgroup reap boundary.
4. **Creation Failure Symmetry**: All container creation failures automatically trigger immediate cleanup of orphan companions and artifacts.
5. **Automated Regression**: Independent rerun after the Runtime-manager/baseimage fix, supervisor fix, bounded resource-override hardening, and complete Compose PIDs coverage: `test_wechat_runtime.py` `45/45 PASS`, simulated churn `1/1 PASS`, complete Runtime suite `49/49 PASS`, Stack wiring `10/10 PASS`. The 60-cycle test is explicitly a **simulated lifecycle churn regression** using a dummy companion manager. It verifies bounded leases/timers and callback cleanup, but does not launch real Selkies/xclip/Docker cgroups and is **not** the required NAS host soak.

### Release Policy

- **DO NOT MODIFY 0.1.0-rc.1**: `0.1.0-rc.1` digests are immutable and will NOT be overwritten.
- **Target Release**: `0.1.0-rc.2` (hotfix RC).
- **Next Progression Gate**:
  1. Commit/review the follow-up baseimage clipboard hard-disable on top of `work/runtime@a6b37b1` and `main@bacf555`.
  2. Push the reviewed commits to GitHub to trigger GitHub Actions build for `wechat-hub-runtime:0.1.0-rc.2`.
  3. Obtain immutable GHCR SHA256 digest for `rc.2`.
  4. Author `release/manifest-0.1.0-rc.2.yaml` and update production compose.
  5. Canary deploy on Single Account (Beta Canary) on NAS.
  6. Run a **real 30-minute canary host soak** recording `pids.current/pids.max`, real `xclip` process count, companion create/reap, CPU/RAM, host load, SSH latency and ping loss.
  7. Resume H3 NAS Acceptance and H2 Profiling only after that real Canary soak PASS.

---

## Historical Wave 1 Release Artifacts (0.1.0-rc.1)

| Stream | Component | Git Branch | Commit SHA | CI Run | Publish Run | Immutable GHCR Image Reference |
|---|---|---|---|---|---|---|
| **G1** | Runtime | feat/multi-account-runtime | c24521c | 33741590013 (PASS) | 33742740806 (PASS) | ghcr.io/onestao/wechat-hub-runtime@sha256:a937410908e6fe1df0b06df9b9e3ef51a532fc0d56405fc3d0e0817b9a09244c |
| **G2** | Core | feat/multi-account-core | 1b797ca | 33742411219 (PASS) | 33742744467 (PASS) | ghcr.io/onestao/wechat-hub-core@sha256:40dea31b7b28e67e53e9f570334b488d68e3314703381dd1f59b32b22bbde453 |
| **G3** | Console | feat/decoupled-console | c1b5c02 | 33749826624 (PASS) | 33749952014 (PASS) | ghcr.io/onestao/wechat-hub-console@sha256:d27870c69cf964d06e09b840f984a3a8031b4863d29157aff50420f3123094a1 |
| **G5** | Agent | feat/mcp-monitor-agent | fc941c7 | 33741600166 (PASS) | 33742748637 (PASS) | ghcr.io/onestao/wechat-hub-agent@sha256:d84d66182a84063598b6147ac1e64a098e0c5203b8f74aa472b86ddaa702df74 |
| **G5** | EFB Slave | feat/linux-wechat-slave | 33fa7d6 | 33742419043 (PASS) | 33742753005 (PASS) | ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:b635714873ffe2c0ad9bcfce9295545631d1e2ad301a48f7f71f0d59a5ee5e15 |
| **G4** | Upstream AgentWechat | - | 0.11.15 | - | - | ghcr.io/thisnick/agent-wechat@sha256:31a4e351c191bcbfc75e5c10be51e207d22a3eedd97f3ff56ad579fcce717b24 (amd64: sha256:b5e92047e28ce67e34576e574d8ccf00f8619f485597109f7342a137300285c0) |

## 0.1.0-rc.2 Single Account NAS Canary Soak Results

- **Execution Date**: 2026-09-04 12:34:08 ~ 13:03:52 (UTC+8)
- **Target Host**: Unraid NAS (Linux 6.6, cgroup v2, Docker 27.x)
- **Account**: Beta Single Account (`testB`), Alpha (`f-live-a`) disabled
- **Protocol**: 60 consecutive rounds at 30s interval (30 minutes total)
- **Final Verdict**: `P0 RC2 HOST STABILITY CANARY = PASS`

### Observability & Evidence Summary Table

| Metric Category | Baseline (Round 1) | Peak Observation | End (Round 60) | Limit / Hard Cap | Pass Criteria | Verdict |
|---|---|---|---|---|---|---|
| **Host Load 1m** | 0.91 | 1.45 | 0.79 | Safe Idle (< 4.0) | No abnormal escalation | **PASS** |
| **Host Load 5m** | 0.96 | 1.08 | 0.91 | Safe Idle (< 4.0) | Stable moving average | **PASS** |
| **Host Load 15m** | 0.92 | 0.97 | 0.92 | Safe Idle (< 4.0) | Stable background | **PASS** |
| **Host-wide xclip** | 0 | 0 | 0 | 0 | Strictly == 0 throughout | **PASS** |
| **WeChat Processes** | 1 | 1 | 1 | 1 | Single real instance | **PASS** |
| **Non-Beta Account** | 0 | 0 | 0 | 0 | Zero unauthorized accounts | **PASS** |
| **Runtime Pids** | 54 | 60 | 54 | 200 (`pids_limit`) | events max == 0 | **PASS** |
| **AgentWechat Pids** | 153 | 156 | 155 | 256 (`PidsLimit`) | events max == 0 | **PASS** |
| **Companion Pids** | 4 | 4 | 0 (reaped) | 100 (`PidsLimit`) | events max == 0 | **PASS** |
| **Core Pids** | 10 | 10 | 4 | 100 (`pids_limit`) | events max == 0 | **PASS** |
| **Console Pids** | 2 | 4 | 2 | 100 (`pids_limit`) | events max == 0 | **PASS** |
| **Companion Cleanup** | 1 (active R1-5) | 1 | 0 (reaped R6-60) | 0 orphans | Reaped within TTL, 0 orphans | **PASS** |
| **Kernel OOM** | 0 | 0 | 0 | 0 | Zero dmesg OOM | **PASS** |
| **Ping RTT** | 7ms | 879ms | 6ms | Median 8ms | Sustained connectivity | **PASS** |
| **SSH Latency** | 314ms | 1290ms | 329ms | Median 322ms | Zero handshake failure | **PASS** |

### Release Gate Actions
- **H3 General Acceptance**: Updated to `MAY RESUME`.
- **H2 Resource Profiling**: Remains `SUSPENDED` (Do NOT auto-resume).
- **Production Overlay**: Digests locked to `0.1.0-rc.2`. Do NOT auto-promote to production without operator sign-off.
- **EasyConnect Status**: Verified restored to `Status=exited, RestartPolicy=no`.


---

## 0.1.0-rc.3 Immutable Artifact Verification & Canary Acceptance

### Release & Artifact Identifiers
- **Runtime Source Commit**: `4b76bf67bb3e2e95d9bedf25b1c3cbb53ec7cd9f` (branch `feat/multi-account-runtime`)
- **Runtime Tests**: 50/50 PASS | Stack Tests: 10/10 PASS
- **GitHub Actions CI Run**: `33839413173` (PASS)
- **GitHub Actions Publish Run**: `33856493083` (PASS)
- **Immutable Digest**: `sha256:8fced2d85176f14ee9d804b0bd0d8d88786851d868ed1cb9c846e9f672bdbe9f`
- **OCI Revision**: `4b76bf67bb3e2e95d9bedf25b1c3cbb53ec7cd9f`
- **Release Manifest**: `release/manifest-0.1.0-rc.3.yaml`

### NAS Canary Execution Summary
- **Target Host**: Unraid NAS (Linux 6.6, cgroup v2, Docker 27.x)
- **Account**: Beta Single Account (`testB`), Alpha (`f-live-a`) disabled
- **Execution Window**: 2026-09-04T17:46:45+08:00 ~ 2026-09-04T18:17:31+08:00
- **Duration**: 1846 seconds (30 minutes 46 seconds, >= 30m30s)
- **Samples**: 62 consecutive rounds at 30s interval
- **Zero Hot-Patch Audit (`docker diff`)**: Clean (zero source python files modified)
- **Final Verdict**: `P0 RC3 IMMUTABLE HOST STABILITY CANARY = PASS`

### Observability & Evidence Summary Table (62 Rounds)

| Metric Category | Baseline (Round 1) | Min Observation | Peak Observation | End (Round 62) | Limit / Hard Cap | Verdict |
|---|---|---|---|---|---|---|
| **Host Load 1m** | 2.56 | 0.62 | 2.56 | 1.08 | Safe Idle (< 4.0) | **PASS** |
| **Host Load 5m** | 2.08 | 0.93 | 2.10 | 1.03 | Safe Idle (< 4.0) | **PASS** |
| **Host Load 15m** | 1.49 | 1.06 | 1.56 | 1.08 | Safe Idle (< 4.0) | **PASS** |
| **Host-wide xclip** | 0 | 0 | 0 | 0 | Strictly == 0 throughout | **PASS** |
| **WeChat Processes** | 1 | 1 | 1 | 1 | Single real instance | **PASS** |
| **Non-Beta Account** | 0 | 0 | 0 | 0 | Zero unauthorized accounts | **PASS** |
| **Runtime Pids** | 52 | 52 | 53 | 52 | 200 (`pids_limit`), events max == 0 | **PASS** |
| **AgentWechat Pids** | 155 | 155 | 158 | 155 | 256 (`PidsLimit`), events max == 0 | **PASS** |
| **Companion Pids** | 4 | 0 | 4 | 0 (reaped) | 100 (`PidsLimit`), events max == 0 | **PASS** |
| **Core Pids** | 5 | 4 | 5 | 4 | 100 (`pids_limit`), events max == 0 | **PASS** |
| **Console Pids** | 4 | 2 | 4 | 3 | 100 (`pids_limit`), events max == 0 | **PASS** |
| **Companion Lifecycle** | 1 (active R1-5) | 0 | 1 | 0 (reaped R6-62) | Reaped in <2s, 0 orphans | **PASS** |
| **Kernel OOM** | 0 | 0 | 0 | 0 | Zero dmesg OOM | **PASS** |
| **Ping Latency (GW)** | 0.232ms | 0.155ms | 0.537ms | 0.537ms | Median 0.31ms | **PASS** |

### Release Gate Actions
- **P0 RC3 IMMUTABLE HOST STABILITY CANARY**: **PASS**
- **H3 General Acceptance**: Updated to `MAY RESUME`.
- **H2 Resource Profiling**: Remains `SUSPENDED` (Do NOT auto-resume).
- **Production Overlay**: Digests locked to `0.1.0-rc.3`. Do NOT auto-promote to production without operator sign-off.
- **EasyConnect Status**: Verified maintained at `Status=exited, RestartPolicy=no`.
