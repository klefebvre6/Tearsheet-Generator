"""
Optional BTC/ETH overlays for the TCP NAV chart.

Side-effect free: no Dash, no network, no ledger/JSON state I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Optional, Sequence, Union

import pandas as pd

from tcp_benchmarks import (
    BENCHMARK_STATUS_UNAVAILABLE,
    BTC_SYMBOL,
    ETH_SYMBOL,
    BenchmarkResult,
)
from tcp_comparison import (
    OVERLAY_BASELINE,
    _as_timestamp,
    _result_returns,
    _series_end,
    align_overlays_to_tcp_dates,
    benchmark_stale_notice,
    common_comparison_cutoff,
    compound_benchmark_to_baseline,
    overlay_price_cutoff_label,
)
from tcp_dashboard import canonical_records_to_series

BENCHMARK_PRICE_PROVIDER = "Yahoo Finance"


def _format_display_date(value: Union[date, datetime, pd.Timestamp, str, None]) -> str:
    stamp = _as_timestamp(value)
    if stamp is None:
        return "unknown date"
    return stamp.strftime("%B %d, %Y")


def _refresh_date(result: BenchmarkResult) -> Optional[str]:
    raw = result.fetched_at
    if not raw:
        return None
    try:
        return _format_display_date(datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date())
    except ValueError:
        return str(raw)[:10]


def overlay_ticker(symbol: str) -> str:
    return symbol.lstrip("^")


def overlay_attribution_segment(
    result: Optional[BenchmarkResult],
    *,
    chart_price_through: Optional[pd.Timestamp],
) -> Optional[str]:
    if result is None or result.status == BENCHMARK_STATUS_UNAVAILABLE:
        return None
    if result.returns is None or result.returns.empty:
        return None
    name = result.display_name or "Benchmark"
    ticker = overlay_ticker(result.symbol)
    price_through = chart_price_through or _as_timestamp(result.as_of)
    if price_through is None:
        price_through = _as_timestamp(result.as_of)
    price_text = _format_display_date(price_through)
    refreshed = _refresh_date(result) or "unknown"
    stale = " (stale cache)" if result.status == "stale" else ""
    return (
        f"{name}: {BENCHMARK_PRICE_PROVIDER} ({ticker}); "
        f"prices through {price_text}; cache refreshed {refreshed}{stale}"
    )


def compact_overlay_attribution_row(segments: Sequence[str]) -> str:
    return " · ".join(segment for segment in segments if segment)


def benchmark_series_through_label(result: Optional[BenchmarkResult]) -> Optional[str]:
    """Display date for one benchmark's own last price, independent of the other asset."""
    if result is None or result.status == BENCHMARK_STATUS_UNAVAILABLE:
        return None
    if result.returns is None or result.returns.empty:
        return None
    end = _series_end(result.returns) or _as_timestamp(result.as_of)
    if end is None:
        return None
    return _format_display_date(end)


def compact_selected_benchmark_attribution(
    *,
    show_btc: bool,
    show_eth: bool,
    btc_through: Optional[str],
    eth_through: Optional[str],
) -> str:
    """Short footer credit for the overlays that are actually turned on."""
    selected: list[tuple[str, Optional[str]]] = []
    if show_btc:
        selected.append(("BTC", btc_through))
    if show_eth:
        selected.append(("ETH", eth_through))
    if not selected:
        return ""
    dates = [label for _, label in selected if label]
    if len(selected) == 2 and len(set(dates)) == 1 and dates:
        return f"BTC/ETH: {BENCHMARK_PRICE_PROVIDER} · through {dates[0]}"
    parts = []
    for name, label in selected:
        through = label or "unknown date"
        parts.append(f"{name}: {BENCHMARK_PRICE_PROVIDER} · through {through}")
    return " · ".join(parts)


@dataclass(frozen=True)
class NavOverlayBundle:
    tcp_dates: pd.DatetimeIndex
    tcp_nav: pd.Series
    btc_overlay: pd.Series
    eth_overlay: pd.Series
    baseline_date: Optional[pd.Timestamp]
    chart_price_through: Optional[pd.Timestamp]
    baseline_nav: Optional[float]
    attribution_row: str
    stale_notices: tuple[str, ...]
    price_cutoff_label: str
    btc_through_label: Optional[str] = None
    eth_through_label: Optional[str] = None

    @property
    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "TCP": self.tcp_nav,
                "BTC": self.btc_overlay,
                "ETH": self.eth_overlay,
            }
        )

    @property
    def cutoff(self) -> Optional[pd.Timestamp]:
        return self.chart_price_through

    @property
    def cutoff_label(self) -> str:
        return self.price_cutoff_label

    @property
    def disclosure(self) -> str:
        from tcp_comparison import OVERLAY_DISCLOSURE

        return OVERLAY_DISCLOSURE


def build_nav_overlay_bundle(
    canonical_records: Sequence[Mapping[str, object]],
    btc_result: Optional[BenchmarkResult] = None,
    eth_result: Optional[BenchmarkResult] = None,
    *,
    baseline: float = OVERLAY_BASELINE,
) -> NavOverlayBundle:
    nav = canonical_records_to_series(canonical_records)
    btc_returns = _result_returns(btc_result)
    eth_returns = _result_returns(eth_result)
    baseline_date = pd.Timestamp(nav.index.min()).normalize() if not nav.empty else None
    chart_through = common_comparison_cutoff(
        _series_end(nav),
        _series_end(btc_returns),
        _series_end(eth_returns),
    )
    if chart_through is not None and not nav.empty:
        nav = nav.loc[nav.index <= chart_through]
    baseline_nav = float(nav.iloc[0]) if not nav.empty else None
    if baseline_date is not None and chart_through is not None:
        btc_growth = compound_benchmark_to_baseline(
            btc_returns, inception=baseline_date, cutoff=chart_through, baseline=baseline
        )
        eth_growth = compound_benchmark_to_baseline(
            eth_returns, inception=baseline_date, cutoff=chart_through, baseline=baseline
        )
    else:
        btc_growth = pd.Series(dtype=float)
        eth_growth = pd.Series(dtype=float)
    aligned = align_overlays_to_tcp_dates(nav, btc_growth, eth_growth)
    segments = tuple(
        segment
        for segment in (
            overlay_attribution_segment(btc_result, chart_price_through=chart_through),
            overlay_attribution_segment(eth_result, chart_price_through=chart_through),
        )
        if segment
    )
    notices = tuple(
        notice
        for notice in (
            benchmark_stale_notice(btc_result),
            benchmark_stale_notice(eth_result),
        )
        if notice
    )
    return NavOverlayBundle(
        tcp_dates=pd.DatetimeIndex(aligned.index),
        tcp_nav=aligned["TCP"],
        btc_overlay=aligned["BTC"],
        eth_overlay=aligned["ETH"],
        baseline_date=baseline_date,
        chart_price_through=chart_through,
        baseline_nav=baseline_nav,
        attribution_row=compact_overlay_attribution_row(segments),
        stale_notices=notices,
        price_cutoff_label=overlay_price_cutoff_label(chart_through),
        btc_through_label=benchmark_series_through_label(btc_result),
        eth_through_label=benchmark_series_through_label(eth_result),
    )


build_normalized_comparison_bundle = build_nav_overlay_bundle
