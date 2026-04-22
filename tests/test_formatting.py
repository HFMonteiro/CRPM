from crpm.formatting import format_decimal, format_metric_value


def test_format_decimal_caps_precision_at_three_places() -> None:
    assert format_decimal(1.0) == "1"
    assert format_decimal(0.1234) == "0.123"
    assert format_decimal(12.1) == "12.1"


def test_format_metric_value_uses_compact_human_readable_output() -> None:
    assert format_metric_value(0.98765, kind="score") == "0.988"
    assert format_metric_value(100.0, kind="percent") == "100%"
    assert format_metric_value(12.3456, kind="days") == "12.346 days"
    assert format_metric_value(1000.0, kind="count") == "1,000"
