from collections import OrderedDict

from crpm.observability import build_cache_telemetry


def test_build_cache_telemetry_reports_sizes_limits_and_runtime() -> None:
    telemetry = build_cache_telemetry(
        caches={
            "filtered_cache": OrderedDict([("a", object()), ("b", object())]),
            "dfg_cache": OrderedDict(),
        },
        cache_limits={"filtered_cache": 8, "dfg_cache": 8},
        stage_timings={"filtering_s": 0.1, "discovery_s": 0.2},
    )

    assert telemetry["summary"]["cache_count"] == 2
    assert telemetry["summary"]["total_entries"] == 2
    assert telemetry["summary"]["total_capacity"] == 16
    assert telemetry["summary"]["runtime_s"] == 0.3
    assert telemetry["summary"]["utilization_pct"] == 12.5
    assert telemetry["caches"][0] == {
        "name": "filtered_cache",
        "entries": 2,
        "limit": 8,
        "utilization_pct": 25.0,
    }
    assert telemetry["stage_timings_s"] == {"discovery_s": 0.2, "filtering_s": 0.1}


def test_build_cache_telemetry_is_safe_for_missing_or_zero_limits() -> None:
    telemetry = build_cache_telemetry(
        caches={"unknown": OrderedDict([("x", object())])},
        cache_limits={},
        stage_timings={"bad": "not-a-number"},
    )

    assert telemetry["summary"]["total_capacity"] == 0
    assert telemetry["summary"]["utilization_pct"] == 0.0
    assert telemetry["caches"][0]["name"] == "unknown"
    assert telemetry["caches"][0]["limit"] == 0
    assert telemetry["caches"][0]["utilization_pct"] == 0.0
    assert telemetry["stage_timings_s"] == {}
