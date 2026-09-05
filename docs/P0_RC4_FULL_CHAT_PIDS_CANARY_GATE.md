# P0 RC.4 Full-Chat PIDs Canary Gate

**Date**: 2026-09-05
**Scope**: `0.1.0-rc.4` single-account NAS canary under real, fully logged-in Chat workload.
**Target Release**: `0.1.0-rc.4`
**Target Host**: Unraid NAS (`/mnt/user/appdata/wechat-hub-f-live`)

---

## 1. Release Gate Directives

The following gate statuses remain strictly in effect:

```text
P0 RC3 IMMUTABLE HOST STABILITY CANARY
= INVALIDATED / FAIL FOR FULL-CHAT WORKLOAD

H3 General Acceptance
= FAIL / BLOCKED

Sending Gate
= SUSPENDED

H2 Resource Profiling
= SUSPENDED (Prohibit auto-resume)

Production Overlay / Promotion
= PENDING APPROVAL (Prohibit auto-advance)
```

**Reason**: The previous `0.1.0-rc.3` Canary tested only startup/idle states (~155 tasks) and failed to test fully authenticated Chat workloads (~250 tasks), failing to detect the `PidsLimit = 256` exhaustion defect.

---

## 2. Hard Prerequisites

Do **not** begin canary sampling until all prerequisites are verified:

1. **RC.3 Immutability**:
   - `0.1.0-rc.1`, `0.1.0-rc.2`, and `0.1.0-rc.3` manifests, digests, and tags remain untouched.
   - `release/manifest-0.1.0-rc.3.yaml` must not be modified.
2. **RC.4 Image & Digest**:
   - GitHub Actions has built the new Runtime image containing the 512 PidsLimit default and resource drift detection.
   - The new immutable GHCR digest is recorded in `release/manifest-0.1.0-rc.4.yaml`.
3. **Container Policy Verification**:
   - The test child container inspect must show:
     ```text
     HostConfig.PidsLimit = 512
     HostConfig.Memory    = 2147483648 (2 GiB)
     ```
   - **Never** test on an un-recreated child still running with `PidsLimit = 256`.
4. **Data Preservation**:
   - Persistent volumes (`/data`, `/home/wechat`, browser files, Core/Console DB) must be preserved.
   - Account B (currently stopped with preserved data) is recommended for controlled recreation.
5. **No Unrelated Actions**:
   - Strict prohibition against `docker system prune`, `docker volume prune`, or unrelated NAS operations.

---

## 3. Mandatory Workload Definition (Full-Chat)

Sampling during QR code display, phone confirmation screens, or initial idle states is **invalid**.

Canary sampling may only commence after confirming:

```text
auth_status:
  view: "Chat"
  status: "logged_in"
```

And verifying in the UI:
1. WeChat main conversation window is completely rendered and responsive.
2. Contact lists and chat history have synced.
3. At least one active conversation has been opened.
4. Child helpers (`WeChatAppEx`, `wxplayer`, `wxocr`, `agent-server`) have spawned naturally.

---

## 4. Host-Side Non-Intrusive Sampling Protocol

**STRICT PROHIBITION**:
Never execute `docker exec <agent-wechat-container> ...` during canary sampling. `docker exec` spawns processes directly inside the container cgroup, which skews measurements and risks triggering cgroup limit exhaustion.

### Sampling Commands & Host-Side Traversal Protocol (Executed on Unraid Host via SSH):

**Critical Methodology Correction**:
Do **NOT** use `ps -T -p "$PID" | wc -l`. In Docker containers, `$PID` is merely the container init PID (for example entrypoint/tini/supervisor). That command only counts the init process's own threads and ignores `wechat`, `WeChatAppEx`, `wxplayer`, `wxocr`, `crashpad`, and `agent-server`.

Instead, the host must traverse all host processes in `/proc/[0-9]*` belonging to the container's cgroup `$CG`, extracting per-process `Name:` and `Threads:` from `status`, plus the command from `cmdline`.

#### Host-Side Read-Only Sampler Script:

