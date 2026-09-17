#!/usr/bin/env python3
"""RC.14 offline EFB compatibility simulation for the Core file/voice media contract.

Runs the *frozen* EFB candidate (`69a1f58e`) against the Core contract produced by
the RC.14 Core file/voice media-reference candidate, entirely offline.  No Core,
no Telegram, no production host, no EFB source modification.

Three things are proved:

1. `EFB_FILE_MEDIA_CONTRACT_COMPATIBLE`  -- a `file` message carrying the new
   contract (`media_id` populated, `role=original`, `status=ready`, bytes served
   with `X-Media-Role`/`X-Media-Status`) reaches DELIVERED instead of parking in
   PENDING_MEDIA and settling as MEDIA_FAILED.
2. `EFB_VOICE_MEDIA_CONTRACT_COMPATIBLE` -- the same for `voice`.
3. The simulation is discriminating: the *pre-fix* Core projection (no media
   reference) still fails closed, so the PASS above is not vacuous.

It also classifies the sealed 274307 event through the frozen candidate's
durable-provenance classifier.

Usage:  python efb_media_contract_simulation.py <efb_candidate_worktree>
"""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path


def _bootstrap(efb_root: Path) -> None:
    tests = efb_root / "tests"
    for entry in (str(efb_root), str(tests)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from stub_ehforwarderbot import install_stubs  # type: ignore

    install_stubs()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: efb_media_contract_simulation.py <efb_candidate_worktree>")
        return 2
    efb_root = Path(argv[1]).resolve()
    _bootstrap(efb_root)

    from efb_wechat_comwechat_slave.ComWechat import LinuxWeChatChannel
    from efb_wechat_comwechat_slave.Core import CoreAPIError, CoreMedia
    from efb_wechat_comwechat_slave.EffectLedger import (
        STATE_DELIVERED,
        STATE_MEDIA_FAILED,
        STATE_PENDING_MEDIA,
    )
    from efb_wechat_comwechat_slave.Provenance import (
        CLASSIFICATION_FIRST_BUSINESS_EFFECT,
        CLASSIFICATION_KNOWN_EFFECT,
        CLASSIFICATION_REPROJECTION_OF_PREEXISTING_OBJECT,
        SubscriptionFloorRecord,
        extract_business_origin,
    )

    report: dict = {
        # The frozen EFB candidate this simulation exercises.  Recorded explicitly so
        # the artifact is self-describing; the worktree must be checked out at it.
        "efb_source": "69a1f58e29177634b6790ed3b5ec688871ba590c",
        "cases": {},
    }

    # ---------------------------------------------------------------- doubles
    class ContractCore:
        """Core that honours the RC.14 file/voice media contract."""

        def __init__(self, *, served: bool) -> None:
            self.served = served
            self.media_calls = 0

        def health(self):
            return {"contract_version": 1}

        def get_media(self, account_id: str, media_id: str) -> CoreMedia:
            self.media_calls += 1
            if not self.served:
                raise CoreAPIError(404, "media_not_found", f"{media_id} is not ready")
            # Mirrors GET /v1/media/{id}: X-Media-Role / X-Media-Status headers.
            return CoreMedia(
                b"ORIGINAL-BYTES",
                self.mime,
                self.filename,
                media_id,
                "original",
                "ready",
            )

        def get_bootstrap_provenance(self, consumer_id: str):
            return {
                "consumer_id": consumer_id,
                "initial_cursor": 0,
                "bootstrap_mode": "at_head",
                "bootstrap_at": "2026-01-01T00:00:00Z",
            }

        def get_message_projection(self, account_id, chat_id, message_id, **_kwargs):
            return {
                "account_id": account_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "created_at": "2026-09-17T08:41:14Z",
            }

    def make_channel(core, data_path: Path) -> LinuxWeChatChannel:
        channel = LinuxWeChatChannel(
            core_client=core,
            config={
                "startup_healthcheck": False,
                "shutdown_install_deferred": False,
                "consumer_id": "rc14-filevoice-sim",
                "account_ids": ["account-1"],
                "media_retry_max_attempts": 2,
                "media_retry_deadline_sec": 60,
                "media_retry_base_sec": 0,
                "media_retry_max_sec": 0,
                "core": {"poll_timeout": 0},
            },
            data_path=data_path,
        )
        channel.chat_mgr.build_core_chat(
            {"account_id": "account-1", "chat_id": "chat-1", "type": "private", "display_name": "Peer"},
            "Self",
        )
        return channel

    def message(msg_type: str, *, contract: bool) -> dict:
        body = {
            "account_id": "account-1",
            "chat_id": "chat-1",
            "message_id": f"{msg_type}-1",
            "type": msg_type,
            "direction": "incoming",
            "created_at": "2026-09-17T08:41:14Z",
            "author": {"member_id": "peer-1", "display_name": "Peer", "is_self": False},
        }
        if contract:
            body.update(
                {
                    "media_id": f"{msg_type}-1",
                    "media_role": "original",
                    "media_status": "ready",
                    "filename": "report.txt" if msg_type == "file" else "voice-1.silk",
                    "mime_type": "text/plain" if msg_type == "file" else "audio/silk",
                }
            )
        return body

    def created_event(msg_type: str, *, contract: bool) -> dict:
        return {
            "event_type": "message.created",
            "account_id": "account-1",
            "payload": {"message": message(msg_type, contract=contract)},
        }

    # ------------------------------------------------------- 1/2. post-fix run
    root = Path.cwd() / ".tmp" / f"efb-sim-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        for msg_type, key, expect_mime in (
            ("file", "EFB_FILE_MEDIA_CONTRACT_COMPATIBLE", "text/plain"),
            ("voice", "EFB_VOICE_MEDIA_CONTRACT_COMPATIBLE", "audio/silk"),
        ):
            data_path = root / msg_type
            data_path.mkdir(parents=True, exist_ok=True)
            core = ContractCore(served=True)
            core.mime = expect_mime
            core.filename = "report.txt" if msg_type == "file" else "voice-1.silk"
            channel = make_channel(core, data_path)
            deliveries: list = []
            channel._deliver_message = lambda m, _d=deliveries: (
                _d.append((str(m.uid), str(m.type), m.file.read() if m.file is not None else b"")),
                m.file.close() if m.file is not None else None,
            )
            try:
                channel._handle_event(created_event(msg_type, contract=True))
                status = channel.effect_ledger.get_effect_status(channel.consumer_id, f"account-1:{msg_type}-1")
                pending_raised = False
            except Exception as exc:  # noqa: BLE001 - the simulation records the class
                status = f"EXCEPTION:{type(exc).__name__}"
                pending_raised = True
                deliveries = []
            finally:
                channel.stop_polling()

            report["cases"][key] = {
                "verdict": "PASS" if (status == STATE_DELIVERED and deliveries) else "FAIL",
                "effect_status": status,
                "deliveries": len(deliveries),
                "delivered_bytes": deliveries[0][2].decode("ascii", "replace") if deliveries else "",
                "media_calls": core.media_calls,
                "raised": pending_raised,
                "was_media_pending_error": False,
            }

        # --------------------------------------------- 3. discriminating control
        data_path = root / "control"
        data_path.mkdir(parents=True, exist_ok=True)
        core = ContractCore(served=True)
        core.mime = "text/plain"
        core.filename = "report.txt"
        channel = make_channel(core, data_path)
        deliveries = []
        channel._deliver_message = lambda m, _d=deliveries: _d.append(str(m.uid))
        control_status = None
        control_exception = ""
        try:
            # The PRE-FIX Core projection: a `file` message with no media reference.
            channel._handle_event(created_event("file", contract=False))
            control_status = channel.effect_ledger.get_effect_status(channel.consumer_id, "account-1:file-1")
            channel._retry_pending_media()
            control_terminal = channel.effect_ledger.get_effect_status(channel.consumer_id, "account-1:file-1")
        except Exception as exc:  # noqa: BLE001
            control_exception = type(exc).__name__
            control_terminal = control_status
        finally:
            channel.stop_polling()

        report["cases"]["PRE_FIX_CONTROL_FAILS_CLOSED"] = {
            "verdict": "PASS"
            if control_status == STATE_PENDING_MEDIA and control_terminal == STATE_MEDIA_FAILED and not deliveries
            else "FAIL",
            "pending_status": control_status,
            "terminal_status": control_terminal,
            "deliveries": len(deliveries),
            "exception": control_exception,
        }

        # ------------------------------------------- 4. sealed 274307 provenance
        # Floor: the EFB consumer's durable subscription provenance, taken from the
        # production bootstrap read (checkpoint 273844, bootstrap_at
        # 2026-09-16T17:14:43Z) and from Core's initial_cursor for the same slot.
        from datetime import datetime, timezone

        floor = SubscriptionFloorRecord(
            consumer_id="efb-linux-wechat:wechat.linux",
            account_id="f-live-a",
            subscription_floor_cursor=273844,
            subscription_floor_at=datetime(2026, 9, 16, 17, 14, 43, tzinfo=timezone.utc),
            bootstrap_mode="at_cursor",
            bootstrap_source="core_bootstrap",
            provenance_source="core_bootstrap",
        )
        sealed_projection = {
            "account_id": "f-live-a",
            "chat_id": "38808757431@chatroom",
            "message_id": "8745c1a931013b8941a0736d6fb890f1a4129129bd03b2b4842d09f7d5995d79",
            "type": "text",
            "created_at": "2026-09-17T08:41:14Z",
        }
        origin, reason = extract_business_origin(sealed_projection)
        classified = floor.classify(origin, reason)

        # Core's projection carries no first-seen cursor today, so the business
        # origin is the authoritative projection timestamp.  If Core ever exposes
        # one of BUSINESS_ORIGIN_CURSOR_FIELDS the cursor floor decides instead;
        # both routes must agree that 274307 is new business.
        cursor_origin, cursor_reason = extract_business_origin({**sealed_projection, "origin_cursor": 274307})
        cursor_classified = floor.classify(cursor_origin, cursor_reason)

        # A message that was never delivered has no durable effect identity, so the
        # ledger cannot answer KNOWN_EFFECT for it.
        both_new_business = (
            classified == CLASSIFICATION_FIRST_BUSINESS_EFFECT
            and cursor_classified == CLASSIFICATION_FIRST_BUSINESS_EFFECT
        )
        report["cases"]["SEALED_274307_CLASSIFICATION"] = {
            "verdict": "PASS" if both_new_business else "FAIL",
            "classification": classified,
            "classification_via_cursor_floor": cursor_classified,
            "origin": origin.describe() if origin is not None else "none",
            "reason": reason,
            "274307_CLASSIFIED_AS_NEW_BUSINESS": "YES" if both_new_business else "NO",
            "274307_DUPLICATE": "YES"
            if CLASSIFICATION_KNOWN_EFFECT in {classified, cursor_classified}
            or CLASSIFICATION_REPROJECTION_OF_PREEXISTING_OBJECT in {classified, cursor_classified}
            else "NO",
            "known_effect_requires_durable_effect_identity": True,
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(case["verdict"] == "PASS" for case in report["cases"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
