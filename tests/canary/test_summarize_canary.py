"""Verdict tests for scripts/canary/summarize_canary.py.

Each scenario maps onto a PASS criterion (or evidence-integrity rule) from
docs/P0_RC4_FULL_CHAT_PIDS_CANARY_GATE.md section 6/7.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import make_run, write_jsonl

ROOT = Path(__file__).resolve().parents[2]

OSCILLATING = (280, 285, 310, 290, 305, 280, 295, 275, 300, 285)


def summarize(tmp_path: Path, samples, *extra_args: str) -> dict:
    input_path = tmp_path / "evidence.jsonl"
    write_jsonl(input_path, samples)
    result = run_summarizer(input_path, *extra_args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_summarizer(input_path: Path, *extra_args: str):
    import subprocess

    script = ROOT / "scripts" / "canary" / "summarize_canary.py"
    return subprocess.run(
        [sys.executable, str(script), str(input_path), *extra_args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_stable_full_chat_run_is_pass_candidate(tmp_path: Path) -> None:
    samples = make_run(mutate=lambda i, s: s["pids"].update(current=OSCILLATING[i % len(OSCILLATING)]))
    summary = summarize(tmp_path, samples)
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert summary["promotion_performed"] is False
    assert summary["failure_reasons"] == []
    assert summary["incomplete_reasons"] == []
    assert summary["duration_seconds"] == 1800
    assert summary["pids"]["events_max_hit"]["delta"] == 0
    assert summary["watchdog"]["kill_delta"] == 0
    assert summary["watchdog"]["restart_delta"] == 0
    assert summary["auth"]["sampled"] is True
    assert summary["auth"]["current_ui_observation"] == "unknown"


def test_monotonic_task_growth_fails(tmp_path: Path) -> None:
    samples = make_run(count=20, mutate=lambda i, s: s["pids"].update(current=250 + i * 12))
    summary = summarize(tmp_path, samples)
    assert summary["outcome"] == "FAIL"
    assert any("monotonic growth" in reason for reason in summary["failure_reasons"])


def test_pids_events_increment_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        s["pids"]["events_max_hit"] = 0 if i < 4 else 3

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("pids.events" in reason for reason in summary["failure_reasons"])


def test_watchdog_kill_restart_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        cycles = i // 12
        s["watchdog"].update(
            unresponsive_kill=cycles,
            killed_wechat=cycles,
            process_disappeared=cycles,
            spawned_wechat=cycles,
        )

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert summary["watchdog"]["killed_wechat"]["delta"] == 5
    assert summary["watchdog"]["kill_delta"] == 15  # unresponsive + killed + disappeared each +5
    assert summary["watchdog"]["restart_delta"] == 5
    assert any("health-monitor" in reason for reason in summary["failure_reasons"])


def test_pthread_eagain_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i >= 30:
            s["watchdog"]["pthread_create_eagain"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("EAGAIN" in reason for reason in summary["failure_reasons"])


def test_thread_constructor_failure_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i >= 30:
            s["watchdog"]["thread_constructor_failed"] = 2

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("thread constructor failed" in reason for reason in summary["failure_reasons"])


def test_oom_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i >= 30:
            s["memory"]["events_oom"] = 2
            s["memory"]["events_oom_kill"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("oom_kill" in reason for reason in summary["failure_reasons"])


def test_docker_oom_killed_flag_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 30:
            s["container"]["docker_oom_killed"] = True

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("OOMKilled" in reason for reason in summary["failure_reasons"])


def test_zombie_accumulation_fails(tmp_path: Path) -> None:
    samples = make_run(count=40, mutate=lambda i, s: s["tasks"].update(zombie_count=i // 10))
    summary = summarize(tmp_path, samples)
    assert summary["outcome"] == "FAIL"
    assert any("zombie" in reason for reason in summary["failure_reasons"])
    assert summary["zombies"]["baseline"] == 0
    assert summary["zombies"]["end"] == 3


def test_single_transient_zombie_is_only_a_warning(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 10:
            s["tasks"]["zombie_count"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert summary["zombies"]["maximum"] == 1


def test_pids_limit_mismatch_fails(tmp_path: Path) -> None:
    summary = summarize(tmp_path, make_run(pids_max=256, host_pids_limit=256))
    assert summary["outcome"] == "FAIL"
    assert any("256" in reason for reason in summary["failure_reasons"])


def test_unbounded_pids_limit_fails(tmp_path: Path) -> None:
    summary = summarize(tmp_path, make_run(pids_max="max", host_pids_limit=None))
    assert summary["outcome"] == "FAIL"
    assert any("unbounded" in reason for reason in summary["failure_reasons"])


def test_peak_reaching_limit_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 30:
            s["pids"]["current"] = 512

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("reached the configured limit" in reason for reason in summary["failure_reasons"])


def test_peak_near_limit_is_only_a_warning(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 30:
            s["pids"]["current"] = 480

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert any("480" in warning for warning in summary["warnings"])


def test_short_duration_is_incomplete(tmp_path: Path) -> None:
    samples = make_run(count=5)
    summary = summarize(tmp_path, samples)
    assert summary["outcome"] == "INCOMPLETE"
    assert any("below the required" in reason for reason in summary["incomplete_reasons"])


def test_pregate_window_passes_with_lowered_minimum(tmp_path: Path) -> None:
    samples = make_run(count=11)
    summary = summarize(tmp_path, samples, "--minimum-duration", "300")
    assert summary["outcome"] == "PASS-CANDIDATE"


def test_proc_race_is_incomplete_by_default(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 20:
            s["tasks"]["proc_race_count"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "INCOMPLETE"
    assert any("/proc" in reason for reason in summary["incomplete_reasons"])


def test_proc_race_within_tolerance_passes(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 20:
            s["tasks"]["proc_race_count"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate), "--max-proc-races", "1")
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert summary["proc_races_total"] == 1


def scatter_races(i: int, s: dict) -> None:
    """8 transient vanish-type races in 8 distinct samples (within the 8
    tolerance): the empirical pattern of the R5 baseline and final canary."""
    if i in (4, 12, 20, 28, 36, 44, 52, 58):
        s["tasks"]["proc_race_count"] = 1


def summarize_with_races(tmp_path: Path, extra_mutate, *extra_args: str) -> dict:
    def mutate(i: int, s: dict) -> None:
        scatter_races(i, s)
        extra_mutate(i, s)

    return summarize(tmp_path, make_run(mutate=mutate), *extra_args)


def test_races_within_tolerance_cannot_mask_eagain(tmp_path: Path) -> None:
    def eagain(i: int, s: dict) -> None:
        if i >= 30:
            s["watchdog"]["pthread_create_eagain"] = 1

    summary = summarize_with_races(tmp_path, eagain, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("EAGAIN" in reason for reason in summary["failure_reasons"])


def test_races_within_tolerance_cannot_mask_pids_events(tmp_path: Path) -> None:
    def fork_rejects(i: int, s: dict) -> None:
        if i >= 10:
            s["pids"]["events_max_hit"] = 2

    summary = summarize_with_races(tmp_path, fork_rejects, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("pids.events" in reason for reason in summary["failure_reasons"])


def test_races_within_tolerance_cannot_mask_oom(tmp_path: Path) -> None:
    def oom(i: int, s: dict) -> None:
        if i >= 30:
            s["memory"]["events_oom_kill"] = 1

    summary = summarize_with_races(tmp_path, oom, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("oom_kill" in reason for reason in summary["failure_reasons"])


def test_races_within_tolerance_cannot_mask_watchdog_restart(tmp_path: Path) -> None:
    def restart(i: int, s: dict) -> None:
        if i >= 30:
            s["watchdog"]["spawned_wechat"] = 1

    summary = summarize_with_races(tmp_path, restart, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("restart" in reason for reason in summary["failure_reasons"])


def test_races_within_tolerance_cannot_mask_monotonic_thread_growth(tmp_path: Path) -> None:
    def growth(i: int, s: dict) -> None:
        s["tasks"]["grand_total"]["threads"] = 280 + i

    summary = summarize_with_races(tmp_path, growth, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("monotonic growth" in reason for reason in summary["failure_reasons"])


def test_races_within_tolerance_cannot_mask_zombie_accumulation(tmp_path: Path) -> None:
    def zombies(i: int, s: dict) -> None:
        s["tasks"]["zombie_count"] = i // 10

    summary = summarize_with_races(tmp_path, zombies, "--max-proc-races", "8")
    assert summary["outcome"] == "FAIL"
    assert any("zombie" in reason for reason in summary["failure_reasons"])


def test_proc_race_policy_block_records_tolerance_and_distribution(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        scatter_races(i, s)
        if i == 44:
            s["tasks"]["proc_race_count"] = 2  # one sample carries a second race

    summary = summarize(tmp_path, make_run(mutate=mutate), "--max-proc-races", "9")
    assert summary["outcome"] == "PASS-CANDIDATE"
    policy = summary["proc_race_policy"]
    assert policy["max_proc_races"] == 9
    assert policy["races_total"] == 9
    assert policy["samples_with_races"] == 8
    assert policy["max_races_in_single_sample"] == 2
    assert policy["read_errors_total"] == 0
    assert policy["race_recheck_available"] is True
    assert policy["recheck_note"] == ""
    assert "never tolerated" in policy["definition"]


def test_read_errors_are_never_tolerated_even_within_race_tolerance(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        scatter_races(i, s)
        if i == 20:
            s["tasks"]["proc_read_error_count"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate), "--max-proc-races", "8")
    assert summary["outcome"] == "INCOMPLETE"
    assert any("persistent /proc read error" in reason for reason in summary["incomplete_reasons"])
    assert summary["proc_race_policy"]["read_errors_total"] == 1


def test_legacy_evidence_without_recheck_field_is_flagged_not_failed(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        del s["tasks"]["proc_read_error_count"]  # pre-recheck sampler schema
        if i == 20:
            s["tasks"]["proc_race_count"] = 1

    summary = summarize(tmp_path, make_run(mutate=mutate), "--max-proc-races", "1")
    assert summary["outcome"] == "PASS-CANDIDATE"
    policy = summary["proc_race_policy"]
    assert policy["race_recheck_available"] is False
    assert "recheck" in policy["recheck_note"]


def test_auth_never_sampled_is_incomplete(tmp_path: Path) -> None:
    summary = summarize(tmp_path, make_run(status_url=None, auth_reported=None))
    assert summary["outcome"] == "INCOMPLETE"
    assert any("--status-url" in reason for reason in summary["incomplete_reasons"])


def test_auth_logged_out_mid_run_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i == 40:
            s["auth"]["reported_auth_status"] = {
                "http_ok": True,
                "status": "logged_out",
                "view": "Login",
                "logged_in": False,
            }

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("logged_in/Chat" in reason for reason in summary["failure_reasons"])


def test_stale_persisted_context_is_flagged_as_warning_not_ui_truth(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        s["auth"]["reported_auth_status"]["main_window"] = None

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert any("main_window" in warning for warning in summary["warnings"])
    assert summary["auth"]["current_ui_observation"] == "unknown"


def test_component_series_reported(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        s["tasks"]["components"]["wechatappex"]["threads"] = 60 + i
        s["tasks"]["grand_total"]["threads"] = 280 + i

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    wechatappex = summary["components"]["wechatappex"]
    assert wechatappex["baseline"] == 60
    assert wechatappex["end"] == 120
    assert summary["components"]["grand_total"]["maximum"] == 340


def test_missing_required_field_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.jsonl"
    samples = make_run(count=3)
    del samples[1]["pids"]
    write_jsonl(input_path, samples)
    result = run_summarizer(input_path)
    assert result.returncode == 2
    assert "pids" in result.stderr


def test_wrong_schema_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.jsonl"
    sample = make_run(count=2)[0]
    sample["schema"] = "some.other.schema/v9"
    write_jsonl(input_path, [sample])
    result = run_summarizer(input_path)
    assert result.returncode == 2


def test_empty_input_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.jsonl"
    input_path.write_text("", encoding="utf-8")
    result = run_summarizer(input_path)
    assert result.returncode == 2


@pytest.mark.parametrize("flag", ["--minimum-duration", "--minimum-samples", "--pids-headroom-warn-frac"])
def test_invalid_arguments_are_rejected(tmp_path: Path, flag: str) -> None:
    input_path = tmp_path / "evidence.jsonl"
    write_jsonl(input_path, make_run(count=3))
    bad = {"--minimum-duration": "-5", "--minimum-samples": "0", "--pids-headroom-warn-frac": "1.5"}[flag]
    result = run_summarizer(input_path, flag, bad)
    assert result.returncode == 2


def test_matching_expected_digests_and_wxid_passes(tmp_path: Path) -> None:
    samples = make_run(
        container_repo_digest="ghcr.io/onestao/wechat-hub-agent-wechat@sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd",
        runtime={
            "id": "runtime-1",
            "state": "running",
            "repo_digest": "ghcr.io/onestao/wechat-hub-runtime@sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116",
        },
        logged_in_user="wxid_rpfflqttdz4a22_7fcd",
    )
    summary = summarize(
        tmp_path,
        samples,
        "--expected-agent-wechat-digest",
        "sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd",
        "--expected-runtime-digest",
        "sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116",
        "--expected-wxid",
        "wxid_rpfflqttdz4a22_7fcd",
    )
    assert summary["outcome"] == "PASS-CANDIDATE"
    assert summary["identity"]["expected_wxid"] == "wxid_rpfflqttdz4a22_7fcd"
    assert summary["auth"]["expected_wxid_matched"] is True


def test_mismatched_agent_wechat_child_digest_fails(tmp_path: Path) -> None:
    samples = make_run(
        container_repo_digest="ghcr.io/onestao/wechat-hub-agent-wechat@sha256:wrongchilddigest",
    )
    summary = summarize(
        tmp_path,
        samples,
        "--expected-agent-wechat-digest",
        "sha256:53bff2ad969beea93107f54015978f66caa9e8dac0609851870f5eeeeabb1ddd",
    )
    assert summary["outcome"] == "FAIL"
    assert any("AgentWechat child image/digest" in r for r in summary["failure_reasons"])


def test_mismatched_runtime_digest_fails(tmp_path: Path) -> None:
    samples = make_run(
        runtime={
            "id": "runtime-1",
            "state": "running",
            "repo_digest": "ghcr.io/onestao/wechat-hub-runtime@sha256:wrongruntimedigest",
        }
    )
    summary = summarize(
        tmp_path,
        samples,
        "--expected-runtime-digest",
        "sha256:3d0bc2cfc13a0748d08c32efc0c9040dd43a2b4080cb6a82c8bce151cca52116",
    )
    assert summary["outcome"] == "FAIL"
    assert any("Runtime image/digest" in r for r in summary["failure_reasons"])


def test_mismatched_authoritative_wxid_fails(tmp_path: Path) -> None:
    samples = make_run(logged_in_user="wxid_other_account")
    summary = summarize(
        tmp_path,
        samples,
        "--expected-wxid",
        "wxid_rpfflqttdz4a22_7fcd",
    )
    assert summary["outcome"] == "FAIL"
    assert any("authoritative wxid" in r for r in summary["failure_reasons"])


def test_degraded_or_unknown_auth_fails_and_rejects_stale_login_proof(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i >= 30:
            s["auth"]["reported_auth_status"]["status"] = "unknown"
            s["auth"]["reported_auth_status"]["logged_in_user"] = "wxid_rpfflqttdz4a22_7fcd"

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("stale logged_in_user" in r for r in summary["failure_reasons"])


def test_failed_status_endpoint_probe_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        if i >= 50:
            s["auth"]["reported_auth_status"] = {"http_ok": False, "error": "connection refused"}

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("auth status endpoint probe failed" in r for r in summary["failure_reasons"])


def test_monotonic_process_growth_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        s["tasks"]["grand_total"]["processes"] = 40 + i

    summary = summarize(tmp_path, make_run(mutate=mutate))
    assert summary["outcome"] == "FAIL"
    assert any("unreaped subprocess accumulation" in r for r in summary["failure_reasons"])


def test_net_process_growth_exceeding_tolerance_fails(tmp_path: Path) -> None:
    def mutate(i: int, s: dict) -> None:
        s["tasks"]["grand_total"]["processes"] = 40 + (i % 3) + (5 if i >= 55 else 0)

    summary = summarize(tmp_path, make_run(mutate=mutate), "--fail-proc-growth", "2")
    assert summary["outcome"] == "FAIL"
    assert any("process count grew from" in r for r in summary["failure_reasons"])
