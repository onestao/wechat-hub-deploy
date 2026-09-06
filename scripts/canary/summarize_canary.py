#!/usr/bin/env python3
"""Summarize host-side WeChat Hub canary JSONL evidence into a verdict.

Reads JSONL produced by scripts/canary/wechat_cgroup_sample.sh (via
wechat_canary_run.sh), computes baseline/peak/end statistics and window
deltas, and classifies the run as PASS-CANDIDATE, FAIL, or INCOMPLETE.

The classification maps 1:1 onto the PASS criteria in
docs/P0_RC4_FULL_CHAT_PIDS_CANARY_GATE.md section 6. The verdict is advisory
evidence triage only: it never performs or authorizes promotion.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "wechat-hub.canary.summary/v1"
SAMPLE_SCHEMA_PREFIX = "wechat-hub.canary.sample/"
COMPONENT_KEYS = (
    "wechat",
    "wechatappex",
    "wxplayer",
    "wxocr",
    "crashpad",
    "agent-server",
    "other",
)
WATCHDOG_KILL_KEYS = ("unresponsive_kill", "killed_wechat", "process_disappeared")


def load_samples(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(sample, dict):
                raise ValueError(f"line {line_number}: sample must be a JSON object")
            schema = sample.get("schema")
            if not isinstance(schema, str) or not schema.startswith(SAMPLE_SCHEMA_PREFIX):
                raise ValueError(
                    f"line {line_number}: unexpected schema {schema!r}; expected {SAMPLE_SCHEMA_PREFIX}<version>"
                )
            for required in ("timestamp", "container", "pids", "memory", "tasks", "watchdog", "auth"):
                if required not in sample:
                    raise ValueError(f"line {line_number}: sample is missing required field {required!r}")
            samples.append(sample)
    if not samples:
        raise ValueError("input contains no samples")
    return samples


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("sample timestamp must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def series(values: list[int]) -> dict[str, int | float]:
    return {
        "baseline": values[0],
        "minimum": min(values),
        "maximum": max(values),
        "end": values[-1],
        "mean": round(statistics.fmean(values), 3),
    }


def endpoint(first: int, last: int) -> dict[str, int]:
    return {"baseline": first, "end": last, "delta": last - first}


def delta_of(first: dict[str, Any], last: dict[str, Any], *keys: str) -> int:
    node: Any = first
    other: Any = last
    for key in keys:
        node = node.get(key, 0) if isinstance(node, dict) else 0
        other = other.get(key, 0) if isinstance(other, dict) else 0
    try:
        return int(other) - int(node)
    except (TypeError, ValueError):
        return 0


def is_monotonic_growth(values: list[int]) -> bool:
    return len(values) >= 3 and values[-1] > values[0] and all(
        later >= earlier for earlier, later in zip(values, values[1:])
    )


def numeric_pids_max(sample: dict[str, Any]) -> int | None:
    value = sample["pids"].get("max")
    if isinstance(value, int) and value > 0:
        return value
    return None


def auth_status_fields(sample: dict[str, Any]) -> dict[str, Any]:
    reported = sample["auth"].get("reported_auth_status")
    if not isinstance(reported, dict) or not reported.get("http_ok"):
        return {}
    return reported


def summarize(
    samples: list[dict[str, Any]],
    minimum_duration: int,
    minimum_samples: int,
    expected_pids_limit: int,
    max_proc_races: int,
    fail_zombie_growth: int,
    fail_zombie_max: int,
    pids_headroom_warn_frac: float,
    fail_proc_growth: int = 2,
    expected_agent_wechat_digest: str | None = None,
    expected_runtime_digest: str | None = None,
    expected_wxid: str | None = None,
) -> dict[str, Any]:
    first, last = samples[0], samples[-1]
    start = parse_timestamp(first["timestamp"])
    end = parse_timestamp(last["timestamp"])
    duration_seconds = max(0, int((end - start).total_seconds()))

    pids_current = [int(s["pids"]["current"]) for s in samples]
    grand_threads = [int(s["tasks"]["grand_total"]["threads"]) for s in samples]
    grand_procs = [int(s["tasks"]["grand_total"]["processes"]) for s in samples]
    zombies = [int(s["tasks"]["zombie_count"]) for s in samples]
    proc_races = [int(s["tasks"]["proc_race_count"]) for s in samples]
    # Evidence produced before the vanish/read-error recheck policy has no
    # proc_read_error_count field; treat those samples as 0 (no gate) but
    # flag the policy block as lacking recheck information.
    proc_read_errors = [int(s["tasks"].get("proc_read_error_count", 0)) for s in samples]
    race_recheck_available = all("proc_read_error_count" in s["tasks"] for s in samples)
    memory_current = [int(s["memory"]["current_bytes"]) for s in samples]

    pids_max_observed = sorted({str(s["pids"].get("max")) for s in samples}, key=str)
    host_limits = sorted(
        {
            s["container"].get("host_config_pids_limit")
            for s in samples
            if isinstance(s["container"].get("host_config_pids_limit"), int)
        }
    )
    numeric_max = [value for value in (numeric_pids_max(s) for s in samples) if value is not None]

    failure_reasons: list[str] = []
    warnings: list[str] = []

    # Gate criterion 1: PidsLimit == expected throughout (never unbounded).
    if "max" in pids_max_observed:
        failure_reasons.append("pids.max is unbounded (cgroup 'max'); PidsLimit must be a hard numeric cap")
    bad_limits = sorted(value for value in pids_max_observed if value != "max" and int(value) != expected_pids_limit)
    if bad_limits:
        failure_reasons.append(
            f"observed pids.max values {bad_limits} do not match the expected policy limit {expected_pids_limit}"
        )
    bad_host_limits = [value for value in host_limits if value <= 0 or value != expected_pids_limit]
    if bad_host_limits:
        failure_reasons.append(
            f"observed HostConfig.PidsLimit values {bad_host_limits} do not match the expected policy limit {expected_pids_limit}"
        )

    # Gate criterion 2: pids.events (fork rejections) delta == 0.
    pids_events = endpoint(
        int(first["pids"].get("events_max_hit", 0)), int(last["pids"].get("events_max_hit", 0))
    )
    if pids_events["delta"] > 0:
        failure_reasons.append(f"pids.events max delta == {pids_events['delta']} (cgroup pids limit was hit)")

    # Gate criteria 3+4: zero pthread_create EAGAIN / thread constructor failures.
    eagain_delta = delta_of(first["watchdog"], last["watchdog"], "pthread_create_eagain")
    ctor_delta = delta_of(first["watchdog"], last["watchdog"], "thread_constructor_failed")
    if eagain_delta > 0:
        failure_reasons.append(f"pthread_create EAGAIN count increased by {eagain_delta}")
    if ctor_delta > 0:
        failure_reasons.append(f"thread constructor failed count increased by {ctor_delta}")

    # Gate criterion 5: zero health-monitor kills / restarts.
    watchdog_endpoints = {
        key: endpoint(
            int(first["watchdog"].get(key, 0)),
            int(last["watchdog"].get(key, 0)),
        )
        for key in ("unresponsive_kill", "killed_wechat", "process_disappeared", "spawned_wechat")
    }
    kill_delta = sum(watchdog_endpoints[key]["delta"] for key in WATCHDOG_KILL_KEYS)
    restart_delta = watchdog_endpoints["spawned_wechat"]["delta"]
    if kill_delta > 0:
        failure_reasons.append(
            f"health-monitor kill counter delta == {kill_delta} "
            + ", ".join(f"{key}+{watchdog_endpoints[key]['delta']}" for key in WATCHDOG_KILL_KEYS if watchdog_endpoints[key]["delta"] > 0)
        )
    if restart_delta > 0:
        failure_reasons.append(f"health-monitor restart (Spawned WeChat) delta == {restart_delta}")

    # Gate criterion 9: no OOM.
    oom = endpoint(int(first["memory"].get("events_oom", 0)), int(last["memory"].get("events_oom", 0)))
    oom_kill = endpoint(int(first["memory"].get("events_oom_kill", 0)), int(last["memory"].get("events_oom_kill", 0)))
    if oom["delta"] > 0:
        failure_reasons.append(f"memory.events oom delta == {oom['delta']}")
    if oom_kill["delta"] > 0:
        failure_reasons.append(f"memory.events oom_kill delta == {oom_kill['delta']}")
    if any(s["container"].get("docker_oom_killed") for s in samples):
        failure_reasons.append("docker reported State.OOMKilled=true during the window")

    # Gate criterion 7: task counts oscillate without monotonic growth.
    if is_monotonic_growth(pids_current):
        failure_reasons.append("cgroup pids.current shows monotonic growth across the window")
    if is_monotonic_growth(grand_threads):
        failure_reasons.append("aggregated /proc Threads shows monotonic growth across the window")
    if is_monotonic_growth(grand_procs):
        failure_reasons.append("aggregated /proc processes shows monotonic growth across the window (unreaped subprocess accumulation)")

    proc_growth = grand_procs[-1] - grand_procs[0]
    if proc_growth >= fail_proc_growth:
        failure_reasons.append(
            f"process count grew from {grand_procs[0]} to {grand_procs[-1]} across the window (growth {proc_growth} >= tolerance {fail_proc_growth})"
        )

    # Gate criterion: AgentWechat child image digest matches expected.
    observed_agent_wechat_digests = sorted(
        {
            str(val)
            for s in samples
            for val in (
                s.get("container", {}).get("repo_digest"),
                s.get("container", {}).get("image"),
                s.get("container", {}).get("image_id"),
            )
            if val
        }
    )
    if expected_agent_wechat_digest:
        matched_agent = any(
            expected_agent_wechat_digest in d or d in expected_agent_wechat_digest
            for d in observed_agent_wechat_digests
        )
        if not matched_agent:
            failure_reasons.append(
                f"observed AgentWechat child image/digest(s) {observed_agent_wechat_digests} do not match expected '{expected_agent_wechat_digest}'"
            )

    # Gate criterion: Runtime image digest matches expected.
    observed_runtime_digests = sorted(
        {
            str(val)
            for s in samples
            for val in (
                s.get("runtime", {}).get("repo_digest") if isinstance(s.get("runtime"), dict) else None,
                s.get("runtime", {}).get("image") if isinstance(s.get("runtime"), dict) else None,
                s.get("runtime", {}).get("image_id") if isinstance(s.get("runtime"), dict) else None,
            )
            if val
        }
    )
    if expected_runtime_digest:
        matched_runtime = any(
            expected_runtime_digest in d or d in expected_runtime_digest
            for d in observed_runtime_digests
        )
        if not matched_runtime:
            failure_reasons.append(
                f"observed Runtime image/digest(s) {observed_runtime_digests} do not match expected '{expected_runtime_digest}'"
            )

    peak_pids = max(pids_current)
    limit_for_peak = min(numeric_max) if numeric_max else None
    if limit_for_peak is not None and peak_pids >= limit_for_peak:
        failure_reasons.append(f"pids.current peak {peak_pids} reached the configured limit {limit_for_peak}")
    elif limit_for_peak is not None and peak_pids >= pids_headroom_warn_frac * limit_for_peak:
        warnings.append(
            f"pids.current peak {peak_pids} reached {peak_pids / limit_for_peak:.0%} of the {limit_for_peak} limit"
        )

    # Gate criterion 8: no accumulating zombies / dead generations.
    zombie_stats = series(zombies)
    if zombies[-1] - zombies[0] >= fail_zombie_growth:
        failure_reasons.append(
            f"zombie count grew from {zombies[0]} to {zombies[-1]} (accumulating dead generations)"
        )
    if max(zombies) >= fail_zombie_max:
        failure_reasons.append(f"zombie count peak {max(zombies)} reached the accumulation threshold {fail_zombie_max}")

    # Gate criterion 6: upstream auth stays logged_in (reported status only).
    auth_probes = [
        s["auth"].get("reported_auth_status")
        for s in samples
        if isinstance(s.get("auth", {}).get("reported_auth_status"), dict)
    ]
    bad_http_probes = [p for p in auth_probes if not p.get("http_ok")]
    if bad_http_probes:
        errors = sorted({str(p.get("error", "unknown error")) for p in bad_http_probes})
        failure_reasons.append(
            f"auth status endpoint probe failed in {len(bad_http_probes)} sample(s): {errors}"
        )

    auth_observed = [p for p in auth_probes if p.get("http_ok")]
    statuses_seen = sorted({str(entry.get("status")) for entry in auth_observed if entry.get("status") is not None})
    views_seen = sorted({str(entry.get("view")) for entry in auth_observed if entry.get("view") is not None})
    users_seen = sorted({str(entry.get("logged_in_user")) for entry in auth_observed if entry.get("logged_in_user") is not None})

    all_logged_in: bool | None = None
    if auth_observed:
        all_logged_in = all(
            entry.get("status") == "logged_in"
            and (entry.get("logged_in") is not False)
            and (entry.get("view") in (None, "Chat"))
            for entry in auth_observed
        )
        if not all_logged_in:
            failure_reasons.append(
                "reported auth left logged_in/Chat during the window "
                f"(statuses seen: {statuses_seen}, views seen: {views_seen})"
            )

        # Flag degraded/unknown states explicitly and prohibit treating stale logged_in_user as fresh proof
        degraded_or_unknown = [
            e for e in auth_observed
            if str(e.get("status")).lower() in ("unknown", "degraded", "logged_out", "app_not_running")
        ]
        if degraded_or_unknown:
            bad_statuses = sorted({str(e.get("status")) for e in degraded_or_unknown})
            stale_users = sorted({str(e.get("logged_in_user")) for e in degraded_or_unknown if e.get("logged_in_user")})
            msg = f"auth status reported as non-logged_in {bad_statuses} during the window"
            if stale_users:
                msg += f"; stale logged_in_user {stale_users} is not fresh login proof"
            if msg not in failure_reasons:
                failure_reasons.append(msg)

        if expected_wxid:
            if not users_seen:
                failure_reasons.append(
                    f"expected authoritative wxid '{expected_wxid}', but logged_in_user was never observed"
                )
            elif any(u != expected_wxid for u in users_seen):
                failure_reasons.append(
                    f"observed logged_in_user {users_seen} does not match expected authoritative wxid '{expected_wxid}'"
                )

        if all(entry.get("main_window") in (None, "") for entry in auth_observed):
            warnings.append(
                "reported logged_in with identified.main_window unset matches the RC.4 persisted-FSM-context "
                "staleness signature; reported auth is not proof of the current Chat UI"
            )

    incomplete_reasons: list[str] = []
    if duration_seconds < minimum_duration:
        incomplete_reasons.append(f"duration {duration_seconds}s is below the required {minimum_duration}s")
    if len(samples) < minimum_samples:
        incomplete_reasons.append(f"only {len(samples)} sample(s); at least {minimum_samples} are required")
    races_total = sum(proc_races)
    read_errors_total = sum(proc_read_errors)
    if read_errors_total > 0:
        incomplete_reasons.append(
            f"{read_errors_total} persistent /proc read error(s) (pid still present but unreadable "
            "after an immediate retry); task attribution is unexplained and the proc-race "
            "tolerance never covers read errors — inspect the host before trusting this evidence"
        )
    if races_total > max_proc_races:
        incomplete_reasons.append(
            f"{races_total} transient /proc read races exceeded the explicit tolerance {max_proc_races}; "
            "task-thread attribution is incomplete"
        )
    if not auth_observed:
        incomplete_reasons.append(
            "auth was never sampled via --status-url; gate criterion 6 (view=Chat, status=logged_in) is unverifiable"
        )

    component_stats = {
        key: series([int(s["tasks"]["components"].get(key, {}).get("threads", 0)) for s in samples])
        for key in COMPONENT_KEYS
    }
    component_stats["grand_total"] = series(grand_threads)

    if failure_reasons:
        outcome = "FAIL"
    elif incomplete_reasons:
        outcome = "INCOMPLETE"
    else:
        outcome = "PASS-CANDIDATE"

    return {
        "schema": SCHEMA,
        "outcome": outcome,
        "advisory": "Advisory evidence triage only: this tool never performs or authorizes promotion.",
        "promotion_performed": False,
        "input_samples": len(samples),
        "start_timestamp": first["timestamp"],
        "end_timestamp": last["timestamp"],
        "duration_seconds": duration_seconds,
        "minimum_duration_seconds": minimum_duration,
        "pids": {
            "current": series(pids_current),
            "max_observed": pids_max_observed,
            "expected_limit": expected_pids_limit,
            "host_config_pids_limit_observed": host_limits,
            "events_max_hit": pids_events,
        },
        "memory": {
            "current_bytes": series(memory_current),
            "events_oom": oom,
            "events_oom_kill": oom_kill,
        },
        "watchdog": {**watchdog_endpoints, "kill_delta": kill_delta, "restart_delta": restart_delta},
        "eagain": {
            "pthread_create_eagain_delta": eagain_delta,
            "thread_constructor_failed_delta": ctor_delta,
        },
        "identity": {
            "expected_agent_wechat_digest": expected_agent_wechat_digest,
            "observed_agent_wechat_digests": observed_agent_wechat_digests,
            "expected_runtime_digest": expected_runtime_digest,
            "observed_runtime_digests": observed_runtime_digests,
            "expected_wxid": expected_wxid,
            "observed_wxids": users_seen,
        },
        "zombies": zombie_stats,
        "processes": series(grand_procs),
        "process_growth": {
            "baseline": grand_procs[0],
            "end": grand_procs[-1],
            "delta": proc_growth,
        },
        "components": component_stats,
        "task_reconciliation": {
            "pids_current_end": pids_current[-1],
            "grand_total_threads_end": grand_threads[-1],
            "delta": grand_threads[-1] - pids_current[-1],
        },
        "auth": {
            "sampled": bool(auth_observed),
            "statuses_seen": statuses_seen,
            "views_seen": views_seen,
            "users_seen": users_seen,
            "all_reported_logged_in": all_logged_in,
            "expected_wxid_matched": (
                all(u == expected_wxid for u in users_seen) if (expected_wxid and users_seen) else None
            ),
            "current_ui_observation": "unknown",
            "freshness_note": (
                "reported_auth_status comes from the persisted FSM context and is not proof of the "
                "current Chat UI (see docs/P0_RC4_FULL_CHAT_PIDS_CANARY_ERRATA.md section 2.3)"
            ),
        },
        "proc_races_total": races_total,
        "proc_race_policy": {
            "definition": (
                "A tolerated race is a /proc/<pid> read failure where the pid directory no longer "
                "exists (natural exit during the sampling sweep) or a torn read that succeeds on an "
                "immediate retry. Pids that remain present but persistently unreadable are counted "
                "separately as read errors and are never tolerated. Races cannot mask real failure "
                "signals: EAGAIN, thread constructor failures, OOM, pids.events, watchdog kill/"
                "restart, monotonic task growth, zombie accumulation, pids.current peak-at-limit, "
                "auth continuity, and digest/wxid identity are independent FAIL criteria that take "
                "precedence over this tolerance."
            ),
            "max_proc_races": max_proc_races,
            "races_total": races_total,
            "samples_with_races": sum(1 for value in proc_races if value > 0),
            "max_races_in_single_sample": max(proc_races) if proc_races else 0,
            "read_errors_total": read_errors_total,
            "race_recheck_available": race_recheck_available,
            "recheck_note": (
                ""
                if race_recheck_available
                else "Evidence predates the vanish/read-error recheck policy (no "
                "proc_read_error_count field): vanish races could not be distinguished from "
                "persistent read failures in this input."
            ),
        },
        "warnings": warnings,
        "failure_reasons": failure_reasons,
        "incomplete_reasons": incomplete_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSONL sample file from wechat_canary_run.sh")
    parser.add_argument("--minimum-duration", type=int, default=1800,
                        help="required window length in seconds (canary default 1800; use 21600 for H2)")
    parser.add_argument("--minimum-samples", type=int, default=2)
    parser.add_argument("--expected-pids-limit", type=int, default=512,
                        help="policy PidsLimit the candidate must run with (RC.5: 512)")
    parser.add_argument("--max-proc-races", type=int, default=0,
                        help="explicit tolerance for total vanish-type /proc read races before the run "
                             "is marked INCOMPLETE (default 0 = strict). Never mask real failures: "
                             "approved baseline is 8 races per 60-sample 30-min window, linearly "
                             "scaled by sample count (e.g. 48 for the 360-sample 6h H2 window); the "
                             "chosen value is recorded in the summary's proc_race_policy block")
    parser.add_argument("--fail-zombie-growth", type=int, default=1)
    parser.add_argument("--fail-zombie-max", type=int, default=25)
    parser.add_argument("--fail-proc-growth", type=int, default=2,
                        help="tolerated net process growth across the window (default 2)")
    parser.add_argument("--expected-agent-wechat-digest", type=str, default=None,
                        help="expected digest or image ref for the agent-wechat child container")
    parser.add_argument("--expected-runtime-digest", type=str, default=None,
                        help="expected digest or image ref for the runtime container")
    parser.add_argument("--expected-wxid", type=str, default=None,
                        help="expected authoritative wxid (e.g. wxid_rpfflqttdz4a22_7fcd)")
    parser.add_argument("--pids-headroom-warn-frac", type=float, default=0.9)
    parser.add_argument("--output", type=Path, help="write the summary JSON here instead of stdout")
    args = parser.parse_args()

    if args.minimum_duration < 0:
        parser.error("--minimum-duration must not be negative")
    if args.minimum_samples < 1:
        parser.error("--minimum-samples must not be less than 1")
    if args.max_proc_races < 0:
        parser.error("--max-proc-races must not be negative")
    if not 0 < args.pids_headroom_warn_frac <= 1:
        parser.error("--pids-headroom-warn-frac must be in (0, 1]")

    try:
        summary = summarize(
            load_samples(args.input),
            minimum_duration=args.minimum_duration,
            minimum_samples=args.minimum_samples,
            expected_pids_limit=args.expected_pids_limit,
            max_proc_races=args.max_proc_races,
            fail_zombie_growth=args.fail_zombie_growth,
            fail_zombie_max=args.fail_zombie_max,
            pids_headroom_warn_frac=args.pids_headroom_warn_frac,
            fail_proc_growth=args.fail_proc_growth,
            expected_agent_wechat_digest=args.expected_agent_wechat_digest,
            expected_runtime_digest=args.expected_runtime_digest,
            expected_wxid=args.expected_wxid,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
