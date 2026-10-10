"""NAV overlay math and single-chart placement."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from layout_helpers import layout_text as render_layout_text
from tcp_benchmarks import (
    BENCHMARK_STATUS_READY,
    BENCHMARK_STATUS_STALE,
    BENCHMARK_STATUS_UNAVAILABLE,
    BTC_SYMBOL,
    ETH_SYMBOL,
    BenchmarkResult,
)
from tcp_comparison import (
    OVERLAY_BASELINE,
    OVERLAY_DISCLOSURE,
    align_overlays_to_tcp_dates,
    common_comparison_cutoff,
    compound_benchmark_to_baseline,
    normalize_tcp_to_baseline,
    overlay_price_cutoff_label,
)
from tcp_dashboard import (
    NAV_CHART_TITLE,
    NAV_PCT_AXIS_TITLE,
    build_tcp_nav_chart_figure,
    build_tcp_nav_figure,
    canonical_nav_records_from_ledger,
    dollar_range_to_pct_range,
    dollar_value_to_pct_return,
    nav_pct_axis_baseline,
    patch_nav_chart_overlay_visibility,
    patch_nav_chart_pct_axis,
    propagate_tcp_dashboard,
)
from tcp_nav_overlays import build_nav_overlay_bundle
from tcp_public_sections import build_nav_chart_section


def _series(values, start="2026-01-20", freq="D"):
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float)


def _ready(symbol: str, name: str, series: pd.Series, as_of: str | None = None) -> BenchmarkResult:
    return BenchmarkResult(
        status=BENCHMARK_STATUS_READY,
        symbol=symbol,
        display_name=name,
        as_of=as_of or series.index.max().strftime("%Y-%m-%d"),
        fetched_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        returns=series,
        warning=None,
    )


def test_tcp_btc_eth_overlay_start_at_50000_on_baseline():
    records = [
        {"Date": "2026-01-20", "NAV": 50000.0},
        {"Date": "2026-01-21", "NAV": 51000.0},
        {"Date": "2026-01-22", "NAV": 52000.0},
    ]
    btc = _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02, -0.01], start="2026-01-20", freq="D"))
    eth = _ready(ETH_SYMBOL, "ETH", _series([0.00, 0.03, 0.01], start="2026-01-20", freq="D"))
    bundle = build_nav_overlay_bundle(records, btc, eth)
    assert bundle.tcp_nav.iloc[0] == pytest.approx(50000.0)
    assert bundle.btc_overlay.iloc[0] == pytest.approx(OVERLAY_BASELINE)
    assert bundle.eth_overlay.iloc[0] == pytest.approx(OVERLAY_BASELINE)


def test_common_cutoff_is_min_of_required_series():
    cutoff = common_comparison_cutoff("2026-10-08", "2026-10-10", "2026-10-07")
    assert cutoff == pd.Timestamp("2026-10-07")


def test_overlay_bundle_respects_cutoff():
    records = [
        {"Date": "2026-01-20", "NAV": 50000.0},
        {"Date": "2026-01-21", "NAV": 51000.0},
        {"Date": "2026-01-22", "NAV": 52000.0},
    ]
    btc = _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02, 0.03, 0.04], start="2026-01-20", freq="D"))
    eth = _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D"))
    bundle = build_nav_overlay_bundle(records, btc, eth)
    assert bundle.chart_price_through == pd.Timestamp("2026-01-21")
    assert bundle.frame.index.max() == pd.Timestamp("2026-01-21")


def test_tcp_nav_chart_preserves_raw_nav_values():
    records = [{"Date": "2026-01-20", "NAV": 50013.472}, {"Date": "2026-01-21", "NAV": 50031.504}]
    bundle = build_nav_overlay_bundle(records, None, None)
    fig = build_tcp_nav_chart_figure(bundle)
    assert fig.data[0].y[0] == pytest.approx(50013.472)
    legacy = build_tcp_nav_figure(records)
    assert legacy.data[0].y[0] == pytest.approx(50013.472)


def test_pct_axis_baseline_alignment_examples():
    baseline = nav_pct_axis_baseline()
    assert baseline == pytest.approx(OVERLAY_BASELINE)
    assert dollar_value_to_pct_return(40_000.0, baseline) == pytest.approx(-20.0)
    assert dollar_value_to_pct_return(50_000.0, baseline) == pytest.approx(0.0)
    assert dollar_value_to_pct_return(60_000.0, baseline) == pytest.approx(20.0)
    assert dollar_value_to_pct_return(75_000.0, baseline) == pytest.approx(50.0)


def test_pct_axis_range_tracks_dollar_range():
    dollar_range = [40_000.0, 75_000.0]
    assert dollar_range_to_pct_range(dollar_range) == pytest.approx([-20.0, 50.0])


def test_pct_axis_hidden_by_default():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 51000.0}]
    bundle = build_nav_overlay_bundle(records, None, None)
    fig = build_tcp_nav_chart_figure(bundle)
    assert fig.layout.yaxis.title.text == "Value ($)"
    yaxis2 = fig.layout.yaxis2
    assert yaxis2 is None or yaxis2.visible is False


def test_pct_axis_visible_when_enabled():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 51000.0}]
    bundle = build_nav_overlay_bundle(records, None, None)
    fig = build_tcp_nav_chart_figure(bundle, show_pct_axis=True)
    assert fig.layout.yaxis2.visible is True
    assert NAV_PCT_AXIS_TITLE in (fig.layout.yaxis2.title.text or "")
    assert fig.layout.yaxis2.range == pytest.approx(
        dollar_range_to_pct_range(fig.layout.yaxis.range),
        rel=1e-6,
    )


def test_pct_axis_toggle_does_not_change_tcp_trace_values():
    records = [{"Date": "2026-01-20", "NAV": 50013.472}, {"Date": "2026-01-21", "NAV": 50031.504}]
    bundle = build_nav_overlay_bundle(records, None, None)
    fig = build_tcp_nav_chart_figure(bundle)
    before_y = list(fig.data[0].y)
    patch_nav_chart_pct_axis(fig, show_pct_axis=True, show_btc=False, show_eth=False)
    assert list(fig.data[0].y) == before_y
    assert fig.data[0].y[0] == pytest.approx(50013.472)


def test_overlay_visibility_flags_on_rebuild():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 51000.0}]
    bundle = build_nav_overlay_bundle(
        records,
        _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02], start="2026-01-20", freq="D")),
        _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D")),
    )
    fig = build_tcp_nav_chart_figure(bundle, show_btc=True, show_eth=False)
    assert fig.data[1].visible is True
    assert fig.data[2].visible is False
    fig_tcp_only = build_tcp_nav_chart_figure(bundle, show_btc=False, show_eth=False)
    assert fig_tcp_only.data[1].visible is False
    assert fig_tcp_only.data[2].visible is False


def test_overlay_attribution_names_price_provider():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 50100.0}]
    btc = _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02], start="2026-01-20", freq="D"), as_of="2026-10-10")
    eth = _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D"), as_of="2026-10-10")
    bundle = build_nav_overlay_bundle(records, btc, eth)
    assert "Yahoo Finance" in bundle.attribution_row
    assert "BTC-USD" in bundle.attribution_row
    assert "ETH-USD" in bundle.attribution_row
    assert "prices through" in bundle.attribution_row
    assert "cache refreshed" in bundle.attribution_row


def test_single_nav_chart_layout_markers(layout_text):
    nav_at = layout_text.find("Non-Compounded NAV Since Inception")
    strategy_at = layout_text.find("Strategy Overview")
    assert nav_at != -1
    assert strategy_at != -1
    assert nav_at < strategy_at
    assert layout_text.count("nav-preview-graph") == 1
    assert "tcp-comparison-graph" not in layout_text
    assert "Growth of $50,000 Since Inception" not in layout_text
    assert "tcp-overlay-btc" in layout_text
    assert "tcp-overlay-eth" in layout_text
    assert "tcp-overlay-pct-axis" in layout_text
    assert "tcp-overlay-attribution" in layout_text


def test_overlay_disclosure_present(layout_text):
    assert "$50,000" in OVERLAY_DISCLOSURE
    assert "Yahoo Finance" in layout_text or "adjusted-close" in layout_text


def test_unavailable_benchmark_does_not_crash_overlay():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 50100.0}]
    missing = BenchmarkResult(
        status=BENCHMARK_STATUS_UNAVAILABLE,
        symbol=BTC_SYMBOL,
        display_name="BTC",
        as_of=None,
        fetched_at=None,
        returns=None,
        warning="BTC benchmark data is temporarily unavailable.",
    )
    bundle = build_nav_overlay_bundle(records, missing, missing)
    fig = build_tcp_nav_chart_figure(bundle)
    assert fig is not None
    assert len(fig.data) == 3


def test_existing_drawdown_calculations_unchanged(tmp_path):
    from tcp_config import load_config
    from tcp_ledger import load_ledger

    cfg = load_config()
    if not Path(cfg.workbook_path).is_file():
        pytest.skip("TCP workbook not available")
    ledger = load_ledger(cfg.workbook_path, cfg.sheet_name)
    canonical = canonical_nav_records_from_ledger(ledger.completed_records)
    before = deepcopy(propagate_tcp_dashboard(canonical).drawdown_profile)
    build_nav_overlay_bundle(
        canonical,
        _ready(BTC_SYMBOL, "BTC", _series([0.001] * 20, start="2026-01-20", freq="D")),
        _ready(ETH_SYMBOL, "ETH", _series([0.001] * 20, start="2026-01-20", freq="D")),
    )
    after = propagate_tcp_dashboard(canonical).drawdown_profile
    assert before["TCP (Inception)"].equals(after["TCP (Inception)"])


@pytest.fixture(scope="module")
def layout_text():
    import os

    saved = {
        "TCP_V2_ADMIN_TOKEN": os.environ.get("TCP_V2_ADMIN_TOKEN"),
        "TCP_V2_SESSION_SECRET": os.environ.get("TCP_V2_SESSION_SECRET"),
    }
    os.environ["TCP_V2_ADMIN_TOKEN"] = "comparison-test-token"
    os.environ["TCP_V2_SESSION_SECRET"] = "comparison-test-secret"
    from tcp_config import AdminAuthSettings
    from tcp_layout_support import tcp_layout_benchmark_patches
    from tcp_ts_v2 import create_app

    with tcp_layout_benchmark_patches():
        app, _cfg, state, _auth, _holder = create_app(
            auth_settings=AdminAuthSettings(
                admin_token="comparison-test-token",
                session_secret="comparison-test-secret",
            )
        )
        if state.snapshot is None:
            pytest.skip("runtime unavailable")
        text = render_layout_text(app)
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return text


def test_live_btc_overlay_matches_compounded_history_on_tcp_dates():
    cache = Path(r"C:\HC\data\tcp\benchmark\tcp_benchmark_btc_cache.json")
    state = Path(r"C:\HC\data\tcp\tcp_daily_returns_secret_state.json")
    if not cache.is_file() or not state.is_file():
        pytest.skip("production data not available on this host")
    import json

    from tcp_benchmarks import BenchmarkResult
    from tcp_comparison import align_overlays_to_tcp_dates

    payload = json.loads(cache.read_text(encoding="utf-8"))
    dates = [row["date"] for row in payload["returns"]]
    values = [row["value"] for row in payload["returns"]]
    returns = pd.Series(values, index=pd.to_datetime(dates), dtype=float)
    btc = BenchmarkResult(
        status=BENCHMARK_STATUS_READY,
        symbol=BTC_SYMBOL,
        display_name="BTC",
        as_of=payload.get("as_of"),
        fetched_at=payload.get("fetched_at"),
        returns=returns,
        warning=None,
    )
    eth = _ready(ETH_SYMBOL, "ETH", returns * 0 + 0.001)
    ledger = json.loads(state.read_text(encoding="utf-8"))
    records = [{"Date": row["Date"], "NAV": row["nav-x1"]} for row in ledger["records"]]
    bundle = build_nav_overlay_bundle(records, btc, eth)
    expected_growth = compound_benchmark_to_baseline(
        returns,
        inception=bundle.baseline_date,
        cutoff=bundle.chart_price_through,
    )
    expected = align_overlays_to_tcp_dates(bundle.tcp_nav, expected_growth, bundle.eth_overlay)["BTC"]
    pd.testing.assert_series_equal(bundle.btc_overlay, expected, check_names=False)
