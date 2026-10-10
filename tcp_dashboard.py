"""
Pure TCP dashboard recomputation for TCP v2.

Side-effect free: no Dash, Flask, JSON persistence, or workbook I/O on import.
"""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import pandas as pd
import plotly.graph_objs as go

from tcp_ledger import LedgerRecord

PRIMARY_COLOR = "#0D3562"
GREY_BG = "#EBEBEB"
WHITE_BG = "#ffffff"
STRATEGY_NAME = "TCP"

MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

METRIC_LABELS = [
    "Cumulative Return",
    "Annualized Return",
    "Avg Daily Return",
    "Number of Trading Days",
    "% Winning Days",
    "% Losing Days",
    "Best 3 Days",
    "Worst 3 Days",
]

LABEL_HEADER = "Data current to"
LABEL_UNAVAILABLE = "Data unavailable"
LABEL_DATE_SUFFIX = " close"


class TCPDashboardError(Exception):
    """Base dashboard error."""


class EmptyLedgerError(TCPDashboardError):
    """No canonical NAV records supplied."""


class DuplicateCanonicalDate(TCPDashboardError):
    """Duplicate completed Date in canonical records."""


class InvalidCanonicalNAV(TCPDashboardError):
    """NAV is missing or non-finite."""


class NonChronologicalCanonicalDate(TCPDashboardError):
    """Canonical records are not in ascending date order."""


@dataclass(frozen=True)
class CurrentDataLabels:
    header: str
    date_line: str
    source_date: Optional[date]


@dataclass(frozen=True)
class DashboardPropagation:
    canonical_records: List[Dict[str, Any]]
    monthly_calendar: pd.DataFrame
    daily_performance: pd.DataFrame
    drawdown_profile: pd.DataFrame
    nav_figure: go.Figure
    desktop_label: CurrentDataLabels
    mobile_label: CurrentDataLabels
    latest_date: Optional[date]
    latest_nav: Optional[float]
    baseline_nav: Optional[float]
    nav_point_count: int


def _coerce_row_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise InvalidCanonicalNAV(f"Invalid Date value: {value!r}")


def _coerce_nav(value: Any) -> float:
    if value is None:
        raise InvalidCanonicalNAV("NAV is required")
    try:
        nav = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidCanonicalNAV(f"Invalid NAV value: {value!r}") from exc
    if not math.isfinite(nav):
        raise InvalidCanonicalNAV(f"NAV must be finite, got {value!r}")
    return nav


