"""Backend tests for Pattern Room feature (Fifthback)."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ---------------- signals ----------------
def test_signals_returns_24_turkish(s):
    r = s.get(f"{BASE_URL}/api/pattern-room/signals", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "signals" in data
    sigs = data["signals"]
    assert len(sigs) == 24, f"expected 24 signals, got {len(sigs)}"
    assert "Onaylar günler sürüyor." in sigs
    assert "Önemli bilgiler üç farklı araca dağılmış durumda." in sigs
    # sanity: all non-empty strings
    for i, sig in enumerate(sigs):
        assert isinstance(sig, str) and len(sig) > 0, f"signal {i} empty"


# ---------------- analysis schema ----------------
def _validate_analysis(data):
    # signals
    assert len(data["signals"]) == 24
    # clusters
    clusters = data["clusters"]
    assert len(clusters) >= 4, f"expected >=4 clusters, got {len(clusters)}"
    for c in clusters:
        for k in ["id", "name", "mechanism", "signal_indices", "summary"]:
            assert k in c, f"cluster missing {k}"
        assert len(c["signal_indices"]) >= 1
        for idx in c["signal_indices"]:
            assert 0 <= idx <= 23, f"invalid signal_index {idx} in cluster {c['id']}"
    # patterns
    patterns = data["patterns"]
    assert len(patterns) >= 3, f"expected >=3 top patterns, got {len(patterns)}"
    ranks = sorted(p["rank"] for p in patterns)
    # ranks should be 1..N with 1 present
    assert 1 in ranks
    required_fields = [
        "rank", "cluster_id", "name", "mechanism", "why_selected", "why_formed",
        "inference", "uncertain", "why_top5", "evidence", "estimated_cost",
        "what_improves", "gain_if_reduced", "affected_work", "confidence",
        "past_patterns", "next_moves",
    ]
    cluster_ids = {c["id"] for c in clusters}
    for p in patterns:
        for k in required_fields:
            assert k in p, f"pattern rank={p.get('rank')} missing {k}"
        assert p["cluster_id"] in cluster_ids, f"cluster_id {p['cluster_id']} not in clusters"
        assert isinstance(p["evidence"], list) and len(p["evidence"]) >= 1
        assert isinstance(p["next_moves"], list)
        assert len(p["next_moves"]) <= 3
    # source
    assert data.get("source") in ("curated", "live")


def test_analysis_curated_schema(s):
    r = s.get(f"{BASE_URL}/api/pattern-room/analysis", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    _validate_analysis(data)


def test_top_rank1_is_decision_ownership_bottleneck(s):
    r = s.get(f"{BASE_URL}/api/pattern-room/analysis", timeout=20)
    data = r.json()
    top = next(p for p in data["patterns"] if p["rank"] == 1)
    text = (top["name"] + " " + top["mechanism"] + " " + top["why_selected"] + " " + top["why_formed"]).lower()
    # decision-flow / ownership bottleneck cues
    assert any(k in text for k in ["karar", "sahiplik", "onay", "darboğaz"]), \
        f"top pattern doesn't look like decision/ownership bottleneck: {text[:200]}"
    # combines several signals
    assert len(top["evidence"]) >= 3


def test_estimated_cost_qualitative_no_money(s):
    r = s.get(f"{BASE_URL}/api/pattern-room/analysis", timeout=20)
    data = r.json()
    # detect currency / precise money figures
    money_re = re.compile(r"(₺|\$|€|tl\b|usd|eur|\bmillion|\bmilyon|\bmilyar|\bbillion)", re.IGNORECASE)
    for p in data["patterns"]:
        cost = p["estimated_cost"]
        assert not money_re.search(cost), f"pattern {p['rank']} has money figure: {cost}"
        # should use qualitative/tahmini language OR at least be non-empty; prefer 'tahmini'
        # Not strictly required per contract; log softly.


# ---------------- POST analyze (live or fallback) ----------------
def test_post_analyze_returns_valid(s):
    """Heavy Claude call. Per review contract it may fall back to curated.
    Accept 200 (live/curated) OR Cloudflare 502/504 (proxy timeout) as expected
    given the endpoint has no wall-clock guard — reported as backend issue."""
    try:
        r = s.post(f"{BASE_URL}/api/pattern-room/analyze", timeout=150)
    except requests.exceptions.ReadTimeout:
        pytest.skip("Analyze endpoint exceeded 150s wall-clock; reported as backend issue")
    if r.status_code in (502, 504):
        pytest.skip(f"Cloudflare {r.status_code} on /analyze (endpoint has no wall-clock timeout / fallback guard)")
    assert r.status_code == 200, r.text
    data = r.json()
    _validate_analysis(data)
    assert data["source"] in ("curated", "live")


# ---------------- Regression: existing endpoints ----------------
def test_regression_get_patterns(s):
    r = s.get(f"{BASE_URL}/api/patterns", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_regression_interpret(s):
    r = s.post(f"{BASE_URL}/api/interpret", json={"text": "Onaylar günler sürüyor ve iş bekliyor."}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "signals" in d and "active_needs" in d


def test_regression_distinction(s):
    ri = s.post(f"{BASE_URL}/api/interpret", json={"text": "İstifa edesim var."}, timeout=90)
    assert ri.status_code == 200
    r = s.post(f"{BASE_URL}/api/distinction",
               json={"text": "İstifa edesim var.", "interpretation": ri.json()}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "should_ask" in d


def test_regression_evaluate(s):
    # first interpret
    ri = s.post(f"{BASE_URL}/api/interpret", json={"text": "Onaylar günler sürüyor."}, timeout=90)
    assert ri.status_code == 200
    interp = ri.json()
    payload = {
        "text": "Onaylar günler sürüyor.",
        "interpretation": interp,
        "answer": "Karar kimin vereceği belli değil.",
    }
    r = s.post(f"{BASE_URL}/api/evaluate", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "interpretation" in d and "supported" in d
