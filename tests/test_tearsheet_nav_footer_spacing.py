"""Presentation-only regression for TKP/YQ NAV chart footer spacing."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = REPO_ROOT / "assets" / "styles.css"
TKP_PATH = REPO_ROOT / "tkp_ts.py"
YQ_PATH = REPO_ROOT / "yq_ts.py"


def _css_text() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def test_shared_css_contains_tearsheet_nav_footer_spacing():
    css = _css_text()
    assert ".tearsheet-nav-chart-plot-wrap" in css
    assert ".tearsheet-nav-chart-notes" in css
    assert ".tearsheet-nav-footnote-primary" in css
    assert ".tearsheet-nav-footnote-secondary" in css
    assert "overflow: hidden" in css
    assert "height: clamp(360px, 46vh, 460px)" in css


def test_tkp_source_uses_plot_wrap_and_bottom_margin():
    text = TKP_PATH.read_text(encoding="utf-8")
    assert "tearsheet-nav-chart-plot-wrap" in text
    assert "tearsheet-nav-chart-notes" in text
    assert "NAV_CHART_MARGIN_DEFAULT = {\"l\": 40, \"r\": 10, \"t\": 40, \"b\": 64}" in text
    assert "style={\"marginTop\": \"4rem\"}" not in text
    assert "maxHeight\": \"400px\"" not in text


def test_yq_source_uses_plot_wrap_and_bottom_margin():
    text = YQ_PATH.read_text(encoding="utf-8")
    assert "tearsheet-nav-chart-plot-wrap" in text
    assert "tearsheet-nav-chart-notes" in text
    assert "margin={\"l\": 40, \"r\": 10, \"t\": 40, \"b\": 64}" in text
    assert "style={\"marginTop\": \"4rem\"}" not in text


def test_tkp_nav_figure_keeps_bottom_margin():
    try:
        import tkp_ts
    except SystemExit as exc:
        pytest.skip(f"tkp_ts exited at import: {exc}")

    fig = tkp_ts.build_NAV_figure()
    margin = fig.layout.margin
    assert int(margin.b) == 64


def test_yq_nav_figure_keeps_bottom_margin():
    try:
        import yq_ts
    except SystemExit as exc:
        pytest.skip(f"yq_ts exited at import: {exc}")

    fig = yq_ts.build_NAV_figure()
    margin = fig.layout.margin
    assert int(margin.b) == 64
