"""Backend tests for Fifthback (Turkish 5-step Solution Journey) API.

Covers new Turkish response schema:
- POST /api/interpret returns feedback_type, signals(verbatim), pattern_candidate,
  active_needs (>=1), responsibility (org & personal lists), channels (>=2 with
  title/detail/tradeoff), prevalence object.
- prevalence.found=true with real seeded numbers for meeting-overload Turkish text.
- prevalence.found=false for unrelated novel text.
- POST /api/interpret empty text -> 400.
- POST /api/feedback/confirm stores feedback and creates/increments live pattern.
- GET /api/patterns returns 5 Turkish seeded patterns.
"""

import os
import re
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FEEDBACK_TYPES = {"REQUEST", "TENSION", "PROBLEM", "SUGGESTION", "POSITIVE", "OTHER"}
VALID_STATUSES = {"NEW", "ACTIVE", "STUCK", "RESOLVED"}


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------- Health ----------------
def test_health_root(api_client):
    r = api_client.get(f"{BASE_URL}/api/", timeout=15)
    assert r.status_code == 200
    assert "Fifthback" in r.json().get("message", "")


# ---------------- /api/interpret rich schema (meeting overload TR) ----------------
MEETINGS_TEXT = (
    "Takvimim tamamen toplantılarla dolu ve asıl işi yapmaya neredeyse hiç vaktim "
    "kalmıyor. Odaklanabildiğimde saat çoktan 18:00 oluyor."
)


def _assert_verbatim_evidence(text, evidence):
    assert evidence.strip(), "empty evidence"
    assert evidence in text or evidence.lower() in text.lower(), (
        f"Evidence not verbatim substring: {evidence!r}"
    )


def test_interpret_meeting_overload_full_schema(api_client):
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": MEETINGS_TEXT}, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()

    # feedback_type
    assert data["feedback_type"] in FEEDBACK_TYPES

    # signals 1..4 with verbatim TR evidence
    signals = data["signals"]
    assert isinstance(signals, list) and 1 <= len(signals) <= 4
    for sig in signals:
        assert sig["label"].strip()
        _assert_verbatim_evidence(MEETINGS_TEXT, sig["evidence"])

    # pattern_candidate
    assert isinstance(data["pattern_candidate"], str) and data["pattern_candidate"].strip()

    # active_needs >= 1
    needs = data.get("active_needs") or []
    assert len(needs) >= 1, "active_needs must have at least one entry"
    for n in needs:
        assert n.get("title", "").strip(), "need title must be non-empty"

    # responsibility with org & personal (both must be lists; at least one non-empty)
    resp = data.get("responsibility") or {}
    org = resp.get("organizational") or []
    per = resp.get("personal") or []
    assert isinstance(org, list) and isinstance(per, list)
    assert len(org) >= 1, "organizational responsibility should not be empty"
    assert len(per) >= 1, "personal responsibility should not be empty"

    # channels >= 2 each with title/detail/tradeoff
    channels = data.get("channels") or []
    assert len(channels) >= 2, f"expected >=2 channels, got {len(channels)}"
    for c in channels:
        assert c.get("title", "").strip()
        assert "detail" in c
        assert "tradeoff" in c

    # prevalence must be present
    prev = data.get("prevalence")
    assert prev is not None, "prevalence object missing"
    # For Turkish meeting overload text there IS a seeded pattern -> found True
    # with real seeded numbers.
    assert prev.get("found") is True, f"expected prevalence.found True for meetings, got {prev}"
    assert isinstance(prev.get("frequency"), int) and prev["frequency"] > 0
    assert isinstance(prev.get("affected_teams"), list) and prev["affected_teams"]
    assert isinstance(prev.get("unresolved_for"), str) and prev["unresolved_for"].strip()
    assert isinstance(prev.get("matched_title"), str) and prev["matched_title"].strip()


def test_interpret_prevalence_not_found_for_novel_text(api_client):
    novel = (
        "Ofis kahve makinesinin espresso ayarı benim damak zevkime uygun değil, "
        "keşke biraz daha yumuşak çekim seçeneği olsa."
    )
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": novel}, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    prev = data.get("prevalence") or {}
    # unrelated novel text should NOT be matched against seeded patterns
    assert prev.get("found") is False, (
        f"prevalence must be False for unrelated text; got {prev}"
    )
    # And no fabricated stats
    assert prev.get("frequency") in (None, 0)
    assert not prev.get("matched_title")


def test_interpret_empty_text_returns_400(api_client):
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": "   "}, timeout=15)
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


