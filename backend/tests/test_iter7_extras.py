"""Iter 7 extras: verify _fallback_interpret ftype default + distinction/evaluate + add-signals path."""
import os
import requests

EXTERNAL = os.environ.get("REACT_APP_BACKEND_URL")
if not EXTERNAL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                EXTERNAL = line.split("=", 1)[1].strip()
                break
EXTERNAL = EXTERNAL.rstrip("/")


VALID_FTYPES = {"POSITIVE", "REQUEST", "SUGGESTION", "TENSION", "PROBLEM", "OTHER"}


def test_interpret_gibberish_fallback_ftype_defaults():
    # Text with no recognisable keywords should hit fallback path returning ftype='OTHER'
    payload = {"text": "xyzq qwer asdf zxcv"}
    r = requests.post(f"{EXTERNAL}/api/interpret", json=payload, timeout=90)
    assert r.status_code == 200
    data = r.json()
    assert data.get("feedback_type") in VALID_FTYPES
    # empty gibberish should not crash & prevalence structure exists
    assert "prevalence" in data
    assert "signals" in data


def test_interpret_empty_text():
    # An almost-empty text; must still not 500
    r = requests.post(f"{EXTERNAL}/api/interpret", json={"text": "."}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert d.get("feedback_type") in VALID_FTYPES


def _interp(text):
    r = requests.post(f"{EXTERNAL}/api/interpret", json={"text": text}, timeout=90)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_distinction():
    text = "Ekibin motivasyonu düşük ve toplantılar çok uzun sürüyor."
    interp = _interp(text)
    r = requests.post(f"{EXTERNAL}/api/distinction", json={"text": text, "interpretation": interp}, timeout=90)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert isinstance(d, dict)
    assert "should_ask" in d


def test_evaluate():
    text = "Ekibimizin motivasyonu düşük, çünkü haftalık toplantılar çok uzun sürüyor ve gündemsiz."
    interp = _interp(text)
    payload = {"text": text, "interpretation": interp, "question": "", "answer": "Toplantılar 60 dakikadan uzun."}
    r = requests.post(f"{EXTERNAL}/api/evaluate", json=payload, timeout=90)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert "interpretation" in d and "supported" in d and "evaluation_note" in d


def test_add_signals_appends():
    # capture current pool
    before = requests.get(f"{EXTERNAL}/api/pattern-room/signals", timeout=20).json()
    before_pool = before.get("signals", before if isinstance(before, list) else [])
    before_count = len(before_pool)

    payload = {"signals": ["TEST_iter7 sinyal a", "TEST_iter7 sinyal b"]}
    r = requests.post(f"{EXTERNAL}/api/pattern-room/add-signals", json=payload, timeout=90)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("source") in ("live", "curated")

    after = requests.get(f"{EXTERNAL}/api/pattern-room/signals", timeout=20).json()
    after_pool = after.get("signals", after if isinstance(after, list) else [])
    assert len(after_pool) >= before_count + 2


def test_action_board_create_and_patch():
    payload = {
        "pattern_name": "TEST_iter7 pattern",
        "mechanism": "TEST mechanism",
        "cluster_id": "",
        "evidence_snapshot": ["TEST_iter7 sinyal a"],
        "hypothesis": "TEST hipotez",
        "intervention": "TEST intervention",
    }
    r = requests.post(f"{EXTERNAL}/api/action-board", json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text[:300]
    item = r.json()
    aid = item.get("id")
    assert aid
    assert item.get("status") == "DETECTED"

    # PATCH -> REJECTED
    r2 = requests.patch(f"{EXTERNAL}/api/action-board/{aid}", json={"status": "REJECTED", "outcome": "test"}, timeout=20)
    assert r2.status_code == 200, r2.text[:300]
    updated = r2.json()
    assert updated.get("status") == "REJECTED"
    assert updated.get("outcome") == "test"
