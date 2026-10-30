# OHLCV Guard

[![Tests](https://github.com/franok-research/ohlcv-guard/actions/workflows/tests.yml/badge.svg)](https://github.com/franok-research/ohlcv-guard/actions/workflows/tests.yml)

Small, dependency-free Python utility for checking **OHLCV market data quality** before backtesting.

## Features

- Accepts timestamp columns in timezone-aware ISO 8601 format or Unix seconds / milliseconds.
- Rejects non-finite, missing, non-positive prices and negative volume.
- Checks `low <= open, close <= high` and `low <= high`.
- Detects duplicate and out-of-order timestamps.
- Optionally detects time gaps for regular candles (e.g. `15m`), and time steps shorter than the configured interval.
- Prints concise diagnostics and optionally writes a JSON report.
- No third-party runtime dependencies; automated unit tests run on GitHub Actions.

## Install

Requires Python 3.10+.

```bash
python -m pip install -e .
```

## Usage

```bash
ohlcv-guard examples/sample.csv --interval 15m
# Equivalent:
python -m ohlcv_guard examples/sample.csv --interval 15m --json report.json
```

Expected CSV columns: `timestamp,open,high,low,close,volume`. You may select another timestamp column name:

```bash
ohlcv-guard candles.csv --time-column open_time --interval 1h
```

Timestamps must have a timezone (`Z` or an offset) if formatted as ISO 8601. Exchange timestamps in epoch seconds and milliseconds are supported. **The parser assumes a millisecond epoch for numeric magnitudes >= 1e11**; avoid ambiguous epoch-like numeric formats.

Exit codes: `0` no issues, `1` data issues found, `2` invalid file or arguments.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Limitations

This is a **data-integrity** tool. It does not detect every look-ahead leak, and it does not certify that your backtest is free of leakage. It does not infer exchange calendars, holidays, deliberately missing inactive bars, corporate actions, or mixed timestamp conventions. A valid file only means it satisfies the checks described above. The first row starts at CSV line 2.

## License

MIT
