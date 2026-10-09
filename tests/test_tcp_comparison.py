"""Normalized TCP/BTC/ETH comparison series and public-chart placement."""
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
    COMPARISON_BASELINE,
    COMPARISON_DISCLOSURE,
    align_comparison_to_tcp_dates,
    build_normalized_comparison_bundle,
    common_comparison_cutoff,
    comparison_cutoff_label,
    compound_benchmark_to_baseline,
    normalize_tcp_to_baseline,
)
from tcp_dashboard import build_tcp_comparison_figure, canonical_nav_records_from_ledger, propagate_tcp_dashboard
from tcp_public_sections import COMPARISON_CHART_TITLE_PLAIN, build_comparison_chart_block


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


def test_tcp_btc_eth_normalized_series_start_at_50000():
    tcp = _series([40000.0, 41000.0, 42000.0], start="2026-01-20", freq="B")
    btc = _series([0.01, 0.02, -0.01], start="2026-01-20", freq="D")
    eth = _series([0.00, 0.03, 0.01], start="2026-01-20", freq="D")
    tcp_norm = normalize_tcp_to_baseline(tcp)
    btc_norm = compound_benchmark_to_baseline(
        btc, inception="2026-01-20", cutoff="2026-01-22"
    )
    eth_norm = compound_benchmark_to_baseline(
        eth, inception="2026-01-20", cutoff="2026-01-22"
    )
    assert tcp_norm.iloc[0] == pytest.approx(COMPARISON_BASELINE)
    assert btc_norm.iloc[0] == pytest.approx(COMPARISON_BASELINE)
    assert eth_norm.iloc[0] == pytest.approx(COMPARISON_BASELINE)


def test_common_cutoff_is_min_of_required_series():
    cutoff = common_comparison_cutoff("2026-10-08", "2026-10-10", "2026-10-07")
    assert cutoff == pd.Timestamp("2026-10-07")


def test_common_cutoff_respected_in_frame():
    records = [
        {"Date": "2026-01-20", "NAV": 50000.0},
        {"Date": "2026-01-21", "NAV": 51000.0},
        {"Date": "2026-01-22", "NAV": 52000.0},
    ]
    btc = _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02, 0.03, 0.04], start="2026-01-20", freq="D"))
    eth = _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D"))
    bundle = build_normalized_comparison_bundle(records, btc, eth)
    assert bundle.cutoff == pd.Timestamp("2026-01-21")
    assert bundle.frame.index.max() == pd.Timestamp("2026-01-21")


def test_no_benchmark_observation_beyond_common_cutoff():
    # TCP last completed Thursday; BTC/ETH continue through the weekend.
    records = [
        {"Date": "2026-10-07", "NAV": 50000.0},
        {"Date": "2026-10-08", "NAV": 50500.0},
    ]
    crypto = _series([0.01, 0.02, 0.03, 0.04], start="2026-10-07", freq="D")
    bundle = build_normalized_comparison_bundle(
        records,
        _ready(BTC_SYMBOL, "BTC", crypto),
        _ready(ETH_SYMBOL, "ETH", crypto),
    )
    assert bundle.cutoff == pd.Timestamp("2026-10-08")
    assert bundle.frame.index.max() <= bundle.cutoff
    assert pd.Timestamp("2026-10-10") not in bundle.frame.index
    assert pd.Timestamp("2026-10-11") not in bundle.frame.index


def test_align_comparison_keeps_only_tcp_dates():
    tcp = _series([50000.0, 51000.0], start="2026-10-07", freq="D")
    btc = _series([50000.0, 50100.0, 50200.0, 51000.0], start="2026-10-07", freq="D")
    eth = _series([50000.0, 49900.0, 49800.0, 49700.0], start="2026-10-07", freq="D")
    frame = align_comparison_to_tcp_dates(tcp, btc, eth)
    assert list(frame.index) == list(tcp.index)


def test_comparison_chart_title_and_disclosure_helpers():
    assert "October 08, 2026" in comparison_cutoff_label("2026-10-08")
    assert "$50,000" in COMPARISON_DISCLOSURE
    assert "does not represent" in COMPARISON_DISCLOSURE.lower()


def test_stale_benchmark_disclosure_renders():
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 50100.0}]
    stale_btc = BenchmarkResult(
        status=BENCHMARK_STATUS_STALE,
        symbol=BTC_SYMBOL,
        display_name="BTC",
        as_of="2026-10-01",
        fetched_at="2026-10-01T00:00:00+00:00",
        returns=_series([0.01, 0.02], start="2026-01-20", freq="D"),
        warning="Benchmark data is stale; showing last successful download.",
    )
    eth = _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D"))
    bundle = build_normalized_comparison_bundle(records, stale_btc, eth)
    block = build_comparison_chart_block(build_tcp_comparison_figure(bundle), bundle)
    text = str(block)
    assert "stale" in text.lower()
    assert "2026-10-01" in text
    assert "tcp-comparison-stale-notice" in text


def test_unavailable_benchmark_does_not_crash_comparison():
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
    bundle = build_normalized_comparison_bundle(records, missing, missing)
    fig = build_tcp_comparison_figure(bundle)
    assert fig is not None
    assert bundle.cutoff is None


def test_existing_drawdown_calculations_unchanged(tmp_path):
    from tcp_config import load_config
    from tcp_ledger import load_ledger

    cfg = load_config()
    if not Path(cfg.workbook_path).is_file():
        pytest.skip("TCP workbook not available")
    ledger = load_ledger(cfg.workbook_path, cfg.sheet_name)
    canonical = canonical_nav_records_from_ledger(ledger.completed_records)
    before = deepcopy(propagate_tcp_dashboard(canonical).drawdown_profile)
    build_normalized_comparison_bundle(
        canonical,
        _ready(BTC_SYMBOL, "BTC", _series([0.001] * 20, start="2026-01-20", freq="D")),
        _ready(ETH_SYMBOL, "ETH", _series([0.001] * 20, start="2026-01-20", freq="D")),
    )
    after = propagate_tcp_dashboard(canonical).drawdown_profile
    assert before["TCP (Inception)"].equals(after["TCP (Inception)"])
    assert list(before.columns) == list(after.columns)


def test_comparison_does_not_write_state_json(tmp_path):
    state_path = tmp_path / "tcp_daily_returns_secret_state.json"
    state_path.write_text('{"revision": 89}', encoding="utf-8")
    before = state_path.read_text(encoding="utf-8")
    records = [{"Date": "2026-01-20", "NAV": 50000.0}, {"Date": "2026-01-21", "NAV": 50100.0}]
    build_normalized_comparison_bundle(
        records,
        _ready(BTC_SYMBOL, "BTC", _series([0.01, 0.02], start="2026-01-20", freq="D")),
        _ready(ETH_SYMBOL, "ETH", _series([0.01, 0.02], start="2026-01-20", freq="D")),
    )
    assert state_path.read_text(encoding="utf-8") == before


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


def test_comparison_chart_exists_below_nav_and_above_strategy(layout_text):
    nav_at = layout_text.find("Non-Compounded NAV Since Inception")
    growth_at = layout_text.find(COMPARISON_CHART_TITLE_PLAIN)
    if growth_at < 0:
        growth_at = layout_text.find("Growth of $50,000")
    strategy_at = layout_text.find("Strategy Overview")
    assert nav_at != -1
    assert growth_at != -1
    assert strategy_at != -1
    assert nav_at < growth_at < strategy_at
    assert "tcp-comparison-graph" in layout_text
    assert "tcp-comparison-disclosure" in layout_text
    assert "tcp-comparison-cutoff" in layout_text