```bash
#!/usr/bin/env bash
# Host-side non-intrusive cgroup task and thread sampler.
# Read-only inspection via /proc and cgroup v2. No docker exec, no cgroup mutation.
set -euo pipefail

CONTAINER="${1:-}"
if [ -z "$CONTAINER" ]; then
    echo "Usage: $0 <container_name_or_id>" >&2
    exit 1
fi

PID=$(docker inspect -f '{{.State.Pid}}' "$CONTAINER" 2>/dev/null)
if [ -z "$PID" ] || [ "$PID" -le 0 ]; then
    echo "Error: Container $CONTAINER is not running or has no valid PID" >&2
    exit 1
fi

if [ ! -r "/proc/$PID/cgroup" ]; then
    echo "Error: Cannot read /proc/$PID/cgroup" >&2
    exit 1
fi

CG=$(awk -F: '$1=="0"{print $3}' "/proc/$PID/cgroup")
if [ -z "$CG" ]; then
    echo "Error: Cannot resolve cgroup v2 path for PID $PID" >&2
    exit 1
fi

CG_DIR="/sys/fs/cgroup$CG"
PIDS_CURRENT=""
PIDS_MAX=""
PIDS_EVENTS=""
MEM_CURRENT=""
MEM_MAX=""
MEM_EVENTS=""
if [ -d "$CG_DIR" ]; then
    [ -r "$CG_DIR/pids.current" ] && PIDS_CURRENT=$(cat "$CG_DIR/pids.current")
    [ -r "$CG_DIR/pids.max" ] && PIDS_MAX=$(cat "$CG_DIR/pids.max")
    [ -r "$CG_DIR/pids.events" ] && PIDS_EVENTS=$(tr '\n' ' ' < "$CG_DIR/pids.events")
    [ -r "$CG_DIR/memory.current" ] && MEM_CURRENT=$(cat "$CG_DIR/memory.current")
    [ -r "$CG_DIR/memory.max" ] && MEM_MAX=$(cat "$CG_DIR/memory.max")
    [ -r "$CG_DIR/memory.events" ] && MEM_EVENTS=$(tr '\n' ' ' < "$CG_DIR/memory.events")
fi

echo "============================================================"
echo "Container:      $CONTAINER (init PID: $PID)"
echo "Cgroup Path:    $CG"
echo "pids.current:   ${PIDS_CURRENT:-N/A} | pids.max: ${PIDS_MAX:-N/A}"
echo "pids.events:    ${PIDS_EVENTS:-N/A}"
echo "memory.current: ${MEM_CURRENT:-N/A} | memory.max: ${MEM_MAX:-N/A}"
echo "memory.events:  ${MEM_EVENTS:-N/A}"
echo "============================================================"
printf "%-8s %-8s %-20s %s\n" "PID" "THREADS" "NAME" "COMMAND"
echo "------------------------------------------------------------"

total_wechat=0
total_wechatappex=0
total_wxplayer=0
total_wxocr=0
total_crashpad=0
total_agent_server=0
total_other=0
grand_total=0

for d in /proc/[0-9]*; do
    [ -r "$d/cgroup" ] || continue
    # Compare the complete cgroup v2 path in field 3. Substring matching can
    # accidentally include a similarly named container cgroup.
    if ! awk -F: -v want="$CG" '$1=="0" && $3==want { found=1; exit } END { exit found ? 0 : 1 }' "$d/cgroup"; then
        continue
    fi

    pid=${d#/proc/}
    [ -r "$d/status" ] || continue

    name=$(awk '/^Name:/{print $2}' "$d/status" 2>/dev/null || true)
    threads=$(awk '/^Threads:/{print $2}' "$d/status" 2>/dev/null || true)
    threads=${threads:-1}
    cmd=$(tr '\000' ' ' < "$d/cmdline" 2>/dev/null || true)
    [ -z "$cmd" ] && cmd="[$name]"

    printf "%-8s %-8s %-20s %s\n" "$pid" "$threads" "$name" "$cmd"

    grand_total=$((grand_total + threads))

    case "$name" in
        *WeChatAppEx*|*wechatappex*)
            total_wechatappex=$((total_wechatappex + threads))
            ;;
        *wxplayer*)
            total_wxplayer=$((total_wxplayer + threads))
            ;;
        *wxocr*)
            total_wxocr=$((total_wxocr + threads))
            ;;
        *crashpad*)
            total_crashpad=$((total_crashpad + threads))
            ;;
        *agent-server*|*node*)
            total_agent_server=$((total_agent_server + threads))
            ;;
        *wechat*|*WeChat*)
            total_wechat=$((total_wechat + threads))
            ;;
        *)
            case "$cmd" in
                *WeChatAppEx*)
                    total_wechatappex=$((total_wechatappex + threads))
                    ;;
                *wxplayer*)
                    total_wxplayer=$((total_wxplayer + threads))
                    ;;
                *wxocr*)
                    total_wxocr=$((total_wxocr + threads))
                    ;;
                *crashpad*)
                    total_crashpad=$((total_crashpad + threads))
                    ;;
                *agent-server*)
                    total_agent_server=$((total_agent_server + threads))
                    ;;
                *wechat*|*WeChat*)
                    total_wechat=$((total_wechat + threads))
                    ;;
                *)
                    total_other=$((total_other + threads))
                    ;;
            esac
            ;;
    esac
done

echo "------------------------------------------------------------"
echo "Component Thread Breakdown:"
echo "  wechat:       $total_wechat"
echo "  WeChatAppEx:  $total_wechatappex"
echo "  wxplayer:     $total_wxplayer"
echo "  wxocr:        $total_wxocr"
echo "  crashpad:     $total_crashpad"
echo "  agent-server: $total_agent_server"
echo "  other:        $total_other"
echo "  grand_total:  $grand_total"
if [ -n "$PIDS_CURRENT" ]; then
    delta=$((grand_total - PIDS_CURRENT))
    echo "  cgroup pids.current: $PIDS_CURRENT (delta: $delta)"
fi
echo "============================================================"
```

