# P0 RC.4 Full-Chat PIDs Canary Result

**Date**: 2026-09-05
**Target Release**: `0.1.0-rc.4`
**Target Host**: Unraid NAS (`/mnt/user/appdata/wechat-hub-f-live`, Linux 6.6, cgroup v2)
**Target Account**: `testB` (`wechat-agent-testb-a7c4f6c8`, `wxid_rpfflqttdz4a22_7fcd`)
**Runtime Manager Image**: `ghcr.io/onestao/wechat-hub-runtime@sha256:80490cf6a29de306887ca2a9b2218825be1d28c5eafe9cfb9f7978faa1a12e4c`
**Canary Verdict**: **FAIL / STOPPED_BY_HEALTH_MONITOR_RESTART_LOOP**

---

## 1. Executive Summary & Release Gate Directives

The Full-Chat Canary for `0.1.0-rc.4` evaluated the 512 PidsLimit mitigation on Unraid NAS under a fully logged-in, authenticated Chat workload on Account B (`testB`).

### Gate Status

```text
RC.4 RUNTIME IMMUTABLE BUILD   = PASS (bc0c7bf9283cd7299852227cecc27bbbc1842184)
RC.4 RELEASE ASSEMBLY          = PASS (d531a2b051073a9869f17d8f0e1116edba74e9d2)
RC.4 FULL-CHAT PIDS CANARY     = FAIL / STOPPED_BY_HEALTH_MONITOR_RESTART_LOOP
LONG-TERM LEAK                 = NOT ASSESSED IN SHORTENED WINDOW

H3 General Acceptance          = BLOCKED
Sending Gate                   = SUSPENDED
H2 Resource Profiling          = SUSPENDED (Prohibit auto-resume)
Production Promotion           = PENDING APPROVAL (Prohibit auto-advance)
```

### Key Findings

1. **PidsLimit = 512 Headroom Success**:
   - `pids.events max delta == 0` (zero cgroup limit exhaustion).
   - `pthread_create EAGAIN delta == 0` (zero thread creation failures).
   - Peak task count was 186, leaving >326 tasks of headroom within the 512 limit.
   - PIDs exhaustion from RC.3 (at 256 limit) was completely eliminated.
2. **Dual-Account Isolation & Running Quarantine Success**:
   - Running Account A (`f-live-a`, 256 PidsLimit) was **not** recreated and remained running (`Up 16+ hours`).
   - Resource drift was quarantined automatically: `agent_server_healthy: null`, DB keys export blocked, desktop/login blocked, zero `docker exec` executed against A.
   - Account B (`testB`) underwent controlled restart from 256 to 512 with all persistent volumes and auth credentials preserved.
3. **Canary Triggered Immediate STOP Condition (FAIL)**:
   - Upstream `agent_server::sessions::health_monitor` declared WeChat unresponsive every 60s and repeatedly killed/restarted it:
     `[health] WeChat (pid=...) unresponsive for 60s, killing process`
   - A total of **29 health kill/restart events** occurred during the 21.42-minute observation window.
   - Per Gate Rules 17 & 18: `health-monitor kill/restart delta == 0` failed, triggering an immediate Canary stop and FAIL verdict.

---

## 2. Environment & Container Verification

### 2.1 Runtime Manager
- **Container**: `wechat-hub-f-live-runtime` (`b7984dc2efe1ddb1c0e7efb09007c82b0964bca2e90f6e8f4df5ac38823fbe3d`)
- **Image Digest**: `ghcr.io/onestao/wechat-hub-runtime@sha256:80490cf6a29de306887ca2a9b2218825be1d28c5eafe9cfb9f7978faa1a12e4c`
- **PidsLimit**: 200
- **Status**: `healthy`

### 2.2 Account A (f-live-a) — Quarantined Running Drift
- **Container ID**: `3e23182967cea52b000903c51705b0f3ead39492f1bb9070960f6045f2756138` (Created `2026-09-04 20:46:10 +0800`, Up 16+ hours)
- **HostConfig.PidsLimit**: `256` (unchanged, never modified via docker update)
- **Runtime Health**: `degraded`
- **Login Status**: `quarantined-resource-drift`
- **Quarantine Reason**: `agent-wechat container is quarantined due to running resource policy drift ({'PidsLimit': {'current': 256, 'desired': 512}}); controlled restart required`
- **Protection**:
  - Upstream `/health` and `/api/status/auth` probes short-circuited (`agent_server_healthy: null`).
  - DB keys export blocked with drift guard error.
  - Desktop / login creation blocked.
  - Zero `docker exec` executed.

### 2.3 Account B (testB) — Reconciled Canary Target
- **Old Container ID**: `cd658da8bc70fce3ad91413a9a8f7df2050d0e0b2e8119e19c702817015e99c2` (exited, 256 PidsLimit)
- **New Container ID**: `3cad093cfe23e4d33f65fa5d7c47c77a0e281927e4d11751863c05a706714efa`
- **HostConfig.PidsLimit**: `512`
- **HostConfig.Memory**: `2147483648` (2 GiB)
- **PortBindings**: `null` (Port 6174 has zero host binding)
- **Volume Mounts**:
  - `/data` -> `wechat-agent-testb-a7c4f6c8-data` (preserved)
  - `/home/wechat` -> `wechat-agent-testb-a7c4f6c8-home` (preserved)
  - `/home/wechat/WeChatHubFiles` -> `wechat-agent-testb-a7c4f6c8-browser-files` (preserved)
  - `/data/auth-token` -> `/mnt/user/appdata/wechat-hub-f-live/runtime-config/agent-wechat/testb-a7c4f6c8/auth-token` (read-only, preserved)
