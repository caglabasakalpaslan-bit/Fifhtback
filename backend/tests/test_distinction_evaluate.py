"""Backend tests for the NEW Distinction Questioner + Evaluator AI workers.

- POST /api/distinction with 'İstifa edesim var.' -> should_ask=true + Turkish question + 3-5 options
- POST /api/distinction with clearly single-signal gratitude text -> should_ask=false + Turkish stop_reason
- POST /api/distinction empty text -> 400
- POST /api/evaluate with text+question+answer -> refined interpretation (full journey fields),
  supported bool, evaluation_note; refined signals evidence is verbatim substring of combined text+answer.
"""

import os
import re
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FEEDBACK_TYPES = {"REQUEST", "TENSION", "PROBLEM", "SUGGESTION", "POSITIVE", "OTHER"}


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _interpret(api_client, text):
    r = api_client.post(f"{BASE_URL}/api/interpret", json={"text": text}, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- /api/distinction ambiguous multi-factor text ----------------
RESIGN_TEXT = "İstifa edesim var."


@pytest.fixture(scope="module")
def resign_interpretation(api_client):
    return _interpret(api_client, RESIGN_TEXT)


def test_distinction_asks_for_ambiguous_resignation_text(api_client, resign_interpretation):
    r = api_client.post(
        f"{BASE_URL}/api/distinction",
        json={"text": RESIGN_TEXT, "interpretation": resign_interpretation},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["should_ask"] is True, f"Expected should_ask=true for ambiguous resign text, got {data}"

    q = data.get("question")
    assert isinstance(q, str) and q.strip(), "question must be a non-empty Turkish string"
    # Very light Turkish sanity check (contains Turkish letter or common TR word or ends with '?')
    assert q.endswith("?") or re.search(r"[çğıöşüÇĞİÖŞÜ]", q), f"question doesn't look Turkish: {q!r}"

    options = data.get("options") or []
    assert isinstance(options, list) and 3 <= len(options) <= 5, (
        f"expected 3-5 options, got {len(options)}: {options}"
    )
    for opt in options:
        assert isinstance(opt, str) and opt.strip()
        assert "hiçbiri" not in opt.lower(), f"options must not include 'Hiçbiri', got {opt!r}"


# ---------------- /api/distinction clear single-signal gratitude text ----------------
GRATITUDE_TEXT = "Destek ekibi harikaydı, gerçekten minnettarım."


@pytest.fixture(scope="module")
def gratitude_interpretation(api_client):
    return _interpret(api_client, GRATITUDE_TEXT)


def test_distinction_stops_for_clear_gratitude_text(api_client, gratitude_interpretation):
    r = api_client.post(
        f"{BASE_URL}/api/distinction",
        json={"text": GRATITUDE_TEXT, "interpretation": gratitude_interpretation},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["should_ask"] is False, (
        f"Expected should_ask=false for clearly single-signal gratitude, got {data}"
    )
    sr = data.get("stop_reason")
    assert isinstance(sr, str) and sr.strip(), "stop_reason must be a non-empty Turkish string when should_ask=false"
    # Options must be empty per contract
    assert not data.get("options"), f"options must be empty when should_ask=false, got {data.get('options')}"


# ---------------- /api/distinction empty ----------------
def test_distinction_empty_text_returns_400(api_client, resign_interpretation):
    r = api_client.post(
        f"{BASE_URL}/api/distinction",
        json={"text": "   ", "interpretation": resign_interpretation},
        timeout=15,
    )
    assert r.status_code == 400, r.text
    assert "detail" in r.json()


# ---------------- /api/evaluate refined interpretation + grounding ----------------
def test_evaluate_returns_refined_interpretation_and_grounding(api_client, resign_interpretation):
    question = "İstifa düşünceni en çok ne besliyor?"
    answer = "Yöneticimle son toplantıda anlaşamadık ve tükendiğimi hissediyorum."
    combined = f"{RESIGN_TEXT}\n\n[Netleştirici soru] {question}\n[Çalışanın yanıtı] {answer}"

    r = api_client.post(
        f"{BASE_URL}/api/evaluate",
        json={
            "text": RESIGN_TEXT,
            "interpretation": resign_interpretation,
            "question": question,
            "answer": answer,
        },
        timeout=180,
    )
    assert r.status_code == 200, r.text
    data = r.json()

    # Envelope
    assert "interpretation" in data and "supported" in data and "evaluation_note" in data
    assert isinstance(data["supported"], bool)
    note = data["evaluation_note"]
    assert isinstance(note, str) and note.strip(), "evaluation_note must be a non-empty Turkish string"

    interp = data["interpretation"]

    # Full journey fields present
    assert interp.get("feedback_type") in FEEDBACK_TYPES
    signals = interp.get("signals") or []
    assert 1 <= len(signals) <= 4, f"signals count out of bounds: {len(signals)}"
    # Each signal.evidence must be a verbatim substring of the combined text+answer
    for s in signals:
        ev = s.get("evidence", "")
        assert ev.strip(), "empty evidence"
        assert ev in combined or ev.lower() in combined.lower(), (
            f"Refined signal evidence not a verbatim substring of combined text+answer: {ev!r}"
        )

    assert isinstance(interp.get("pattern_candidate"), str) and interp["pattern_candidate"].strip()
    assert len(interp.get("active_needs") or []) >= 1
    resp = interp.get("responsibility") or {}
    assert isinstance(resp.get("organizational"), list) and len(resp["organizational"]) >= 1
    assert isinstance(resp.get("personal"), list) and len(resp["personal"]) >= 1
    assert len(interp.get("channels") or []) >= 2
    # prevalence object must be present too (may be found=false)
    assert "prevalence" in interp and isinstance(interp["prevalence"], dict)
