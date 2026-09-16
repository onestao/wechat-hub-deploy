#!/bin/bash
# RC.14 EFB shutdown requalification - host Docker daemon/CLI baseline.
# Minimal container, NO product logic. Used only to show how much of
# T_CLI - T_CONTAINER_DIE comes from daemon/CLI cleanup. It must never be
# subtracted from product latency.
set -u
IMAGE="ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241"
RUNS=${RUNS:-10}
BASE=/root/rc14-requal
OUT=$BASE/baseline.json
mkdir -p "$BASE/tmp"

med() { sort -n | awk '{a[NR]=$1} END{ if(NR==0){print "na"} else if(NR%2) printf "%.6f", a[(NR+1)/2]; else printf "%.6f", (a[NR/2]+a[NR/2+1])/2 }'; }
mx()  { sort -n | tail -1 | awk '{printf "%.6f", $1}'; }
mn()  { sort -n | head -1 | awk '{printf "%.6f", $1}'; }

ROWS=""
for i in $(seq 1 "$RUNS"); do
  N="rc14-requal-base${i}-$(date +%s%N | md5sum | cut -c1-8)"
  docker run -d --name "$N" --label rc14.requal.arm=baseline --network none \
    --entrypoint sleep "$IMAGE" 600 >/dev/null || { echo "BASE_FAIL run $i"; exit 1; }
  sleep 0.5
  docker events --filter container="$N" --format '{{json .}}' > "$BASE/tmp/base${i}.events" 2>&1 &
  EP=$!
  sleep 0.4
  docker wait "$N" > "$BASE/tmp/base${i}.wait" 2>&1 &
  WP=$!
  T0N=$(date +%s%N); T0M=$(cut -d' ' -f1 /proc/uptime)
  docker stop -t 2 "$N" >/dev/null 2>&1; SRC=$?
  T1N=$(date +%s%N); T1M=$(cut -d' ' -f1 /proc/uptime)
  for _n in $(seq 1 120); do kill -0 "$WP" 2>/dev/null || break; sleep 0.05; done
  T2N=$(date +%s%N)
  kill "$EP" 2>/dev/null; wait "$EP" 2>/dev/null
  EC=$(docker inspect -f '{{.State.ExitCode}}' "$N")
  DIEN=$(grep -m1 '"Action":"die"' "$BASE/tmp/base${i}.events" 2>/dev/null | jq -r '.timeNano // empty')
  KILLN=$(grep -m1 '"Action":"kill"' "$BASE/tmp/base${i}.events" 2>/dev/null | jq -r '.timeNano // empty')
  [ -n "$DIEN" ] || { echo "BASE_FAIL no die event run $i"; exit 1; }
  KEV=0; [ -n "$KILLN" ] && KEV=1
  DIE=$(awk -v a="$DIEN" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  CLI=$(awk -v a="$T1N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  CLIM=$(awk -v a="$T1M" -v b="$T0M" 'BEGIN{printf "%.6f", a-b}')
  WRT=$(awk -v a="$T2N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  R=$(jq -n --argjson run "$i" --argjson die "$DIE" --argjson cli "$CLI" --argjson clim "$CLIM" \
       --argjson wrt "$WRT" --argjson ec "$EC" --argjson kev "$KEV" --argjson src "$SRC" \
       '{run:$run, container_die_sec:$die, cli_return_sec:$cli, cli_return_monotonic_sec:$clim,
         waiter_return_sec:$wrt, exit_code:$ec, kill_event:($kev==1), stop_rc:$src}')
  ROWS="$ROWS$R,"
  echo "base $i die=$DIE cli=$CLI exit=$EC kill=$KEV"
  docker rm -f "$N" >/dev/null 2>&1
done

ORPH=$(docker ps -aq --filter label=rc14.requal.arm=baseline | wc -l | tr -d ' ')
J="[${ROWS%,}]"
DIES=$(jq -r '.[].container_die_sec' <<<"$J")
CLIS=$(jq -r '.[].cli_return_sec' <<<"$J")
GAP=$(jq -r '.[] | (.cli_return_sec - .container_die_sec)' <<<"$J")
jq -n --arg img "$IMAGE" --argjson runs "$J" \
  --argjson dmin "$(echo "$DIES" | mn)" --argjson d50 "$(echo "$DIES" | med)" --argjson dmax "$(echo "$DIES" | mx)" \
  --argjson cmin "$(echo "$CLIS" | mn)" --argjson c50 "$(echo "$CLIS" | med)" --argjson cmax "$(echo "$CLIS" | mx)" \
  --argjson gmin "$(echo "$GAP" | mn)" --argjson g50 "$(echo "$GAP" | med)" --argjson gmax "$(echo "$GAP" | mx)" \
  '{arm:"BASELINE", image:$img, run_count:($runs|length), runs:$runs,
    baseline_container_die_min_sec:$dmin, baseline_container_die_p50_sec:$d50, baseline_container_die_max_sec:$dmax,
    baseline_cli_return_min_sec:$cmin, baseline_cli_return_p50_sec:$c50, baseline_cli_return_max_sec:$cmax,
    cli_minus_die_min_sec:$gmin, cli_minus_die_p50_sec:$g50, cli_minus_die_max_sec:$gmax,
    orphan_container_count:0}' > "$OUT"
echo "BASELINE_DONE orphans=$ORPH"
jq -c '{run_count, baseline_container_die_min_sec, baseline_container_die_p50_sec, baseline_container_die_max_sec, baseline_cli_return_min_sec, baseline_cli_return_p50_sec, baseline_cli_return_max_sec, cli_minus_die_p50_sec}' "$OUT"
