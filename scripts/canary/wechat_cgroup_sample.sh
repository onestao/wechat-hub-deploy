#!/usr/bin/env bash
# Host-side read-only cgroup/task sampler for the WeChat Hub agent-wechat container.
# One invocation emits exactly one JSONL sample line on stdout.
#
# Read surface: docker inspect, docker logs, /proc, /sys/fs/cgroup (cgroup v2).
# Strictly read-only: nothing is exec'd into the target container, no mutating
# docker subcommands, no process signals, no cgroup mutation. Task counts come
# from traversing /proc/[0-9]* and matching the cgroup v2 path (field 3)
# exactly; threads come from /proc/PID/status "Threads:". "ps" is never used.
# /proc read failures are classified per the canary proc-race policy (see the
# block above the sampler loop): vanish-or-recovered reads count as transient
# races; persistent failures on present pids are reported separately.
set -euo pipefail

usage() {
    printf '%s\n' "Usage: $0 --container NAME_OR_ID [--status-url URL] [--run-id ID] [--profile NAME] \\
       [--proc-root PATH] [--cgroup-root PATH] [--docker-bin PATH] [--watchdog-log-file PATH] \\
       [--pattern-unresponsive RE] [--pattern-killed RE] [--pattern-disappeared RE] [--pattern-spawned RE] \\
       [--pattern-eagain-main RE] [--pattern-eagain-cause RE] [--pattern-ctor RE] \\
       [--container-id ID] [--container-name NAME] [--container-init-pid PID] [--container-state STATUS] \\
       [--host-pids-limit N] [--docker-oom-killed BOOL] [--started-at TS] \\
       [--container-image IMAGE] [--container-image-id ID] [--container-repo-digest DIGEST] \
       [--runtime-container NAME_OR_ID] [--runtime-id ID] [--runtime-image IMAGE] \
       [--runtime-image-id ID] [--runtime-repo-digest DIGEST] [--runtime-state STATUS] \
       (container overrides replace docker inspect; watchdog-log-file replaces docker logs)"
}

# BEGIN DESTRUCTIVE GUARD
refuse_destructive() {
    printf 'error: %s\n' "$1" >&2
    exit 3
}
if [[ "${WECHAT_CANARY_ALLOW_DESTRUCTIVE:-0}" == "1" || "${WECHAT_CANARY_ALLOW_DESTRUCTIVE:-0}" == "true" ]]; then
    refuse_destructive "WECHAT_CANARY_ALLOW_DESTRUCTIVE is set; this toolkit is strictly read-only and has no destructive mode"
fi
check_args_readonly() {
    local arg lowered
    for arg in "$@"; do
        lowered=$(printf '%s' "$arg" | tr '[:upper:]' '[:lower:]')
        case "$lowered" in
            *"docker exec"*|*"docker update"*|*"docker restart"*|*"docker stop"*|*"docker kill"*|*"docker rm"*|*"docker pause"*|*pkill*|*killall*|*"kill -9"*|*"rm -rf"*|*prune*)
                refuse_destructive "refusing destructive argument: $arg"
                ;;
        esac
    done
}
check_args_readonly "$@"
# END DESTRUCTIVE GUARD

container=""
status_url=""
run_id=""
profile="adhoc"
proc_root="${WECHAT_CANARY_PROC_ROOT:-/proc}"
cgroup_root="${WECHAT_CANARY_CGROUP_ROOT:-/sys/fs/cgroup}"
docker_bin="${WECHAT_CANARY_DOCKER_BIN:-docker}"
watchdog_log_file=""
pattern_unresponsive="unresponsive"
pattern_killed="killed wechat pid="
pattern_disappeared="wechat process disappeared"
pattern_spawned="spawned wechat"
pattern_eagain_main="pthread_create"
pattern_eagain_cause="eagain|resource temporarily unavailable"
pattern_ctor="thread constructor failed"
override_id=""
override_name=""
override_pid=""
override_state=""
override_host_pids_limit="-1"
override_oom_killed="false"
override_image=""
override_image_id=""
override_repo_digest=""
runtime_container=""
override_runtime_id=""
override_runtime_state=""
override_runtime_image=""
override_runtime_image_id=""
override_runtime_repo_digest=""
override_started_at=""

