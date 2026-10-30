"""Dependency-free CSV OHLCV validation.

This is a data-quality checker, not a trading strategy or proof of no look-ahead.
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CANDLE_FIELDS = ("open", "high", "low", "close", "volume")
INTERVAL_RE = re.compile(r"^([1-9]\d*)(s|m|h|d|w)$")


@dataclass(frozen=True)
class Finding:
    row: int
    code: str
    message: str


@dataclass
class Report:
    file: str
    checked: int
    valid: int
    interval: str | None
    findings: list[Finding]

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "checked": self.checked,
                "valid": self.valid, "interval": self.interval,
                "ok": self.ok, "findings": [asdict(x) for x in self.findings]}


def parse_interval(spec: str) -> timedelta:
    match = INTERVAL_RE.fullmatch(spec)
    if not match:
        raise ValueError("Interval must look like 15m, 1h, or 1d")
    n = int(match.group(1))
    unit = match.group(2)
    seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
    return timedelta(seconds=n * seconds)


def parse_timestamp(raw: str) -> datetime:
    value = raw.strip()
    if not value:
        raise ValueError("empty timestamp")
    # Most exchange exports use epoch milliseconds; an explicit 13+ digit number
    # is interpreted as milliseconds, while a 10-digit number is seconds.
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite timestamp")
        if abs(number) >= 1e11:
            number /= 1000
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError("timestamp out of range") from exc
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO 8601 or epoch seconds/ms") from exc
    if dt.tzinfo is None:
        raise ValueError("ISO timestamp must specify a timezone")
    return dt.astimezone(timezone.utc)


def _positive_number(raw: str, field: str) -> float:
    try:
        value = float(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}")
    if field == "volume":
        if value < 0:
            raise ValueError("negative volume")
    elif value <= 0:
        raise ValueError(f"non-positive {field}")
    return value


def check_csv(path: str | Path, *, interval: str | None = None,
              time_column: str = "timestamp") -> Report:
    source = Path(path)
    step = parse_interval(interval) if interval is not None else None
    findings: list[Finding] = []
    valid = checked = 0
    previous_time: datetime | None = None
    # Detect non-adjacent duplicate timestamps as well as consecutive duplicates.
    seen: set[datetime] = set()
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = (time_column, *CANDLE_FIELDS)
        if reader.fieldnames is None:
            raise ValueError("CSV is empty or has no header")
        missing = [col for col in required if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(missing)}")
        for row_num, row in enumerate(reader, start=2):
            checked += 1
            row_errors: list[Finding] = []
            try:
                t = parse_timestamp(row[time_column] or "")
            except ValueError as exc:
                row_errors.append(Finding(row_num, "BAD_TIMESTAMP", str(exc)))
                t = None
            values: dict[str, float] = {}
            for col in CANDLE_FIELDS:
                try:
                    values[col] = _positive_number(row[col] or "", col)
                except ValueError as exc:
                    row_errors.append(Finding(row_num, "BAD_VALUE", str(exc)))
            if len(values) == len(CANDLE_FIELDS):
                o, h, l, c = (values[k] for k in ("open", "high", "low", "close"))
                if l > h or h < max(o, c) or l > min(o, c):
                    row_errors.append(Finding(row_num, "OHLC_INCONSISTENT",
                                              "Expected low <= open,close <= high"))
            if t is not None:
                if t in seen:
                    row_errors.append(Finding(row_num, "DUPLICATE_TIMESTAMP", t.isoformat()))
                seen.add(t)
                if previous_time is not None:
                    delta = t - previous_time
                    if delta < timedelta(0):
                        row_errors.append(Finding(row_num, "OUT_OF_ORDER", "Timestamp decreased"))
                    elif step is not None and delta > step:
                        missing_count = int(delta // step) - 1
                        row_errors.append(Finding(row_num, "TIME_GAP",
                                                  f"Missing at least {missing_count} bars between rows"))
                    elif step is not None and timedelta(0) < delta < step:
                        row_errors.append(Finding(row_num, "TOO_CLOSE",
                                                  f"Time step is shorter than {interval}"))
                previous_time = t
            findings.extend(row_errors)
            if not row_errors:
                valid += 1
    return Report(str(source), checked, valid, interval, findings)
