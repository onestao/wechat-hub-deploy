#!/usr/bin/env python3
"""Dependency-free mock implementation of WeChat Core Interface Contract V1."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


CONTRACT_VERSION = 1
MAX_INLINE_MEDIA_BYTES = 20 * 1024 * 1024
SAMPLE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


class MockCoreState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.accounts = [
            {
                "account_id": "account-alpha",
                "display_name": "Alpha WeChat",
                "state": "online",
                "runtime": {"display": ":1", "pid": 4101, "healthy": True},
                "sync": {"healthy": True, "last_event_at": "2026-08-31T07:00:03Z"},
            },
            {
                "account_id": "account-beta",
                "display_name": "Beta WeChat",
                "state": "online",
                "runtime": {"display": ":1", "pid": 4102, "healthy": True},
                "sync": {"healthy": True, "last_event_at": "2026-08-31T07:00:02Z"},
            },
        ]
        self.chats = {
            "account-alpha": [
                {
                    "account_id": "account-alpha",
                    "chat_id": "alpha-private-1",
                    "type": "private",
                    "display_name": "Alice",
                    "alias": "alice",
                    "updated_at": "2026-08-31T07:00:01Z",
                },
                {
                    "account_id": "account-alpha",
                    "chat_id": "alpha-group-1@chatroom",
                    "type": "group",
                    "display_name": "Alpha Research Group",
                    "member_count": 3,
                    "updated_at": "2026-08-31T07:00:03Z",
                },
            ],
            "account-beta": [
                {
                    "account_id": "account-beta",
                    "chat_id": "beta-private-1",
                    "type": "private",
                    "display_name": "Bob",
                    "alias": "bob",
                    "updated_at": "2026-08-31T07:00:02Z",
                }
            ],
        }
        self.media = {
            "media-image-1": {
                "account_id": "account-beta",
                "filename": "one-pixel.png",
                "mime_type": "image/png",
                "content": SAMPLE_PNG,
            }
        }
        self.events = [
            {
                "event_id": "event-0001",
                "cursor": "1",
                "account_id": "account-alpha",
                "event_type": "message.created",
                "occurred_at": "2026-08-31T07:00:01Z",
                "payload": {
                    "message": {
                        "account_id": "account-alpha",
                        "message_id": "alpha-msg-1",
                        "chat_id": "alpha-private-1",
                        "type": "text",
                        "direction": "incoming",
                        "created_at": "2026-08-31T07:00:01Z",
                        "text": "Hello from Alpha",
                        "author": {"member_id": "alice", "display_name": "Alice", "is_self": False},
                    }
                },
            },
            {
                "event_id": "event-0002",
                "cursor": "2",
                "account_id": "account-beta",
                "event_type": "message.created",
                "occurred_at": "2026-08-31T07:00:02Z",
                "payload": {
                    "message": {
                        "account_id": "account-beta",
                        "message_id": "beta-msg-1",
                        "chat_id": "beta-private-1",
                        "type": "image",
                        "direction": "incoming",
                        "created_at": "2026-08-31T07:00:02Z",
                        "media_id": "media-image-1",
                        "filename": "one-pixel.png",
                        "mime_type": "image/png",
                        "author": {"member_id": "bob", "display_name": "Bob", "is_self": False},
                    }
                },
            },
            {
                "event_id": "event-0003",
                "cursor": "3",
                "account_id": "account-alpha",
                "event_type": "chat.updated",
                "occurred_at": "2026-08-31T07:00:03Z",
                "payload": {"chat_id": "alpha-group-1@chatroom", "member_count": 3},
            },
        ]
        self.acked: dict[str, set[str]] = {}
        self.sends: list[dict[str, Any]] = []
        self.idempotency: dict[str, dict[str, Any]] = {}

    def account(self, account_id: str) -> dict[str, Any]:
        for account in self.accounts:
            if account["account_id"] == account_id:
                return account
        raise ApiError(404, "account_not_found", f"Unknown account_id: {account_id}")

    def chat(self, account_id: str, chat_id: str) -> dict[str, Any]:
        self.account(account_id)
        for chat in self.chats.get(account_id, []):
            if chat["chat_id"] == chat_id:
                return chat
        raise ApiError(404, "chat_not_found", f"Unknown chat_id for {account_id}: {chat_id}")

    def runtime_accounts(self) -> dict[str, Any]:
        with self.lock:
            rows = []
            for account in self.accounts:
                runtime = account.get("runtime") or {}
                pid = runtime.get("pid")
                running = account.get("state") not in {"stopped", "offline"} and bool(pid)
                provider = str(runtime.get("runtime_provider") or "legacy")
                rows.append(
                    {
                        "account_id": account["account_id"],
                        "display_name": account.get("display_name") or account["account_id"],
                        "runtime_provider": provider,
                        "enabled": True,
                        "autostart": True,
                        "legacy": False,
                        "username": (
                            f"agent_{account['account_id'].replace('-', '_')}"
                            if provider == "agent_wechat"
                            else f"wx_{account['account_id'].replace('-', '_')}"
                        ),
                        "uid": None if provider == "agent_wechat" else 22000 + len(rows),
                        "home": (
                            f"/config/agent-wechat/{account['account_id']}/home"
                            if provider == "agent_wechat"
                            else f"/config/wechat-accounts/{account['account_id']}/home"
                        ),
                        "display": "isolated" if provider == "agent_wechat" else runtime.get("display") or ":1",
                        "running": running,
                        "container_running": running if provider == "agent_wechat" else running,
                        "agent_server_healthy": True if provider == "agent_wechat" and running else None,
                        "runtime_health": "healthy" if provider == "agent_wechat" and running else ("stopped" if not running else "healthy"),
                        "wechat_login_status": "logged_in" if provider == "agent_wechat" and account.get("state") == "online" else "unknown",
                        "pids": [pid] if running else [],
                        "windows": (
                            []
                            if provider == "agent_wechat"
                            else ([{"window_id": pid + 100, "pid": pid, "title": "Weixin"}] if running else [])
                        ),
                        "window_error": None,
                        "container_name": f"wechat-agent-{account['account_id']}" if provider == "agent_wechat" else "",
                        "current_image": "ghcr.io/thisnick/agent-wechat:0.11.15" if provider == "agent_wechat" else "",
                    }
                )
        return {
            "accounts": rows,
            "registry_reload": {"ok": True, "changed": False, "added": [], "removed": [], "updated": []},
        }

    def create_runtime_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        account_id = required_text(payload, "account_id")
        with self.lock:
            if any(row["account_id"] == account_id for row in self.accounts):
                raise ApiError(409, "account_exists", f"account already exists: {account_id}")
            running = bool(payload.get("start", True))
            pid = 5000 + len(self.accounts) + 1 if running else None
            provider = str(payload.get("runtime_provider") or payload.get("provider") or "legacy")
            account = {
                "account_id": account_id,
                "display_name": str(payload.get("display_name") or account_id),
                "state": "login_required" if running else "stopped",
                "runtime": {
                    "display": str(payload.get("display") or ":1"),
                    "pid": pid,
                    "healthy": running,
                    "runtime_provider": provider,
                    "sender_capabilities": {
                        "text": provider == "agent_wechat",
                        "image": provider == "agent_wechat",
                        "file": provider == "agent_wechat",
                        "native_reply": False,
                        "media_caption": False,
                        "max_mentions": 0,
                        "echo_confirmation": False,
                        "verified_chat_target": provider == "agent_wechat",
                        "driver": provider,
                    },
                },
                "sync": {"healthy": True, "last_event_at": utc_now()},
            }
            self.accounts.append(account)
            self.chats[account_id] = []
        runtime = next(row for row in self.runtime_accounts()["accounts"] if row["account_id"] == account_id)
        return {
            "account": {"id": account_id, "display_name": account["display_name"]},
            "status": runtime,
            "registry_reload": {"ok": True, "changed": True, "added": [account_id], "removed": [], "updated": []},
        }

    def runtime_action(self, account_id: str, action: str) -> dict[str, Any]:
        if action not in {"start", "stop", "restart"}:
            raise ApiError(404, "not_found", f"Unknown Runtime account action: {action}")
        with self.lock:
            account = self.account(account_id)
            if action == "stop":
                account["state"] = "stopped"
                account["runtime"]["pid"] = None
                account["runtime"]["healthy"] = False
            else:
                account["state"] = "online"
                account["runtime"]["pid"] = account["runtime"].get("pid") or 6000 + len(self.accounts)
                account["runtime"]["healthy"] = True
        status = next(row for row in self.runtime_accounts()["accounts"] if row["account_id"] == account_id)
        status["action"] = action
        return {"status": status, "registry_reload": {"ok": True, "changed": False}}

    def remove_runtime_account(self, account_id: str) -> dict[str, Any]:
        with self.lock:
            self.account(account_id)
            self.accounts = [row for row in self.accounts if row["account_id"] != account_id]
            self.chats.pop(account_id, None)
        return {
            "removed": account_id,
            "data_preserved": f"/config/wechat-accounts/{account_id}/home",
            "unix_user_preserved": f"wx_{account_id.replace('-', '_')}",
            "registry_reload": {"ok": True, "changed": True, "added": [], "removed": [account_id], "updated": []},
        }

    def runtime_login_status(self, account_id: str) -> dict[str, Any]:
        account = self.account(account_id)
        runtime = account.get("runtime") or {}
        running = bool(runtime.get("pid")) and account.get("state") != "stopped"
        if account.get("state") == "online":
            state = "online"
        elif not running:
            state = "stopped"
        else:
            state = "waiting"
        return {
            "account_id": account_id,
            "display_name": account.get("display_name") or account_id,
            "state": state,
            "core_state": account.get("state"),
            "running": running,
            "container_running": running,
            "agent_server_healthy": True if str(runtime.get("runtime_provider") or "legacy") == "agent_wechat" and running else None,
            "runtime_health": "healthy" if running else "stopped",
            "snapshot_available": running,
            "window_title": "Weixin" if running else "",
            "window_count": 1 if running else 0,
        }

    def runtime_login_start(self, account_id: str) -> dict[str, Any]:
        login = self.runtime_login_status(account_id)
        return {
            "account_id": account_id,
            "running": bool(login.get("running")),
            "snapshot_available": bool(login.get("snapshot_available")),
            "login_flow_state": "waiting_for_scan" if login.get("running") else "idle",
            "login_flow_status": "Waiting for QR scan" if login.get("running") else "",
            "login_flow_error": "",
        }

    def runtime_desktop(self, account_id: str) -> dict[str, Any]:
        account = self.account(account_id)
        runtime = account.get("runtime") or {}
        provider = str(runtime.get("runtime_provider") or "legacy")
        if provider == "agent_wechat":
            return {
                "account_id": account_id,
                "runtime_provider": provider,
                "scheme": "http",
                "port": 17892,
                "path": "/desktop/mock-session-abcdefghijklmnopqrstuvwxyz012345/vnc/?autoconnect=true&path=desktop%2Fmock-session-abcdefghijklmnopqrstuvwxyz012345%2Fvnc%2Fwebsockify",
                "gateway_session_expires_at": 4102444800,
            }
        return {
            "account_id": account_id,
            "runtime_provider": "legacy",
            "scheme": "",
            "port": None,
            "path": "",
        }

    def poll_events(self, query: dict[str, list[str]]) -> dict[str, Any]:
        after_raw = query.get("after", ["0"])[0] or "0"
        try:
            after = int(after_raw)
        except ValueError as exc:
            raise ApiError(400, "invalid_cursor", "after must be an integer cursor in Mock Core") from exc
        try:
            limit = int(query.get("limit", ["50"])[0])
        except ValueError as exc:
            raise ApiError(400, "invalid_limit", "limit must be an integer") from exc
        limit = max(1, min(limit, 200))
        account_id = query.get("account_id", [""])[0]
        if account_id:
            self.account(account_id)
        selected = [
            event
            for event in self.events
            if int(event["cursor"]) > after and (not account_id or event["account_id"] == account_id)
        ][:limit]
        next_cursor = selected[-1]["cursor"] if selected else str(after)
        return {"events": selected, "next_cursor": next_cursor, "has_more": len(selected) == limit}

    def ack_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        consumer_id = required_text(payload, "consumer_id")
        event_ids = payload.get("event_ids")
        if not isinstance(event_ids, list) or not event_ids or not all(isinstance(item, str) and item for item in event_ids):
            raise ApiError(400, "invalid_event_ids", "event_ids must be a non-empty list of strings")
        known = {event["event_id"] for event in self.events}
        unknown = [event_id for event_id in event_ids if event_id not in known]
        if unknown:
            raise ApiError(404, "event_not_found", "One or more event IDs are unknown", {"event_ids": unknown})
        with self.lock:
            bucket = self.acked.setdefault(consumer_id, set())
            bucket.update(event_ids)
        return {"consumer_id": consumer_id, "acked_event_ids": event_ids, "acked_count": len(event_ids)}

    def record_send(self, kind: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        account_id = required_text(payload, "account_id")
        chat_id = required_text(payload, "chat_id")
        self.chat(account_id, chat_id)
        if kind == "text":
            required_text(payload, "text")
        else:
            has_media_id = bool(str(payload.get("media_id") or "").strip())
            has_content = bool(str(payload.get("content_base64") or "").strip())
            if has_media_id == has_content:
                raise ApiError(400, "invalid_media_source", "Provide exactly one of media_id or content_base64")
            if has_media_id:
                media = self.media.get(str(payload["media_id"]))
                if not media or media["account_id"] != account_id:
                    raise ApiError(404, "media_not_found", f"Unknown media_id for {account_id}: {payload['media_id']}")
            else:
                try:
                    content = base64.b64decode(str(payload["content_base64"]), validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ApiError(400, "invalid_base64", "content_base64 is not valid base64") from exc
                if len(content) > MAX_INLINE_MEDIA_BYTES:
                    raise ApiError(413, "media_too_large", "Inline media exceeds 20 MiB decoded limit")

        request_key = idempotency_key or str(payload.get("client_request_id") or "").strip()
        with self.lock:
            if request_key and request_key in self.idempotency:
                return self.idempotency[request_key]
            now = utc_now()
            receipt = {
                "send_id": f"send-{uuid.uuid4().hex}",
                "status": "accepted",
                "kind": kind,
                "account_id": account_id,
                "chat_id": chat_id,
                "accepted_at": now,
                "client_request_id": str(payload.get("client_request_id") or ""),
            }
            self.sends.append({"receipt": receipt, "request": payload})
            if request_key:
                self.idempotency[request_key] = receipt
            return receipt


def required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "invalid_request", f"{key} must be a non-empty string", {"field": key})
    return value.strip()


class MockCoreHandler(BaseHTTPRequestHandler):
    server_version = "WeChatMockCore/1"
    state: MockCoreState

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error: ApiError) -> None:
        self._json(
            error.status,
            {"error": {"code": error.code, "message": error.message, "details": error.details}},
        )

    def _body_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ApiError(400, "invalid_content_length", "Invalid Content-Length") from exc
        if length <= 0:
            raise ApiError(400, "empty_body", "Request body is required")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid_json", "Request body must be valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise ApiError(400, "invalid_json", "Top-level JSON value must be an object")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            path = parsed.path.rstrip("/") or "/"
            if path == "/health":
                self._json(
                    200,
                    {
                        "ok": True,
                        "service": "wechat-core-mock",
                        "contract_version": CONTRACT_VERSION,
                        "time": utc_now(),
                        "accounts": len(self.state.accounts),
                        "sender_capabilities": {
                            "text": True,
                            "image": True,
                            "file": True,
                            "native_reply": True,
                            "media_caption": True,
                            "max_mentions": 0,
                            "echo_confirmation": False,
                        },
                        "registry": {"ok": True, "hot_reload": True, "accounts": len(self.state.accounts)},
                        "runtime_management": {"configured": True, "available": True, "registry_hot_reload": True},
                    },
                )
                return
            if path == "/v1/accounts":
                self._json(200, {"accounts": self.state.accounts})
                return
            if path == "/v1/runtime/accounts":
                self._json(200, self.state.runtime_accounts())
                return
            runtime_prefix = "/v1/runtime/accounts/"
            if path.startswith(runtime_prefix):
                runtime_suffix = path[len(runtime_prefix) :]
                if runtime_suffix.endswith("/login/snapshot"):
                    account_id = unquote(runtime_suffix[: -len("/login/snapshot")].strip("/"))
                    self.state.account(account_id)
                    content = SAMPLE_PNG
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "no-store, max-age=0")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if runtime_suffix.endswith("/login"):
                    account_id = unquote(runtime_suffix[: -len("/login")].strip("/"))
                    self._json(200, self.state.runtime_login_status(account_id))
                    return
                if runtime_suffix.endswith("/desktop"):
                    account_id = unquote(runtime_suffix[: -len("/desktop")].strip("/"))
                    self._json(200, self.state.runtime_desktop(account_id))
                    return
            prefix = "/v1/accounts/"
            suffix = "/chats"
            if path.startswith(prefix) and path.endswith(suffix):
                account_id = unquote(path[len(prefix) : -len(suffix)].strip("/"))
                self.state.account(account_id)
                rows = list(self.state.chats.get(account_id, []))
                search = query.get("query", [""])[0].strip().lower()
                if search:
                    rows = [row for row in rows if search in row.get("display_name", "").lower()]
                try:
                    limit = max(1, min(int(query.get("limit", ["100"])[0]), 200))
                except ValueError as exc:
                    raise ApiError(400, "invalid_limit", "limit must be an integer") from exc
                self._json(200, {"account_id": account_id, "chats": rows[:limit], "next_cursor": ""})
                return
            if path == "/v1/events/poll":
                self._json(200, self.state.poll_events(query))
                return
            media_prefix = "/v1/media/"
            if path.startswith(media_prefix):
                media_id = unquote(path[len(media_prefix) :])
                account_id = query.get("account_id", [""])[0].strip()
                if not account_id:
                    raise ApiError(400, "invalid_request", "account_id query parameter is required")
                self.state.account(account_id)
                media = self.state.media.get(media_id)
                if not media or media["account_id"] != account_id:
                    raise ApiError(404, "media_not_found", f"Unknown media_id for {account_id}: {media_id}")
                content = media["content"]
                self.send_response(200)
                self.send_header("Content-Type", media["mime_type"])
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", f'inline; filename="{media["filename"]}"')
                self.send_header("X-Media-Id", media_id)
                self.end_headers()
                self.wfile.write(content)
                return
            raise ApiError(404, "not_found", f"Unknown endpoint: {path}")
        except ApiError as error:
            self._error(error)

    def do_POST(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path.rstrip("/") or "/"
            payload = self._body_json()
            if path == "/v1/events/ack":
                self._json(200, self.state.ack_events(payload))
                return
            if path == "/v1/runtime/accounts":
                self._json(201, self.state.create_runtime_account(payload))
                return
            runtime_prefix = "/v1/runtime/accounts/"
            if path.startswith(runtime_prefix):
                suffix = path[len(runtime_prefix) :]
                parts = suffix.split("/")
                if len(parts) == 2 and parts[0] and parts[1]:
                    if parts[1] == "login":
                        self._json(202, self.state.runtime_login_start(unquote(parts[0])))
                        return
                    self._json(200, self.state.runtime_action(unquote(parts[0]), parts[1]))
                    return
            send_prefix = "/v1/send/"
            if path.startswith(send_prefix):
                kind = path[len(send_prefix) :]
                if kind not in {"text", "image", "file"}:
                    raise ApiError(404, "not_found", f"Unknown send operation: {kind}")
                receipt = self.state.record_send(kind, payload, self.headers.get("Idempotency-Key", "").strip())
                self._json(202, receipt)
                return
            raise ApiError(404, "not_found", f"Unknown endpoint: {path}")
        except ApiError as error:
            self._error(error)

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path.rstrip("/") or "/"
            prefix = "/v1/runtime/accounts/"
            if path.startswith(prefix):
                account_id = unquote(path[len(prefix) :])
                if account_id and "/" not in account_id:
                    self._json(200, self.state.remove_runtime_account(account_id))
                    return
            raise ApiError(404, "not_found", f"Unknown endpoint: {path}")
        except ApiError as error:
            self._error(error)


def create_server(host: str, port: int, state: MockCoreState | None = None) -> ThreadingHTTPServer:
    handler = type("BoundMockCoreHandler", (MockCoreHandler,), {"state": state or MockCoreState()})
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    server = create_server(args.host, args.port)
    print(f"Mock Core V{CONTRACT_VERSION} listening on http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
