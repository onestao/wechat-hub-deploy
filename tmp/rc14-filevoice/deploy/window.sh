#!/bin/bash
exec > /root/rc14fv-window.log 2>&1
FROM=274814
C=$FROM
TOTAL=0
for i in $(seq 1 20); do
  R=$(curl -s -m 20 "http://127.0.0.1:18082/v1/events/poll?after=$C&limit=200")
  N=$(printf "%s" "$R" | jq ".events|length")
  if [ "$N" -eq 0 ]; then echo "page=$i after=$C n=0 STOP"; break; fi
  printf "page=%s after=%s n=%s " "$i" "$C" "$N"
  printf "%s" "$R" | jq -c "[.events[]|.event_type]|group_by(.)|map({(.[0]):length})|add"
  L=$(printf "%s" "$R" | jq -r ".events[-1].cursor")
  C=$L
  TOTAL=$((TOTAL+N))
  if [ "$N" -lt 200 ]; then break; fi
done
echo "WINDOW_FROM=$FROM WINDOW_TO=$C TOTAL_EVENTS=$TOTAL"
echo "STREAM_HEAD_NOW=$(curl -s -m 10 "http://127.0.0.1:18082/v1/events/poll?after=0&limit=1" | jq -r ".stream_head_cursor")"