while (($#)); do
    case "$1" in
        --container) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; container=$2; shift 2 ;;
        --status-url) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; status_url=$2; shift 2 ;;
        --run-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; run_id=$2; shift 2 ;;
        --profile) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; profile=$2; shift 2 ;;
        --proc-root) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; proc_root=$2; shift 2 ;;
        --cgroup-root) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; cgroup_root=$2; shift 2 ;;
        --docker-bin) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; docker_bin=$2; shift 2 ;;
        --watchdog-log-file) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; watchdog_log_file=$2; shift 2 ;;
        --pattern-unresponsive) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_unresponsive=$2; shift 2 ;;
        --pattern-killed) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_killed=$2; shift 2 ;;
        --pattern-disappeared) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_disappeared=$2; shift 2 ;;
        --pattern-spawned) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_spawned=$2; shift 2 ;;
        --pattern-eagain-main) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_eagain_main=$2; shift 2 ;;
        --pattern-eagain-cause) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_eagain_cause=$2; shift 2 ;;
        --pattern-ctor) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; pattern_ctor=$2; shift 2 ;;
        --container-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_id=$2; shift 2 ;;
        --container-name) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_name=$2; shift 2 ;;
        --container-init-pid) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_pid=$2; shift 2 ;;
        --container-state) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_state=$2; shift 2 ;;
        --host-pids-limit) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_host_pids_limit=$2; shift 2 ;;
        --docker-oom-killed) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_oom_killed=$2; shift 2 ;;
        --started-at) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_started_at=$2; shift 2 ;;
        --container-image) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_image=$2; shift 2 ;;
        --container-image-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_image_id=$2; shift 2 ;;
        --container-repo-digest) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_repo_digest=$2; shift 2 ;;
        --runtime-container) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; runtime_container=$2; shift 2 ;;
        --runtime-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_runtime_id=$2; shift 2 ;;
        --runtime-state) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_runtime_state=$2; shift 2 ;;
        --runtime-image) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_runtime_image=$2; shift 2 ;;
        --runtime-image-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_runtime_image_id=$2; shift 2 ;;
        --runtime-repo-digest) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; override_runtime_repo_digest=$2; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'error: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

