"""
BTC/ETH overlay math for the TCP NAV chart.

Side-effect free: no Dash, no network, no ledger/JSON state I/O.

Methodology
-----------
TCP trace uses canonical ``nav-x1`` (non-compounded, net of fees).

BTC / ETH overlays start at $50,000 on the TCP inception date. Each curve is
built only from that asset's own daily total-return history (Yahoo Finance
via quantstats/yfinance), not from TCP cash flows:

    Overlay(t) = 50000 × Π (1 + r_i)  for inception < i <= t

Common chart cutoff
    min(TCP latest completed date, BTC latest available date, ETH latest available date)

Overlay values are carried onto TCP observation dates (forward-filled) so
weekend crypto moves appear on the next TCP trading date without adding
extra x-axis points.

No forward-looking dates. No interpolation of TCP onto dates it did not trade.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Mapping, Optional, Sequence, Union

import pandas as pd

from tcp_benchmarks import BENCHMARK_STATUS_UNAVAILABLE, BenchmarkResult
from tcp_dashboard import canonical_records_to_series

OVERLAY_BASELINE = 50_000.0
COMPARISON_BASELINE = OVERLAY_BASELINE
OVERLAY_DISCLOSURE = (
    "Optional BTC and ETH overlays are normalized to $50,000 on the TCP inception "
    "date using each asset's own Yahoo Finance adjusted-close history (total return "
    "since that date). They do not represent investments by TCP."
)


def _as_timestamp(value: Union[date, datetime, pd.Timestamp, str, None]) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    return pd.Timestamp(value).normalize()


def _series_end(series: Optional[pd.Series]) -> Optional[pd.Timestamp]:
    if series is None or series.empty:
        return None
    return pd.Timestamp(series.index.max()).normalize()


def common_comparison_cutoff(
    tcp_end: Union[date, datetime, pd.Timestamp, str, None],
    btc_end: Union[date, datetime, pd.Timestamp, str, None],
    eth_end: Union[date, datetime, pd.Timestamp, str, None],
) -> Optional[pd.Timestamp]:
    """Latest date present in every required comparison series."""
    dates = [_as_timestamp(item) for item in (tcp_end, btc_end, eth_end)]
    present = [item for item in dates if item is not None]
    if len(present) < 3:
        return None
    return min(present)


def normalize_tcp_to_baseline(
    nav_series: pd.Series,
    *,
    baseline: float = COMPARISON_BASELINE,
    cutoff: Union[date, datetime, pd.Timestamp, str, None] = None,
) -> pd.Series:
    series = pd.Series(nav_series, dtype=float).copy()
    if series.empty:
        return pd.Series(dtype=float)
    series.index = pd.to_datetime(series.index).normalize()
    series = series.sort_index()
    end = _as_timestamp(cutoff)
    if end is not None:
        series = series.loc[series.index <= end]
    if series.empty or float(series.iloc[0]) == 0:
        return pd.Series(dtype=float)
    return (series * (float(baseline) / float(series.iloc[0]))).astype(float)


def compound_benchmark_to_baseline(
    returns: Optional[pd.Series],
    *,
    inception: Union[date, datetime, pd.Timestamp, str],
    cutoff: Union[date, datetime, pd.Timestamp, str],
    baseline: float = COMPARISON_BASELINE,
) -> pd.Series:
    """$50,000 at inception, then compound subsequent daily returns through cutoff."""
    if returns is None or returns.empty:
        return pd.Series(dtype=float)
    start = _as_timestamp(inception)
    end = _as_timestamp(cutoff)
    if start is None or end is None or end < start:
        return pd.Series(dtype=float)
    series = pd.Series(returns, dtype=float).copy()
    series.index = pd.to_datetime(series.index).normalize()
    series = series.sort_index()
    series = series.loc[(series.index >= start) & (series.index <= end)]
    subsequent = series.loc[series.index > start]
    head = pd.Series([float(baseline)], index=pd.DatetimeIndex([start]))
    if subsequent.empty:
        return head
    growth = (1.0 + subsequent.astype(float)).cumprod() * float(baseline)
    out = pd.concat([head, growth])
    return out[~out.index.duplicated(keep="first")].sort_index().astype(float)


def _reindex_growth_to_tcp_dates(growth: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    if growth is None or growth.empty:
        return pd.Series(index=idx, dtype=float)
    aligned = pd.Series(growth, dtype=float).copy()
    aligned.index = pd.to_datetime(aligned.index).normalize()
    aligned = aligned.sort_index()
    union = aligned.index.union(idx)
    return aligned.reindex(union).ffill().reindex(idx)


def align_overlays_to_tcp_dates(
    tcp_nav: pd.Series,
    btc_growth: pd.Series,
    eth_growth: pd.Series,
) -> pd.DataFrame:
    """Keep TCP observation dates only; carry compounded BTC/ETH values forward."""
    if tcp_nav.empty:
        return pd.DataFrame(columns=["TCP", "BTC", "ETH"])
    idx = pd.DatetimeIndex(pd.to_datetime(tcp_nav.index).normalize())
    return pd.DataFrame(
        {
            "TCP": pd.Series(tcp_nav.values, index=idx, dtype=float),
            "BTC": _reindex_growth_to_tcp_dates(btc_growth, idx),
            "ETH": _reindex_growth_to_tcp_dates(eth_growth, idx),
        }
    )


def align_comparison_to_tcp_dates(
    tcp_norm: pd.Series,
    btc_growth: pd.Series,
    eth_growth: pd.Series,
) -> pd.DataFrame:
    return align_overlays_to_tcp_dates(tcp_norm, btc_growth, eth_growth)


def overlay_price_cutoff_label(cutoff: Union[date, datetime, pd.Timestamp, str, None]) -> str:
    stamp = _as_timestamp(cutoff)
    if stamp is None:
        return "Overlay price history unavailable."
    return f"Overlay prices aligned through {stamp.strftime('%B %d, %Y')} (latest TCP ledger date)."


def comparison_cutoff_label(cutoff: Union[date, datetime, pd.Timestamp, str, None]) -> str:
    return overlay_price_cutoff_label(cutoff)


def benchmark_stale_notice(result: Optional[BenchmarkResult]) -> Optional[str]:
    if result is None or result.status == "ready":
        return None
    if result.status == "stale":
        as_of = result.as_of or "unknown date"
        return (
            f"{result.display_name} benchmark data is stale; "
            f"last successful data through {as_of}."
        )
    if result.status == BENCHMARK_STATUS_UNAVAILABLE:
        return result.warning or f"{result.display_name} benchmark data is temporarily unavailable."
    return None


def _result_returns(result: Optional[BenchmarkResult]) -> Optional[pd.Series]:
    if result is None or result.status == BENCHMARK_STATUS_UNAVAILABLE:
        return None
    if result.returns is None or result.returns.empty:
        return None
    return result.returns


