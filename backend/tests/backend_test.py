"""Backend tests for Fifthback (feedback resolution) API.

Covers:
- POST /api/interpret (LLM path with verbatim evidence + optional song note)
- POST /api/interpret input validation
- GET  /api/patterns (5 pre-seeded demo patterns)
- POST /api/feedback/confirm end-to-end -> pattern appears in /api/patterns
"""

import os
import re
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FEEDBACK_TYPES = {"REQUEST", "TENSION", "PROBLEM", "SUGGESTION", "POSITIVE", "OTHER"}


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


# ---------------- /api/interpret ----------------
def test_interpret_meeting_overload(api_client):
    text = (
        "My calendar is completely full of meetings and I have almost no time to do "
        "the actual work. By the time I can focus it's already 6pm."
    )
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": text}, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()

    # Required top-level fields
    assert data["feedback_type"] in FEEDBACK_TYPES
    assert isinstance(data["signals"], list)
    assert 1 <= len(data["signals"]) <= 4
    assert isinstance(data["pattern_candidate"], str) and data["pattern_candidate"].strip()

    # Each signal has label + verbatim evidence
    for sig in data["signals"]:
        assert sig["label"].strip()
        assert sig["evidence"].strip()
        # verbatim substring of the input (case-insensitive tolerance)
        assert sig["evidence"] in text or sig["evidence"].lower() in text.lower(), (
            f"Evidence not verbatim substring: {sig['evidence']!r}"
        )

    # Meeting overload -> should likely classify as PROBLEM (per fallback + LLM prompt)
    # We won't hard-fail on the type since this is a judgement call, but log it.
    # However the pattern_candidate should be short-ish
    assert len(data["pattern_candidate"].split()) <= 12


def test_interpret_with_song_returns_song_note(api_client):
    text = "Every sprint the designs come in late and half of them can't actually be built."
    body = {
        "text": text,
        "song": {"title": "Under Pressure", "artist": "Queen & David Bowie"},
    }
    r = api_client.post(f"{BASE_URL}/api/interpret", json=body, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("song_note"), "song_note should be present when song provided"
    assert isinstance(data["song_note"], str) and len(data["song_note"]) > 5


def test_interpret_empty_text_returns_400(api_client):
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": "   "}, timeout=15)
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


def test_interpret_positive_type(api_client):
    text = "I just want to say the support team quietly saved a huge customer escalation last week and they're amazing. I'm really grateful."
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": text}, timeout=90)
    assert r.status_code == 200
    data = r.json()
    # Should not force A vs B; expect POSITIVE ideally, but at least in the valid set
    assert data["feedback_type"] in FEEDBACK_TYPES
    # verify evidence still verbatim
    for sig in data["signals"]:
        assert sig["evidence"] in text or sig["evidence"].lower() in text.lower()


# ---------------- /api/patterns ----------------
REQUIRED_PATTERN_FIELDS = {
    "id", "title", "feedback_type", "frequency", "affected_teams",
    "unresolved_for", "blocker", "status",
}
VALID_STATUSES = {"NEW", "ACTIVE", "STUCK", "RESOLVED"}


def test_patterns_returns_seeded(api_client):
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


# ---------------- /api/feedback/confirm ----------------
def test_confirm_creates_live_pattern_visible_in_patterns(api_client):
    # Use a unique pattern_candidate we control
    unique_marker = f"TEST_focus_time_erosion_{int(time.time())}"
    text = "Meetings keep eating my day and I never get focus time."
    interpretation = {
        "id": "test-" + str(int(time.time())),
        "feedback_type": "PROBLEM",
        "signals": [
            {"label": "No focus time", "evidence": "Meetings keep eating my day"},
        ],
        "pattern_candidate": unique_marker,
        "song_note": None,
    }
    # Snapshot patterns before
    before = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()
    before_count = len(before)

    r = api_client.post(
        f"{BASE_URL}/api/feedback/confirm",
        json={"text": text, "song": None, "interpretation": interpretation, "corrected": False},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    after = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()
    # find pattern with our unique marker title
    matches = [p for p in after if p.get("title", "").lower() == unique_marker.lower()]
    assert matches, f"Live pattern with title {unique_marker} not found after confirm"
    m = matches[0]
    assert m["feedback_type"] == "PROBLEM"
    assert m["status"] == "NEW"
    assert m["seeded"] is False
    assert m["frequency"] == 1
    assert after != before or len(after) > before_count


def test_confirm_second_time_increments_frequency(api_client):
    unique_marker = f"TEST_dup_pattern_{int(time.time())}"
    interpretation = {
        "id": "test-inc-1",
        "feedback_type": "SUGGESTION",
        "signals": [{"label": "Async docs", "evidence": "we should write things down"}],
        "pattern_candidate": unique_marker,
        "song_note": None,
    }
    body = {"text": "we should write things down", "song": None,
            "interpretation": interpretation, "corrected": False}
    r1 = api_client.post(f"{BASE_URL}/api/feedback/confirm", json=body, timeout=15)
    assert r1.status_code == 200
    r2 = api_client.post(f"{BASE_URL}/api/feedback/confirm", json=body, timeout=15)
    assert r2.status_code == 200

    patterns = api_client.get(f"{BASE_URL}/api/patterns", timeout=15).json()
    m = [p for p in patterns if p["title"].lower() == unique_marker.lower()]
    assert len(m) == 1, f"Expected exactly one merged pattern, got {len(m)}"
    assert m[0]["frequency"] == 2, f"Frequency should be 2 after two confirms, got {m[0]['frequency']}"