def _record_fields(record: Union[LedgerRecord, Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(record, LedgerRecord):
        return record.fields
    return record


def canonical_nav_records_from_ledger(
    records: Sequence[Union[LedgerRecord, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Build canonical Date/NAV records from ledger rows.

    Internal daily returns use decimal representation (0.01 == 1%).
    Monthly table values use percentage points (4.58 == 4.58%).
    """
    canonical: List[Dict[str, Any]] = []
    seen_dates: set[date] = set()
    previous_date: Optional[date] = None

    for record in records:
        fields = _record_fields(record)
        row_date = _coerce_row_date(fields.get("Date"))
        if row_date in seen_dates:
            raise DuplicateCanonicalDate(f"Duplicate Date {row_date.isoformat()}")
        seen_dates.add(row_date)
        if previous_date is not None and row_date < previous_date:
            raise NonChronologicalCanonicalDate(
                f"Date {row_date} is out of order after {previous_date}"
            )
        previous_date = row_date
        nav = _coerce_nav(fields.get("nav-x1"))
        canonical.append({"Date": row_date.isoformat(), "NAV": nav})

    return canonical


def canonical_records_to_series(
    canonical_records: Sequence[Mapping[str, Any]],
) -> pd.Series:
    if not canonical_records:
        return pd.Series(dtype=float)
    dates = [_coerce_row_date(row["Date"]) for row in canonical_records]
    nav_values = [_coerce_nav(row["NAV"]) for row in canonical_records]
    series = pd.Series(nav_values, index=pd.to_datetime(dates))
    return series.sort_index()


def recompute_tcp_monthly_performance(
    canonical_records: Sequence[Mapping[str, Any]],
    *,
    baseline_nav: Optional[float] = None,
) -> pd.DataFrame:
    """Rebuild TCP monthly calendar using first NAV as baseline (no legacy overrides)."""
    nav_series = canonical_records_to_series(canonical_records)
    if nav_series.empty:
        return pd.DataFrame(columns=["Year", *MONTH_LABELS, "Year Total"])

    baseline = baseline_nav if baseline_nav is not None else float(nav_series.iloc[0])
    if baseline == 0:
        raise InvalidCanonicalNAV("Baseline NAV cannot be zero")

    month_periods = nav_series.index.to_period("M")
    month_last = nav_series.groupby(month_periods).last()
    month_first = pd.Series(index=month_last.index, dtype=float)
    for period in month_last.index:
        month_start = period.start_time
        nav_before_month = nav_series[nav_series.index < month_start]
        if len(nav_before_month) > 0:
            month_first.loc[period] = float(nav_before_month.iloc[-1])
        else:
            month_first.loc[period] = baseline

    monthly_simple = (month_last - month_first) / baseline * 100.0
    yearly_simple = monthly_simple.groupby(monthly_simple.index.year).sum()

    years = sorted(monthly_simple.index.year.unique())
    monthly_data: Dict[str, List[str]] = {"Year": [str(y) for y in years]}
    for idx, month_name in enumerate(MONTH_LABELS, start=1):
        monthly_data[month_name] = []
        for year in years:
            period = pd.Period(f"{year}-{idx:02d}", freq="M")
            if period in monthly_simple.index:
                monthly_data[month_name].append(f"{monthly_simple.loc[period]:.4f}%")
            else:
                monthly_data[month_name].append("")

    monthly_data["Year Total"] = [f"{yearly_simple.get(y, 0):.4f}%" for y in years]
    return pd.DataFrame(monthly_data)


def _short_period_metrics() -> Dict[str, str]:
    return {
        "Cumulative Return": "0.0%",
        "Annualized Return": "0.0%",
        "Avg Daily Return": "0.000%",
        "Number of Trading Days": "0",
        "% Winning Days": "0 (0.0%)",
        "% Losing Days": "0 (0.0%)",
        "Best 3 Days": "0.00%, 0.00%, 0.00%",
        "Worst 3 Days": "0.00%, 0.00%, 0.00%",
    }


def calculate_period_metrics(
    returns: pd.Series,
    start_date: pd.Timestamp,
) -> Dict[str, str]:
    """
    TCP non-compounded daily metrics.

    Daily returns are decimal fractions; displayed values multiply by 100.
    Annualization uses 365 calendar days. No risk-free rate. No Sharpe ratio.
    Zero-return days are neither wins nor losses.
    """
    if len(returns) < 2:
        return _short_period_metrics()

    cum = float(returns.sum())
    days = len(returns)
    span_days = (returns.index.max() - start_date).days
    annualized = cum if span_days == 0 else cum * 365.0 / span_days
    avg = float(returns.mean())

    wins = int((returns > 0).sum())
    losses = int((returns < 0).sum())

    top3 = returns.nlargest(3) * 100.0
    bot3 = returns.nsmallest(3) * 100.0

    return {
        "Cumulative Return": f"{cum * 100:.1f}%",
        "Annualized Return": f"{annualized * 100:.1f}%",
        "Avg Daily Return": f"{avg * 100:.3f}%",
        "Number of Trading Days": str(days),
        "% Winning Days": f"{wins} ({wins / days * 100:.1f}%)",
        "% Losing Days": f"{losses} ({losses / days * 100:.1f}%)",
        "Best 3 Days": ", ".join(f"{v:.2f}%" for v in top3),
        "Worst 3 Days": ", ".join(f"{v:.2f}%" for v in bot3),
    }


def recompute_tcp_daily_metrics(
    canonical_records: Sequence[Mapping[str, Any]],
    *,
    baseline_nav: Optional[float] = None,
    strategy_name: str = STRATEGY_NAME,
) -> pd.DataFrame:
    """Rebuild TCP Performance Metrics table from canonical NAV records."""
    nav_series = canonical_records_to_series(canonical_records)
    if nav_series.empty:
        return pd.DataFrame(
            {
                "Metric": METRIC_LABELS,
                f"{strategy_name} (1 Year/TTM)": [
                    _short_period_metrics()[m] for m in METRIC_LABELS
                ],
                f"{strategy_name} (Inception)": [
                    _short_period_metrics()[m] for m in METRIC_LABELS
                ],
            }
        )

    baseline = baseline_nav if baseline_nav is not None else float(nav_series.iloc[0])
    if baseline == 0:
        raise InvalidCanonicalNAV("Baseline NAV cannot be zero")

    daily_returns = nav_series.diff().div(baseline).dropna()
    inception_start = nav_series.index.min()
    ttm_start = nav_series.index.max() - pd.DateOffset(years=1)

    one_year_returns = daily_returns.loc[ttm_start:].dropna()
    inception_returns = daily_returns.copy()

    one_year_metrics = calculate_period_metrics(one_year_returns, ttm_start)
    inception_metrics = calculate_period_metrics(inception_returns, inception_start)

    return pd.DataFrame(
        {
            "Metric": METRIC_LABELS,
            f"{strategy_name} (1 Year/TTM)": [one_year_metrics[m] for m in METRIC_LABELS],
            f"{strategy_name} (Inception)": [inception_metrics[m] for m in METRIC_LABELS],
        }
    )


NAV_CHART_TITLE = "<u>Non-Compounded NAV Since Inception</u>"
NAV_CHART_UIREVISION = "tcp-nav-chart-v1"
NAV_PCT_AXIS_TITLE = "Return since inception (%)"
NAV_CHART_MARGIN_DEFAULT = {"l": 48, "r": 12, "t": 56, "b": 64}
NAV_CHART_MARGIN_WITH_PCT_AXIS = {"l": 48, "r": 72, "t": 56, "b": 64}
BTC_LINE_COLOR = "#F7931A"
ETH_LINE_COLOR = "#627EEA"
TCP_TRACE_NAME = "TCP"


def nav_pct_axis_baseline() -> float:
    from tcp_comparison import OVERLAY_BASELINE

    return float(OVERLAY_BASELINE)


def dollar_value_to_pct_return(dollar_value: float, baseline: Optional[float] = None) -> float:
    base = float(baseline if baseline is not None else nav_pct_axis_baseline())
    if not base:
        return 0.0
    return (float(dollar_value) / base - 1.0) * 100.0


def dollar_range_to_pct_range(
    dollar_range: Sequence[float],
    baseline: Optional[float] = None,
) -> List[float]:
    return [
        dollar_value_to_pct_return(dollar_range[0], baseline),
        dollar_value_to_pct_return(dollar_range[1], baseline),
    ]


def nav_pct_axis_ticks(
    dollar_range: Sequence[float],
    baseline: Optional[float] = None,
) -> tuple[List[float], List[str]]:
    """Dollar tick positions with percent labels (shared y scale)."""
    base = float(baseline if baseline is not None else nav_pct_axis_baseline())
    pct_min = dollar_value_to_pct_return(dollar_range[0], base)
    pct_max = dollar_value_to_pct_return(dollar_range[1], base)
    span = abs(pct_max - pct_min)
    if span > 50:
        step = 10
    elif span > 20:
        step = 5
    elif span > 10:
        step = 2
    else:
        step = 1
    tick_start = int(pct_min / step - 1) * step
    tick_end = int(pct_max / step + 2) * step
    pct_ticks = list(range(tick_start, tick_end + step, step))
    tickvals = [base * (1.0 + pct / 100.0) for pct in pct_ticks]
    ticktext = [f"{pct:.0f}%" for pct in pct_ticks]
    return tickvals, ticktext


def build_nav_pct_yaxis2(
    dollar_range: Optional[Sequence[float]],
    *,
    visible: bool,
) -> Dict[str, Any]:
    """Secondary axis shares the dollar scale; tick text shows return since inception."""
    layout: Dict[str, Any] = {
        "overlaying": "y",
        "side": "right",
        "showgrid": False,
        "zeroline": False,
        "visible": True,
        "automargin": True,
        "fixedrange": True,
        "showticklabels": visible,
        "showline": visible,
        "ticklen": 0 if not visible else 4,
        "title": {"text": NAV_PCT_AXIS_TITLE if visible else ""},
    }
    if dollar_range is not None and len(dollar_range) == 2:
        tickvals, ticktext = nav_pct_axis_ticks(dollar_range)
        layout["tickmode"] = "array"
        layout["tickvals"] = tickvals
        layout["ticktext"] = ticktext
        layout["range"] = [float(dollar_range[0]), float(dollar_range[1])]
    return layout


def _figure_as_dict(figure: Any) -> Mapping[str, Any]:
    if hasattr(figure, "to_plotly_json"):
        return figure.to_plotly_json()
    return figure


def _figure_shows_pct_axis(figure: Mapping[str, Any]) -> bool:
    yaxis2 = figure.get("layout", {}).get("yaxis2") or {}
    if not yaxis2:
        return False
    title = yaxis2.get("title") or {}
    title_text = title.get("text") if isinstance(title, dict) else title
    return bool(yaxis2.get("showticklabels")) or title_text == NAV_PCT_AXIS_TITLE


def _return_since_baseline(values: Sequence[float], baseline: float) -> List[float]:
    if not baseline:
        return [0.0 for _ in values]
    return [float(value) / float(baseline) - 1.0 for value in values]


def _visible_y_range(
    tcp_values: Sequence[float],
    btc_values: Sequence[float],
    eth_values: Sequence[float],
    *,
    show_btc: bool,
    show_eth: bool,
) -> Optional[List[float]]:
    values: List[float] = [float(v) for v in tcp_values if v is not None and math.isfinite(float(v))]
    if show_btc:
        values.extend(float(v) for v in btc_values if v is not None and math.isfinite(float(v)))
    if show_eth:
        values.extend(float(v) for v in eth_values if v is not None and math.isfinite(float(v)))
    if not values:
        return None
    low = min(values)
    high = max(values)
    pad = max((high - low) * 0.05, 250.0)
    return [low - pad, high + pad]


def build_tcp_nav_chart_figure(
    overlay_bundle: Any,
    *,
    show_btc: bool = False,
    show_eth: bool = False,
    show_pct_axis: bool = False,
) -> go.Figure:
    """Single NAV chart with optional BTC/ETH overlays. TCP accounting is unchanged."""
    fig = go.Figure()
    if overlay_bundle is None or overlay_bundle.tcp_nav.empty:
        fig.add_annotation(
            text="No NAV data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
    else:
        dates = overlay_bundle.tcp_dates
        tcp_values = overlay_bundle.tcp_nav.astype(float).tolist()
        btc_values = overlay_bundle.btc_overlay.astype(float).tolist()
        eth_values = overlay_bundle.eth_overlay.astype(float).tolist()
        tcp_base = float(overlay_bundle.baseline_nav or tcp_values[0])
        from tcp_comparison import OVERLAY_BASELINE

        overlay_base = float(OVERLAY_BASELINE)
        tcp_returns = _return_since_baseline(tcp_values, tcp_base)
        btc_returns = _return_since_baseline(btc_values, overlay_base)
        eth_returns = _return_since_baseline(eth_values, overlay_base)
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=tcp_values,
                mode="lines",
                name=TCP_TRACE_NAME,
                line={"color": PRIMARY_COLOR, "width": 2.4},
                customdata=tcp_returns,
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    f"{TCP_TRACE_NAME}=$%{{y:,.2f}}<br>"
                    "Return since inception=%{customdata:.2%}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=btc_values,
                mode="lines",
                name="BTC",
                visible=show_btc,
                line={"color": BTC_LINE_COLOR, "width": 2.0},
                customdata=btc_returns,
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    "BTC=$%{y:,.2f}<br>"
                    "Return since inception=%{customdata:.2%}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=eth_values,
                mode="lines",
                name="ETH",
                visible=show_eth,
                line={"color": ETH_LINE_COLOR, "width": 2.0},
                customdata=eth_returns,
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    "ETH=$%{y:,.2f}<br>"
                    "Return since inception=%{customdata:.2%}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[dates[-1]],
                y=[tcp_values[-1]],
                mode="markers",
                name="TCP % axis anchor",
                yaxis="y2",
                marker={"opacity": 0, "size": 1},
                showlegend=False,
                hoverinfo="skip",
            )
        )
    y_range = None
    if overlay_bundle is not None and not overlay_bundle.tcp_nav.empty:
        y_range = _visible_y_range(
            overlay_bundle.tcp_nav.astype(float).tolist(),
            overlay_bundle.btc_overlay.astype(float).tolist(),
            overlay_bundle.eth_overlay.astype(float).tolist(),
            show_btc=show_btc,
            show_eth=show_eth,
        )
    margin = (
        dict(NAV_CHART_MARGIN_WITH_PCT_AXIS)
        if show_pct_axis
        else dict(NAV_CHART_MARGIN_DEFAULT)
    )
    fig.update_layout(
        title={"text": NAV_CHART_TITLE, "x": 0.5, "xanchor": "center"},
        template="ggplot2",
        plot_bgcolor=GREY_BG,
        paper_bgcolor=WHITE_BG,
        xaxis_title="Date",
        yaxis_title="Value ($)",
        autosize=True,
        showlegend=False,
        hovermode="x unified",
        uirevision=NAV_CHART_UIREVISION,
        margin=margin,
        yaxis2=build_nav_pct_yaxis2(y_range, visible=show_pct_axis),
    )
    fig.update_xaxes(showgrid=True, automargin=True, tickangle=-25)
    yaxis_layout: Dict[str, Any] = {
        "showgrid": True,
        "automargin": True,
        "tickprefix": "$",
        "tickformat": ",.0f",
    }
    if y_range is not None:
        yaxis_layout["range"] = y_range
    fig.update_layout(yaxis=yaxis_layout)
    return fig


def build_tcp_nav_figure(
    canonical_records: Sequence[Mapping[str, Any]],
    *,
    show_percentage_axis: bool = False,
) -> go.Figure:
    """Backward-compatible TCP-only figure (tests and legacy callers)."""
    from tcp_nav_overlays import build_nav_overlay_bundle

    bundle = build_nav_overlay_bundle(canonical_records, None, None)
    return build_tcp_nav_chart_figure(
        bundle,
        show_btc=False,
        show_eth=False,
        show_pct_axis=show_percentage_axis,
    )


def _resolve_nav_chart_dollar_y_range(
    figure: Any,
    *,
    show_btc: bool,
    show_eth: bool,
    explicit_range: Optional[Sequence[float]] = None,
) -> Optional[List[float]]:
    figure = _figure_as_dict(figure)
    if explicit_range is not None and len(explicit_range) == 2:
        return [float(explicit_range[0]), float(explicit_range[1])]
    layout_range = figure.get("layout", {}).get("yaxis", {}).get("range")
    if layout_range and len(layout_range) == 2:
        return [float(layout_range[0]), float(layout_range[1])]
    if not figure.get("data") or len(figure["data"]) < 4:
        return None
    return _visible_y_range(
        figure["data"][0].get("y", []),
        figure["data"][1].get("y", []),
        figure["data"][2].get("y", []),
        show_btc=show_btc,
        show_eth=show_eth,
    )


def _patch_nav_chart_yaxis2_range(
    patched: Any,
    figure: Mapping[str, Any],
    dollar_range: Optional[Sequence[float]],
) -> None:
    if not _figure_shows_pct_axis(figure):
        return
    if dollar_range is None or len(dollar_range) != 2:
        return
    patched["layout"]["yaxis2"]["range"] = dollar_range_to_pct_range(dollar_range)


def patch_nav_chart_overlay_visibility(
    figure: Any,
    *,
    show_btc: bool,
    show_eth: bool,
    show_pct_axis: bool = False,
) -> Dict[str, Any]:
    """Toggle overlay traces without rebuilding the figure (preserves zoom)."""
    from dash import Patch

    figure = _figure_as_dict(figure)
    patched = Patch()
    if not figure or not figure.get("data"):
        return patched
    if len(figure["data"]) < 4:
        return patched
    patched["data"][1]["visible"] = show_btc
    patched["data"][2]["visible"] = show_eth
    tcp_y = figure["data"][0].get("y", [])
    btc_y = figure["data"][1].get("y", [])
    eth_y = figure["data"][2].get("y", [])
    y_range = _visible_y_range(tcp_y, btc_y, eth_y, show_btc=show_btc, show_eth=show_eth)
    if y_range is not None:
        patched["layout"]["yaxis"]["range"] = y_range
        if show_pct_axis or _figure_shows_pct_axis(figure):
            patched["layout"]["yaxis2"] = build_nav_pct_yaxis2(y_range, visible=True)
            patched["layout"]["margin"] = dict(NAV_CHART_MARGIN_WITH_PCT_AXIS)
    patched["layout"]["uirevision"] = figure.get("layout", {}).get("uirevision", NAV_CHART_UIREVISION)
    return patched


def patch_nav_chart_pct_axis(
    figure: Any,
    *,
    show_pct_axis: bool,
    show_btc: bool,
    show_eth: bool,
) -> Dict[str, Any]:
    """Show or hide the synchronized return (%) axis without rebuilding traces."""
    figure = deepcopy(_figure_as_dict(figure))
    if not figure:
        return figure
    margin = NAV_CHART_MARGIN_WITH_PCT_AXIS if show_pct_axis else NAV_CHART_MARGIN_DEFAULT
    figure.setdefault("layout", {})["margin"] = dict(margin)
    dollar_range = _resolve_nav_chart_dollar_y_range(
        figure,
        show_btc=show_btc,
        show_eth=show_eth,
    )
    figure["layout"]["yaxis2"] = build_nav_pct_yaxis2(dollar_range, visible=show_pct_axis)
    figure["layout"]["uirevision"] = figure.get("layout", {}).get("uirevision", NAV_CHART_UIREVISION)
    return figure


def patch_nav_chart_pct_axis_from_relayout(
    figure: Any,
    relayout_data: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    """Keep the right-hand % axis aligned with the primary dollar axis after zoom/pan."""
    figure = _figure_as_dict(figure)
    if not figure:
        return None
    if not relayout_data:
        return None
    dollar_range: Optional[List[float]] = None
    if "yaxis.range" in relayout_data:
        raw = relayout_data["yaxis.range"]
        if raw and len(raw) == 2:
            dollar_range = [float(raw[0]), float(raw[1])]
    elif "yaxis.range[0]" in relayout_data and "yaxis.range[1]" in relayout_data:
        dollar_range = [
            float(relayout_data["yaxis.range[0]"]),
            float(relayout_data["yaxis.range[1]"]),
        ]
    elif relayout_data.get("yaxis.autorange"):
        show_btc = len(figure.get("data", ())) > 1 and figure["data"][1].get("visible") in (True, "true")
        show_eth = len(figure.get("data", ())) > 2 and figure["data"][2].get("visible") in (True, "true")
        dollar_range = _resolve_nav_chart_dollar_y_range(
            figure,
            show_btc=show_btc,
            show_eth=show_eth,
        )
    if dollar_range is None:
        return None
    updated = deepcopy(figure)
    layout = updated.setdefault("layout", {})
    layout["yaxis2"] = build_nav_pct_yaxis2(dollar_range, visible=True)
    layout["uirevision"] = layout.get("uirevision", NAV_CHART_UIREVISION)
    return updated


def _format_label_date(row_date: date) -> str:
    return f"{row_date.strftime('%B %d, %Y')}{LABEL_DATE_SUFFIX}"


def build_tcp_current_data_labels(
    canonical_records: Sequence[Mapping[str, Any]],
) -> CurrentDataLabels:
    """Desktop and mobile labels share the same latest completed ledger date."""
    if not canonical_records:
        return CurrentDataLabels(
            header=LABEL_UNAVAILABLE,
            date_line="",
            source_date=None,
        )

    latest = _coerce_row_date(canonical_records[-1]["Date"])
    date_line = _format_label_date(latest)
    return CurrentDataLabels(header=LABEL_HEADER, date_line=date_line, source_date=latest)


def propagate_tcp_dashboard(
    canonical_records: Sequence[Mapping[str, Any]],
    *,
    benchmark_result: Optional[Any] = None,
    btc_benchmark_result: Optional[Any] = None,
    eth_benchmark_result: Optional[Any] = None,
    tranche_count: Optional[int] = None,
) -> DashboardPropagation:
    """Recompute all Step 7 dynamic outputs from one canonical NAV snapshot."""
    from tcp_benchmarks import BENCHMARK_STATUS_UNAVAILABLE
    from tcp_drawdown import build_drawdown_dataframe, normalize_drawdown_nav_records

    records_copy = deepcopy(list(canonical_records))
    nav_series = canonical_records_to_series(records_copy)
    baseline = float(nav_series.iloc[0]) if not nav_series.empty else None
    latest_date = _coerce_row_date(records_copy[-1]["Date"]) if records_copy else None
    latest_nav = _coerce_nav(records_copy[-1]["NAV"]) if records_copy else None
    labels = build_tcp_current_data_labels(records_copy)

    spxtr_returns = None
    btc_returns = None
    eth_returns = None
    benchmark_pairs = (
        (benchmark_result, "spxtr"),
        (btc_benchmark_result, "btc"),
        (eth_benchmark_result, "eth"),
    )
    for result, key in benchmark_pairs:
        if result is None or result.status == BENCHMARK_STATUS_UNAVAILABLE:
            continue
        if result.returns is None or result.returns.empty:
            continue
        if key == "spxtr":
            spxtr_returns = result.returns
        elif key == "btc":
            btc_returns = result.returns
        else:
            eth_returns = result.returns

    return DashboardPropagation(
        canonical_records=records_copy,
        monthly_calendar=recompute_tcp_monthly_performance(records_copy, baseline_nav=baseline),
        daily_performance=recompute_tcp_daily_metrics(records_copy, baseline_nav=baseline),
        drawdown_profile=build_drawdown_dataframe(
            records_copy,
            tranche_count=tranche_count,
            spxtr_aligned_returns=spxtr_returns,
            btc_aligned_returns=btc_returns,
            eth_aligned_returns=eth_returns,
        ),
        nav_figure=build_tcp_nav_figure(records_copy),
        desktop_label=labels,
        mobile_label=labels,
        latest_date=latest_date,
        latest_nav=latest_nav,
        baseline_nav=baseline,
        nav_point_count=len(records_copy),
    )
