# Mock Core

Dependency-free implementation of the frozen Core Interface Contract V1. It seeds two accounts, private/group chats, text/image events, media bytes, acknowledgements and outbound receipts.

Run locally:

```powershell
python stack\mock-core\app.py --host 127.0.0.1 --port 8080
```

Run tests:

```powershell
python -m unittest discover -s stack\mock-core\tests -v
```

This is a contract simulator. It does not connect to WeChat, decrypt databases, control GUI windows or contact Telegram.
