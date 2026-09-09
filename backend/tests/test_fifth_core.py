"""Backend tests for THE FIFTH core (one prompt, one model call, one session record).

- GET  /api/fifth/status -> credential mode, never the secret
- GET  /api/fifth/session/{id} -> restore a turn after refresh
- when the model is unreachable the API answers 503 model_unavailable (no fabricated turn)

- GET  /api/fifth/stories -> prototype seed cards + avatars
- POST /api/fifth/start (door=tell) -> QUESTION (status=question) or REVEAL (status=done); Turkish
- POST /api/fifth/answer -> ALWAYS REVEAL (status=done), never a second question
- POST /api/fifth/answer twice -> 409 (the experience stops)
- POST /api/fifth/start (door=find) with a card + "tanıdık gelen" -> same contract
- validation: empty nickname / empty story / unknown card -> 400
"""

import os
import re
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
TR = re.compile(r"[çğıöşüÇĞİÖŞÜ]")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _assert_turn_contract(t):
    assert t["session_id"]
    assert t["status"] in ("question", "done")
    assert t["mode"] in ("QUESTION", "REVEAL")
    if t["status"] == "question":
        assert t["mode"] == "QUESTION"
        assert isinstance(t["question"], str) and t["question"].strip()
        assert 2 <= len(t["options"]) <= 4
        assert t["reveal"] is None
    else:
        assert t["mode"] == "REVEAL"
        assert isinstance(t["reveal"], str) and len(t["reveal"].strip()) > 20
        assert t["question"] is None and t["options"] == []


