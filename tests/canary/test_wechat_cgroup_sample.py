"""Behavior tests for the host-side read-only canary sampler.

These tests never touch docker or a real container: docker is replaced by a
mock executable and /proc + /sys/fs/cgroup by synthetic fixture trees.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLER = ROOT / "scripts" / "canary" / "wechat_cgroup_sample.sh"
RUNNER = ROOT / "scripts" / "canary" / "wechat_canary_run.sh"

# Pin the bash binary explicitly: a bare "bash" in argv can be hijacked by the
# Windows System32 (WSL) launcher, whose mount table differs from Git Bash.
def _find_bash() -> str:
    candidates = [
        os.environ.get("WECHAT_HUB_TEST_BASH"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        shutil.which("bash"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return "bash"


BASH = _find_bash()


def rel(path: Path) -> str:
    """ROOT-relative POSIX path; safe under any bash flavor with cwd=ROOT."""
    return path.relative_to(ROOT).as_posix()

CG_PATH = "system.slice/docker-abc123def456.scope"
CONTAINER_ID = "abc123def456" * 5 + "abcd"

WATCHDOG_LOG_LINES = [
    "[health] monitoring WeChat",
    "[health] WeChat unresponsive for 60s, killing",
    "[health] Killed WeChat pid=42",
    "[health] WeChat process disappeared, recovering",
    "[health] Spawned WeChat pid=43",
    "pthread_create failed: EAGAIN",
    "std::system_error: thread constructor failed",
    "[health] Spawned WeChat pid=44",
]


def run_sampler(*args: str, env_extra: dict[str, str] | None = None):
    env = os.environ.copy()
    env.pop("WECHAT_CANARY_ALLOW_DESTRUCTIVE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [BASH, SAMPLER.relative_to(ROOT).as_posix(), *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def make_docker_mock(bin_dir: Path, log_lines: list[str]) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    docker = bin_dir / "docker"
    printf_args = " ".join(json.dumps(line) for line in log_lines)
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "if [[ \"$1\" == inspect ]]; then\n"
        f"  printf '%s\\n' '{CONTAINER_ID}|100|512|running|false|2026-09-05T04:13:00.123456789Z'\n"
        "elif [[ \"$1\" == logs ]]; then\n"
        f"  printf '%s\\n' {printf_args}\n"
        "else\n"
        "  exit 64\n"
        "fi\n",
        encoding="utf-8",
        newline="\n",
    )
    docker.chmod(0o755)
    return docker


def build_proc_fixture(
    proc_root: Path,
    cgroup_root: Path,
    *,
    omit_status_for: set[str] = frozenset(),
) -> None:
    """Tasks 100-103 live in the container cgroup (wechat, WeChatAppEx, node
    agent-server, a zombie); task 104 is in a foreign cgroup that must never
    be counted."""
    cgroup_dir = cgroup_root / CG_PATH
    for pid_dir in (proc_root / "100", proc_root / "101", proc_root / "102", proc_root / "103"):
        pid_dir.mkdir(parents=True, exist_ok=True)
        (pid_dir / "cgroup").write_text(f"0::/{CG_PATH}\n", encoding="utf-8", newline="\n")
    (proc_root / "104").mkdir(parents=True, exist_ok=True)
    (proc_root / "104" / "cgroup").write_text("0::/system.slice/docker-foreign.scope\n", encoding="utf-8", newline="\n")

    statuses = {
        "100": "Name:\tWeChat\nState:\tS (sleeping)\nThreads:\t40\n",
        "101": "Name:\tWeChatAppEx\nState:\tS (sleeping)\nThreads:\t25\n",
        "102": "Name:\tnode\nState:\tS (sleeping)\nThreads:\t30\n",
        "103": "Name:\tdefunct-helper\nState:\tZ (zombie)\nThreads:\t1\n",
        "104": "Name:\tforeign\nState:\tZ (zombie)\nThreads:\t99\n",
    }
    cmdlines = {
        "100": b"/opt/WeChat\0",
        "101": b"/opt/WeChatAppEx --type=renderer\0",
        "102": b"node /app/agent-server.js\0",
    }
    for pid, status in statuses.items():
        if pid in omit_status_for:
            continue
        (proc_root / pid / "status").write_text(status, encoding="utf-8", newline="\n")
        if pid in cmdlines:
            (proc_root / pid / "cmdline").write_bytes(cmdlines[pid])

    cgroup_dir.mkdir(parents=True, exist_ok=True)
    (cgroup_dir / "pids.current").write_text("96\n", encoding="utf-8", newline="\n")
    (cgroup_dir / "pids.max").write_text("512\n", encoding="utf-8", newline="\n")
    (cgroup_dir / "pids.events").write_text("max 0\n", encoding="utf-8", newline="\n")
    (cgroup_dir / "memory.current").write_text("1610612736\n", encoding="utf-8", newline="\n")
    (cgroup_dir / "memory.max").write_text("2147483648\n", encoding="utf-8", newline="\n")
    (cgroup_dir / "memory.events").write_text("oom 0\noom_kill 0\n", encoding="utf-8", newline="\n")


def test_shell_entrypoints_are_syntax_valid() -> None:
    for script in (SAMPLER, RUNNER):
        result = subprocess.run(
            [BASH, "-n", script.relative_to(ROOT).as_posix()],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_scripts_exclude_mutating_interfaces_outside_the_guard() -> None:
    forbidden = (
        "docker exec",
        "docker update",
        "docker restart",
        "docker stop",
        "docker kill",
        "docker rm",
        "docker pause",
        "pkill",
        "killall",
        "kill -9",
        "system prune",
        "volume prune",
        "container prune",
        "rm -rf",
        "ssh ",
        "ps -T",
    )
    for script in (SAMPLER, RUNNER):
        text = script.read_text(encoding="utf-8").lower()
        assert "# begin destructive guard" in text and "# end destructive guard" in text
        head = text.split("# begin destructive guard")[0]
        tail = text.split("# end destructive guard", 1)[1]
        outside_guard = head + tail
        for command in forbidden:
            assert command not in outside_guard, f"{script.name} contains forbidden interface: {command}"


def test_live_mode_sample_with_mock_docker(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    bin_dir = tmp_path / "bin"
    build_proc_fixture(proc_root, cgroup_root)
    docker = make_docker_mock(bin_dir, WATCHDOG_LOG_LINES)

    result = run_sampler(
        "--container", "agent-wechat",
        "--docker-bin", rel(docker),
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)

    assert sample["schema"] == "wechat-hub.canary.sample/v1"
    assert sample["container"]["name"] == "agent-wechat"
    assert sample["container"]["id"] == CONTAINER_ID
    assert sample["container"]["init_pid"] == 100
    assert sample["container"]["host_config_pids_limit"] == 512
    assert sample["container"]["docker_oom_killed"] is False
    assert sample["cgroup"]["path"] == f"/{CG_PATH}"
    assert sample["collection"]["mode"] == "live"
    assert sample["collection"]["log_source"] == "docker"

    assert sample["pids"] == {"current": 96, "max": 512, "events_max_hit": 0}
    assert sample["memory"] == {
        "current_bytes": 1610612736,
        "max_bytes": 2147483648,
        "events_oom": 0,
        "events_oom_kill": 0,
    }

    tasks = sample["tasks"]
    # 100 + 101 + 102 + 103 matched; 104 is foreign and skipped.
    assert tasks["grand_total"]["processes"] == 4
    assert tasks["grand_total"]["threads"] == 40 + 25 + 30 + 1
    assert tasks["zombie_count"] == 1
    assert tasks["proc_race_count"] == 0
    assert tasks["proc_read_error_count"] == 0
    components = tasks["components"]
    assert components["wechat"] == {"processes": 1, "threads": 40}
    assert components["wechatappex"] == {"processes": 1, "threads": 25}
    assert components["agent-server"] == {"processes": 1, "threads": 30}
    assert components["crashpad"] == {"processes": 0, "threads": 0}
    assert components["other"] == {"processes": 1, "threads": 1}

    watchdog = sample["watchdog"]
    assert watchdog["unresponsive_kill"] == 1
    assert watchdog["killed_wechat"] == 1
    assert watchdog["process_disappeared"] == 1
    assert watchdog["spawned_wechat"] == 2
    assert watchdog["pthread_create_eagain"] == 1
    assert watchdog["thread_constructor_failed"] == 1

    assert sample["auth"]["status_url"] is None
    assert sample["auth"]["reported_auth_status"] is None
    assert sample["auth"]["current_ui_observation"] == "unknown"
    assert sample["auth"]["current_ui_fresh"] is False


def test_offline_fixture_mode_needs_no_docker(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    log_file = tmp_path / "watchdog.log"
    build_proc_fixture(proc_root, cgroup_root)
    log_file.write_text("\n".join(WATCHDOG_LOG_LINES) + "\n", encoding="utf-8", newline="\n")

    result = run_sampler(
        "--container-init-pid", "100",
        "--container-id", "abc123def456abc123",
        "--container-name", "agent-wechat-fixture",
        "--watchdog-log-file", rel(log_file),
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    assert sample["collection"]["mode"] == "offline-fixture"
    assert sample["collection"]["log_source"] == "file"
    assert sample["container"]["name"] == "agent-wechat-fixture"
    assert sample["container"]["host_config_pids_limit"] is None
    assert sample["pids"]["current"] == 96
    assert sample["watchdog"]["spawned_wechat"] == 2


def test_status_url_is_recorded_as_reported_only(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    bin_dir = tmp_path / "bin"
    build_proc_fixture(proc_root, cgroup_root)
    # The URL targets a closed port: collection must degrade to http_ok=false,
    # never fabricate auth state or crash the sample.
    docker = make_docker_mock(bin_dir, [])

    result = run_sampler(
        "--container", "agent-wechat",
        "--docker-bin", rel(docker),
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
        "--status-url", "http://127.0.0.1:1/api/status/auth",
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    assert sample["auth"]["status_url"] == "http://127.0.0.1:1/api/status/auth"
    assert sample["auth"]["reported_auth_status"]["http_ok"] is False
    assert sample["auth"]["current_ui_observation"] == "unknown"
    assert sample["auth"]["current_ui_fresh"] is False


def test_persistent_read_errors_are_counted_separately_from_races(tmp_path: Path) -> None:
    """Policy: a pid that is still present but persistently unreadable is a
    read error, never a tolerated /proc race (pids 100-103 lose their status
    files, 105 has no cgroup file, 106 has an empty one — all stay present)."""
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    log_file = tmp_path / "watchdog.log"
    build_proc_fixture(proc_root, cgroup_root, omit_status_for={"100", "101", "102", "103"})
    (proc_root / "105").mkdir(parents=True, exist_ok=True)
    (proc_root / "106").mkdir(parents=True, exist_ok=True)
    (proc_root / "106" / "cgroup").write_text("", encoding="utf-8", newline="\n")
    log_file.write_text("", encoding="utf-8", newline="\n")

    result = run_sampler(
        "--container-init-pid", "100",
        "--watchdog-log-file", rel(log_file),
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    assert sample["tasks"]["grand_total"]["processes"] == 0
    assert sample["tasks"]["grand_total"]["threads"] == 0
    assert sample["tasks"]["proc_race_count"] == 0
    assert sample["tasks"]["proc_read_error_count"] == 6  # 100..103 status + 105 cgroup + 106 empty


def test_vanished_pid_counts_as_race_not_read_error(tmp_path: Path) -> None:
    """Policy: a pid that disappears during the sweep (natural exit) is the
    only tolerated race. Deterministic handshake: pid 105's cgroup is a FIFO;
    the writer process removes the whole pid dir while the sampler is blocked
    inside the read, then closes the FIFO so the read gets EOF — the sampler's
    directory recheck must then see the pid gone and classify a race."""
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    log_file = tmp_path / "watchdog.log"
    build_proc_fixture(proc_root, cgroup_root)
    victim = proc_root / "105"
    victim.mkdir(parents=True)
    fifo = victim / "cgroup"
    subprocess.run([BASH, "-c", f"mkfifo '{fifo.as_posix()}'"], check=True, capture_output=True)
    log_file.write_text("", encoding="utf-8", newline="\n")

    writer_script = (
        f"exec 3>'{fifo.as_posix()}'\n"
        f"rm -r '{victim.as_posix()}'\n"
        "exec 3>&-\n"
    )
    writer = subprocess.Popen([BASH, "-c", writer_script])

    try:
        result = run_sampler(
            "--container-init-pid", "100",
            "--watchdog-log-file", rel(log_file),
            "--proc-root", rel(proc_root),
            "--cgroup-root", rel(cgroup_root),
        )
    finally:
        try:
            writer.wait(timeout=10)
        except subprocess.TimeoutExpired:
            writer.kill()
            writer.wait()
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    assert sample["tasks"]["proc_race_count"] == 1  # 105 vanished mid-sweep
    assert sample["tasks"]["proc_read_error_count"] == 0
    assert sample["tasks"]["grand_total"]["processes"] == 4


def test_destructive_env_is_refused(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    build_proc_fixture(proc_root, cgroup_root)

    for value in ("1", "true"):
        result = run_sampler(
            "--container-init-pid", "100",
            "--proc-root", rel(proc_root),
            "--cgroup-root", rel(cgroup_root),
            env_extra={"WECHAT_CANARY_ALLOW_DESTRUCTIVE": value},
        )
        assert result.returncode == 3, result.stderr
        assert "read-only" in result.stderr


def test_destructive_argument_is_refused(tmp_path: Path) -> None:
    result = run_sampler("--container", "agent-wechat docker exec evil")
    assert result.returncode == 3
    assert "refusing destructive argument" in result.stderr


def test_unresolvable_cgroup_fails_closed(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    (proc_root / "100").mkdir(parents=True)
    (proc_root / "100" / "cgroup").write_text("10:cpuset:/legacy-only\n", encoding="utf-8", newline="\n")

    result = run_sampler(
        "--container-init-pid", "100",
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(tmp_path / "cgroup"),
    )
    assert result.returncode == 1
    assert "cgroup v2" in result.stderr


def test_sampler_status_url_reads_fresh_auth_and_user_via_get_only(tmp_path: Path) -> None:
    import http.server
    import threading

    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    build_proc_fixture(proc_root, cgroup_root)

    requests_received = []

    class MockAuthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests_received.append(("GET", self.path))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "logged_in",
                "view": "Chat",
                "logged_in": True,
                "loggedInUser": "wxid_rpfflqttdz4a22_7fcd",
                "accountId": "testB",
            }).encode("utf-8"))

        def do_POST(self):
            requests_received.append(("POST", self.path))
            self.send_response(500)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), MockAuthHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    status_url = f"http://127.0.0.1:{port}/api/status/auth"
    result = run_sampler(
        "--container-init-pid", "100",
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
        "--status-url", status_url,
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    reported = sample["auth"]["reported_auth_status"]
    assert reported["http_ok"] is True
    assert reported["status"] == "logged_in"
    assert reported["view"] == "Chat"
    assert reported["logged_in_user"] == "wxid_rpfflqttdz4a22_7fcd"
    assert reported["account_id"] == "testB"
    # Ensure ONLY GET was executed (no POST, no GUI mutation, no send)
    assert len(requests_received) == 1
    assert requests_received[0][0] == "GET"


def test_sampler_emits_image_and_runtime_digests(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    build_proc_fixture(proc_root, cgroup_root)

    result = run_sampler(
        "--container-init-pid", "100",
        "--proc-root", rel(proc_root),
        "--cgroup-root", rel(cgroup_root),
        "--container-image", "ghcr.io/onestao/wechat-hub-agent-wechat:0.11.15-wh.3",
        "--container-repo-digest", "ghcr.io/onestao/wechat-hub-agent-wechat@sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd",
        "--runtime-id", "wechat-hub-runtime",
        "--runtime-image", "ghcr.io/onestao/wechat-hub-runtime:0.1.0-rc.5",
        "--runtime-repo-digest", "ghcr.io/onestao/wechat-hub-runtime@sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116",
    )
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout)
    assert sample["container"]["image"] == "ghcr.io/onestao/wechat-hub-agent-wechat:0.11.15-wh.3"
    assert sample["container"]["repo_digest"] == "ghcr.io/onestao/wechat-hub-agent-wechat@sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd"
    assert sample["runtime"]["id"] == "wechat-hub-runtime"
    assert sample["runtime"]["image"] == "ghcr.io/onestao/wechat-hub-runtime:0.1.0-rc.5"
    assert sample["runtime"]["repo_digest"] == "ghcr.io/onestao/wechat-hub-runtime@sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116"
