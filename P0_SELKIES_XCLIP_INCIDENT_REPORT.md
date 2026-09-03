# P0 Incident Report: Selkies / xclip Host Stability Incident

**Incident Date**: 2026-09-03 ~ 2026-09-04  
**Severity**: P0 (Host Exhaustion / Unresponsive Host)  
**Affected Target**: Unraid NAS (Continuous Uptime: 146 Days prior to incident)  
**Release Impacted**: `0.1.0-rc.1`  
**Current Resolution Status**: CONTAINED & MITIGATED (Hotfix Committed in `work/runtime`, Automated Tests & Soak Gate PASS)  
**Release Gate Status**: `0.1.0-rc.1` NAS ACCEPTANCE BLOCKED — P0 HOST STABILITY  

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
| **2026-09-04 ~00:50** | Validation | 43 unit/integration tests and automated 60-cycle Soak Gate executed with 100% PASS. `AGENT.md` updated with Section 15. |
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
2. **Runnable / D-State Task Queue Saturation**:
   Global `kernel.pid_max` was **not** exhausted (7,059 << 4,194,304). Instead, over 7,000 hanging, blocked, or rapidly polling `xclip` processes overwhelmed the Linux kernel task scheduler. CPU scheduler lock contention and timer queue thrashing caused complete starvation of user-space processes, making `sshd` unable to fork/authenticate and network drivers unable to process packets in time.
3. **Selkies Base Image Polling Loop**:
   The LinuxServer `baseimage-selkies` WebRTC service includes clipboard synchronization. When `SELKIES_CLIPBOARD_ENABLED=true`, it repeatedly forks `xclip` to query the X11 clipboard. Without an active X11 selection owner or when the call hung, child processes were not reaped with a strict timeout, leading to unbounded accumulation.

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
   - Non-WeChat Hub workloads on Unraid were completely unaffected.

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
  - Safe opt-in via environment variable: `WECHAT_SELKIES_CLIPBOARD_ENABLED=true` (requires HTTPS).

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
- **Fail-Closed Guarantee**: Any rogue process fork hitting the limit receives `-EAGAIN` within the container cgroup. The host kernel scheduler cannot be affected.

### Principle D: Desktop Session Lifecycle & Companion Auto-Reap
- In [desktop_gateway.py](work/runtime/root/scripts/wechat/desktop_gateway.py):
  - When the last WebSocket/browser session disconnects, `release_manual_gui_lease` schedules idle companion cleanup.
  - Default TTL: 10 seconds (`WECHAT_SELKIES_IDLE_TTL_SECONDS=10`).
  - Upon TTL expiration, `_remove_selkies_container` terminates and removes the companion container.
  - Companion shell entrypoint trap includes `pkill -P "$selkies_pid"` and `pkill -u wechat xclip` to prevent orphan helper processes.

### Principle E: Creation / Deletion Symmetry
- `ensure_selkies_desktop` wrapped in full `try ... except`:
  - If container creation, startup, or health probing fails, `_remove_selkies_container` is immediately executed.
  - No orphan containers or intermediate artifacts remain.

---

## 6. Verification & Automated Test Results

### 6.1 Unit & Integration Test Suite
- Test module: [work/runtime/tests/test_wechat_runtime.py](work/runtime/tests/test_wechat_runtime.py)
- Command: `pytest work/runtime/tests/test_wechat_runtime.py`
- **Result**: **43 passed in 0.74s (100% PASS)**
- Dedicated regression tests:
  1. `test_selkies_clipboard_override_via_env`: Verifies default disabled state and env override.
  2. `test_companion_pids_limit_and_resource_caps_override`: Verifies PidsLimit=100 and memory caps.
  3. `test_desktop_session_release_cleans_up_companion_container`: Verifies companion container removal on session close.
  4. `test_ensure_selkies_desktop_cleans_up_on_probe_failure`: Verifies symmetrical cleanup on creation/probe failure.
  5. `test_companion_failure_on_a_does_not_affect_b_desktop`: Verifies container failure on account A does not degrade account B.
  6. `test_runtime_account_api_returns_fast_degraded_when_companion_fails`: Verifies fast degraded response without blocking.
  7. `test_repeated_session_acquire_release_has_bounded_idle_reap`: Verifies 50 rapid lease churn cycles leave zero orphan leases or timers.

### 6.2 Controlled Soak Gate (Principle G)
- Test module: [work/runtime/tests/test_soak_gate.py](work/runtime/tests/test_soak_gate.py)
- Protocol: 60 cycles simulating repeated multi-account desktop session acquire, churn, and release.
- **Metrics Recorded**:
  - `xclip` process count: `0` (clipboard disabled).
  - Leases at cycle end: `0` (bounded).
  - Active cleanup timers at cycle end: `0` (bounded).
  - Companion containers reaped: `180 / 180` (100% cleanup rate).
  - Memory leak in `desktop_gateway.py`: `0 bytes` (measured via `tracemalloc`).
  - Monotonic resource growth: `None`.
- **Verdict**: **PASS**.

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
Canary Soak Gate (30 min: PIDs < 100, xclip == 0, Load normal)
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
   If clipboard is re-enabled in the future, it must strictly require HTTPS secure context and incorporate an audited in-process reaper or WebRTC data-channel clipboard engine instead of external `xclip` forks.
2. **Upstream AgentWechat Subprocesses**:
   `agent-wechat:0.11.15` wine and chromium renderer processes are now bounded by `PidsLimit: 256`, preventing wine subprocess leaks from affecting the host.
3. **Execution Prohibition**:
   In accordance with P0 instructions, H2 profiling and H3 acceptance drills remain strictly paused until `0.1.0-rc.2` image is published by CI and passes canary soak.
