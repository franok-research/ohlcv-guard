import tempfile
import unittest
from pathlib import Path

from ohlcv_guard.core import check_csv, parse_interval, parse_timestamp

HEADER = "timestamp,open,high,low,close,volume\n"


class TestOHLCVGuard(unittest.TestCase):
    def write_rows(self, rows: str) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "candles.csv"
        p.write_text(HEADER + rows, encoding="utf-8")
        return p

    def codes(self, rows: str, interval="15m") -> set[str]:
        report = check_csv(self.write_rows(rows), interval=interval)
        return {x.code for x in report.findings}

    def test_valid_candles(self):
        self.assertEqual(self.codes("2026-01-01T00:00:00Z,10,12,9,11,100\n"
                                    "2026-01-01T00:15:00Z,11,13,10,12,0\n"), set())

    def test_bad_ohlc(self):
        self.assertIn("OHLC_INCONSISTENT", self.codes("2026-01-01T00:00:00Z,10,9,8,11,1\n"))

    def test_gap(self):
        self.assertIn("TIME_GAP", self.codes("2026-01-01T00:00:00Z,10,12,9,11,100\n"
                                               "2026-01-01T00:30:00Z,11,13,10,12,50\n"))

    def test_duplicate(self):
        self.assertIn("DUPLICATE_TIMESTAMP", self.codes("2026-01-01T00:00:00Z,10,12,9,11,100\n"
                                                          "2026-01-01T00:00:00Z,10,12,9,11,100\n"))

    def test_reversed(self):
        self.assertIn("OUT_OF_ORDER", self.codes("2026-01-01T00:15:00Z,10,12,9,11,100\n"
                                              "2026-01-01T00:00:00Z,11,13,10,12,50\n"))

    def test_negative_volume(self):
        self.assertIn("BAD_VALUE", self.codes("2026-01-01T00:00:00Z,10,12,9,11,-2\n"))

    def test_unix_ms_and_seconds_equal(self):
        self.assertEqual(parse_timestamp("1767225600000"), parse_timestamp("1767225600"))

    def test_interval_validation(self):
        with self.assertRaises(ValueError):
            parse_interval("15minutes")

    def test_missing_columns(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "bad.csv"
        p.write_text("timestamp,open,close\n2026-01-01T00:00:00Z,1,2\n")
        with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
            check_csv(p)


if __name__ == "__main__":
    unittest.main()
