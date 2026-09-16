#!/bin/bash
# RC.14 EFB exact-digest shutdown requalification - v2 harness (post-preflight).
# Supersedes arm_a.sh / baseline.sh for the gate run. The sealed v1 harnesses
# remain byte-identical on disk so their pinned SHA256 stays verifiable.
#
# Arms:
#   a  = gate-carrying, frozen in-image probe, 10 runs
#   bs = BASELINE_SLEEP (frozen sealed baseline), sleep 600 as PID 1, 10 runs
#   bc = BASELINE_CLEAN (erratum addition), python idle that exits 0 on SIGTERM, 10 runs
#
# Records per run: sigterm/sigkill/die/stop/destroy event offsets, FinishedAt
# offset, docker wait completion, CLI return, exit code, evidence checks.
set -u
IMAGE="ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241"
PROBE=/opt/efb-linux-wechat-slave/scripts/qualification/image_shutdown_probe.py
IDLE='import signal,sys,time; signal.signal(signal.SIGTERM, lambda *a: sys.exit(0)); time.sleep(600)'
N_A=${N_A:-10}
N_BS=${N_BS:-10}
N_BC=${N_BC:-10}
BASE=/root/rc14-requal
OUT=$BASE/requal_v2.json
mkdir -p "$BASE/tmp" "$BASE/evidence"

write_profile() {
  mkdir -p "$1/profile/blueset.wechat.linux"
  cat > "$1/profile/blueset.wechat.linux/config.yaml" <<'YAML'
core:
  base_url: http://127.0.0.1:1
  timeout: 2
  poll_timeout: 0
  verify_tls: false
consumer_id: rc14-functional-image-gate
account_ids: []
poll_interval: 0.05
event_limit: 10
startup_healthcheck: false
bootstrap_mode: at_head
shutdown_master_budget_sec: 1.0
shutdown_slave_drain_budget_sec: 0.75
shutdown_hard_exit: true
shutdown_install_deferred: false
YAML
}

FAILMSG=""
fail() { echo "REQUAL_V2_FAIL: $1"; printf '{"gate":"FAIL","error":"%s"}\n' "$1" > "$OUT"; exit 1; }
sp() { jq -r --arg k "$1" '[.[] | .[$k] | select(. != null)] | sort as $s | ($s|length) as $n | if $n == 0 then "na|na|na" else "\($s[0])|\(if ($n % 2) == 1 then $s[($n-1)/2] else (($s[$n/2 - 1] + $s[$n/2]) / 2) end)|\($s[-1])" end'; }

