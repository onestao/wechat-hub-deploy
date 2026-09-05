# P0 Incident Report: RC.3 AgentWechat Full-Chat PIDs Exhaustion

**Incident Date**: 2026-09-04 ~ 2026-09-05
**Severity**: P0 (Container Exhaustion / Release Gate Blocked)
**Affected Target**: Unraid NAS (`/mnt/user/appdata/wechat-hub-f-live`)
**Release Impacted**: `0.1.0-rc.3`
**Current Resolution Status**: CODE READY / RC.4 CANDIDATE IMPLEMENTED (Runtime PidsLimit=512 default + drift detection + 64/64 runtime tests passed; awaiting RC.4 image build and Live Full-Chat Canary Soak)
**Release Gate Status**:
- P0 RC3 IMMUTABLE HOST STABILITY CANARY = **INVALIDATED / FAIL FOR FULL-CHAT WORKLOAD**
- H3 General Acceptance = **FAIL / BLOCKED**
- Sending Gate = **SUSPENDED**
- H2 Resource Profiling = **SUSPENDED** (Prohibit auto-resume)
- Production = **PENDING APPROVAL** (Prohibit auto-advance)

---

## 1. Executive Summary

During Live NAS acceptance of `0.1.0-rc.3` on Unraid, both real accounts (Account A and Account B) experienced severe PID cgroup exhaustion after completing authentication and entering active Chat workload.

The root cause was determined to be a cgroup resource sizing defect:
- `0.1.0-rc.3` enforced a hard `PidsLimit = 256` on the AgentWechat primary container.
- Under full-chat workloads (active chat sessions, synchronized contact lists, spawned `WeChatAppEx` Chromium helper processes, audio/video players, OCR modules, and `agent-server`), the **observed full-chat steady working set** reaches **250–251** concurrent Linux tasks.
- The `256` limit left only ~5 tasks of headroom (~2%), causing intermittent `pthread_create EAGAIN` failures, thread constructor crashes, and cascading health monitor kills/restarts.
- Memory usage was completely normal (~0.98 GiB / 2.0 GiB; zero OOM kills).

---

## 2. Confirmed Field Evidence (Unraid Host Sampling)

### 2.1 Account A Evidence (`wechat-agent-f-live-a-faf35abb`)

Read-only host-side cgroup and log extraction on Account A yielded:

```text
Container:          wechat-agent-f-live-a-faf35abb
Upstream Auth:      view=Chat, status=logged_in
pids.current:       250
pids.max:           256
pids.events.max:    232
```

Error counts across recent 6 hours:
- `pthread_create EAGAIN`: **92**
- `thread constructor failed`: **1**

Memory & OOM exclusion:
- `Docker OOMKilled`: `false`
- `memory.current`: `~0.98 GiB`
- `memory.max`: `2.0 GiB`
- `memory.events` (`max`, `oom`, `oom_kill`): all **0**

Task composition breakdown at peak (total: 250 tasks):

| Process / Component | Task Count (Threads) |
|---|---|
| `wechat` (Main Wine/WeChat process) | 67 |
| `WeChatAppEx` (Chromium applet engine) | 116 |
| `wxplayer` (Media playback helper) | 18 |
| `wxocr` (Optical character recognition) | 5 |
| `crashpad` (Crash handler) | 7 |
| `agent-server` (HTTP API daemon) | 15 |
| other (helpers / bash / tini) | 22 |
| **WeChat Family Total** | **213** |
| **Grand Total (Container Tasks)** | **250** |

Host-side process tree inspection verified a single, coherent WeChat main process tree with its expected child/worker processes. There was **no evidence of massive dead WeChat generational accumulation** from previous runs. Sampling over short host-side intervals showed task counts oscillating tightly in the range **250–251 / 256**.

### 2.2 Account B Evidence

Account B exhibited severe downstream amplification:
- `pthread_create EAGAIN`: **74**
- `thread constructor failed`: **8**
- Health monitor `"WeChat unresponsive"` kills: **7**

