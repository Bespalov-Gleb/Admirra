import datetime as dt
import tempfile
import unittest
from pathlib import Path

from ops.api2_canary.check_canary import Result, atomic_write, recent_canary_rows, render_metrics


class Api2CanaryMonitorTest(unittest.TestCase):
    def test_recent_canary_rows_filters_old_entries_and_preserves_failover(self):
        now = dt.datetime.now(dt.timezone.utc)
        old = now - dt.timedelta(hours=1)
        current = now - dt.timedelta(seconds=5)
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "canary.log"
            log.write_text(
                "\n".join(
                    [
                        f"{old.isoformat()} request_id=old method=GET uri=/api/auth/me status=500 upstream=127.0.0.1:8001 upstream_status=500",
                        f"{current.isoformat()} request_id=new method=GET uri=/api/auth/me status=200 upstream=10.77.0.2:8001, 127.0.0.1:8001 upstream_status=502, 200",
                    ]
                ),
                encoding="utf-8",
            )

            rows = list(recent_canary_rows(log, window_seconds=600))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "200")
        self.assertEqual(rows[0]["upstream"], "10.77.0.2:8001,")

    def test_result_prioritizes_critical_over_warning(self):
        result = Result(role="ingress")
        result.check("warning", False, "warning", warning=True)
        result.check("critical", False, "critical")

        self.assertEqual(result.status, "critical")
        self.assertEqual(result.exit_code, 2)

    def test_metrics_are_prometheus_compatible_and_do_not_include_messages(self):
        result = Result(role="api2")
        result.check("api2_ready", True, "")
        result.metrics["disk_free_percent"] = 42.5
        result.warnings.append("sensitive diagnostic must not become a label")

        metrics = render_metrics(result)

        self.assertIn('admirra_api2_monitor_check_ok{role="api2",check="api2_ready"} 1', metrics)
        self.assertIn('admirra_api2_monitor_value{role="api2",name="disk_free_percent"} 42.5', metrics)
        self.assertNotIn("sensitive diagnostic", metrics)

    def test_atomic_write_makes_metrics_world_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "monitor.prom"
            atomic_write(path, "metric 1\n")

            self.assertEqual(path.stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