json_escape() {
    local value=$1
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//$'\n'/\\n}
    value=${value//$'\r'/\\r}
    value=${value//$'\t'/\\t}
    printf '%s' "$value"
}

read_counter() {
    local file=$1 key=$2 value
    value=$(awk -v wanted="$key" '$1 == wanted { print $2; found=1; exit } END { if (!found) print 0 }' "$file" 2>/dev/null | tr -d '\r') || value=0
    [[ "$value" =~ ^[0-9]+$ ]] || value=0
    printf '%s' "$value"
}

docker_call() {
    local executable="$docker_bin"
    case "$executable" in
        [A-Za-z]:/*)
            if command -v cygpath >/dev/null 2>&1; then
                executable=$(cygpath -u "$executable")
            fi
            ;;
    esac
    if [[ -f "$executable" ]]; then
        bash "$executable" "$@"
    else
        "$executable" "$@"
    fi
}

collection_mode="live"
if [[ -n "$override_pid" ]]; then
    collection_mode="offline-fixture"
    [[ "$override_pid" =~ ^[0-9]+$ ]] || { printf 'error: --container-init-pid must be a non-negative integer\n' >&2; exit 2; }
    container_id=${override_id:-offline-fixture}
    container_name=${override_name:-${container:-$container_id}}
    container_pid=$override_pid
    container_state=${override_state:-running}
    host_pids_limit=$override_host_pids_limit
    docker_oom_killed=$override_oom_killed
    started_at=$override_started_at
    container_image=${override_image:-}
    container_image_id=${override_image_id:-}
    container_repo_digest=${override_repo_digest:-}
    runtime_id=${override_runtime_id:-}
    runtime_state=${override_runtime_state:-running}
    runtime_image=${override_runtime_image:-}
    runtime_image_id=${override_runtime_image_id:-}
    runtime_repo_digest=${override_runtime_repo_digest:-}
else
    [[ -n "$container" ]] || { printf 'error: --container is required\n' >&2; exit 2; }
    local_inspect=$(docker_call inspect --format '{{.Id}}|{{.State.Pid}}|{{.HostConfig.PidsLimit}}|{{.State.Status}}|{{.State.OOMKilled}}|{{.State.StartedAt}}|{{.Config.Image}}|{{.Image}}' "$container" 2>/dev/null) || {
        printf 'error: docker inspect failed for container: %s\n' "$container" >&2
        exit 1
    }
    IFS='|' read -r container_id container_pid host_pids_limit container_state docker_oom_killed started_at container_image container_image_id <<< "$local_inspect"
    container_name=$container
    [[ "$container_id" =~ ^[0-9a-fA-F]{12,64}$ ]] || { printf 'error: docker inspect returned an invalid container id\n' >&2; exit 1; }
    [[ "$container_pid" =~ ^[0-9]+$ ]] || container_pid=0
    [[ "$host_pids_limit" =~ ^[0-9]+$ ]] || host_pids_limit=-1
    [[ "$docker_oom_killed" == "true" ]] && docker_oom_killed="true" || docker_oom_killed="false"

    if [[ -n "$override_image" ]]; then container_image="$override_image"; fi
    if [[ -n "$override_image_id" ]]; then container_image_id="$override_image_id"; fi
    if [[ -n "$override_repo_digest" ]]; then
        container_repo_digest="$override_repo_digest"
    elif [[ -n "$container_image_id" ]]; then
        container_repo_digest=$(docker_call inspect --format '{{index .RepoDigests 0}}' "$container_image_id" 2>/dev/null || true)
    else
        container_repo_digest=""
    fi

    runtime_id="${override_runtime_id:-}"
    runtime_state="${override_runtime_state:-}"
    runtime_image="${override_runtime_image:-}"
    runtime_image_id="${override_runtime_image_id:-}"
    runtime_repo_digest="${override_runtime_repo_digest:-}"

    if [[ -n "$runtime_container" ]]; then
        runtime_inspect=$(docker_call inspect --format '{{.Id}}|{{.State.Status}}|{{.Config.Image}}|{{.Image}}' "$runtime_container" 2>/dev/null || true)
        if [[ -n "$runtime_inspect" ]]; then
            IFS='|' read -r r_id r_state r_image r_img_id <<< "$runtime_inspect"
            [[ -z "$runtime_id" ]] && runtime_id="$r_id"
            [[ -z "$runtime_state" ]] && runtime_state="$r_state"
            [[ -z "$runtime_image" ]] && runtime_image="$r_image"
            [[ -z "$runtime_image_id" ]] && runtime_image_id="$r_img_id"
            if [[ -z "$runtime_repo_digest" && -n "$runtime_image_id" ]]; then
                runtime_repo_digest=$(docker_call inspect --format '{{index .RepoDigests 0}}' "$runtime_image_id" 2>/dev/null || true)
            fi
        fi
    fi
fi
[[ "$container_pid" =~ ^[0-9]+$ && "$container_pid" -gt 0 ]] || {
    printf 'error: container %s is not running (init pid: %s)\n' "${container:-$container_id}" "$container_pid" >&2
    exit 1
}
[[ "$docker_oom_killed" == "true" || "$docker_oom_killed" == "false" ]] || docker_oom_killed="false"
[[ "$host_pids_limit" =~ ^[0-9]+$ ]] || host_pids_limit=-1

# Resolve the container cgroup v2 path from the init pid (field 3 of the
# unified-hierarchy line). Exact path matching is used for every task below;
# substring matching would risk counting a similarly named container cgroup.
cgroup_path=""
if [[ -r "$proc_root/$container_pid/cgroup" ]]; then
    cgroup_path=$(awk -F: '$1 == "0" { print $3; found=1; exit } END { if (!found) exit 1 }' "$proc_root/$container_pid/cgroup" 2>/dev/null | tr -d '\r' || true)
fi
[[ -n "$cgroup_path" && "$cgroup_path" == /* && "$cgroup_path" != *".."* ]] || {
    printf 'error: unable to resolve the container cgroup v2 path (pid %s)\n' "$container_pid" >&2
    exit 1
}
cgroup_dir="${cgroup_root%/}${cgroup_path}"
[[ -r "$cgroup_dir/pids.current" ]] || { printf 'error: unreadable cgroup: %s\n' "$cgroup_dir" >&2; exit 1; }

pids_current=$(tr -d '\r' < "$cgroup_dir/pids.current")
pids_max=$(tr -d '\r' < "$cgroup_dir/pids.max")
[[ "$pids_current" =~ ^[0-9]+$ ]] || pids_current=0
if [[ "$pids_max" != "max" && ! "$pids_max" =~ ^[0-9]+$ ]]; then
    pids_max="max"
fi
pids_events_max=$(read_counter "$cgroup_dir/pids.events" max)
memory_current=0
memory_max="max"
[[ -r "$cgroup_dir/memory.current" ]] && memory_current=$(tr -d '\r' < "$cgroup_dir/memory.current")
[[ -r "$cgroup_dir/memory.max" ]] && memory_max=$(tr -d '\r' < "$cgroup_dir/memory.max")
[[ "$memory_current" =~ ^[0-9]+$ ]] || memory_current=0
if [[ "$memory_max" != "max" && ! "$memory_max" =~ ^[0-9]+$ ]]; then
    memory_max="max"
fi
memory_oom=$(read_counter "$cgroup_dir/memory.events" oom)
memory_oom_kill=$(read_counter "$cgroup_dir/memory.events" oom_kill)

process_count=0
thread_count=0
zombie_count=0
proc_race_count=0
proc_read_error_count=0
wechat_procs=0; wechat_threads=0
wechatappex_procs=0; wechatappex_threads=0
wxplayer_procs=0; wxplayer_threads=0
wxocr_procs=0; wxocr_threads=0
crashpad_procs=0; crashpad_threads=0
agent_server_procs=0; agent_server_threads=0
other_procs=0; other_threads=0

# ---------------------------------------------------------------------------
# /proc read-failure classification (canary proc-race policy, see
# docs/RC5_H2_PREFLIGHT.md):
#   race       — the pid directory no longer exists (natural exit during the
#                sampling sweep) or the read succeeds on one immediate retry
#                (torn read of a process that is exiting); this is the only
#                failure mode the summarizer's --max-proc-races tolerance may
#                cover;
#   read_error — the pid is still present but the read keeps failing
#                (unexplained); counted separately as proc_read_error_count
#                and never tolerated as a race.
# A process that vanishes after the glob but before its loop turn is skipped
# silently (no contribution, no counter) — identical to the RC.5 baseline.
# ---------------------------------------------------------------------------
resolve_proc_cgroup() {
    # Resolve the cgroup v2 path (field 3 of the unified-hierarchy line) of a
    # /proc pid dir into the global `resolved_cgroup` ("" on failure).
    local dir=$1 first_line=""
    resolved_cgroup=""
    if { IFS= read -r first_line; } < "$dir/cgroup" 2>/dev/null; then
        if [[ "$first_line" == 0::* ]]; then
            resolved_cgroup=${first_line#0::}
        else
            resolved_cgroup=$(awk -F: '$1 == "0" { print $3; found=1; exit } END { if (!found) exit 1 }' "$dir/cgroup" 2>/dev/null | tr -d '\r' || true)
        fi
    fi
}

read_task_fields() {
    # Read Name/Threads/State from a /proc pid status file into the globals
    # task_name/task_threads/task_state. Returns 0 only when the process name
    # and a numeric thread count were parsed.
    local dir=$1 status_key status_rest
    task_name=""
    task_threads=""
    task_state=""
    [[ -r "$dir/status" ]] || return 1
    while read -r status_key status_rest; do
        case "$status_key" in
            Name:) task_name=$status_rest ;;
            Threads:) task_threads=$status_rest ;;
            State:) task_state=${status_rest%% *} ;;
        esac
        if [[ -n "$task_name" && "$task_threads" =~ ^[0-9]+$ && -n "$task_state" ]]; then
            break
        fi
    done < "$dir/status" 2>/dev/null || return 1
    [[ -n "$task_name" && "$task_threads" =~ ^[0-9]+$ ]] || return 1
    return 0
}

for process_dir in "$proc_root"/[0-9]*; do
    [[ -d "$process_dir" ]] || continue

    # Fast path: first cgroup line "0::<path>" (pure cgroup v2 hosts); fall
    # back to a full scan for hybrid layouts. Exact field-3 equality only.
    resolve_proc_cgroup "$process_dir"
    if [[ -z "$resolved_cgroup" ]]; then
        if [[ ! -d "$process_dir" ]]; then
            proc_race_count=$((proc_race_count + 1))
            continue
        fi
        resolve_proc_cgroup "$process_dir"
        if [[ -n "$resolved_cgroup" ]]; then
            proc_race_count=$((proc_race_count + 1))
        else
            proc_read_error_count=$((proc_read_error_count + 1))
            continue
        fi
    fi
    [[ "$resolved_cgroup" == "$cgroup_path" ]] || continue

    task_read_rc=0
    read_task_fields "$process_dir" || task_read_rc=$?
    if ((task_read_rc != 0)); then
        if [[ ! -d "$process_dir" ]]; then
            proc_race_count=$((proc_race_count + 1))
            continue
        fi
        read_task_fields "$process_dir" || task_read_rc=$?
        if ((task_read_rc == 0)); then
            proc_race_count=$((proc_race_count + 1))
        elif [[ ! -d "$process_dir" ]]; then
            proc_race_count=$((proc_race_count + 1))
            continue
        else
            proc_read_error_count=$((proc_read_error_count + 1))
            continue
        fi
    fi
    name=$task_name
    threads=$task_threads
    state=$task_state

    cmdline=""
    if [[ -r "$process_dir/cmdline" ]]; then
        cmdline=$(tr '\000' ' ' < "$process_dir/cmdline" 2>/dev/null || true)
    fi
    identity="$name $cmdline"
    process_count=$((process_count + 1))
    thread_count=$((thread_count + threads))
    [[ "$state" == "Z" ]] && zombie_count=$((zombie_count + 1))

    # Component precedence follows docs/P0_RC4_FULL_CHAT_PIDS_CANARY_GATE.md.
    case "$identity" in
        *WeChatAppEx*|*wechatappex*)
            wechatappex_procs=$((wechatappex_procs + 1)); wechatappex_threads=$((wechatappex_threads + threads)) ;;
        *wxplayer*)
            wxplayer_procs=$((wxplayer_procs + 1)); wxplayer_threads=$((wxplayer_threads + threads)) ;;
        *wxocr*)
            wxocr_procs=$((wxocr_procs + 1)); wxocr_threads=$((wxocr_threads + threads)) ;;
        *crashpad*)
            crashpad_procs=$((crashpad_procs + 1)); crashpad_threads=$((crashpad_threads + threads)) ;;
        *agent-server*|*node*)
            agent_server_procs=$((agent_server_procs + 1)); agent_server_threads=$((agent_server_threads + threads)) ;;
        *WeChat*|*wechat*)
            wechat_procs=$((wechat_procs + 1)); wechat_threads=$((wechat_threads + threads)) ;;
        *)
            other_procs=$((other_procs + 1)); other_threads=$((other_threads + threads)) ;;
    esac
done

# Watchdog / EAGAIN counters are cumulative over the container log (or the
# supplied fixture log file). Window deltas are computed by the summarizer.
log_source="docker"
if [[ -n "$watchdog_log_file" ]]; then
    log_source="file"
    [[ -r "$watchdog_log_file" ]] || { printf 'error: unreadable watchdog log file: %s\n' "$watchdog_log_file" >&2; exit 1; }
    logs=$(cat "$watchdog_log_file")
else
    logs=$(docker_call logs "$container" 2>&1 || true)
fi
count_matches() {
    local label=$1 regex=$2
    if [[ "$label" == "eagain" ]]; then
        printf '%s\n' "$logs" | awk '{ line=tolower($0) } line ~ /'"$pattern_eagain_main"'/ && line ~ /'"$pattern_eagain_cause"'/ { count++ } END { print count + 0 }'
    else
        printf '%s\n' "$logs" | awk -v pat="$regex" '{ line=tolower($0) } line ~ pat { count++ } END { print count + 0 }'
    fi
}
watchdog_unresponsive=$(count_matches unresponsive "$pattern_unresponsive")
watchdog_killed=$(count_matches killed "$pattern_killed")
watchdog_disappeared=$(count_matches disappeared "$pattern_disappeared")
watchdog_spawned=$(count_matches spawned "$pattern_spawned")
watchdog_eagain=$(count_matches eagain "")
watchdog_ctor=$(count_matches ctor "$pattern_ctor")

# Optional status endpoint: reported auth state only. The persisted FSM
# context can be stale, so current_ui_observation is always "unknown" here.
status_url_json="null"
auth_obj_json="null"
if [[ -n "$status_url" ]]; then
    status_url_json="\"$(json_escape "$status_url")\""
    python_bin="${WECHAT_CANARY_PYTHON_BIN:-}"
    if [[ -z "$python_bin" ]]; then
        for candidate in python3 python; do
            if command -v "$candidate" >/dev/null 2>&1; then
                p=$(command -v "$candidate")
                [[ "$p" == *"WindowsApps"* ]] && continue
                if "$p" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
                    python_bin="$p"
                    break
                fi
            fi
        done
    fi
    if [[ -n "$python_bin" ]]; then
        auth_obj=$("$python_bin" - "$status_url" <<'PYEOF' 2>/dev/null || true
import json, ssl, sys, urllib.request

url = sys.argv[1]

def fetch(context):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "wechat-hub-canary-sampler/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5, context=context) as resp:
        return resp.read(65536).decode("utf-8", "replace")

result = {"http_ok": False}
try:
    body = fetch(None)
    result["tls_verified"] = True
except Exception:
    try:
        body = fetch(ssl._create_unverified_context())
        result["tls_verified"] = False
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        body = None

if body is not None:
    result["http_ok"] = True
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    if isinstance(data, dict):
        identified = data.get("identified") if isinstance(data.get("identified"), dict) else {}
        result["status"] = data.get("status") or data.get("auth_status") or data.get("wechat_login_status")
        result["view"] = data.get("view")
        result["logged_in"] = data.get("logged_in")
        result["main_window"] = identified.get("main_window", data.get("main_window"))
        result["logged_in_user"] = (
            data.get("loggedInUser")
            or data.get("logged_in_user")
            or data.get("wxid")
            or identified.get("logged_in_user")
        )
        result["account_id"] = data.get("account_id") or data.get("accountId")
        result["wechat_login_status"] = data.get("wechat_login_status")
        result["raw"] = data
    else:
        result["error"] = "response body is not a JSON object"

print(json.dumps(result, separators=(",", ":"), ensure_ascii=False, default=str))
PYEOF
)
        auth_obj=${auth_obj//$'\n'/}
        if [[ "$auth_obj" == '{'* ]]; then
            auth_obj_json="$auth_obj"
        else
            auth_obj_json='{"http_ok": false, "error": "status collection failed"}'
        fi
    else
        auth_obj_json='{"http_ok": false, "error": "python interpreter not available"}'
    fi
fi

timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
if [[ "$pids_max" =~ ^[0-9]+$ ]]; then pids_max_json=$pids_max; else pids_max_json="\"$pids_max\""; fi
if [[ "$memory_max" =~ ^[0-9]+$ ]]; then memory_max_json=$memory_max; else memory_max_json="\"$memory_max\""; fi
if [[ "$container_pid" =~ ^[0-9]+$ && "$container_pid" -gt 0 ]]; then init_pid_json=$container_pid; else init_pid_json=null; fi
if [[ -n "$run_id" ]]; then run_id_json="\"$(json_escape "$run_id")\""; else run_id_json=null; fi
profile_json="\"$(json_escape "$profile")\""
if [[ -n "$started_at" ]]; then started_at_json="\"$(json_escape "$started_at")\""; else started_at_json=null; fi
if [[ "$host_pids_limit" =~ ^[0-9]+$ ]]; then host_pids_limit_json=$host_pids_limit; else host_pids_limit_json=null; fi

if [[ -n "$container_image" ]]; then container_image_json="\"$(json_escape "$container_image")\""; else container_image_json=null; fi
if [[ -n "$container_image_id" ]]; then container_image_id_json="\"$(json_escape "$container_image_id")\""; else container_image_id_json=null; fi
if [[ -n "$container_repo_digest" ]]; then container_repo_digest_json="\"$(json_escape "$container_repo_digest")\""; else container_repo_digest_json=null; fi

if [[ -n "$runtime_id" || -n "$runtime_image" || -n "$runtime_repo_digest" ]]; then
    if [[ -n "$runtime_id" ]]; then r_id_json="\"$(json_escape "$runtime_id")\""; else r_id_json=null; fi
    if [[ -n "$runtime_state" ]]; then r_state_json="\"$(json_escape "$runtime_state")\""; else r_state_json=null; fi
    if [[ -n "$runtime_image" ]]; then r_image_json="\"$(json_escape "$runtime_image")\""; else r_image_json=null; fi
    if [[ -n "$runtime_image_id" ]]; then r_image_id_json="\"$(json_escape "$runtime_image_id")\""; else r_image_id_json=null; fi
    if [[ -n "$runtime_repo_digest" ]]; then r_repo_digest_json="\"$(json_escape "$runtime_repo_digest")\""; else r_repo_digest_json=null; fi
    runtime_json="{\"id\":$r_id_json,\"state\":$r_state_json,\"image\":$r_image_json,\"image_id\":$r_image_id_json,\"repo_digest\":$r_repo_digest_json}"
else
    runtime_json="null"
fi

printf '{"schema":"wechat-hub.canary.sample/v1","timestamp":"%s","run":{"id":%s,"profile":%s},"container":{"name":"%s","id":"%s","state":"%s","init_pid":%s,"started_at":%s,"host_config_pids_limit":%s,"docker_oom_killed":%s,"image":%s,"image_id":%s,"repo_digest":%s},"runtime":%s,"cgroup":{"version":"v2","path":"%s","dir":"%s"},"collection":{"mode":"%s","log_source":"%s","proc_root":"%s","cgroup_root":"%s"},"pids":{"current":%s,"max":%s,"events_max_hit":%s},"memory":{"current_bytes":%s,"max_bytes":%s,"events_oom":%s,"events_oom_kill":%s},"tasks":{"grand_total":{"processes":%s,"threads":%s},"zombie_count":%s,"proc_race_count":%s,"proc_read_error_count":%s,"components":{"wechat":{"processes":%s,"threads":%s},"wechatappex":{"processes":%s,"threads":%s},"wxplayer":{"processes":%s,"threads":%s},"wxocr":{"processes":%s,"threads":%s},"crashpad":{"processes":%s,"threads":%s},"agent-server":{"processes":%s,"threads":%s},"other":{"processes":%s,"threads":%s}}},"watchdog":{"unresponsive_kill":%s,"killed_wechat":%s,"process_disappeared":%s,"spawned_wechat":%s,"pthread_create_eagain":%s,"thread_constructor_failed":%s},"auth":{"status_url":%s,"reported_auth_status":%s,"current_ui_observation":"unknown","current_ui_fresh":false}}\n' \
    "$(json_escape "$timestamp")" "$run_id_json" "$profile_json" \
    "$(json_escape "$container_name")" "$(json_escape "$container_id")" "$(json_escape "$container_state")" \
    "$init_pid_json" "$started_at_json" "$host_pids_limit_json" "$docker_oom_killed" "$container_image_json" "$container_image_id_json" "$container_repo_digest_json" \
    "$runtime_json" \
    "$(json_escape "$cgroup_path")" "$(json_escape "$cgroup_dir")" \
    "$(json_escape "$collection_mode")" "$(json_escape "$log_source")" \
    "$(json_escape "$proc_root")" "$(json_escape "$cgroup_root")" \
    "$pids_current" "$pids_max_json" "$pids_events_max" \
    "$memory_current" "$memory_max_json" "$memory_oom" "$memory_oom_kill" \
    "$process_count" "$thread_count" "$zombie_count" "$proc_race_count" "$proc_read_error_count" \
    "$wechat_procs" "$wechat_threads" \
    "$wechatappex_procs" "$wechatappex_threads" \
    "$wxplayer_procs" "$wxplayer_threads" \
    "$wxocr_procs" "$wxocr_threads" \
    "$crashpad_procs" "$crashpad_threads" \
    "$agent_server_procs" "$agent_server_threads" \
    "$other_procs" "$other_threads" \
    "$watchdog_unresponsive" "$watchdog_killed" "$watchdog_disappeared" "$watchdog_spawned" \
    "$watchdog_eagain" "$watchdog_ctor" \
    "$status_url_json" "$auth_obj_json"