Account B was safely halted by operator intervention via standard `docker stop`:
- Container status: `Exited (137)`
- `OOMKilled`: `false`
- **Clarification**: Exit code `137` reflects `SIGKILL` dispatched by the health monitor / `docker stop` timeout, **not** a kernel OOM kill.

The health monitor kill/restart chain acted as a secondary amplifier: when `pthread_create` failed due to cgroup exhaustion, internal HTTP request handlers and window message loops stalled, triggering health monitor timeouts that repeatedly killed and restarted WeChat.

---

## 3. Discrepancy Analysis: RC.3 Canary vs. Real Full-Chat

The original `0.1.0-rc.3` Host Stability Canary recorded:
- Baseline: `155`
- Peak: `158`
- End: `155`
- `pids.events.max`: `0`

**Why the RC.3 Canary missed this failure:**
1. **Workload State Gap**: The RC.3 canary sampled during preliminary startup/login/idle stages where `WeChatAppEx` (which alone spawns ~116 worker threads across Chromium utility, renderer, and GPU threads) had not yet fully initialized.
2. **Missing Gate Criterion**: The RC.3 canary did not strictly verify `auth_status: view=Chat, status=logged_in` accompanied by fully rendered conversations, loaded contact lists, and active renderer sub-processes.
3. Once fully logged into active chat, concurrent tasks immediately jumped from ~155 to ~250, saturating the `256` ceiling.

---

## 4. Root Cause Conclusion & Sizing Justification

1. **Confirmed Root Cause**:
   RC.3 `AGENT_WECHAT_PIDS_LIMIT=256` is an undersized hard limit for the observed real full-chat workload. The 256 hard cap was breached in production (`pids.events.max > 0`), causing repeated `pthread_create EAGAIN` failures while memory OOM was conclusively ruled out.
2. **Remaining Open Hypotheses**:
   While the observed process and thread breakdown reflects expected multi-process WeChat architecture (`WeChatAppEx`, `wxplayer`, `wxocr`, `agent-server`), the 250–251 level must be treated as an **observed full-chat steady working set**, not an irrefutably proven permanent baseline. A multi-hour slow thread or process leak is not yet fully ruled out and must be verified by the 512 Full-Chat Canary.
3. **Selected Candidate Hard Cap: 512 Tasks**:
   - `512` is selected as a **candidate safe hard cap** (clamped to `[64, 1024]`), offering substantial headroom above the observed working set (~250–280 tasks) while strictly preserving cgroup host protection against unbounded exhaustion.
   - `512` is not yet proven to be the minimum production limit; the definitive baseline and final cap will be validated by the 30+ minute Full-Chat Canary Gate.

---

## 5. Existing Child Container Policy Drift Defect

In `0.1.0-rc.3`, `ensure_container()` only checked:
- Image tag mismatch (`current_image != desired_image`)
- Missing desktop mounts (`needs_desktop_mounts`)

It did **not** inspect `HostConfig.PidsLimit` or `HostConfig.Memory`. Consequently, simply changing `AGENT_WECHAT_PIDS_LIMIT=512` in the environment would **not** update existing stopped child containers from `256` to `512`.

**Fixed Behavior in RC.4 Candidate**:
1. Added explicit `_desired_primary_resource_policy()` and `_primary_resource_policy_drift()` inspection.
2. **Stopped containers with drift**: removed (container object only) and recreated with 512, preserving all named volumes, tokens, and data.
3. **Stopped containers matching policy**: preserved without recreation.
4. **Running containers with drift**: inline recreation and `docker update` are strictly prohibited. Running drift is treated as a unified quarantine: status returns `degraded` with `resource_reconcile_required = true`, skips both `/health` and `/api/status/auth` probes, and existing health gates block `api_request`, desktop, and login flows. Defense-in-depth guards also prevent `ensure_interactive_desktop()`, Selkies companion creation, and `export_db_keys()` from issuing any `exec_container` call against the quarantined child. Controlled restart (`restart()`) remains the designated safe path to stop the old container, recreate with 512, and restore normal functionality.
