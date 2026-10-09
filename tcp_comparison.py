"""
Normalized TCP vs BTC vs ETH growth comparison.

Side-effect free: no Dash, no network, no ledger/JSON state I/O.

Methodology
-----------
Question answered: if $50,000 started in TCP, BTC, or ETH on TCP inception,
what would each series be worth over time?

Common cutoff
    min(TCP latest completed date, BTC latest available date, ETH latest available date)

    Crypto weekend observations after that cutoff are dropped so they cannot
    imply extra comparison performance beyond the last comparable TCP date.

TCP
    Canonical strategy NAV series, scaled so the first in-window point equals
    $50,000. Underlying TCP accounting is not changed.

BTC / ETH
    Start at $50,000 on TCP inception (day-0 snapshot). Subsequent daily
    returns through the cutoff are compounded:

        Growth(t) = 50000 × Π (1 + r_i)  for inception < i <= t

    Weekend/holiday crypto returns on or before the cutoff are included in
    that compound path. The published frame is then reindexed to TCP
    observation dates (ffill of already-compounded values) so weekend-only
    points never appear as extra x-axis observations.

No forward-looking dates. No interpolation of TCP onto dates it did not trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional, Sequence, Union

import pandas as pd

from tcp_benchmarks import BENCHMARK_STATUS_UNAVAILABLE, BenchmarkResult
from tcp_dashboard import canonical_records_to_series

COMPARISON_BASELINE = 50_000.0
COMPARISON_TITLE = "<u>Growth of $50,000 Since Inception</u>"
COMPARISON_DISCLOSURE = (
    "BTC and ETH are normalized to the same $50,000 starting value as one TCP "
    "tranche for comparative purposes. Benchmark performance does not represent "
    "an investment by TCP."
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


def align_comparison_to_tcp_dates(
    tcp_norm: pd.Series,
    btc_growth: pd.Series,
    eth_growth: pd.Series,
) -> pd.DataFrame:
    """Keep TCP observation dates only; carry compounded BTC/ETH values forward."""
    if tcp_norm.empty:
        return pd.DataFrame(columns=["TCP", "BTC", "ETH"])
    idx = pd.DatetimeIndex(pd.to_datetime(tcp_norm.index).normalize())

    def _onto_tcp(growth: pd.Series) -> pd.Series:
        if growth is None or growth.empty:
            return pd.Series(index=idx, dtype=float)
        aligned = pd.Series(growth, dtype=float).copy()
        aligned.index = pd.to_datetime(aligned.index).normalize()
        aligned = aligned.sort_index()
        union = aligned.index.union(idx)
        return aligned.reindex(union).ffill().reindex(idx)

    return pd.DataFrame(
        {
            "TCP": pd.Series(tcp_norm.values, index=idx, dtype=float),
            "BTC": _onto_tcp(btc_growth),
            "ETH": _onto_tcp(eth_growth),
        }
    )


def comparison_cutoff_label(cutoff: Union[date, datetime, pd.Timestamp, str, None]) -> str:
    stamp = _as_timestamp(cutoff)
    if stamp is None:
        return "Comparison data unavailable."
    return f"Comparison data through {stamp.strftime('%B %d, %Y')}"


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


@dataclass(frozen=True)
class ComparisonBundle:
    frame: pd.DataFrame
    inception: Optional[pd.Timestamp]
    cutoff: Optional[pd.Timestamp]
    baseline: float
    btc_status: str
    eth_status: str
    btc_as_of: Optional[str]
    eth_as_of: Optional[str]
    cutoff_label: str
    disclosure: str
    stale_notices: tuple[str, ...]


def _result_returns(result: Optional[BenchmarkResult]) -> Optional[pd.Series]:
    if result is None or result.status == BENCHMARK_STATUS_UNAVAILABLE:
        return None
    if result.returns is None or result.returns.empty:
        return None
    return result.returns


def build_normalized_comparison_bundle(
    canonical_records: Sequence[Mapping[str, Any]],
    btc_result: Optional[BenchmarkResult] = None,
    eth_result: Optional[BenchmarkResult] = None,
    *,
    baseline: float = COMPARISON_BASELINE,
) -> ComparisonBundle:
    nav = canonical_records_to_series(canonical_records)
    btc_returns = _result_returns(btc_result)
    eth_returns = _result_returns(eth_result)
    inception = _series_end(nav.iloc[:1]) if not nav.empty else None
    if not nav.empty:
        inception = pd.Timestamp(nav.index.min()).normalize()
    cutoff = common_comparison_cutoff(
        _series_end(nav),
        _series_end(btc_returns),
        _series_end(eth_returns),
    )
    tcp_norm = normalize_tcp_to_baseline(nav, baseline=baseline, cutoff=cutoff)
    if inception is not None and cutoff is not None:
        btc_growth = compound_benchmark_to_baseline(
            btc_returns, inception=inception, cutoff=cutoff, baseline=baseline
        )
        eth_growth = compound_benchmark_to_baseline(
            eth_returns, inception=inception, cutoff=cutoff, baseline=baseline
        )
    else:
        btc_growth = pd.Series(dtype=float)
        eth_growth = pd.Series(dtype=float)
    frame = align_comparison_to_tcp_dates(tcp_norm, btc_growth, eth_growth)
    notices = tuple(
        notice
        for notice in (
            benchmark_stale_notice(btc_result),
            benchmark_stale_notice(eth_result),
        )
        if notice
    )
    return ComparisonBundle(
        frame=frame,
        inception=inception,
        cutoff=cutoff,
        baseline=float(baseline),
        btc_status=btc_result.status if btc_result is not None else BENCHMARK_STATUS_UNAVAILABLE,
        eth_status=eth_result.status if eth_result is not None else BENCHMARK_STATUS_UNAVAILABLE,
        btc_as_of=btc_result.as_of if btc_result is not None else None,
        eth_as_of=eth_result.as_of if eth_result is not None else None,
        cutoff_label=comparison_cutoff_label(cutoff),
        disclosure=COMPARISON_DISCLOSURE,
        stale_notices=notices,
    )
