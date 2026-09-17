#!/bin/bash
exec > /root/rc14fv-qual.log 2>&1
B=http://127.0.0.1:18082
FROM=274814
curl -s -m 30 "$B/v1/events/poll?after=$FROM&limit=200" > /tmp/rc14fv-window.json

echo "=== 1. window event histogram ==="
jq -c "[.events[]|.event_type]|group_by(.)|map({(.[0]):length})|add" /tmp/rc14fv-window.json

echo "=== 2. message.updated by projected type ==="
jq -c "[.events[]|select(.event_type==\"message.updated\")|.payload.message.type]|group_by(.)|map({(.[0]):length})|add" /tmp/rc14fv-window.json

echo "=== 3. distinct message ids in message.updated ==="
jq "[.events[]|select(.event_type==\"message.updated\")|.payload.message.message_id]|unique|length" /tmp/rc14fv-window.json

echo "=== 4. CLASSIFICATION: source_type_label=link_or_file -> app_type vs projected type ==="
jq -c "[.events[]|select(.event_type|startswith(\"message.\"))|.payload.message|select(.vendor_specific.source_type_label==\"link_or_file\")|{a:(.attributes.app_type//\"none\"),t:.type}]|group_by([.a,.t])|map({(.[0].a+\" -> \"+.[0].t):length})|add" /tmp/rc14fv-window.json

echo "=== 5. genuine files (app_type 6) ==="
jq -c "[.events[]|select(.event_type|startswith(\"message.\"))|.payload.message|select(.attributes.app_type==\"6\")|{mid:.message_id,type:.type,media_id:.media_id,role:.media_role,status:.media_status,filename:.filename,mime:.mime_type}]|unique_by(.mid)" /tmp/rc14fv-window.json

echo "=== 6. voice messages ==="
jq -c "[.events[]|select(.event_type|startswith(\"message.\"))|.payload.message|select(.type==\"voice\")|{mid:.message_id,media_id:.media_id,role:.media_role,status:.media_status,filename:.filename,mime:.mime_type}]|unique_by(.mid)" /tmp/rc14fv-window.json

echo "=== 7. media.ready events ==="
jq -c "[.events[]|select(.event_type==\"media.ready\")|{mid:.payload.media.media_id,role:.payload.media.role,status:.payload.media.status,filename:.payload.media.filename,mime:.payload.media.mime_type}]" /tmp/rc14fv-window.json

echo "=== 8. 274307 current projection ==="
jq -c "[.events[]|select(.payload.message.message_id==\"8745c1a931013b8941a0736d6fb890f1a4129129bd03b2b4842d09f7d5995d79\")|{event:.event_type,type:.payload.message.type,media_id:.payload.message.media_id,app_type:(.payload.message.attributes.app_type//\"none\"),stl:.payload.message.vendor_specific.source_type_label}]" /tmp/rc14fv-window.json

echo "=== 9. F3 contract presence in message payloads ==="
jq -c "[.events[]|select(.event_type|startswith(\"message.\"))|.payload.message|select(.media_id!=\"\" and .media_id!=null)|{has_role:(.media_role!=null),has_status:(.media_status!=null)}]|group_by(.)|map({(.[0]|tostring):length})|add" /tmp/rc14fv-window.json

echo "=== 10. media endpoint for genuine file + voice ==="
for MID in $(jq -r "[.events[]|select(.event_type|startswith(\"message.\"))|.payload.message|select((.attributes.app_type==\"6\") or (.type==\"voice\"))|select(.media_id!=\"\" and .media_id!=null)|.media_id]|unique[]" /tmp/rc14fv-window.json); do
  echo "--- media_id=$MID ---"
  curl -s -m 20 -D /tmp/rc14fv-h.txt -o /tmp/rc14fv-b.bin "$B/v1/media/$MID?account_id=f-live-a"
  grep -iE "^(HTTP/|content-type:|content-length:|content-disposition:|x-media-)" /tmp/rc14fv-h.txt | tr -d "\r"
  echo "bytes_returned=$(wc -c < /tmp/rc14fv-b.bin)"
  echo "sha256=$(sha256sum /tmp/rc14fv-b.bin | cut -c1-16)"
done