def test_interpret_with_song_returns_song_note(api_client):
    body = {
        "text": MEETINGS_TEXT,
        "song": {"title": "Everything In Its Right Place", "artist": "Radiohead"},
    }
    r = api_client.post(f"{BASE_URL}/api/interpret", json=body, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("song_note"), "song_note should be present when a song is provided"
    assert isinstance(data["song_note"], str) and len(data["song_note"]) > 5


# ---------------- /api/patterns (5 Turkish seeded) ----------------
REQUIRED_PATTERN_FIELDS = {
    "id", "title", "feedback_type", "frequency", "affected_teams",
    "unresolved_for", "blocker", "status",
}


def test_patterns_returns_5_turkish_seeded(api_client):
    r = api_client.get(f"{BASE_URL}/api/patterns", timeout=15)
    assert r.status_code == 200
    patterns = r.json()
    assert isinstance(patterns, list)
    seeded = [p for p in patterns if p.get("seeded") is True]
    assert len(seeded) == 5, f"Expected 5 seeded patterns, got {len(seeded)}"
    for p in seeded:
        missing = REQUIRED_PATTERN_FIELDS - set(p.keys())
        assert not missing, f"Missing fields on seeded pattern: {missing}"
        assert p["feedback_type"] in FEEDBACK_TYPES
        assert p["status"] in VALID_STATUSES
        assert isinstance(p["affected_teams"], list) and len(p["affected_teams"]) >= 1
        assert isinstance(p["frequency"], int) and p["frequency"] >= 0

    # Check at least one seeded title contains Turkish content
    titles = " | ".join(p["title"] for p in seeded)
    assert any(w in titles for w in ["Toplantı", "Tasarım", "işe alışma", "async", "Perde"]), (
        f"seeded pattern titles look non-Turkish: {titles}"
    )


# ---------------- /api/feedback/confirm ----------------
def test_confirm_creates_live_pattern_visible_in_patterns(api_client):
    unique_marker = f"TEST_odak_erozyonu_{int(time.time())}"
    text = "Toplantılar günümü yiyor ve odak zamanı kalmıyor."
    interpretation = {
        "id": "test-" + str(int(time.time())),
        "feedback_type": "PROBLEM",
        "signals": [
            {"label": "Odak zamanı yok", "evidence": "Toplantılar günümü yiyor"},
        ],
        "pattern_candidate": unique_marker,
        "song_note": None,
        "active_needs": [{"title": "Kesintisiz zaman", "detail": "detay"}],
        "responsibility": {"organizational": ["blok saatler"], "personal": ["takvimi savun"]},
        "channels": [
            {"title": "Anonim paylaş", "detail": "d1", "tradeoff": "t1"},
            {"title": "Ekiple konuş", "detail": "d2", "tradeoff": "t2"},
        ],
        "safety_note": None,
        "prevalence": {"found": False},
    }
    before = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()

    r = api_client.post(
        f"{BASE_URL}/api/feedback/confirm",
        json={"text": text, "song": None, "interpretation": interpretation, "corrected": False},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    after = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()
    matches = [p for p in after if p.get("title", "").lower() == unique_marker.lower()]
    assert matches, f"Live pattern with title {unique_marker} not found after confirm"
    m = matches[0]
    assert m["feedback_type"] == "PROBLEM"
    assert m["status"] == "NEW"
    assert m["seeded"] is False
    assert m["frequency"] == 1
    assert len(after) >= len(before)


def test_confirm_second_time_increments_frequency(api_client):
    unique_marker = f"TEST_dup_pattern_{int(time.time())}"
    interpretation = {
        "id": "test-inc-1",
        "feedback_type": "SUGGESTION",
        "signals": [{"label": "Yazılı öneri", "evidence": "yazılı olsun"}],
        "pattern_candidate": unique_marker,
        "song_note": None,
        "active_needs": [{"title": "Yazılı bağlam", "detail": "d"}],
        "responsibility": {"organizational": ["a"], "personal": ["b"]},
        "channels": [
            {"title": "Kanal A", "detail": "d", "tradeoff": "t"},
            {"title": "Kanal B", "detail": "d", "tradeoff": "t"},
        ],
        "prevalence": {"found": False},
    }
    body = {"text": "yazılı olsun", "song": None,
            "interpretation": interpretation, "corrected": False}
    r1 = api_client.post(f"{BASE_URL}/api/feedback/confirm", json=body, timeout=15)
    assert r1.status_code == 200
    r2 = api_client.post(f"{BASE_URL}/api/feedback/confirm", json=body, timeout=15)
    assert r2.status_code == 200

    patterns = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()
    m = [p for p in patterns if p["title"].lower() == unique_marker.lower()]
    assert len(m) == 1, f"Expected exactly one merged pattern, got {len(m)}"
    assert m[0]["frequency"] == 2, f"Frequency should be 2 after two confirms, got {m[0]['frequency']}"
