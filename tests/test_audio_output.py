from lumen.services.player import choose_output


def test_follows_the_system_default_when_a_monitor_is_plugged_in_or_out():
    assert choose_output(b"laptop-speakers", b"hdmi-monitor") == b"hdmi-monitor"
    assert choose_output(b"hdmi-monitor", b"laptop-speakers") == b"laptop-speakers"


def test_stays_put_when_nothing_changed():
    assert choose_output(b"laptop-speakers", b"laptop-speakers") is None


def test_no_default_device_means_stay():
    assert choose_output(b"laptop-speakers", None) is None
    assert choose_output(b"laptop-speakers", b"") is None


def test_binds_to_the_default_at_startup():
    assert choose_output(None, b"laptop-speakers") == b"laptop-speakers"
