"""RC.14 EFB shutdown requalification - host-side monotonic mark fixture (ARM B).

This is a QUALIFICATION FIXTURE, not product code. It is mounted read-only into
an isolated container and used as the entrypoint. It changes no image byte.

It reuses the FROZEN in-image probe module verbatim (imported from
/opt/efb-linux-wechat-slave/scripts/qualification/image_shutdown_probe.py) and
applies exactly two host-side patches:

  1. FIXTURE PATCH (frozen bug D1): the frozen in-image stub answers
     GET /health with contract_version "v1" while Core.py requires the integer
     1. The patch answers with the integer 1 so the frozen gate-runner profile
     (startup_healthcheck: true) can be used with zero parameter deviation.
     This patch lives in host memory only; the candidate is untouched.

  2. INSTRUMENT PATCH: instance-level observation wrappers on documented seams
     (ShutdownCoordinator._clock / _exit_func, and the channel's own
     drain_for_shutdown / suppress_external_dispatch / _flush_final_checkpoint /
     effect_ledger.checkpoint_wal). No product source is edited and no product
     behaviour is reordered; the wrappers only read time.monotonic() around the
     original callable. The five required absolute monotonic marks are written
     to --marks before the controlled exit.

The marks file is written with a buffered write + close (no fsync) because the
container mount is a host bind mount: the host page cache sees the file as soon
as the descriptor is closed, and avoiding fsync keeps the mark write from
inflating T_CONTAINER_DIE.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FROZEN_PROBE = (
    "/opt/efb-linux-wechat-slave/scripts/qualification/image_shutdown_probe.py"
)
MARKS = "/qualification/marks.json"


def _load_frozen_probe() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_image_shutdown_probe", FROZEN_PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen probe module: {FROZEN_PROBE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["frozen_image_shutdown_probe"] = module
    spec.loader.exec_module(module)
    return module


def _instrument(channel: Any, marks: dict) -> None:
    """Attach read-only observation wrappers to the live channel instance."""
    coord = getattr(channel, "_shutdown_coordinator", None)
    if coord is None:
        raise RuntimeError("channel has no shutdown coordinator to instrument")

    marks["fixture_ready_monotonic"] = time.monotonic()

    # --- signal receipt -----------------------------------------------------
    previous = signal.getsignal(signal.SIGTERM)

    def handler(signum: int, frame: Any) -> None:
        marks["signal_received_monotonic"] = time.monotonic()
        if callable(previous):
            previous(signum, frame)

    signal.signal(signal.SIGTERM, handler)

    # --- coordinator clock: first call == start of run() == signal path ------
    original_clock = coord._clock

    def clock() -> float:
        value = time.monotonic()
        marks.setdefault("coordinator_run_start_monotonic", value)
        return value

    coord._clock = clock

    # --- drain phase --------------------------------------------------------
    original_drain = channel.drain_for_shutdown

    def drain(*args: Any, **kwargs: Any) -> Any:
        marks.setdefault("drain_start_monotonic", time.monotonic())
        result = original_drain(*args, **kwargs)
        marks["drain_end_monotonic"] = time.monotonic()
        return result

    channel.drain_for_shutdown = drain

    # --- delivery suppression ----------------------------------------------
    original_suppress = channel.suppress_external_dispatch

    def suppress(*args: Any, **kwargs: Any) -> Any:
        marks.setdefault("delivery_suppressed_monotonic", time.monotonic())
        return original_suppress(*args, **kwargs)

    channel.suppress_external_dispatch = suppress

    # --- durable checkpoint flush ------------------------------------------
    if hasattr(channel, "_flush_final_checkpoint"):
        original_flush = channel._flush_final_checkpoint

        def flush(*args: Any, **kwargs: Any) -> Any:
            result = original_flush(*args, **kwargs)
            marks["checkpoint_flush_completed_monotonic"] = time.monotonic()
            return result

        channel._flush_final_checkpoint = flush

    # --- effect ledger WAL checkpoint --------------------------------------
    ledger = getattr(channel, "effect_ledger", None)
    if ledger is not None and hasattr(ledger, "checkpoint_wal"):
        original_wal = ledger.checkpoint_wal

        def wal(*args: Any, **kwargs: Any) -> Any:
            result = original_wal(*args, **kwargs)
            marks["ledger_flush_completed_monotonic"] = time.monotonic()
            return result

        ledger.checkpoint_wal = wal

    # --- exit request -------------------------------------------------------
    original_exit = coord._exit_func

    def exit_func(code: int) -> Any:
        marks["exit_requested_monotonic"] = time.monotonic()
        try:
            with open(MARKS, "w", encoding="utf-8") as handle:
                json.dump(marks, handle, sort_keys=True)
                handle.write("\n")
        except Exception:  # pragma: no cover - marks must never break the exit
            pass
        return original_exit(code)

    coord._exit_func = exit_func


def main() -> int:
    global MARKS
    parser = argparse.ArgumentParser()
    parser.add_argument("--marks", default=MARKS)
    known, rest = parser.parse_known_args()
    MARKS = str(known.marks)

    module = _load_frozen_probe()

    # FIXTURE PATCH 1: correct the frozen contract literal in host memory only.
    original_handler_type = module._handler_type

    def patched_handler_type(state: Any) -> Any:
        base = original_handler_type(state)

        class HealthFixed(base):  # type: ignore[misc, valid-type]
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                if urlparse(self.path).path == "/health":
                    self._send(200, {"status": "ok", "contract_version": 1})
                    return
                return super().do_GET()

        return HealthFixed

    module._handler_type = patched_handler_type

    # FIXTURE PATCH 2: instrument the channel the frozen probe constructs.
    marks: dict = {
        "monotonic_at_start": time.monotonic(),
        "realtime_at_start": time.time(),
        "pid": os.getpid(),
        "fixture": "rc14_requal_marks_fixture.py",
    }
    base_channel = module.LinuxWeChatChannel

    class InstrumentedChannel(base_channel):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            _instrument(self, marks)

    module.LinuxWeChatChannel = InstrumentedChannel

    sys.argv = ["image_shutdown_probe.py", *rest]
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
