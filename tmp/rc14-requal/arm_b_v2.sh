#!/bin/bash
# RC.14 EFB shutdown requalification - ARM B v2 (supplementary instrument arm).
# Post-preflight supersede of arm_b.sh. Image bytes unmodified; uses the
# host-side mark fixture whose SHA256 is pinned in the taskbook (unchanged).
set -u
IMAGE="ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241"
RUNS=${RUNS:-3}
BASE=/root/rc14-requal
OUT=$BASE/armB_v2.json
FIX=$BASE/marks/marks_fixture.py
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
startup_healthcheck: true
bootstrap_mode: at_head
shutdown_master_budget_sec: 1.0
shutdown_slave_drain_budget_sec: 0.75
shutdown_hard_exit: true
shutdown_install_deferred: false
YAML
}

fail() { echo "ARM_B_V2_FAIL: $1"; printf '{"gate":"FAIL","arm":"B","error":"%s"}\n' "$1" > "$OUT"; exit 1; }

ROWS=""
for i in $(seq 1 "$RUNS"); do
  D=$(mktemp -d "$BASE/tmp/b${i}-XXXXXX") || fail mktemp
  write_profile "$D"
  mkdir -p "$D/marks"
  cp "$FIX" "$D/marks/marks_fixture.py" || fail "fixture copy"
  N="rc14-requal-b${i}-$(date +%s%N | md5sum | cut -c1-8)"
  docker run -d --name "$N" --label rc14.requal.arm=b --network none \
    --volume "$D:/qualification" --entrypoint python "$IMAGE" \
    /qualification/marks/marks_fixture.py --marks /qualification/marks.json \
    --profile /qualification/profile/blueset.wechat.linux/config.yaml \
    --data-dir /qualification/data \
    --shutdown-evidence /qualification/shutdown-evidence.json \
    --core-evidence /qualification/core-evidence.json \
    --ready /qualification/ready.json >/dev/null || fail "docker run run $i"
  ok=0
  for _n in $(seq 1 150); do
    [ -f "$D/ready.json" ] && { ok=1; break; }
    s=$(docker inspect -f '{{.State.Status}}' "$N" 2>/dev/null || echo missing)
    [ "$s" = running ] || { docker logs "$N" 2>&1 | tail -30; docker rm -f "$N" >/dev/null 2>&1; fail "exited before ready run $i"; }
    sleep 0.1
  done
  [ "$ok" = 1 ] || { docker rm -f "$N" >/dev/null 2>&1; fail "ready timeout run $i"; }
  sleep 0.5
  docker events --filter container="$N" --format '{{json .}}' > "$D/events.jsonl" 2>&1 &
  EP=$!
  sleep 0.4
  docker wait "$N" > "$D/wait.rc" 2>&1 &
  WP=$!
  T0N=$(date +%s%N)
  docker stop -t 2 "$N" >/dev/null 2>&1; SRC=$?
  T1N=$(date +%s%N)
  for _n in $(seq 1 120); do kill -0 "$WP" 2>/dev/null || break; sleep 0.05; done
  T2N=$(date +%s%N)

  INS=$(docker inspect "$N")
  EC=$(echo "$INS" | jq -r '.[0].State.ExitCode')
  OOM=$(echo "$INS" | jq -r '.[0].State.OOMKilled')
  RUN=$(echo "$INS" | jq -r '.[0].State.Running')
  PIDV=$(echo "$INS" | jq -r '.[0].State.Pid')
  FINRAW=$(echo "$INS" | jq -r '.[0].State.FinishedAt')
  WRC=$(tr -d '\r\n' < "$D/wait.rc" 2>/dev/null)
  SE=$D/shutdown-evidence.json; CE=$D/core-evidence.json; MK=$D/marks.json
  [ -f "$SE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no shutdown evidence run $i"; }
  [ -f "$CE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no core evidence run $i"; }
  [ -f "$MK" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no marks file run $i"; }
  cp "$SE" "$BASE/evidence/b-run${i}-shutdown.json"; cp "$CE" "$BASE/evidence/b-run${i}-core.json"; cp "$MK" "$BASE/evidence/b-run${i}-marks.json"
  docker rm -f "$N" >/dev/null 2>&1
  sleep 0.4
  kill "$EP" 2>/dev/null; wait "$EP" 2>/dev/null

  grep -E '^\{' "$D/events.jsonl" > "$D/ev.jq" 2>/dev/null || true
  off() { jq -r --arg a "$1" --arg s "$2" '[.[] | select(.Action == $a) | select(($s == "") or ((.Actor.Attributes?.signal? // "") == $s)) | .timeNano] | first // empty' "$D/ev.jq" 2>/dev/null; }
  T15=$(off kill 15); T9=$(off kill 9); TDIE=$(off die ""); TDES=$(off destroy "")
  FINN=$(date -d "$FINRAW" +%s%N 2>/dev/null || echo "")
  ns() { [ -n "$1" ] || { echo null; return; }; awk -v a="$1" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}'; }
  S15=$(ns "$T15"); S9=$(ns "$T9"); SDIE=$(ns "$TDIE"); SDES=$(ns "$TDES"); SFIN=$(ns "$FINN")
  CLI=$(awk -v a="$T1N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  WRT=$(awk -v a="$T2N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')

  PROC=$(jq -r '.elapsed_sec' "$SE")
  MSIG=$(jq -r '.signal_received_monotonic' "$MK")
  MRT=$(jq -r '.realtime_at_start' "$MK")
  MMA=$(jq -r '.monotonic_at_start' "$MK")
  MSUP=$(jq -r '.delivery_suppressed_monotonic' "$MK")
  MCK=$(jq -r '.checkpoint_flush_completed_monotonic' "$MK")
  MLG=$(jq -r '.ledger_flush_completed_monotonic' "$MK")
  MEX=$(jq -r '.exit_requested_monotonic' "$MK")
  BPROC=$(awk -v a="$MEX" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  SUP=$(awk -v a="$MSUP" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  CKO=$(awk -v a="$MCK" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  LGO=$(awk -v a="$MLG" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  MEXRT=$(awk -v a="$MRT" -v b="$MMA" -v c="$MEX" 'BEGIN{printf "%.0f", (a + (c-b))*1000000000}')
  TAIL=$(awk -v a="$TDIE" -v b="$MEXRT" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  DRIFT=$(awk -v a="$PROC" -v b="$BPROC" 'BEGIN{printf "%.6f", a-b}')

  CHK=""
  [ "$EC" = 0 ] || CHK="$CHK exit_code"
  [ "$RUN" = false ] || CHK="$CHK still_running"
  [ "$PIDV" = 0 ] || CHK="$CHK pid_nonzero"
  [ "$OOM" = false ] || CHK="$CHK oom_killed"
  [ "$SRC" = 0 ] || CHK="$CHK stop_rc"
  [ -n "$S9" ] && [ "$S9" != null ] && CHK="$CHK sigkill_signal9"
  jq -e '.exit_code == 0' "$SE" >/dev/null || CHK="$CHK ev_exit_code"
  jq -e '.delivery_suppressed == true' "$SE" >/dev/null || CHK="$CHK delivery_suppressed"
  jq -e '([.slave_drain[].detail.checkpoint_flushed] | all)' "$SE" >/dev/null || CHK="$CHK checkpoint_flushed"
  jq -e '([.slave_drain[].detail.ledger_wal_checkpointed] | all)' "$SE" >/dev/null || CHK="$CHK ledger_wal_checkpointed"
  jq -e '([.slave_drain[].detail.checkpoint_cursor] | all(. == 272548))' "$SE" >/dev/null || CHK="$CHK checkpoint_cursor"
  jq -e '[.checkpoint_requests[].processed_through_cursor] | index(272548) != null' "$CE" >/dev/null || CHK="$CHK core_checkpoint_272548"

  R=$(jq -n --argjson run "$i" --argjson proc "$PROC" --argjson bproc "$BPROC" --argjson s15 "$S15" \
    --argjson s9 "$S9" --argjson sdie "$SDIE" --argjson sdes "$SDES" --argjson sfin "$SFIN" \
    --argjson cli "$CLI" --argjson wrt "$WRT" --argjson ec "$EC" --argjson src "$SRC" --arg wrc "$WRC" \
    --argjson sup "$SUP" --argjson cko "$CKO" --argjson lgo "$LGO" --argjson tail "$TAIL" --argjson drift "$DRIFT" \
    --arg chk "$CHK" \
    '{arm:"b", run:$run, process_shutdown_sec:$proc, instrumented_process_sec:$bproc,
      sigterm_event_sec:$s15, sigkill_event_sec:$s9, die_event_sec:$sdie, destroy_event_sec:$sdes,
      finished_at_sec:$sfin, cli_return_sec:$cli, waiter_return_sec:$wrt, exit_code:$ec,
      stop_rc:$src, wait_rc:$wrc,
      mark_delivery_suppressed_sec:$sup, mark_checkpoint_flush_completed_sec:$cko,
      mark_ledger_flush_completed_sec:$lgo, post_exit_request_to_die_sec:$tail,
      derived_minus_instrumented_sec:$drift, checks_failed:$chk}')
  ROWS="$ROWS$R,"
  echo "b run $i proc=$PROC inst=$BPROC die=$SDIE fin=$SFIN cli=$CLI sup=$SUP ck=$CKO lg=$LGO tail=$TAIL drift=$DRIFT exit=$EC chk=[$CHK]"
  rm -rf "$D"
done

O=$(docker ps -aq --filter label=rc14.requal.arm=b | wc -l | tr -d ' ')
J="[${ROWS%,}]"
jq -n --arg img "$IMAGE" --argjson runs "$J" '{arm:"B", role:"SUPPLEMENTARY_INSTRUMENT_VALIDATION", carries_gate_verdict:false, image:$img, run_count:($runs|length), runs:$runs}' > "$OUT"
echo "ARM_B_V2_DONE orphans=$O"
jq -r '[.[].process_shutdown_sec]|join(",")' <<<"$J"
jq -r '[.[].instrumented_process_sec]|join(",")' <<<"$J"
jq -r '[.[].derived_minus_instrumented_sec]|join(",")' <<<"$J"
jq -r '[.[].post_exit_request_to_die_sec]|join(",")' <<<"$J"
jq -r '[.[].mark_delivery_suppressed_sec]|join(",")' <<<"$J"
jq -r '[.[].mark_checkpoint_flush_completed_sec]|join(",")' <<<"$J"
jq -r '[.[].mark_ledger_flush_completed_sec]|join(",")' <<<"$J"
jq -r '[.[].finished_at_sec]|join(",")' <<<"$J"
