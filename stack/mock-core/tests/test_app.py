from __future__ import annotations

import base64
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


MOCK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MOCK_ROOT))

from app import MockCoreState, create_server  # noqa: E402


class MockCoreHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0, MockCoreState())
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, method="GET", payload=None, headers=None):
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=request_headers)
        with urllib.request.urlopen(request, timeout=2) as response:
            content_type = response.headers.get_content_type()
            data = response.read()
            if content_type == "application/json":
                return response.status, json.loads(data)
            return response.status, data

    def test_health_accounts_and_chats(self):
        status, health = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["contract_version"], 1)
        self.assertTrue(health["sender_capabilities"]["native_reply"])
        self.assertTrue(health["sender_capabilities"]["file"])
        _, accounts = self.request("/v1/accounts")
        self.assertEqual(len(accounts["accounts"]), 2)
        _, chats = self.request("/v1/accounts/account-alpha/chats")
        self.assertEqual(chats["account_id"], "account-alpha")
        self.assertGreaterEqual(len(chats["chats"]), 2)

    def test_poll_and_ack(self):
        _, page = self.request("/v1/events/poll?after=0&limit=2&consumer_id=etm-test")
        self.assertEqual([item["cursor"] for item in page["events"]], ["1", "2"])
        status, ack = self.request(
            "/v1/events/ack",
            method="POST",
            payload={"consumer_id": "etm-test", "event_ids": ["event-0001", "event-0002"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(ack["acked_count"], 2)

    def test_runtime_account_management_extension(self):
        _, runtime = self.request("/v1/runtime/accounts")
        self.assertEqual(len(runtime["accounts"]), 2)
        status, created = self.request(
            "/v1/runtime/accounts",
            method="POST",
            payload={"account_id": "account-gamma", "display_name": "Gamma", "start": True},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["registry_reload"]["added"], ["account-gamma"])
        _, login = self.request("/v1/runtime/accounts/account-gamma/login")
        self.assertEqual(login["state"], "waiting")
        status, snapshot = self.request("/v1/runtime/accounts/account-gamma/login/snapshot")
        self.assertEqual(status, 200)
        self.assertTrue(snapshot.startswith(b"\x89PNG"))
        _, accounts = self.request("/v1/accounts")
        self.assertIn("account-gamma", {row["account_id"] for row in accounts["accounts"]})
        _, stopped = self.request("/v1/runtime/accounts/account-gamma/stop", method="POST", payload={})
        self.assertFalse(stopped["status"]["running"])
        _, started = self.request("/v1/runtime/accounts/account-gamma/start", method="POST", payload={})
        self.assertTrue(started["status"]["running"])
        _, removed = self.request("/v1/runtime/accounts/account-gamma", method="DELETE")
        self.assertEqual(removed["removed"], "account-gamma")

    def test_media_stream(self):
        status, body = self.request("/v1/media/media-image-1?account_id=account-beta")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\x89PNG"))

    def test_send_endpoints_and_idempotency(self):
        text_payload = {
            "account_id": "account-alpha",
            "chat_id": "alpha-private-1",
            "text": "hello",
            "client_request_id": "client-1",
        }
        _, first = self.request(
            "/v1/send/text", method="POST", payload=text_payload, headers={"Idempotency-Key": "same-key"}
        )
        _, second = self.request(
            "/v1/send/text", method="POST", payload=text_payload, headers={"Idempotency-Key": "same-key"}
        )
        self.assertEqual(first["send_id"], second["send_id"])

        image_payload = {
            "account_id": "account-beta",
            "chat_id": "beta-private-1",
            "filename": "tiny.png",
            "mime_type": "image/png",
            "content_base64": base64.b64encode(b"not-a-real-image-but-valid-bytes").decode("ascii"),
        }
        status, receipt = self.request("/v1/send/image", method="POST", payload=image_payload)
        self.assertEqual(status, 202)
        self.assertEqual(receipt["kind"], "image")

        file_payload = {
            "account_id": "account-beta",
            "chat_id": "beta-private-1",
            "media_id": "media-image-1",
            "filename": "forwarded.png",
        }
        status, receipt = self.request("/v1/send/file", method="POST", payload=file_payload)
        self.assertEqual(status, 202)
        self.assertEqual(receipt["kind"], "file")

    def test_unknown_account_has_structured_error(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/v1/accounts/missing/chats")
        self.assertEqual(caught.exception.code, 404)
        payload = json.loads(caught.exception.read())
        self.assertEqual(payload["error"]["code"], "account_not_found")


if __name__ == "__main__":
    unittest.main()