- **Login Status**: `view=Chat, status=logged_in`, `logged_in_user="wxid_rpfflqttdz4a22_7fcd"` (automatically restored from preserved token)

---

## 3. Canary Metrics & Observation

### 3.1 Sampling Methodology
- Host-side read-only cgroup v2 sampler.
- Exact field match on cgroup path (`/proc/[0-9]*/cgroup` field 3 matching `/docker/<cid>`).
- Zero `docker exec`, zero cgroup writes, zero `docker update`, zero process kill.

### 3.2 Metrics Summary

| Metric | Value | Gate Requirement | Evaluation |
|---|---|---|---|
| **Duration** | 1285.0s (21.42 min) | >= 30 min (stopped early per Rule 18) | **STOPPED EARLY** |
| **Total Samples** | 42 | >= 30 | Recorded |
| **PidsLimit** | 512 | == 512 | **PASS** |
| **PIDs Baseline** | 162 | - | Baseline recorded |
| **PIDs Min / Peak / End** | 53 / 186 / 186 | Headroom > 0 | **PASS** (186 < 512) |
| **pids.events max Delta** | 0 | == 0 | **PASS** |
| **pthread_create EAGAIN Delta** | 0 | == 0 | **PASS** |
| **thread constructor failed Delta** | 0 | == 0 | **PASS** |
| **Memory Current (End)** | 441.6 MB | < 2048 MB | **PASS** |
| **Memory Peak** | 451.8 MB | < 2048 MB | **PASS** |
| **OOM / oom_kill** | 0 / 0 | == 0 | **PASS** |
| **Health Monitor Kill/Restart Delta** | **29** | == 0 | **FAIL** |
| **Auth Stability** | 100% logged_in | Maintained | **PASS** |

### 3.3 Process and Thread Breakdown (Sample 42)

```text
Component Breakdown (Total: 186 tasks):
  wechat:          56 threads
  WeChatAppEx:     55 threads
  wxplayer:         0 threads
  wxocr:            0 threads
  crashpad:         6 threads
  agent-server:    14 threads
  other:           55 threads (Xvfb, dbus, fluxbox, dunst, at-spi, x11vnc, websockify, pulseaudio)
  grand_total:    186 threads
  pids.current:   186 tasks (exact 1:1 match with grand_total)
```

---

## 4. Root Cause of Canary Failure: Upstream Health Monitor Loop

### 4.1 Evidence in Container Logs
The upstream `agent-server` binary contains an internal watchdog (`agent_server::sessions::health_monitor`) that repeatedly times out on WeChat responsiveness:

```text
2026-09-05T04:14:01.442975Z WARN agent_server::sessions::health_monitor: [health] WeChat (pid=105) unresponsive for 60s, killing process
2026-09-05T04:14:01.484662Z INFO agent_server::sessions::health_monitor: [health] Killed WeChat pid=105, will restart automatically
2026-09-05T04:14:02.491156Z WARN agent_server::sessions::health_monitor: [health] WeChat process disappeared (likely crashed), restarting
2026-09-05T04:14:05.508648Z INFO agent_server::sessions::health_monitor: [health] Spawned WeChat for session 'default'
2026-09-05T04:14:06.517265Z INFO agent_server::sessions::health_monitor: [health] WeChat process found (pid=810)
```

This cycle repeated 29 times during the 21.42-minute test run (~every 60-65 seconds).

### 4.2 Impact on Task Count
- When WeChat and its child `WeChatAppEx` processes are alive, tasks peak at ~186.
- When `health_monitor` issues SIGKILL to WeChat, tasks drop to ~53-70 while WeChat restarts.
- Once spawned again, WeChat and WeChatAppEx re-initialize and task count returns to ~180+.

### 4.3 Evaluation
- The PIDs exhaustion mitigation (raising `PidsLimit` from 256 to 512) was 100% effective at the kernel/cgroup level.
- However, the upstream `agent-server:0.11.15` binary's internal health check mechanism fails to maintain a stable session under the authenticated Full-Chat workload.
- In accordance with Gate Rules 17 and 18, this recurring process restart invalidates production stability and requires blocking further rollout.

---

## 5. Data Preservation Verification

Persistent data integrity was verified before and after the controlled restart:

- **Core Database**: `/mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite` (330 MB) intact.
- **Console Database**: `/mnt/user/appdata/wechat-hub-f-live/console-data/console.sqlite` (326 MB) intact.
- **B Auth Token**: `/mnt/user/appdata/wechat-hub-f-live/runtime-config/agent-wechat/testb-a7c4f6c8/auth-token` (65 B) intact.
- **Docker Volumes**: `wechat-agent-testb-a7c4f6c8-data`, `wechat-agent-testb-a7c4f6c8-home`, and `wechat-agent-testb-a7c4f6c8-browser-files` successfully remounted.
- Zero volumes were pruned or deleted.

---

## 6. Conclusion & Gate Actions

1. **RC.4 PIDS CANARY**: Marked **FAIL / STOPPED_BY_HEALTH_MONITOR_RESTART_LOOP**.
2. **Upstream Investigation**: Requires upstream `agent-wechat` analysis to diagnose why `agent_server::sessions::health_monitor` detects WeChat as unresponsive every 60 seconds under authenticated chat conditions.
3. **Rollout Block**:
   - `H3 General Acceptance` remains **BLOCKED**.
   - `Sending Gate` remains **SUSPENDED**.
   - `H2 Resource Profiling` remains **SUSPENDED**.
   - `Production Promotion` remains **PENDING APPROVAL**.
