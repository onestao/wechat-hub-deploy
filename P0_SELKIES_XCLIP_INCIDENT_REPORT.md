# P0 Incident Report: Selkies / xclip Host Stability Incident

**Incident Date**: 2026-09-03 ~ 2026-09-04  
**Severity**: P0 (Host Exhaustion / Unresponsive Host)  
**Affected Target**: Unraid NAS (Continuous Uptime: 146 Days prior to incident)  
**Release Impacted**: `0.1.0-rc.1`  
**Current Resolution Status**: RESOLVED & VERIFIED ON REAL NAS CANARY SOAK (Canary PASS: 60/60 rounds, 30 min; Zero xclip, bounded PIDs, clean auto-reap)
**Release Gate Status**: `0.1.0-rc.2` NAS CANARY PASSED — H3 ACCEPTANCE `MAY RESUME` (H2 remains SUSPENDED)

---

## 1. Incident Timeline

| Time (UTC+8) | Stage | Event / Observation |
|---|---|---|
| **2026-09-03 ~23:30** | Trigger | Selkies Desktop session attachment path was exercised on the Unraid host during preliminary testing. |
| **2026-09-04 ~00:05** | Escalation | Host load average escalated dramatically to `277.11, 281.70, 240.95`. Network latency spiked; SSH TCP port 22 handshakes and Ping requests began timing out. |
| **2026-09-04 ~00:10** | Triage | Diagnostic sampling revealed `wechat-hub-f-live-runtime` container had accumulated **7,059+ hanging child processes** executing `xclip -selection clipboard -o -t TARGETS`. |
| **2026-09-04 ~00:15** | Host Recovery | User performed physical reboot / IPMI reset of Unraid host to recover administrative connectivity. |
| **2026-09-04 ~00:20** | Containment | All WeChat Hub containers updated to `--restart=no` and safely stopped. Zero data deletion; all persistent volumes, `/data`, `/home/wechat`, and databases preserved. |
| **2026-09-04 ~00:35** | P0 Hotfix | Principles A through E implemented in `work/runtime` (clipboard disabled, cgroup PidsLimit added, lifecycle auto-reap, failure symmetry). |
| **2026-09-04 ~00:50** | Validation | Runtime unit/integration tests and a 60-cycle **simulated lifecycle churn test** executed with PASS. This is not a real Selkies/xclip/Docker/NAS soak and does not replace the rc.2 canary. `AGENT.md` updated with Section 15. |
| **2026-09-04 ~01:05** | Sign-Off | P0 report published; `0.1.0-rc.1` marked BLOCKED; preparation for `0.1.0-rc.2` initiated. |

---

## 2. Confirmed Evidence

1. **Host Load Average**:
   - Recorded load: `277.11, 281.70, 240.95`.
   - Normal baseline after reboot: `load average: 2.50, 2.99, 3.38`.
2. **Process Count & Command Signature**:
   - `7,059` child processes accumulated inside container `wechat-hub-f-live-runtime`.
   - Exact invocation command: `xclip -selection clipboard -o -t TARGETS`.
3. **Cgroup Configuration Defect**:
   - Inspected via `docker inspect -f '{{.HostConfig.PidsLimit}}'`: returned `<nil>` (i.e., `pids.max = max`).
   - No container-level cgroup boundary existed to cap process creation.
4. **Host Kernel Limits**:
   - `cat /proc/sys/kernel/pid_max`: `4,194,304` (4.19M max PIDs).
   - Docker daemon was able to allocate PIDs until the process table saturated CPU scheduling queues.
5. **Post-Reboot Verification**:
   - Unraid kernel dmesg clean: zero OOM kills, zero kernel panics.
   - All WeChat Hub containers in state `Exited (137)` / `Exited (0)` with `RestartPolicy=no`.

---

## 3. Inferred vs. Confirmed Root Cause

### Confirmed Root Cause
1. **No Cgroup Process Boundary (`PidsLimit=<nil>`)**:
   Docker containers were spawned without `PidsLimit`. A subprocess leak inside any container was able to allocate arbitrary numbers of processes directly in the host kernel process table.
2. **Massive Task Accumulation Coincident With Host Starvation**:
   Global `kernel.pid_max` was **not** exhausted (7,059 << 4,194,304). More than 7,000 `xclip` tasks accumulated at the same time as extreme load and loss of SSH responsiveness. This is sufficient to establish a severe subprocess leak and scheduler/resource pressure, but the incident evidence retained so far does **not** preserve a complete per-task state distribution (for example exact runnable vs. D-state counts), scheduler lock statistics, or proof that `sshd` failed specifically at `fork()`. Those lower-level mechanisms therefore remain inferred rather than confirmed.
