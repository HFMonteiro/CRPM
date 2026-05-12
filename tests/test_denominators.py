from datetime import datetime

from pm4py.objects.log.obj import EventLog, Trace

from crpm.denominators import build_denominator_registry, build_preprocessing_impact, denominator_rows


def test_denominator_registry_uses_filtered_and_evaluation_logs() -> None:
    trace_a = Trace()
    trace_a.append({"concept:name": "A", "time:timestamp": datetime(2024, 1, 1)})
    trace_a.append({"concept:name": "B", "time:timestamp": datetime(2024, 1, 2)})
    trace_b = Trace()
    trace_b.append({"concept:name": "A", "time:timestamp": datetime(2024, 1, 3)})
    log = EventLog([trace_a, trace_b])

    registry = build_denominator_registry(
        log,
        evaluation_log=EventLog([trace_a]),
        workflow={"summary": {"path_denominator": 1, "activity_denominator": 2, "excluded_case_count": 1}},
    )

    assert registry["case_count"] == 2
    assert registry["event_count"] == 3
    assert registry["evaluation_case_count"] == 1
    assert registry["transition_count"] == 1
    assert registry["path_denominator"] == 1
    assert registry["activity_denominator"] == 2
    assert registry["excluded_case_count"] == 1
    assert any(row["key"] == "path_denominator" for row in denominator_rows(registry))


def test_preprocessing_impact_separates_filter_and_evaluation_exclusions() -> None:
    source = EventLog()
    traces = []
    for index in range(4):
        trace = Trace(attributes={"concept:name": f"case-{index}"})
        trace.append({"concept:name": "A", "time:timestamp": datetime(2024, 1, index + 1)})
        trace.append({"concept:name": "B", "time:timestamp": datetime(2024, 1, index + 2)})
        source.append(trace)
        traces.append(trace)

    filtered = EventLog(traces[:3])
    evaluation = EventLog(traces[:2])

    impact = build_preprocessing_impact(source_log=source, filtered_log=filtered, evaluation_log=evaluation)

    assert impact["source_cases"] == 4
    assert impact["filtered_cases"] == 3
    assert impact["evaluation_cases"] == 2
    assert impact["excluded_by_filter_cases"] == 1
    assert impact["held_out_cases"] == 1
    assert impact["filter_case_retention_pct"] == 75.0
    assert impact["evaluation_case_retention_pct"] == 66.67
