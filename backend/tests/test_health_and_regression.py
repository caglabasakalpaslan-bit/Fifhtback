"""Backend regression tests for /health deployment fix + core endpoint sanity."""
import os
import requests
import pytest

EXTERNAL = os.environ.get("REACT_APP_BACKEND_URL")
if not EXTERNAL:
    # fallback: read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                EXTERNAL = line.split("=", 1)[1].strip()
                break
EXTERNAL = EXTERNAL.rstrip("/")
LOCAL = "http://localhost:8001"


# --- /health primary assertion (deployment probe) ---
def test_health_localhost():
    r = requests.get(f"{LOCAL}/health", timeout=10)
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    data = r.json()
    assert data.get("status") == "healthy", f"Unexpected body: {data}"


def test_health_external():
    # k8s ingress may or may not forward /health, but attempt it
    r = requests.get(f"{EXTERNAL}/health", timeout=15)
    # Accept 200 (routed to backend) or any non-500 (ingress may 404 for non-/api paths)
    assert r.status_code != 500, f"5xx on external /health: {r.status_code}"


# --- /api routing intact ---
def test_api_root():
    r = requests.get(f"{EXTERNAL}/api/", timeout=15)
    assert r.status_code == 200, f"/api/ status {r.status_code}: {r.text[:200]}"


# --- Regression sanity ---
def test_patterns():
    r = requests.get(f"{EXTERNAL}/api/patterns", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0, "No seeded patterns returned"


def test_pattern_room_analysis():
    r = requests.get(f"{EXTERNAL}/api/pattern-room/analysis", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


def test_pattern_room_signals():
    r = requests.get(f"{EXTERNAL}/api/pattern-room/signals", timeout=20)
    assert r.status_code == 200


def test_action_board():
    r = requests.get(f"{EXTERNAL}/api/action-board", timeout=20)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_interpret_turkish():
    payload = {"text": "Bugün kendimi biraz yorgun hissediyorum ama devam ediyorum."}
    r = requests.post(f"{EXTERNAL}/api/interpret", json=payload, timeout=90)
    assert r.status_code == 200, f"interpret status {r.status_code}: {r.text[:300]}"
    data = r.json()
    assert "feedback_type" in data
    assert "signals" in data
    assert "prevalence" in data