3. **Selkies Clipboard Path Was Enabled at the Incident Boundary**:
   The Runtime image is based on LinuxServer `baseimage-selkies`, whose clipboard synchronization defaults to enabled unless the native `SELKIES_CLIPBOARD_*` settings are overridden. The observed command signature (`xclip -selection clipboard -o -t TARGETS`) ties the leak to the X11 clipboard path. The exact upstream loop/reaping defect should remain described as inferred unless reproduced with process-level tracing.

### Inferred Root Cause
- The trigger was exacerbated by LAN HTTP access without browser HTTPS secure context, causing Selkies clipboard API to enter error handling loops while repeatedly querying X11 selections.

---

## 4. Host Recovery & Data Safety Verification

1. **Host Status**:
   - Unraid ping round-trip: 6–7 ms.
   - SSH handshake: ~0.4s.
   - Load average: 2.50 (normal idle for multi-container NAS).
2. **Data Directory Integrity**:
   - `/data` and `/home/wechat` across both accounts (Alpha and Beta) are completely intact.
   - Core SQLite / PostgreSQL databases intact.
   - Console database and user sessions intact.
   - Private browser file directories intact.
3. **Operations Forbidden & Enforced**:
   - `docker system prune` / `docker volume prune`: **STRICTLY FORBIDDEN AND NOT RUN**.
   - No data directories or persistent volumes were removed or modified.
   - No evidence was found of data/configuration modification to non-WeChat Hub workloads. Their **availability/performance was necessarily exposed to the host-wide stall**, so they must not be described as completely unaffected.

---

## 5. Containment & Remediation Implementation

### Principle A: Selkies Clipboard Disabled by Default
- In [agent_wechat_runtime.py](work/runtime/root/scripts/wechat/agent_wechat_runtime.py):
  - `SELKIES_DESKTOP_FEATURES["clipboard_text"] = False`
  - `SELKIES_DESKTOP_FEATURES["clipboard_image"] = False`
  - `_selkies_attach_env()` explicitly injects:
    - `SELKIES_CLIPBOARD_ENABLED=false|locked`
    - `SELKIES_CLIPBOARD_IN_ENABLED=false|locked`
    - `SELKIES_CLIPBOARD_OUT_ENABLED=false|locked`
    - `SELKIES_ENABLE_BINARY_CLIPBOARD=false|locked`
    - `SELKIES_UI_SIDEBAR_SHOW_CLIPBOARD=false|locked`
  - Preserved Features: Chinese IME (`local_ime`), mouse, keyboard, dynamic resolution resize, DPI scaling, file upload, file download.
  - **rc.2 has no runtime opt-in**: clipboard is hard-disabled even if `WECHAT_SELKIES_CLIPBOARD_ENABLED=true` is injected. HTTPS is necessary for browser Clipboard APIs but is not sufficient to prove the upstream X11/xclip subprocess path safe.
- **Independent Runtime Manager boundary**: the Runtime image itself inherits LinuxServer `baseimage-selkies`; its built-in Selkies service is a separate process path from the AgentWechat companion. Follow-up review therefore also hard-disables the native baseimage settings `SELKIES_CLIPBOARD_ENABLED`, `SELKIES_CLIPBOARD_IN_ENABLED`, `SELKIES_CLIPBOARD_OUT_ENABLED`, `SELKIES_ENABLE_BINARY_CLIPBOARD`, and the clipboard sidebar in the Dockerfile/Stack/production overlay. The standalone Runtime compose also carries this hard-disable explicitly.

### Principle B & C: Cgroup PidsLimit & Resource Hard Caps
- Companion container:
  - `PidsLimit = 100` (configurable via `WECHAT_SELKIES_PIDS_LIMIT`)
  - `Memory = 1024MB` (`WECHAT_SELKIES_MEM_LIMIT_MB`)
  - `NanoCpus = 2.0` cores (`WECHAT_SELKIES_CPU_LIMIT_CORES`)
- Primary AgentWechat container:
  - `PidsLimit = 256` (`AGENT_WECHAT_PIDS_LIMIT`)
  - `Memory = 2048MB` (`AGENT_WECHAT_MEM_LIMIT_MB`)
- Compose services ([stack/docker-compose.yml](stack/docker-compose.yml) & [release/docker-compose.production.yml](release/docker-compose.production.yml)):
  - `wechat-runtime`: `pids_limit: 200`
  - `wechat-core`: `pids_limit: 100`
  - `wechat-console`: `pids_limit: 100`
  - `wechat-agent`: `pids_limit: 100`
  - `efb-multi`: `pids_limit: 100`
- **Fail-Closed Boundary**: A process-creation storm is bounded by the container cgroup and further forks are rejected after the limit is reached. This sharply limits blast radius, but it does **not** make host impact mathematically impossible: a bounded number of runnable tasks can still consume CPU/I/O, which is why the Selkies companion also has CPU/memory caps and the real NAS canary must monitor host load/latency.

