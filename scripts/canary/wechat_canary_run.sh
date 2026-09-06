#!/usr/bin/env bash
# Runner for the host-side read-only WeChat Hub canary sampler.
# Appends one JSONL sample per interval to --output and flushes safely on
# INT/TERM (each sample line is appended atomically once fully built).
#
# Typical canary:  --duration 1800 --interval 30
# RC.5 pre-gate:   --duration 600  --interval 30
# H2 profiling:    --duration 21600 --interval 60
set -euo pipefail

usage() {
    printf '%s\n' "Usage: $0 --output FILE --container NAME_OR_ID [--duration SECONDS] [--interval SECONDS] \\
       [--run-id ID] [--profile canary|h2|custom] [sampler options: --status-url --proc-root --cgroup-root \\
       --docker-bin --watchdog-log-file --pattern-* --container-* ...]"
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

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
sampler="$script_dir/wechat_cgroup_sample.sh"
output=""
duration=1800
interval=30
run_id=""
profile="canary"
forward=()

while (($#)); do
    case "$1" in
        --output) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; output=$2; shift 2 ;;
        --duration) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; duration=$2; shift 2 ;;
        --interval) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; interval=$2; shift 2 ;;
        --run-id) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; run_id=$2; shift 2 ;;
        --profile) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; profile=$2; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) forward+=("$1"); shift ;;
    esac
done

[[ -n "$output" ]] || { printf '%s\n' 'error: --output is required' >&2; exit 2; }
[[ "$duration" =~ ^[0-9]+$ ]] && ((duration > 0)) || { printf '%s\n' 'error: --duration must be a positive integer' >&2; exit 2; }
[[ "$interval" =~ ^[0-9]+$ ]] && ((interval > 0)) || { printf '%s\n' 'error: --interval must be a positive integer' >&2; exit 2; }
[[ -r "$sampler" ]] || { printf 'error: sampler not found: %s\n' "$sampler" >&2; exit 2; }
if ((interval < 15)); then
    printf 'warning: interval %ss is below the 30-60s cadence recommended by docs/P0_RC4_FULL_CHAT_PIDS_CANARY_GATE.md\n' "$interval" >&2
fi

bash -n "$sampler" || { printf 'error: sampler failed bash -n syntax check\n' >&2; exit 2; }
if [[ -n "$run_id" ]]; then
    run_id_args=(--run-id "$run_id")
else
    run_id_args=()
fi

stop_requested=0
sleep_pid=""
handle_signal() {
    stop_requested=1
    if [[ -n "$sleep_pid" ]]; then
        kill "$sleep_pid" 2>/dev/null || true
    fi
}
trap handle_signal INT TERM HUP

# The output file is appended to, never truncated here, so an interrupted run
# always leaves previously flushed samples intact.
touch "$output"

start_seconds=$SECONDS
deadline=$((start_seconds + duration))
completed=0
failed=0

while ((SECONDS <= deadline)); do
    ((stop_requested)) && break

    if bash "$sampler" --profile "$profile" "${run_id_args[@]}" "${forward[@]}" >> "$output"; then
        completed=$((completed + 1))
        printf 'sample %d flushed to %s\n' "$completed" "$output" >&2
    else
        failed=$((failed + 1))
        printf 'warning: sampler round %d failed; no line written for this round\n' "$((failed + completed))" >&2
        if ((completed == 0)); then
            printf 'error: first sampler invocation failed; aborting before any evidence was written\n' >&2
            exit 1
        fi
        ((failed >= 3)) && { printf 'error: aborting after %d failed sampler rounds\n' "$failed" >&2; exit 1; }
    fi

    ((SECONDS >= deadline || stop_requested)) && break
    remaining=$((deadline - SECONDS))
    sleep_for=$interval
    ((sleep_for > remaining)) && sleep_for=$remaining
    ((sleep_for > 0)) || break

    sleep "$sleep_for" &
    sleep_pid=$!
    wait "$sleep_pid" || true
    sleep_pid=""
done

elapsed=$((SECONDS - start_seconds))
if ((stop_requested)); then
    printf 'sampling stopped safely after %d second(s); %d sample(s) flushed and preserved at %s\n' "$elapsed" "$completed" "$output" >&2
    exit 130
fi

printf 'sampling completed after %d second(s): %d sample(s) written to %s (%d failed rounds)\n' "$elapsed" "$completed" "$output" "$failed" >&2
((completed > 0)) || exit 1