def test_status_reports_credential_mode_without_secrets(api):
    r = api.get(f"{BASE_URL}/api/fifth/status", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["model"] and d["credential_mode"] in ("proxy", "api_key", None)
    assert isinstance(d["available"], bool)
    assert "sk-" not in r.text  # never leak a key


def test_session_restore_and_journey_metadata(api):
    r = api.post(f"{BASE_URL}/api/fifth/start", json={
        "nickname": "tilki", "avatar": "🦊", "door": "tell", "kind": "anlat", "user_ref": "test-user-ref",
        "story": "Herkese yetişiyorum. İlk kez ben bir şey istedim, cevap iki gün gecikti. Kırıldım ama söylemedim.",
    }, timeout=120)
    if r.status_code == 503:
        pytest.skip("model unavailable in this runtime — honest 503, nothing fabricated")
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["source"] == "api" and t["kind"] == "anlat" and t["created_at"]
    r2 = api.get(f"{BASE_URL}/api/fifth/session/{t['session_id']}", timeout=30)
    assert r2.status_code == 200 and r2.json()["session_id"] == t["session_id"]
    assert r2.json()["status"] == t["status"] and r2.json()["question"] == t["question"]


def test_enrich_endpoint_stops_on_question_and_never_alters_core(api):
    r = api.post(f"{BASE_URL}/api/fifth/start", json={
        "nickname": "tilki", "avatar": "🦊", "door": "tell", "kind": "anlat",
        "story": "Terfi teklif ettiler. Herkes sevindi, ben sevinemedim. Gece uyuyamadım ama nedenini kendime bile söyleyemiyorum. Belki istemiyorum, belki korkuyorum, ayıramıyorum.",
    }, timeout=120)
    if r.status_code == 503:
        pytest.skip("model unavailable in this runtime — honest 503, nothing fabricated")
    t = r.json()
    e = api.post(f"{BASE_URL}/api/fifth/enrich/{t['session_id']}", timeout=180)
    assert e.status_code == 200, e.text
    res = e.json()
    assert res["core_identical"] is True and res["core_reveal"]["session_id"] == t["session_id"]
    assert res["core_reveal"]["distinction"] == t["distinction"] and res["core_reveal"]["reveal"] == t["reveal"]
    if t["status"] == "question":
        assert res["core_reveal"]["route"] == "QUESTION" and res["enrichment"]["used"] is False
        assert res["librarian"] is None and res["total_calls"] == 0
    else:
        assert res["core_reveal"]["route"] in ("REVEAL", "CLOSE") and isinstance(res["enrichment"]["used"], bool)
        if res["enrichment"]["used"]:
            assert res["enrichment"]["myth_id"] and res["enrichment"]["record_id"] and res["enrichment"]["source_refs"]
    # session restore now carries the stored pipeline result
    s2 = api.get(f"{BASE_URL}/api/fifth/session/{t['session_id']}", timeout=30).json()
    assert s2["enrichment"]["core_identical"] is True


def test_stories_seed(api):
    r = api.get(f"{BASE_URL}/api/fifth/stories", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"] == "prototype_seed"
    assert len(d["stories"]) >= 3
    assert all({"id", "title", "text", "lens"} <= set(c) for c in d["stories"])
    assert len(d["avatars"]) >= 3


def test_door_tell_full_loop_stops_after_one_question(api):
    story = (
        "Arkadaşım üçüncü kez son dakika planı iptal etti. Kızmadım ama bir daha teklif etmeyeceğim. "
        "Aslında kendime mi kızıyorum ona mı emin değilim."
    )
    r = api.post(f"{BASE_URL}/api/fifth/start",
                 json={"nickname": "tilki", "avatar": "🦊", "door": "tell", "story": story}, timeout=120)
    if r.status_code == 503:
        pytest.skip("model unavailable in this runtime — honest 503, nothing fabricated")
    assert r.status_code == 200, r.text
    t = r.json()
    _assert_turn_contract(t)
    assert t["nickname"] == "tilki" and t["door"] == "tell"

    if t["status"] == "question":
        assert TR.search(t["question"]) or t["question"].endswith("?")
        r2 = api.post(f"{BASE_URL}/api/fifth/answer",
                      json={"session_id": t["session_id"], "answer": t["options"][0]}, timeout=120)
        assert r2.status_code == 200, r2.text
        t2 = r2.json()
        _assert_turn_contract(t2)
        assert t2["status"] == "done", "answer must ALWAYS end in a Reveal (max one question)"
        sid = t2["session_id"]
    else:
        sid = t["session_id"]

    # The experience stops: a further answer is refused.
    r3 = api.post(f"{BASE_URL}/api/fifth/answer", json={"session_id": sid, "answer": "bir daha"}, timeout=30)
    assert r3.status_code == 409, r3.text


def test_door_find_with_card(api):
    cards = api.get(f"{BASE_URL}/api/fifth/stories", timeout=30).json()["stories"]
    r = api.post(f"{BASE_URL}/api/fifth/start", json={
        "nickname": "baykuş", "avatar": "🦉", "door": "find",
        "story_card_id": cards[0]["id"],
        "familiar": "Ben de teklif etmeyi bırakıyorum, kızmak yerine sessizce çekiliyorum.",
    }, timeout=120)
    if r.status_code == 503:
        pytest.skip("model unavailable in this runtime — honest 503, nothing fabricated")
    assert r.status_code == 200, r.text
    t = r.json()
    _assert_turn_contract(t)
    assert t["door"] == "find"
    if t["status"] == "question":
        r2 = api.post(f"{BASE_URL}/api/fifth/answer",
                      json={"session_id": t["session_id"], "answer": "Daha önce de oldu"}, timeout=120)
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "done"


@pytest.mark.parametrize("payload", [
    {"nickname": "  ", "door": "tell", "story": "bir şey oldu"},
    {"nickname": "x", "door": "tell", "story": "   "},
    {"nickname": "x", "door": "find", "story_card_id": "nope", "familiar": "..."},
    {"nickname": "x", "door": "find", "story_card_id": "s1", "familiar": ""},
])
def test_start_validation(api, payload):
    r = api.post(f"{BASE_URL}/api/fifth/start", json=payload, timeout=30)
    assert r.status_code == 400, r.text


def test_answer_unknown_session(api):
    r = api.post(f"{BASE_URL}/api/fifth/answer", json={"session_id": "missing", "answer": "x"}, timeout=30)
    assert r.status_code == 404
