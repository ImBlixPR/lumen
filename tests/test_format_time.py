from lumen.app import format_time


def test_minutes_and_hours():
    assert format_time(0) == "0:00"
    assert format_time(65.9) == "1:05"
    assert format_time(3723) == "1:02:03"


def test_invalid_values_never_raise():
    assert format_time(float("nan")) == "0:00"
    assert format_time(float("inf")) == "0:00"
    assert format_time(-5) == "0:00"