### Principle D: Desktop Session Lifecycle & Companion Auto-Reap
- In [desktop_gateway.py](work/runtime/root/scripts/wechat/desktop_gateway.py):
  - When the last WebSocket/browser session disconnects, `release_manual_gui_lease` schedules idle companion cleanup.
  - Default TTL: 10 seconds (`WECHAT_SELKIES_IDLE_TTL_SECONDS=10`).
  - Upon TTL expiration, `_remove_selkies_container` terminates and removes the companion container.
  - Follow-up review found the original trap was placed before `exec python3`, so the shell supervisor/trap would not survive. rc.2 source now keeps a Bash PID1 supervisor alive, starts Selkies and the internal gateway as separate children, uses `wait -n` to detect either critical child exiting, and performs symmetrical cleanup before container exit. Cleanup no longer depends on an assumed `wechat` UID; Docker stop/remove remains the final whole-cgroup reap boundary.

### Principle E: Creation / Deletion Symmetry
- `ensure_selkies_desktop` wrapped in full `try ... except`:
  - If container creation, startup, or health probing fails, `_remove_selkies_container` is immediately executed.
  - No orphan containers or intermediate artifacts remain.

---

## 6. Verification & Automated Test Results

### 6.1 Unit & Integration Test Suite
- Test module: [work/runtime/tests/test_wechat_runtime.py](work/runtime/tests/test_wechat_runtime.py)
- Command: `pytest work/runtime/tests/test_wechat_runtime.py`
- **Independent review result after closing the Runtime-manager/baseimage clipboard gap, supervisor lifetime bug, resource-override fail-open, and Compose PIDs coverage gaps**: `test_wechat_runtime.py` **45/45 PASS**, simulated churn **1/1 PASS**, complete `work/runtime/tests` **49/49 PASS**, Stack wiring **10/10 PASS**.
- Dedicated regression tests:
  1. `test_selkies_clipboard_override_via_env`: Verifies default disabled state and env override.
  2. `test_companion_pids_limit_and_resource_caps_override`: Verifies PidsLimit=100 and memory caps.
  3. `test_desktop_session_release_cleans_up_companion_container`: Verifies companion container removal on session close.
  4. `test_ensure_selkies_desktop_cleans_up_on_probe_failure`: Verifies symmetrical cleanup on creation/probe failure.
  5. `test_companion_failure_on_a_does_not_affect_b_desktop`: Verifies container failure on account A does not degrade account B.
  6. `test_runtime_account_api_returns_fast_degraded_when_companion_fails`: Verifies fast degraded response without blocking.
  7. `test_repeated_session_acquire_release_has_bounded_idle_reap`: Verifies 50 rapid lease churn cycles leave zero orphan leases or timers.

### 6.2 Simulated Lifecycle Churn Test (Pre-Canary Only)
- Test module: [work/runtime/tests/test_soak_gate.py](work/runtime/tests/test_soak_gate.py)
- Protocol: 60 cycles simulating repeated multi-account desktop session acquire, churn, and release using an in-process dummy companion manager.
- **What it verifies**:
  - Leases at cycle end: `0` (bounded).
  - Active cleanup timers at cycle end: `0` (bounded).
  - Simulated companion removal callbacks: `180 / 180`.
  - Memory leak in `desktop_gateway.py`: `0 bytes` (measured via `tracemalloc`).
  - Monotonic resource growth: `None`.
- **What it does not verify**: it does not start Selkies, does not fork or count real `xclip`, does not create Docker containers/cgroups, and does not observe Unraid host CPU/load/SSH latency. Therefore it is **PASS as a simulated lifecycle regression**, not a Principle G host soak.

### 6.3 Real Host Soak (Principle G) — COMPLETED WITH PASS
- **Status**: **PASS (60 / 60 consecutive rounds, 30 minutes continuous observation)**.
- **Execution Window**: 2026-09-04 12:34:08 ~ 13:03:52 (UTC+8).
- **Target Host**: Unraid NAS (Linux 6.6, cgroup v2, physical machine).
- **Single Account Canary**: Beta account (`testB`), Alpha account (`f-live-a`) disabled.
- **Images Used**:
  - Runtime: `ghcr.io/onestao/wechat-hub-runtime:0.1.0-rc.2` (`sha256:58ad35b9d01ebc0b2d4435978fd2a3281628228507653c83a08788b6c4b9b712`, image ID `38a0329ffee6`)
  - AgentWechat: `ghcr.io/thisnick/agent-wechat:0.11.15` (pinned digest)
  - Core: `wechat-core:f-live-20260901`
  - Console: `wechat-console:f-live-20260901`

