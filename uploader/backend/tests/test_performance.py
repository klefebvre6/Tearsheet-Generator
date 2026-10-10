"""GET /api/performance — combined mode, program mode, and benchmark rebasing."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from tests.conftest import _make_client


def _next_weekday(start: date, target_weekday: int) -> date:
    """First date on/after `start` that falls on `target_weekday` (Mon=0 ... Sun=6).

    Computed rather than hardcoded so these tests never depend on what
    particular weekday any specific calendar date happens to be.
    """
    offset = (target_weekday - start.weekday()) % 7
    return start + timedelta(days=offset)


_A_MONDAY = _next_weekday(date(2026, 7, 1), 0)
_A_SATURDAY = _next_weekday(date(2026, 7, 1), 5)


def _post(client, program, date_str, **fields):
    payload = {"date": date_str, **fields}
    r = client.post(f"/api/rows/{program}", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# --- combined mode ----------------------------------------------------------
def test_combined_mode_uses_trading_day_index(sandbox_client):
    d0, d1 = _A_MONDAY.isoformat(), (_A_MONDAY + timedelta(days=1)).isoformat()
    _post(sandbox_client, "TKP", d0, stonex_nlv=100000, plus500_nlv=0)
    _post(sandbox_client, "TKP", d1, stonex_nlv=101000, plus500_nlv=0)

    r = sandbox_client.get("/api/performance?mode=combined")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "combined"
    assert body["x_axis"] == "trading_day"
    assert body["base_value"] == 100000
    assert body["program"] is None

    tkp_points = body["points"]["TKP"]
    assert [p["x"] for p in tkp_points] == [0, 1]
    assert tkp_points[0]["y"] == 100000


def test_combined_mode_excludes_benchmarks(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    # Even if a client mistakenly asks for benchmarks in combined mode, they
    # must never appear — combined mode is programs-only by contract.
    r = sandbox_client.get("/api/performance?mode=combined&benchmarks=SPX,NDX,BTC")
    assert r.status_code == 200
    body = r.json()
    assert body["benchmarks"] == []
    for sym in ("SPX", "NDX", "BTC"):
        assert sym not in body["points"]
        assert all(s["key"] != sym for s in body["series"])


def test_combined_mode_shorter_program_ends_earlier(sandbox_client):
    dates = [(_A_MONDAY + timedelta(days=i)).isoformat() for i in range(3)]
    for i, d in enumerate(dates):
        _post(sandbox_client, "TKP", d, stonex_nlv=100000 + i * 1000, plus500_nlv=0)
    _post(sandbox_client, "TCP", dates[0], stonex_nlv=50000)

    body = sandbox_client.get("/api/performance?mode=combined").json()
    assert [p["x"] for p in body["points"]["TKP"]] == [0, 1, 2]
    assert [p["x"] for p in body["points"]["TCP"]] == [0]


def test_combined_mode_all_empty_returns_warnings_not_crash(sandbox_client):
    r = sandbox_client.get("/api/performance?mode=combined")
    assert r.status_code == 200
    body = r.json()
    for code in ("TKP", "TCP", "AGM", "YQ"):
        assert body["points"][code] == []
    assert len(body["warnings"]) >= 4


# --- program mode -------------------------------------------------------------
def test_program_mode_uses_real_dates(sandbox_client):
    dates = [(_A_MONDAY + timedelta(days=i)).isoformat() for i in range(3)]
    for i, d in enumerate(dates):
        _post(sandbox_client, "TKP", d, stonex_nlv=100000 + i * 500, plus500_nlv=0)

    r = sandbox_client.get("/api/performance?mode=program&program=TKP")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "program"
    assert body["x_axis"] == "date"
    assert body["program"] == "TKP"
    assert [p["x"] for p in body["points"]["TKP"]] == dates
    assert body["points"]["TKP"][0]["y"] == 100000


def test_program_mode_requires_program_param(sandbox_client):
    r = sandbox_client.get("/api/performance?mode=program")
    assert r.status_code == 422


def test_program_mode_empty_program_returns_warning_not_crash(sandbox_client):
    r = sandbox_client.get("/api/performance?mode=program&program=AGM")
    assert r.status_code == 200
    body = r.json()
    assert body["points"]["AGM"] == []
    assert len(body["warnings"]) >= 1


# --- benchmark rebasing ---------------------------------------------------
def test_benchmark_rebases_to_100000_at_program_start(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    r = sandbox_client.get("/api/performance?mode=program&program=TCP&benchmarks=SPX")
    body = r.json()
    assert body["benchmarks"] == ["SPX"]
    assert body["points"]["SPX"][0]["y"] == 100000
    assert any(s["key"] == "SPX" and s["kind"] == "benchmark" for s in body["series"])


def test_benchmark_missing_on_start_date_rolls_forward_with_warning(sandbox_client):
    # First row on Saturday has no market close — rebase rolls forward to Monday.
    _post(sandbox_client, "TCP", _A_SATURDAY.isoformat(), stonex_nlv=50000)
    r = sandbox_client.get("/api/performance?mode=program&program=TCP&benchmarks=SPX")
    body = r.json()
    spx = body["points"]["SPX"]
    assert len(spx) == 1
    assert spx[0]["x"] == _A_SATURDAY.isoformat()
    # Prior-weekday close vs Monday rebase anchor — not exactly 100k on a weekend start.
    assert 99000 < spx[0]["y"] < 100000
    assert body["benchmark_status"]["SPX"]["fallback_points"] >= 1
    assert not any("no close within 5d" in w for w in body["warnings"])


def test_unknown_benchmark_symbol_is_ignored_with_warning(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    r = sandbox_client.get("/api/performance?mode=program&program=TCP&benchmarks=FOO")
    body = r.json()
    assert body["benchmarks"] == []
    assert "FOO" not in body["points"]
    assert any("FOO" in w for w in body["warnings"])


# --- accounting: cash-transfer neutralization + AGM fee exclusion -----------
def test_cash_transfer_is_neutralized(sandbox_client):
    d0, d1 = _A_MONDAY.isoformat(), (_A_MONDAY + timedelta(days=1)).isoformat()
    # No transfer: pure 1% trading gain.
    _post(sandbox_client, "TCP", d0, stonex_nlv=100000)
    _post(sandbox_client, "TCP", d1, stonex_nlv=101000, cash_transfer=0)
    # Same 1% trading gain, but a $5,000 deposit is layered on top of the NLV —
    # the deposit must be neutralized so the normalized series matches exactly.
    _post(sandbox_client, "YQ", d0, stonex_nlv=100000)
    _post(sandbox_client, "YQ", d1, stonex_nlv=106000, cash_transfer=5000)

    tcp = sandbox_client.get("/api/performance?mode=program&program=TCP").json()
    yq = sandbox_client.get("/api/performance?mode=program&program=YQ").json()

    tcp_day1 = tcp["points"]["TCP"][1]["y"]
    yq_day1 = yq["points"]["YQ"][1]["y"]
    assert tcp_day1 == 101000
    assert yq_day1 == tcp_day1  # deposit fully neutralized


def test_agm_fee_does_not_affect_performance(sandbox_client):
    d0, d1 = _A_MONDAY.isoformat(), (_A_MONDAY + timedelta(days=1)).isoformat()
    _post(sandbox_client, "AGM", d0, tradestation_nlv=30000, fee=0)
    _post(sandbox_client, "AGM", d1, tradestation_nlv=31000, fee=999999)

    body = sandbox_client.get("/api/performance?mode=program&program=AGM").json()
    expected = round(100000 * (31000 / 30000), 4)
    assert body["points"]["AGM"][1]["y"] == expected


# --- freshness (no caching) -------------------------------------------------
def test_performance_refreshes_after_row_changes(sandbox_client):
    empty = sandbox_client.get("/api/performance?mode=program&program=YQ").json()
    assert empty["points"]["YQ"] == []

    _post(sandbox_client, "YQ", _A_MONDAY.isoformat(), stonex_nlv=60000)
    after_add = sandbox_client.get("/api/performance?mode=program&program=YQ").json()
    assert len(after_add["points"]["YQ"]) == 1

    sandbox_client.delete("/api/rows/YQ/last")
    after_delete = sandbox_client.get("/api/performance?mode=program&program=YQ").json()
    assert after_delete["points"]["YQ"] == []


def test_performance_refreshes_after_export(sandbox_client):
    _post(sandbox_client, "TKP", _A_MONDAY.isoformat(), stonex_nlv=100000, plus500_nlv=0)
    before = sandbox_client.get("/api/performance?mode=combined").json()["last_updated_at"]

    sandbox_client.post("/api/export/all")
    after = sandbox_client.get("/api/performance?mode=combined").json()["last_updated_at"]
    assert after >= before


def test_last_updated_at_present_when_no_data(sandbox_client):
    body = sandbox_client.get("/api/performance?mode=combined").json()
    assert isinstance(body["last_updated_at"], str) and "T" in body["last_updated_at"]


# --- data provenance (client-facing safety) ---------------------------------
def test_combined_mode_declares_uploader_program_source(sandbox_client):
    body = sandbox_client.get("/api/performance?mode=combined").json()
    assert body["program_data_source"] == "uploader_daily_rows"
    assert body["benchmark_data_source"] is None


def test_program_mode_declares_cached_benchmark_source(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    body = sandbox_client.get(
        "/api/performance?mode=program&program=TCP&benchmarks=SPX,NDX"
    ).json()
    assert body["program_data_source"] == "uploader_daily_rows"
    assert body["benchmark_data_source"] == "market_cache_cached"
    assert body["benchmark_align_policy"] == "prior_close_within_5_calendar_days"


def test_program_mode_benchmark_unavailable_without_cache():
    """Empty cache + cache_only must not fabricate benchmark values."""
    empty = Path(__file__).resolve().parent / "_tmp" / f"empty_{uuid4().hex}"
    empty.mkdir(parents=True, exist_ok=True)
    client = _make_client(
        seed_benchmarks=False,
        benchmark_cache_dir=str(empty),
        benchmark_cache_only=True,
    )
    try:
        _post(client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
        body = client.get(
            "/api/performance?mode=program&program=TCP&benchmarks=SPX"
        ).json()
        assert body["benchmarks"] == []
        assert body["benchmark_data_source"] == "unavailable"
        assert "SPX" not in body["points"]
    finally:
        client.close()


def test_program_mode_without_benchmarks_has_null_benchmark_source(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    body = sandbox_client.get("/api/performance?mode=program&program=TCP").json()
    assert body["benchmark_data_source"] is None
    assert body["benchmark_status"] == {}


def _client_with_calendar_cache(start, end, holiday=None):
    from tests.benchmark_fixtures import seed_equity_and_btc_calendar

    cache = Path(__file__).resolve().parent / "_tmp" / f"cal_{uuid4().hex}"
    cache.mkdir(parents=True, exist_ok=True)
    seed_equity_and_btc_calendar(cache, start, end, holiday=holiday)
    return _make_client(
        seed_benchmarks=False,
        benchmark_cache_dir=str(cache),
        benchmark_cache_only=True,
    )


def _post_program_span(client, program, start, days, field, start_nlv):
    dates = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        dates.append(d)
        if program == "AGM":
            _post(client, program, d, tradestation_nlv=start_nlv + i * 100, fee=0)
        elif program == "TKP":
            _post(client, program, d, stonex_nlv=start_nlv + i * 100, plus500_nlv=0)
        else:
            _post(client, program, d, **{field: start_nlv + i * 100})
    return dates


def test_current_benchmarks_extend_through_final_program_date():
    start = _A_MONDAY
    end = start + timedelta(days=10)  # includes a weekend
    client = _client_with_calendar_cache(start - timedelta(days=3), end)
    try:
        dates = _post_program_span(client, "TCP", start, 11, "stonex_nlv", 50000)
        body = client.get(
            "/api/performance?mode=program&program=TCP&benchmarks=SPX,NDX,BTC"
        ).json()
        last = dates[-1]
        assert body["points"]["TCP"][-1]["x"] == last
        for sym in ("SPX", "NDX", "BTC"):
            assert body["points"][sym][-1]["x"] == last
            assert body["benchmark_status"][sym]["status"] == "ready"
            assert body["benchmark_status"][sym]["aligned_points"] == len(dates)
        assert len(body["warnings"]) <= 3
        assert not any("no close within 5d" in w for w in body["warnings"])
        assert not any("used prior close from" in w for w in body["warnings"])
    finally:
        client.close()


def test_benchmarks_extend_for_tkp_and_agm():
    start = _A_MONDAY
    end = start + timedelta(days=6)
    client = _client_with_calendar_cache(start - timedelta(days=2), end)
    try:
        for program, field, nlv in (
            ("TKP", "stonex_nlv", 100000),
            ("AGM", "tradestation_nlv", 30000),
        ):
            dates = _post_program_span(client, program, start, 7, field, nlv)
            body = client.get(
                f"/api/performance?mode=program&program={program}&benchmarks=SPX,NDX,BTC"
            ).json()
            last = dates[-1]
            assert body["points"][program][-1]["x"] == last
            for sym in ("SPX", "NDX", "BTC"):
                assert body["points"][sym][-1]["x"] == last
    finally:
        client.close()


def test_market_holiday_uses_bounded_prior_close():
    start = _A_MONDAY
    holiday = start + timedelta(days=2)  # Wednesday
    end = start + timedelta(days=4)
    client = _client_with_calendar_cache(start - timedelta(days=2), end, holiday=holiday)
    try:
        dates = _post_program_span(client, "TCP", start, 5, "stonex_nlv", 50000)
        body = client.get(
            "/api/performance?mode=program&program=TCP&benchmarks=SPX"
        ).json()
        holiday_iso = holiday.isoformat()
        assert holiday_iso in dates
        xs = [p["x"] for p in body["points"]["SPX"]]
        assert holiday_iso in xs
        assert body["benchmark_status"]["SPX"]["fallback_points"] >= 1
        assert body["points"]["SPX"][-1]["x"] == dates[-1]
        assert not any("no close within 5d" in w for w in body["warnings"])
    finally:
        client.close()


def test_btc_weekend_aligns_to_same_calendar_date():
    start = _A_SATURDAY
    end = start + timedelta(days=2)
    client = _client_with_calendar_cache(start - timedelta(days=2), end)
    try:
        _post(client, "TCP", start.isoformat(), stonex_nlv=50000)
        _post(client, "TCP", (start + timedelta(days=1)).isoformat(), stonex_nlv=50100)
        _post(client, "TCP", end.isoformat(), stonex_nlv=50200)
        body = client.get(
            "/api/performance?mode=program&program=TCP&benchmarks=BTC"
        ).json()
        btc_xs = [p["x"] for p in body["points"]["BTC"]]
        assert start.isoformat() in btc_xs
        assert body["points"]["BTC"][-1]["x"] == end.isoformat()
    finally:
        client.close()


def test_stale_cache_emits_one_warning_not_a_wall():
    start = _A_MONDAY
    cache_end = start + timedelta(days=2)
    program_end = start + timedelta(days=20)
    client = _client_with_calendar_cache(start - timedelta(days=2), cache_end)
    try:
        _post_program_span(client, "TCP", start, 21, "stonex_nlv", 50000)
        before_rows = client.get("/api/rows/TCP?limit=365").json()["count"]
        body = client.get(
            "/api/performance?mode=program&program=TCP&benchmarks=SPX,NDX,BTC"
        ).json()
        after_rows = client.get("/api/rows/TCP?limit=365").json()["count"]
        assert before_rows == after_rows == 21
        stale_warnings = [w for w in body["warnings"] if "stale" in w.lower()]
        assert 1 <= len(stale_warnings) <= 3
        assert len(body["warnings"]) <= 3
        assert not any("no close within 5d" in w for w in body["warnings"])
        for sym in ("SPX", "NDX", "BTC"):
            assert body["benchmark_status"][sym]["status"] == "stale"
            assert body["points"][sym][-1]["x"] != program_end.isoformat()
    finally:
        client.close()


def test_performance_get_does_not_export_or_mutate_rows(sandbox_client):
    _post(sandbox_client, "TCP", _A_MONDAY.isoformat(), stonex_nlv=50000)
    _post(sandbox_client, "TCP", (_A_MONDAY + timedelta(days=1)).isoformat(), stonex_nlv=51000)
    eligibility_before = sandbox_client.get("/api/export/eligibility").json()
    rows_before = sandbox_client.get("/api/rows/TCP?limit=365").json()["count"]
    sandbox_client.get("/api/performance?mode=program&program=TCP&benchmarks=SPX,NDX,BTC")
    sandbox_client.get("/api/performance?mode=combined")
    eligibility_after = sandbox_client.get("/api/export/eligibility").json()
    rows_after = sandbox_client.get("/api/rows/TCP?limit=365").json()["count"]
    assert rows_before == rows_after
    assert eligibility_before["exported"] == eligibility_after["exported"]
    assert eligibility_before["excluded"] == eligibility_after["excluded"]
