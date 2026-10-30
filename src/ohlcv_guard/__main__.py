"""CLI entry point."""
import argparse
import csv
import json
import sys
from pathlib import Path

from .core import check_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check OHLCV CSV integrity")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--interval", help="Expected timeframe, e.g. 15m, 1h, 1d")
    parser.add_argument("--time-column", default="timestamp")
    parser.add_argument("--json", dest="json_path", type=Path,
                        help="Save machine-readable report")
    args = parser.parse_args(argv)
    try:
        report = check_csv(args.csv_path, interval=args.interval,
                           time_column=args.time_column)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print(f"Checked: {report.checked}, valid: {report.valid}, issues: {len(report.findings)}")
    for item in report.findings[:50]:
        print(f"  row {item.row}: [{item.code}] {item.message}")
    if len(report.findings) > 50:
        print(f"  ... and {len(report.findings) - 50} more issues")
    if args.json_path:
        try:
            args.json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"Cannot write report: {exc}", file=sys.stderr)
            return 2
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