#### Detailed Metric Results

1. **Host Load Average**:
   - Baseline (Round 1): `0.91, 0.96, 0.92`
   - Peak (Round 34/55): `1.45, 1.08, 0.97` (momentary background disk I/O, rapidly returned to < 1.0)
   - Final (Round 60): `0.79, 0.91, 0.92`
   - Average across 30 minutes: `0.90` (completely normal NAS idle/operational load). Zero escalation.
2. **xclip Host-Wide Process Count**:
   - Exactly **0 throughout all 60 rounds**. Zero `xclip` process ever spawned.
3. **Single Account Isolation & Real WeChat Process**:
   - WeChat process count: Exactly **1** (`/usr/bin/wechat`, PID 347976).
   - Alpha account container count: Exactly **0**.
4. **Cgroup PIDs Bounded Protection**:
   - `wechat-hub-f-live-runtime`: baseline 54, peak 60, cap 200, headroom 140, `pids.events max` = 0.
   - `wechat-agent-testb-a7c4f6c8`: baseline 153, peak 156, cap 256, headroom 100, `pids.events max` = 0.
   - `wechat-desktop-testb-a7c4f6c8`: baseline 4, peak 4, cap 100, headroom 96, `pids.events max` = 0.
   - `wechat-hub-f-live-core`: baseline 10, peak 10, cap 100, `pids.events max` = 0.
   - `wechat-hub-f-live-console`: baseline 2, peak 4, cap 100, `pids.events max` = 0.
   - **Zero cgroup fork rejections across all containers**.
5. **Selkies Companion Lifecycle & Cleanup**:
   - Active in Rounds 1-5 (verified desktop session creation, mouse, keyboard, Chinese IME, file exchange).
   - Released and cleanly reaped in Round 6 (stopped and removed within 10s TTL).
   - Verified in Rounds 7-60: `docker ps -a --filter name=wechat-desktop-` returned 0 containers. **Zero orphan containers**.
6. **Kernel & Network Stability**:
   - `dmesg` OOM events: **0**.
   - Ping RTT: min 6ms, median 8ms, avg 61.9ms.
   - SSH command latency: min 256.6ms, median 322.2ms, avg 382.3ms.
   - EasyConnect isolation: preserved and verified in original state (`Status=exited, RestartPolicy=no`).

**Canary Soak Verdict**: `P0 RC2 HOST STABILITY CANARY = PASS`.

---

## 7. Release Governance & Next Steps

### Release Handling (Principle H)
- `0.1.0-rc.1` NAS Acceptance: **`BLOCKED — P0 HOST STABILITY`**.
- `0.1.0-rc.1` immutable GHCR image digests are **preserved without modification**.
- Source commit with P0 hotfix: `a6b37b1` in `work/runtime`.
- New target release: **`0.1.0-rc.2`**.

### Release Progression Gate
```text
Commit P0 hotfix (a6b37b1)
  │
  ▼
GitHub Actions CI & Image Build
  │
  ▼
New Immutable GHCR Image Reference (0.1.0-rc.2)
  │
  ▼
Publish release/manifest-0.1.0-rc.2.yaml
  │
  ▼
Single Account Canary Deploy (Beta Canary on NAS)
  │
  ▼
Canary Soak Gate (30 min: real cgroup/process/host observations)
  │
  ▼
Unblock H3 NAS Acceptance & Resume H2 Resource Profiling
```

### Agent Governance Rules (Principle I)
- Updated `AGENT.md` and `AGENTS.md` with **Section 15: Subprocess 与 Container 资源防护硬规则 (P0 防护)**.
- Hard requirements enforced:
  - Mandatory cgroup `PidsLimit` on all containers.
  - Fail-closed isolation between containers.
  - Symmetrical lifecycle cleanup for sessions and companions.
  - Prohibition of un-reaped subprocess polling.
  - Mandatory task completion garbage checks.

---

## 8. Remaining Risks & Recommendations

1. **Clipboard Enablement Risk**:
   Clipboard must remain hard-disabled for rc.2. If re-enabled in a later release, it must strictly require HTTPS secure context **and** incorporate an audited in-process reaper or a clipboard backend that does not permit unbounded external `xclip` forks. Re-enablement requires a new host-stability gate; it is not a configuration-only change.
2. **Upstream AgentWechat Subprocesses**:
   `agent-wechat:0.11.15` wine and chromium renderer processes are now bounded by `PidsLimit: 256`, preventing wine subprocess leaks from affecting the host.
3. **Execution Prohibition**:
   In accordance with P0 instructions, H2 profiling and H3 acceptance drills remain strictly paused until `0.1.0-rc.2` image is published by CI and passes canary soak.