**Execution Constraints**:
- The script is host-side read-only; syntax must be checked with `bash -n` before use.
- `grand_total` reflects Linux tasks across all processes in the container cgroup and must be checked against `/sys/fs/cgroup$CG/pids.current`. Brief transient differences due to process creation or exit races are expected and recorded.
- Strictly zero `docker exec`, zero cgroup mutation, zero `docker update`, and zero process killing.

---

## 5. Sampling Cadence & Recorded Metrics

- **Duration**: Minimum **30 continuous minutes**.
- **Interval**: **30–60 seconds** per sample (avoid high-frequency tight loops).
- **Required Metrics Per Round**:
  1. `timestamp`
  2. `auth view` and `status`
  3. `pids.current` (cgroup task count)
  4. `pids.max` (expected: 512)
  5. `pids.events max` (cumulative count of fork rejections)
  6. Thread count per component (`wechat`, `WeChatAppEx`, `wxplayer`, `wxocr`, `crashpad`, `agent-server`, `other`, `grand_total`)
  7. `memory.current` and `memory.events`
  8. Application health monitor restart count
  9. `pthread_create EAGAIN` error occurrences in logs
  10. `thread constructor failed` occurrences in logs
- Record summary: **baseline**, **peak**, and **end** values.

---

## 6. PASS Criteria

The canary is judged **PASS** if and only if **all** of the following conditions hold:

1. `HostConfig.PidsLimit == 512` throughout the entire run.
2. `pids.events max` delta == **0** across the entire 30+ minute window.
3. `pthread_create EAGAIN` count == **0**.
4. `thread constructor failed` count == **0**.
5. Health monitor kill / restart count == **0**.
6. Upstream auth remains continuously `view=Chat, status=logged_in`.
7. Task counts oscillate within a normal stable range (e.g. `250 -> 285 -> 310 -> 290 -> 305 -> 280`), without monotonic growth.
8. No accumulating dead WeChat generations or zombie processes.
9. `memory.events oom` and `oom_kill` == **0**.
10. All account data, messages, volumes, and credentials remain intact.

---

## 7. Stop Rule & Leak Detection

If any of the following occur during the 512 canary:
- Continuous monotonic task growth across consecutive sample windows (e.g. `250 -> 310 -> 370 -> 430 -> 480...`).
- `pids.events max` increases (> 0 delta).
- Any `pthread_create EAGAIN` or thread constructor failure occurs.
- Health monitor terminates or restarts WeChat.

**Immediate Actions**:
1. Stop the canary immediately.
2. Mark: **`RC.4 PIDS CANARY = FAIL / POSSIBLE THREAD LEAK`**.
3. **DO NOT** increase `PidsLimit` to 768 or 1024 to mask the symptom.
4. **DO NOT** resume H3 Acceptance, H2 Resource Profiling, or Sending Gate.
5. Pivot directly to granular process/thread ownership leak profiling.

---

## 8. Sizing Convergence Rule

A 30+ minute Full-Chat PASS provides bounded evidence, not a proof of the absence of a long-term leak. It establishes:

1. The RC.3 `256` hard cap has insufficient headroom for the observed Full-Chat workload.
2. In that observed window, `512` did not exhibit PIDs exhaustion, `pthread_create EAGAIN`, or monotonic-growth evidence.

Do not state that a 30-minute PASS proves "not a thread leak". Long-term leak assessment must be assigned to H2 Resource Profiling after the Canary PASS has been formally recorded and the operator resumes H2.

If the container runs for 30+ minutes in full Chat state with the PASS criteria met, record:

- `RC.4 PIDS CANARY = PASS / OBSERVED WINDOW`
- `LONG-TERM LEAK = NOT ASSESSED IN 30-MINUTE WINDOW`
- `NEXT REQUIRED GATE = H2 RESOURCE PROFILING`

Subsequent RC.4 acceptance work may proceed only under the existing explicit operator gate policy; H2 remains suspended until the operator resumes it.
