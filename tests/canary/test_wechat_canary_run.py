"""Behavior tests for the canary runner (duration/interval/flush semantics)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_wechat_cgroup_sample import BASH, build_proc_fixture, rel

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "canary" / "wechat_canary_run.sh"


def run_runner(*args: str, env_extra: dict[str, str] | None = None):
    env = os.environ.copy()
    env.pop("WECHAT_CANARY_ALLOW_DESTRUCTIVE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [BASH, RUNNER.relative_to(ROOT).as_posix(), *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def fixture_args(tmp_path: Path) -> list[str]:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    log_file = tmp_path / "watchdog.log"
    build_proc_fixture(proc_root, cgroup_root)
    log_file.write_text("[health] Spawned WeChat pid=7\n", encoding="utf-8", newline="\n")
    return [
        "--container-init-pid", "100",
        "--container-name", "agent-wechat-fixture",
        "--watchdog-log-file", rel(log_file),
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
    ]


def read_samples(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_short_fixture_run_completes_and_flushes(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    result = run_runner(
        "--output", rel(output),
        # Windows process-spawn overhead makes each sampler round take 1-3s,
        # so the window must be generous; on the Linux host a round is fast.
        "--duration", "10",
        "--interval", "1",
        "--run-id", "runner-test",
        *fixture_args(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    samples = read_samples(output)
    assert 2 <= len(samples) <= 10
    for sample in samples:
        assert sample["schema"] == "wechat-hub.canary.sample/v1"
        assert sample["run"]["id"] == "runner-test"
        assert sample["run"]["profile"] == "canary"
        assert sample["container"]["name"] == "agent-wechat-fixture"
        assert sample["collection"]["mode"] == "offline-fixture"
    assert "sampling completed" in result.stderr


def test_interval_below_recommendation_warns(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    result = run_runner(
        "--output", rel(output),
        "--duration", "1",
        "--interval", "5",
        *fixture_args(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "30-60s cadence" in result.stderr


def test_first_round_failure_aborts_without_evidence(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    result = run_runner(
        "--output", rel(output),
        "--duration", "3",
        "--interval", "1",
        "--definitely-not-a-flag", "x",
        *fixture_args(tmp_path),
    )
    assert result.returncode == 1
    assert "first sampler invocation failed" in result.stderr
    assert output.read_text(encoding="utf-8") == ""


def test_destructive_env_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    result = run_runner(
        "--output", rel(output),
        "--duration", "2",
        "--interval", "1",
        *fixture_args(tmp_path),
        env_extra={"WECHAT_CANARY_ALLOW_DESTRUCTIVE": "1"},
    )
    assert result.returncode == 3
    assert "read-only" in result.stderr
    assert not output.exists() or output.read_text(encoding="utf-8") == ""


def test_destructive_argument_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    result = run_runner(
        "--output", rel(output),
        "--container", "agent-wechat docker stop x",
    )
    assert result.returncode == 3
    assert "refusing destructive argument" in result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal delivery to a background bash process")
def test_interrupt_flushes_collected_samples(tmp_path: Path) -> None:
    output = tmp_path / "evidence.jsonl"
    runner_rel = RUNNER.relative_to(ROOT).as_posix()
    fixture_arg_str = " ".join(fixture_args(tmp_path))
    wrapper = (
        f"bash {runner_rel} --output {rel(output)} --duration 30 --interval 1 "
        f"{fixture_arg_str}"
        " & runner_pid=$!; sleep 3; kill -INT $runner_pid; wait $runner_pid; echo \"exit=$?\""
    )
    result = subprocess.run(
        [BASH, "-c", wrapper],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert "exit=130" in result.stdout, result.stdout + result.stderr
    assert "stopped safely" in result.stderr
    samples = read_samples(output)
    assert 1 <= len(samples) <= 4
    for sample in samples:
        assert sample["schema"] == "wechat-hub.canary.sample/v1"
