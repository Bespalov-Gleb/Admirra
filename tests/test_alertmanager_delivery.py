import datetime as dt

import pytest

from ops.monitoring.alertmanager_delivery_smoke import deliver


def test_delivery_submits_bounded_firing_and_resolved_pair():
    calls = []
    sleeps = []
    moments = iter([
        dt.datetime(2026, 9, 20, 15, 0, tzinfo=dt.timezone.utc),
        dt.datetime(2026, 9, 20, 15, 0, 45, tzinfo=dt.timezone.utc),
    ])

    deliver(
        "http://127.0.0.1:9093/api/v2/alerts",
        45,
        3.0,
        send=lambda *args: calls.append(args),
        sleep=lambda seconds: sleeps.append(seconds),
        clock=lambda: next(moments),
    )

    assert sleeps == [45]
    assert len(calls) == 2
    firing = calls[0][1][0]
    resolved = calls[1][1][0]
    assert firing["labels"] == {
        "alertname": "AdMirraDeliveryTest",
        "severity": "warning",
        "environment": "production-test",
    }
    assert firing["endsAt"] == "2026-09-20T15:10:00+00:00"
    assert resolved["endsAt"] == "2026-09-20T15:00:45+00:00"
    assert calls[0][0] == calls[1][0]
    assert calls[0][2] == calls[1][2] == 3.0


@pytest.mark.parametrize("hold", [0, 29, 301, 3600])
def test_delivery_rejects_unbounded_hold(hold):
    with pytest.raises(ValueError, match="between 30 and 300"):
        deliver("http://127.0.0.1", hold, 1, send=lambda *_: None, sleep=lambda *_: None)


def test_delivery_rejects_naive_clock():
    with pytest.raises(ValueError, match="timezone-aware"):
        deliver(
            "http://127.0.0.1",
            30,
            1,
            send=lambda *_: None,
            sleep=lambda *_: None,
            clock=lambda: dt.datetime(2026, 9, 20, 15, 0),
        )
