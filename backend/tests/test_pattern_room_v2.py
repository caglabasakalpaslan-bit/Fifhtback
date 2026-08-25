"""Iteration 5: Add-signals + Action Board tests (Fifthback Pattern Room v2)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def initial_pool_size(s):
    r = s.get(f"{API}/pattern-room/signals", timeout=20)
    assert r.status_code == 200, r.text
    return len(r.json()["signals"])


# ---------- signals pool ----------
def test_signals_returns_pool(s):
    r = s.get(f"{API}/pattern-room/signals", timeout=20)
    assert r.status_code == 200
    sigs = r.json()["signals"]
    assert isinstance(sigs, list) and len(sigs) >= 24


# ---------- add-signals validation ----------
def test_add_signals_empty_returns_400(s):
    r = s.post(f"{API}/pattern-room/add-signals", json={"signals": []}, timeout=20)
    assert r.status_code == 400

def test_add_signals_blank_returns_400(s):
    r = s.post(f"{API}/pattern-room/add-signals", json={"signals": ["  ", ""]}, timeout=20)
    assert r.status_code == 400


# ---------- add-signals happy path ----------
def test_add_signals_appends_and_marks(s, initial_pool_size):
    tag = uuid.uuid4().hex[:6]
    new_sigs = [
        f"TEST_{tag} Sprint sonu demoları planlanandan hep 2 gün kayıyor.",
        f"TEST_{tag} Prod hatalarını kimin sahipleneceği belirsiz kalıyor.",
    ]
    r = s.post(f"{API}/pattern-room/add-signals", json={"signals": new_sigs}, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()

    # pool grew by exactly len(new_sigs)
    assert len(data["signals"]) == initial_pool_size + len(new_sigs)
    # new signals are the last two entries
    assert data["signals"][-2:] == new_sigs

    # new_signal_indices point to the appended positions
    expected_idx = list(range(initial_pool_size, initial_pool_size + len(new_sigs)))
    assert data["new_signal_indices"] == expected_idx

    # source is one of live/curated
    assert data["source"] in ("live", "curated")

    # some cluster should either be is_new or changed (covering the new indices),
    # OR curated fallback should include a "Yeni Sinyaller" cluster containing new_idx
    clusters = data["clusters"]
    covers_new = False
    yeni_found = False
    for c in clusters:
        if any(i in expected_idx for i in c["signal_indices"]):
            covers_new = True
            assert c.get("is_new") or c.get("changed"), f"cluster {c['id']} covers new signals but not flagged"
        if "yeni sinyaller" in c["name"].strip().lower():
            yeni_found = True
    assert covers_new or yeni_found, "no cluster covers new signals nor 'Yeni Sinyaller' fallback"


def test_pool_persists_after_add(s, initial_pool_size):
    # After the previous test appended 2 signals, the pool must still contain them
    r = s.get(f"{API}/pattern-room/signals", timeout=20)
    assert r.status_code == 200
    sigs = r.json()["signals"]
    assert len(sigs) >= initial_pool_size + 2

def test_get_analysis_reflects_new_pool(s, initial_pool_size):
    r = s.get(f"{API}/pattern-room/analysis", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["signals"]) >= initial_pool_size + 2


# ---------- action board ----------
@pytest.fixture(scope="module")
def created_action(s):
    payload = {
        "pattern_name": "TEST_Karar Akışı / Sahiplik Darboğazı",
        "mechanism": "Karar sahibi belirsiz -> onay bekleyen iş yığılıyor",
        "cluster_id": "c1",
        "evidence_snapshot": ["Onaylar günler sürüyor.", "Kimin karar vereceği belli değil."],
        "hypothesis": "Sahiplik matrisi netleşirse onay süresi düşer.",
        "intervention": "RACI tanımla, 48 saatlik SLA koy.",
    }
    r = s.post(f"{API}/action-board", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["status"] == "DETECTED"
    assert item["evidence_snapshot"] == payload["evidence_snapshot"]
    assert item["hypothesis"] == payload["hypothesis"]
    assert item["intervention"] == payload["intervention"]
    assert item["created_at"] == item["updated_at"]
    assert "id" in item and item["id"]
    yield item
    # teardown: attempt to delete via mongo not exposed; leave in DB (TEST_ prefix)


def test_action_board_list_contains_created(s, created_action):
    r = s.get(f"{API}/action-board", timeout=20)
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == created_action["id"] for i in items)


def test_action_board_patch_rejected(s, created_action):
    time.sleep(1.1)  # ensure timestamp changes
    r = s.patch(
        f"{API}/action-board/{created_action['id']}",
        json={"status": "REJECTED", "outcome": "TEST_hipotez desteklenmedi"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["status"] == "REJECTED"
    assert updated["outcome"] == "TEST_hipotez desteklenmedi"
    assert updated["created_at"] == created_action["created_at"]
    assert updated["updated_at"] != updated["created_at"]

    # verify persisted
    r2 = s.get(f"{API}/action-board", timeout=20)
    item = next(i for i in r2.json() if i["id"] == created_action["id"])
    assert item["status"] == "REJECTED"


def test_action_board_patch_unknown_id_404(s):
    r = s.patch(f"{API}/action-board/does-not-exist-xyz", json={"status": "REJECTED"}, timeout=20)
    assert r.status_code == 404


# ---------- regression ----------
def test_regression_get_patterns(s):
    r = s.get(f"{API}/patterns", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_regression_get_pattern_room_analysis(s):
    r = s.get(f"{API}/pattern-room/analysis", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "clusters" in d and "patterns" in d