ROWS=""
run_arm() {
  MODE=$1; CNT=$2
  for i in $(seq 1 "$CNT"); do
    D=$(mktemp -d "$BASE/tmp/${MODE}${i}-XXXXXX") || fail "mktemp"
    case "$MODE" in
      a)
        write_profile "$D"
        N="rc14-requal-a${i}-$(date +%s%N | md5sum | cut -c1-8)"
        docker run -d --name "$N" --label rc14.requal.arm=a --network none \
          --volume "$D:/qualification" --entrypoint python "$IMAGE" "$PROBE" \
          --profile /qualification/profile/blueset.wechat.linux/config.yaml \
          --data-dir /qualification/data \
          --shutdown-evidence /qualification/shutdown-evidence.json \
          --core-evidence /qualification/core-evidence.json \
          --ready /qualification/ready.json >/dev/null || fail "a run $i docker run"
        ok=0
        for _n in $(seq 1 150); do
          [ -f "$D/ready.json" ] && { ok=1; break; }
          s=$(docker inspect -f '{{.State.Status}}' "$N" 2>/dev/null || echo missing)
          [ "$s" = running ] || { docker logs "$N" 2>&1 | tail -20; docker rm -f "$N" >/dev/null 2>&1; fail "a run $i exited before ready"; }
          sleep 0.1
        done
        [ "$ok" = 1 ] || { docker rm -f "$N" >/dev/null 2>&1; fail "a run $i ready timeout"; }
        ;;
      bs)
        N="rc14-requal-bs${i}-$(date +%s%N | md5sum | cut -c1-8)"
        docker run -d --name "$N" --label rc14.requal.arm=bs --network none \
          --entrypoint sleep "$IMAGE" 600 >/dev/null || fail "bs run $i docker run"
        ;;
      bc)
        N="rc14-requal-bc${i}-$(date +%s%N | md5sum | cut -c1-8)"
        docker run -d --name "$N" --label rc14.requal.arm=bc --network none \
          --entrypoint python "$IMAGE" -c "$IDLE" >/dev/null || fail "bc run $i docker run"
        ;;
    esac
    sleep 0.5
    docker events --filter container="$N" --format '{{json .}}' > "$D/events.jsonl" 2>&1 &
    EP=$!
    sleep 0.4
    docker wait "$N" > "$D/wait.rc" 2>&1 &
    WP=$!
    T0N=$(date +%s%N); T0M=$(cut -d' ' -f1 /proc/uptime)
    docker stop -t 2 "$N" >/dev/null 2>&1; SRC=$?
    T1N=$(date +%s%N); T1M=$(cut -d' ' -f1 /proc/uptime)
    for _n in $(seq 1 120); do kill -0 "$WP" 2>/dev/null || break; sleep 0.05; done
    T2N=$(date +%s%N)

    INS=$(docker inspect "$N")
    EC=$(echo "$INS" | jq -r '.[0].State.ExitCode')
    OOM=$(echo "$INS" | jq -r '.[0].State.OOMKilled')
    RUN=$(echo "$INS" | jq -r '.[0].State.Running')
    PIDV=$(echo "$INS" | jq -r '.[0].State.Pid')
    FINRAW=$(echo "$INS" | jq -r '.[0].State.FinishedAt')
    WRC=$(tr -d '\r\n' < "$D/wait.rc" 2>/dev/null)
    [ "$MODE" = a ] && { cp "$D/shutdown-evidence.json" "$BASE/evidence/a-run${i}-shutdown.json" 2>/dev/null; cp "$D/core-evidence.json" "$BASE/evidence/a-run${i}-core.json" 2>/dev/null; }
    docker rm -f "$N" >/dev/null 2>&1
    sleep 0.4
    kill "$EP" 2>/dev/null; wait "$EP" 2>/dev/null

    grep -E '^\{' "$D/events.jsonl" > "$D/ev.jq" 2>/dev/null || true
    off() { jq -r --arg a "$1" --arg s "$2" '[.[] | select(.Action == $a) | select(($s == "") or ((.Actor.Attributes?.signal? // "") == $s)) | .timeNano] | first // empty' "$D/ev.jq" 2>/dev/null; }
    T15=$(off kill 15); T9=$(off kill 9); TDIE=$(off die ""); TSTP=$(off stop ""); TDES=$(off destroy "")
    FINN=$(date -d "$FINRAW" +%s%N 2>/dev/null || echo "")
    ns() { [ -n "$1" ] || { echo null; return; }; awk -v a="$1" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}'; }
    S15=$(ns "$T15"); S9=$(ns "$T9"); SDIE=$(ns "$TDIE"); SSTP=$(ns "$TSTP"); SDES=$(ns "$TDES"); SFIN=$(ns "$FINN")
    CLI=$(awk -v a="$T1N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
    CLIM=$(awk -v a="$T1M" -v b="$T0M" 'BEGIN{printf "%.6f", a-b}')
    WRT=$(awk -v a="$T2N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')

    PROC=null; CKP="na"; LED="na"; DSUP="na"; CURA="na"; CORE="na"; REP="na"
    CHK=""
    if [ "$MODE" = a ]; then
      SE=$D/shutdown-evidence.json; CE=$D/core-evidence.json
      [ -f "$SE" ] || fail "a run $i missing shutdown evidence"
      [ -f "$CE" ] || fail "a run $i missing core evidence"
      PROC=$(jq -r '.elapsed_sec' "$SE")
      jq -e '.exit_code == 0' "$SE" >/dev/null || CHK="$CHK ev_exit_code"
      jq -e '.delivery_suppressed == true' "$SE" >/dev/null || CHK="$CHK delivery_suppressed"
      jq -e '.repeated == false' "$SE" >/dev/null || CHK="$CHK repeated"
      jq -e '(.slave_drain | length) > 0 and ([.slave_drain[].ok] | all)' "$SE" >/dev/null || CHK="$CHK drain_ok"
      jq -e '([.slave_drain[].detail.checkpoint_flushed] | all)' "$SE" >/dev/null || CHK="$CHK checkpoint_flushed"
      jq -e '([.slave_drain[].detail.ledger_wal_checkpointed] | all)' "$SE" >/dev/null || CHK="$CHK ledger_wal_checkpointed"
      jq -e '([.slave_drain[].detail.checkpoint_cursor] | all(. == 272548))' "$SE" >/dev/null || CHK="$CHK checkpoint_cursor"
      jq -e '[.checkpoint_requests[].processed_through_cursor] | index(272548) != null' "$CE" >/dev/null || CHK="$CHK core_checkpoint_272548"
      CKP=$(jq -r '([.slave_drain[].detail.checkpoint_flushed] | all) | tostring' "$SE")
      LED=$(jq -r '([.slave_drain[].detail.ledger_wal_checkpointed] | all) | tostring' "$SE")
      DSUP=$(jq -r '.delivery_suppressed | tostring' "$SE")
      CURA=$(jq -r '[.slave_drain[].detail.checkpoint_cursor] | unique | join(",")' "$SE")
      CORE=$(jq -r '[.checkpoint_requests[].processed_through_cursor] | join(",")' "$CE")
      REP=$(jq -r '.repeated | tostring' "$SE")
    fi
    [ "$EC" = 0 ] || CHK="$CHK exit_code"
    [ "$RUN" = false ] || CHK="$CHK still_running"
    [ "$PIDV" = 0 ] || CHK="$CHK pid_nonzero"
    [ "$OOM" = false ] || CHK="$CHK oom_killed"
    [ "$SRC" = 0 ] || CHK="$CHK stop_rc"
    [ -n "$S9" ] && [ "$S9" != null ] && CHK="$CHK sigkill_signal9"
    [ "$EC" != 137 ] || CHK="$CHK exit_137"

    R=$(jq -n --argjson run "$i" --arg mode "$MODE" --argjson proc "$PROC" --argjson s15 "$S15" \
      --argjson s9 "$S9" --argjson sdie "$SDIE" --argjson sstp "$SSTP" --argjson sdes "$SDES" \
      --argjson sfin "$SFIN" --argjson cli "$CLI" --argjson clim "$CLIM" --argjson wrt "$WRT" \
      --argjson ec "$EC" --argjson src "$SRC" --arg wrc "$WRC" --argjson oom "$OOM" \
      --argjson run2 "$RUN" --argjson pid "$PIDV" --arg ckp "$CKP" --arg led "$LED" --arg dsup "$DSUP" \
      --arg cura "$CURA" --arg core "$CORE" --arg rep "$REP" --arg chk "$CHK" \
      '{arm:$mode, run:$run, process_shutdown_sec:$proc, sigterm_event_sec:$s15, sigkill_event_sec:$s9,
        die_event_sec:$sdie, stop_event_sec:$sstp, destroy_event_sec:$sdes, finished_at_sec:$sfin,
        cli_return_sec:$cli, cli_return_monotonic_sec:$clim, waiter_return_sec:$wrt,
        exit_code:$ec, oom_killed:$oom, running:$run2, pid:$pid, stop_rc:$src, wait_rc:$wrc,
        checkpoint_flush:$ckp, ledger_flush:$led, delivery_suppressed:$dsup,
        checkpoint_cursor:$cura, core_cursor:$core, repeated:$rep, checks_failed:$chk}')
    ROWS="$ROWS$R,"
    echo "$MODE run $i proc=$PROC sigterm=$S15 sigkill=$S9 die=$SDIE fin=$SFIN cli=$CLI exit=$EC stoprc=$SRC chk=[$CHK]"
    rm -rf "$D"
  done
}

run_arm a "$N_A"
run_arm bs "$N_BS"
run_arm bc "$N_BC"

for L in a bs bc; do
  O=$(docker ps -aq --filter "label=rc14.requal.arm=$L" | wc -l | tr -d ' ')
  [ "$O" = 0 ] || fail "orphan containers for arm $L: $O"
done
DCOUNT=$(docker ps -aq --filter status=dead | wc -l | tr -d ' ')
[ "$DCOUNT" = 0 ] || fail "dead containers present: $DCOUNT"

J="[${ROWS%,}]"
jq -n --arg img "$IMAGE" --argjson runs "$J" '{image:$img, run_count:($runs|length), runs:$runs}' > "$OUT"
echo "REQUAL_V2_DONE"
for L in a bs bc; do
  A=$(jq --arg m "$L" '[.[] | select(.arm == $m)]' <<<"$J")
  echo "### ARM=$L n=$(jq 'length' <<<"$A")"
  for K in process_shutdown_sec sigterm_event_sec sigkill_event_sec die_event_sec finished_at_sec cli_return_sec waiter_return_sec; do
    V=$(sp "$K" <<<"$A")
    echo "$K MIN|P50|MAX=$(echo "$V" | tr '|' ' ')"
  done
  echo "exit_codes=$(jq -r '[.[].exit_code]|join(\",\")' <<<"$A")"
  echo "stop_rc=$(jq -r '[.[].stop_rc]|join(\",\")' <<<"$A")"
  echo "wait_rc=$(jq -r '[.[].wait_rc]|join(\",\")' <<<"$A")"
  echo "sigkill_signal9_count=$(jq -r '[.[].sigkill_event_sec|select(.!=null)]|length' <<<"$A")"
  echo "sigterm_signal15_count=$(jq -r '[.[].sigterm_event_sec|select(.!=null)]|length' <<<"$A")"
  echo "checks_failed=$(jq -r '[.[].checks_failed|select(.!=\"\")]|length' <<<"$A")"
  echo "die_event_runs=$(jq -r '[.[].die_event_sec|select(.!=null)]|join(\",\")' <<<"$A")"
  echo "finished_at_runs=$(jq -r '[.[].finished_at_sec|select(.!=null)]|join(\",\")' <<<"$A")"
  echo "cli_return_runs=$(jq -r '[.[].cli_return_sec|select(.!=null)]|join(\",\")' <<<"$A")"
  echo "process_runs=$(jq -r '[.[].process_shutdown_sec|select(.!=null)]|join(\",\")' <<<"$A")"
done
