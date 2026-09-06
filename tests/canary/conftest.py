"""Shared fixtures for the scripts/canary toolkit tests.

Test scratch data is kept inside the project tree (`.local/tmp/canary-tests/`)
instead of the system temp directory, per the workspace data-lifecycle rules:
the base is purged when the session starts and removed again when it ends, and
each test's directory is deleted in the fixture finalizer.
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT_TMP_BASE = ROOT / ".local" / "tmp" / "canary-tests"

BASE_TIME = datetime(2026, 9, 5, 4, 0, 0, tzinfo=timezone.utc)

DEFAULT_COMPONENTS: dict[str, dict[str, int]] = {
    "wechat": {"processes": 1, "threads": 40},
    "wechatappex": {"processes": 2, "threads": 60},
    "wxplayer": {"processes": 1, "threads": 8},
    "wxocr": {"processes": 1, "threads": 5},
    "crashpad": {"processes": 1, "threads": 3},
    "agent-server": {"processes": 1, "threads": 30},
    "other": {"processes": 36, "threads": 134},
}


@pytest.fixture(scope="session", autouse=True)
def _project_tmp_base() -> Iterator[Path]:
    shutil.rmtree(PROJECT_TMP_BASE, ignore_errors=True)
    PROJECT_TMP_BASE.mkdir(parents=True, exist_ok=True)
    yield PROJECT_TMP_BASE
    shutil.rmtree(PROJECT_TMP_BASE, ignore_errors=True)


@pytest.fixture
def tmp_path(_project_tmp_base: Path, request: pytest.FixtureRequest) -> Iterator[Path]:
    base = _project_tmp_base / request.node.name
    base.mkdir(parents=True, exist_ok=True)
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


def make_sample(
    index: int,
    *,
    step_seconds: int = 30,
    pids_current: int = 280,
    pids_max: int | str = 512,
    events_max_hit: int = 0,
    host_pids_limit: int | None = 512,
    memory_current: int = 1_500_000_000,
    events_oom: int = 0,
    events_oom_kill: int = 0,
    zombie_count: int = 0,
    proc_race_count: int = 0,
    proc_read_error_count: int = 0,
    components: dict[str, dict[str, int]] | None = None,
    unresponsive_kill: int = 0,
    killed_wechat: int = 0,
    process_disappeared: int = 0,
    spawned_wechat: int = 0,
    pthread_create_eagain: int = 0,
    thread_constructor_failed: int = 0,
    auth_reported: dict[str, Any] | None = None,
    status_url: str | None = "http://127.0.0.1:8080/api/status/auth",
    docker_oom_killed: bool = False,
    docker_state: str = "running",
    container_image: str | None = None,
    container_image_id: str | None = None,
    container_repo_digest: str | None = None,
    runtime: dict[str, Any] | None = None,
    logged_in_user: str | None = "wxid_rpfflqttdz4a22_7fcd",
) -> dict[str, Any]:
    if status_url is None:
        auth_reported = None
    elif auth_reported is None:
        auth_reported = {
            "http_ok": True,
            "status": "logged_in",
            "view": "Chat",
            "logged_in": True,
            "main_window": "0x1a00003",
            "logged_in_user": logged_in_user,
        }
    elif isinstance(auth_reported, dict) and "logged_in_user" not in auth_reported and logged_in_user is not None:
        auth_reported["logged_in_user"] = logged_in_user
    timestamp = (BASE_TIME + timedelta(seconds=index * step_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    components = copy.deepcopy(components or DEFAULT_COMPONENTS)
    component_threads = sum(part["threads"] for part in components.values())
    return {
        "schema": "wechat-hub.canary.sample/v1",
        "timestamp": timestamp,
        "run": {"id": "test-run", "profile": "canary"},
        "container": {
            "name": "agent-wechat",
            "id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "state": docker_state,
            "init_pid": 100,
            "started_at": "2026-09-05T04:13:00.123456789Z",
            "host_config_pids_limit": host_pids_limit,
            "docker_oom_killed": docker_oom_killed,
            "image": container_image,
            "image_id": container_image_id,
            "repo_digest": container_repo_digest,
        },
        "runtime": runtime or {
            "id": "runtime-container-id",
            "state": "running",
            "image": "ghcr.io/onestao/wechat-hub-runtime:0.1.0-rc.5",
            "image_id": "sha256:80490cf6a29de306887ca2a9b2218825be1d28c5eafe9cfb9f7978faa1a12e4c",
            "repo_digest": "ghcr.io/onestao/wechat-hub-runtime@sha256:80490cf6a29de306887ca2a9b2218825be1d28c5eafe9cfb9f7978faa1a12e4c",
        },
        "cgroup": {
            "version": "v2",
            "path": "/system.slice/docker-0123456789abcdef.scope",
            "dir": "/sys/fs/cgroup/system.slice/docker-0123456789abcdef.scope",
        },
        "collection": {
            "mode": "live",
            "log_source": "docker",
            "proc_root": "/proc",
            "cgroup_root": "/sys/fs/cgroup",
        },
        "pids": {"current": pids_current, "max": pids_max, "events_max_hit": events_max_hit},
        "memory": {
            "current_bytes": memory_current,
            "max_bytes": 2147483648,
            "events_oom": events_oom,
            "events_oom_kill": events_oom_kill,
        },
        "tasks": {
            "grand_total": {
                "processes": sum(part["processes"] for part in components.values()),
                "threads": component_threads,
            },
            "zombie_count": zombie_count,
            "proc_race_count": proc_race_count,
            "proc_read_error_count": proc_read_error_count,
            "components": components,
        },
        "watchdog": {
            "unresponsive_kill": unresponsive_kill,
            "killed_wechat": killed_wechat,
            "process_disappeared": process_disappeared,
            "spawned_wechat": spawned_wechat,
            "pthread_create_eagain": pthread_create_eagain,
            "thread_constructor_failed": thread_constructor_failed,
        },
        "auth": {
            "status_url": status_url,
            "reported_auth_status": auth_reported,
            "current_ui_observation": "unknown",
            "current_ui_fresh": False,
        },
    }


def make_run(
    count: int = 61,
    *,
    mutate: Callable[[int, dict[str, Any]], None] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Build a run of `count` samples at 30s spacing (60 minutes by default)."""
    samples = []
    for index in range(count):
        sample = make_sample(index, **kwargs)
        if mutate is not None:
            mutate(index, sample)
        samples.append(sample)
    return samples


def write_jsonl(path, samples: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for sample in samples:
            stream.write(json.dumps(sample) + "\n")
