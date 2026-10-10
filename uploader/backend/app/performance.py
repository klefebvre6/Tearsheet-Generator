"""Chart-ready performance series for GET /api/performance.

Two modes:

  * combined — one normalized ($100,000) series per PROGRAM only (TKP/TCP/AGM/
    YQ). X-axis is each program's own trading-day index (0, 1, 2, ... — the
    frontend labels these "Day N"), so a program with fewer rows simply ends
    earlier; no shared calendar alignment. Benchmarks are never included.

  * program — the selected program's own series, X-axis = real calendar
    dates, optionally overlaid with SPX/NDX/BTC benchmarks rebased to
    $100,000 as of the program's first available date.

Accounting:
  * Program NLV per row comes from `programs.program_nlv` (TKP=StoneX only,
    Plus500 informational; TCP/YQ=StoneX, AGM=TradeStation — AGM's `fee` is a
    documented exclusion, see that function's docstring).
  * Cash transfers are neutralized so deposits/withdrawals never show up as
    performance:
        daily_return = (ending_nlv - cash_transfer) / prior_ending_nlv - 1
    The first row of a series has no "prior" — it is simply the $100,000
    anchor point, so its own cash_transfer never affects the series.

Benchmarks (program mode only):
  * Real daily closes from ``benchmark_store`` (yfinance + CSV cache).
  * Aligned with ``prior_close_within_5_calendar_days`` — weekends/holidays
    use the latest prior close within 5 calendar days (documented in warnings).
  * Program-start rebasing may roll forward up to 14 days when the first entry
    date has no close (e.g. weekend), with an explicit warning.

This module reads directly from the database on every call (no caching), so
the chart is always current after a row create/update/delete or an export
preview.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from .benchmark_store import MAX_PRIOR_CLOSE_GAP_DAYS
from .benchmarks import (
    BENCHMARK_ALIGN_POLICY,
    BENCHMARK_SYMBOLS,
    aggregate_benchmark_source,
    get_store,
)
from .programs import PROGRAM_LABELS, PROGRAMS, normalize_program, program_nlv

BASE_VALUE = 100_000.0

PROGRAM_DATA_SOURCE = "uploader_daily_rows"
# Emitted instead when any plotted point came from backfilled tearsheet
# history (historical_rows). Manual entries always win on a shared date —
# see Database.get_merged_rows and docs/historical_backfill.md.
PROGRAM_DATA_SOURCE_WITH_BACKFILL = "uploader_daily_rows+tearsheet_backfill"


def _rows_with_nlv(db, program: str) -> list[dict]:
    """This program's chartable rows (oldest first), each annotated with `_nlv`.

    Reads the MERGED view: manual daily_rows plus backfilled historical_rows,
    with a manual entry superseding a historical row on the same date. Each
    row carries `row_source` ("manual" or the import's source label). Rows
    missing a required NLV component are dropped defensively — validation at
    write/import time should already guarantee this never happens.
    """
    out = []
    for row in db.get_merged_rows(program):
        nlv = program_nlv(program, row)
        if nlv is None:
            continue
        row = dict(row)
        row["_nlv"] = nlv
        out.append(row)
    return out


def _backfilled_count(rows: list[dict]) -> int:
    return sum(1 for r in rows if r.get("row_source") not in (None, "manual"))


def _aggregate_program_source(any_backfill: bool) -> str:
    return PROGRAM_DATA_SOURCE_WITH_BACKFILL if any_backfill else PROGRAM_DATA_SOURCE


def _normalized_values(rows: list[dict]) -> list[float]:
    """Compound `rows` (oldest first, each with `_nlv`) into a $100,000 series."""
    values: list[float] = []
    normalized = BASE_VALUE
    prior_raw = None
    for i, row in enumerate(rows):
        raw = row["_nlv"]
        if i == 0:
            normalized = BASE_VALUE
        else:
            cash_transfer = row.get("cash_transfer") or 0.0
            adjusted = raw - cash_transfer
            if not prior_raw:
                daily_return = 0.0
            else:
                daily_return = adjusted / prior_raw - 1.0
            normalized = normalized * (1.0 + daily_return)
        values.append(round(normalized, 4))
        prior_raw = raw
    return values


def _last_updated_at(db) -> str:
    ts = db.get_last_activity_ts()
    return ts or datetime.now(timezone.utc).isoformat()


def _empty_program_series(code: str) -> tuple[list[dict], dict[str, list]]:
    series = [{"key": code, "label": PROGRAM_LABELS[code], "kind": "program", "point_count": 0}]
    return series, {code: []}


def _human_date(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _benchmark_status_entry(
    *,
    status: str,
    latest_date: Optional[str],
    aligned_points: int,
    fallback_points: int,
) -> dict:
    return {
        "status": status,
        "latest_date": latest_date,
        "aligned_points": aligned_points,
        "fallback_points": fallback_points,
    }


def build_combined(db) -> dict:
    """Combined mode: one program-only series per program, trading-day index."""
    warnings: list[str] = []
    series_meta: list[dict] = []
    points: dict[str, list[dict]] = {}
    any_backfill = False

    for code in PROGRAMS:
        rows = _rows_with_nlv(db, code)
        if not rows:
            warnings.append(f"{code}: no data yet.")
            s, p = _empty_program_series(code)
            series_meta.extend(s)
            points.update(p)
            continue
        values = _normalized_values(rows)
        backfilled = _backfilled_count(rows)
        any_backfill = any_backfill or backfilled > 0
        series_meta.append(
            {
                "key": code,
                "label": PROGRAM_LABELS[code],
                "kind": "program",
                "point_count": len(values),
                "backfilled_point_count": backfilled,
                "manual_point_count": len(values) - backfilled,
            }
        )
        points[code] = [{"x": i, "y": v} for i, v in enumerate(values)]

    return {
        "mode": "combined",
        "x_axis": "trading_day",
        "base_value": BASE_VALUE,
        "program": None,
        "benchmarks": [],
        "series": series_meta,
        "points": points,
        "last_updated_at": _last_updated_at(db),
        "warnings": warnings,
        "program_data_source": _aggregate_program_source(any_backfill),
        "benchmark_data_source": None,
        "benchmark_align_policy": None,
        "benchmark_status": {},
    }


def build_program(db, program: str, benchmark_symbols: list[str]) -> dict:
    """Program mode: the selected program's own series plus optional benchmarks."""
    code = normalize_program(program)
    warnings: list[str] = []

    rows = _rows_with_nlv(db, code)
    if not rows:
        warnings.append(f"{code}: no data yet.")
        series_meta, points = _empty_program_series(code)
        return {
            "mode": "program",
            "x_axis": "date",
            "base_value": BASE_VALUE,
            "program": code,
            "benchmarks": [],
            "series": series_meta,
            "points": points,
            "last_updated_at": _last_updated_at(db),
            "warnings": warnings,
            "program_data_source": PROGRAM_DATA_SOURCE,
            "benchmark_data_source": None,
            "benchmark_align_policy": None,
            "benchmark_status": {},
        }

    values = _normalized_values(rows)
    dates = [r["date"] for r in rows]
    backfilled = _backfilled_count(rows)
    series_meta: list[dict] = [
        {
            "key": code,
            "label": PROGRAM_LABELS[code],
            "kind": "program",
            "point_count": len(values),
            "backfilled_point_count": backfilled,
            "manual_point_count": len(values) - backfilled,
        }
    ]
    points: dict[str, list[dict]] = {code: [{"x": d, "y": v} for d, v in zip(dates, values)]}

    resolved_benchmarks: list[str] = []
    benchmark_status: dict[str, dict] = {}
    benchmark_requested = bool(benchmark_symbols)
    store = get_store()
    store.reset_session()
    warned_symbols: set[str] = set()

    def add_symbol_warning(sym: str, msg: Optional[str]) -> None:
        if not msg or sym in warned_symbols:
            return
        warned_symbols.add(sym)
        warnings.append(msg)

    if benchmark_symbols:
        start_date = date.fromisoformat(dates[0])
        end_date = date.fromisoformat(dates[-1])
        for sym in benchmark_symbols:
            if sym not in BENCHMARK_SYMBOLS:
                warnings.append(f"Unknown benchmark '{sym}' ignored.")
                continue

            store.ensure_range(sym, start_date, end_date)
            cache_latest = store.latest_close_date(sym)
            base = store.close_on_or_after(sym, start_date)
            if base.value is None:
                add_symbol_warning(
                    sym,
                    f"{sym} benchmark data is unavailable.",
                )
                benchmark_status[sym] = _benchmark_status_entry(
                    status="unavailable",
                    latest_date=cache_latest.isoformat() if cache_latest else None,
                    aligned_points=0,
                    fallback_points=0,
                )
                continue

            bench_points = []
            fallback_points = 0
            unaligned = 0
            for d_str in dates:
                target = date.fromisoformat(d_str)
                aligned = store.close_on_or_before(sym, target)
                if aligned.value is None:
                    unaligned += 1
                    continue
                if aligned.as_of is not None and aligned.as_of != target:
                    fallback_points += 1
                bench_points.append(
                    {"x": d_str, "y": round(BASE_VALUE * aligned.value / base.value, 4)}
                )

            if not bench_points:
                add_symbol_warning(sym, f"{sym} benchmark data is unavailable.")
                benchmark_status[sym] = _benchmark_status_entry(
                    status="unavailable",
                    latest_date=cache_latest.isoformat() if cache_latest else None,
                    aligned_points=0,
                    fallback_points=0,
                )
                continue

            last_aligned = date.fromisoformat(bench_points[-1]["x"])
            stale = unaligned > 0 or (
                cache_latest is not None
                and (end_date - cache_latest).days > MAX_PRIOR_CLOSE_GAP_DAYS
            )
            status = "stale" if stale else "ready"
            if stale:
                last_close = cache_latest or last_aligned
                add_symbol_warning(
                    sym,
                    f"{sym} benchmark data is stale; last available close is "
                    f"{_human_date(last_close)}.",
                )
            benchmark_status[sym] = _benchmark_status_entry(
                status=status,
                latest_date=(cache_latest or last_aligned).isoformat(),
                aligned_points=len(bench_points),
                fallback_points=fallback_points,
            )

            resolved_benchmarks.append(sym)
            series_meta.append(
                {"key": sym, "label": sym, "kind": "benchmark", "point_count": len(bench_points)}
            )
            points[sym] = bench_points

    bench_source = aggregate_benchmark_source(
        benchmark_requested, len(resolved_benchmarks), store
    )

    return {
        "mode": "program",
        "x_axis": "date",
        "base_value": BASE_VALUE,
        "program": code,
        "benchmarks": resolved_benchmarks,
        "series": series_meta,
        "points": points,
        "last_updated_at": _last_updated_at(db),
        "warnings": warnings,
        "program_data_source": _aggregate_program_source(backfilled > 0),
        "benchmark_data_source": bench_source,
        "benchmark_align_policy": (
            BENCHMARK_ALIGN_POLICY if resolved_benchmarks else None
        ),
        "benchmark_status": benchmark_status,
    }
