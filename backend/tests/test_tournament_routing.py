"""Distinction tournament → deterministic routing (no network). Nothing here names a baseline case."""
import os
import sys
import types

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017"); os.environ.setdefault("DB_NAME", "t")
try:
    import emergentintegrations.llm.chat  # noqa
except ImportError:
    stub = types.ModuleType("emergentintegrations.llm.chat"); stub.LlmChat = object; stub.UserMessage = object
    sys.modules["emergentintegrations"] = types.ModuleType("e"); sys.modules["emergentintegrations.llm"] = types.ModuleType("e.l"); sys.modules["emergentintegrations.llm.chat"] = stub
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402


def cand(id, jcv=2, es=2, disc=2, ua=2, le=2, spec=0, steer=0, closure=1, fact="bir olgu", q="Soru?", opts=("a", "b"), already=False):
    return {"id": id, "distinction": f"{id} X ile Y arasında", "pole_a": "X", "pole_b": "Y", "evidence_from_story": "…",
            "missing_discriminating_fact": fact, "fact_already_in_story": already, "possible_question": q, "possible_options": list(opts),
            "why_it_may_change_judgment": "…", "scores": {"evidence_support": es, "judgment_change_value": jcv, "discriminability": disc,
            "user_answerability": ua, "low_effort": le, "speculation_risk": spec, "steering_risk": steer, "closure_value": closure}}


def data(cands, winner="c1", **extra):
    d = {"noticed": ["a", "b"], "candidates": cands, "winner_id": winner, "ranking_reasons": "…", "proposed_mode": "REVEAL",
         "close": "Duyuldu.", "reveal": "İlk bakışta … ama asıl ayrım ….", "shape": "between_two", "uncertain": "Bilinmiyor.",
         "card": {"title": "Başlık", "why_it_matters": "Önemli.", "still_open": None, "take_with_you": "Yanında götür."}}
    d.update(extra); return d


SESS = {"session_id": "s", "nickname": "n", "avatar": "🦊", "door": "tell", "story": "…", "created_at": "t", "updated_at": "t"}


def test_question_when_a_contender_has_an_answerable_discriminating_fact():
    t = server._fifth_normalize(SESS, data([cand("c1", fact=None, q=None, opts=()), cand("c2", ua=3, le=3, disc=3)]))
    assert t.mode == "QUESTION" and t.tournament.routed_mode == "QUESTION" and t.tournament.question_from == "c2"
    assert t.question == "Soru?" and t.options == ["a", "b"]


def test_premature_reveal_is_blocked_when_a_missing_fact_is_answerable():
    # the model proposes REVEAL, but its own scores say a low-effort, answerable fact would discriminate → QUESTION
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, jcv=3)], proposed_mode="REVEAL"))
    assert t.mode == "QUESTION" and t.tournament.proposed_mode == "REVEAL"


def test_false_close_is_blocked_when_any_candidate_carries_tension():
    # the model proposes CLOSE, but a candidate has judgment_change_value ≥ 2 → cannot CLOSE
    t = server._fifth_normalize(SESS, data([cand("c1", jcv=3, fact=None, q=None, opts=()), cand("c2", jcv=1, fact=None, q=None, opts=())], proposed_mode="CLOSE"))
    assert t.mode in ("QUESTION", "REVEAL") and t.mode != "CLOSE" and "tension" not in (t.tournament.route_reason or "").lower().replace("judgment-changing tension", "")


def test_close_only_when_no_candidate_has_judgment_changing_tension():
    t = server._fifth_normalize(SESS, data([cand("c1", jcv=1, closure=3, fact=None, q=None, opts=()), cand("c2", jcv=0, closure=3, fact=None, q=None, opts=())], proposed_mode="CLOSE"))
    assert t.mode == "CLOSE" and t.close == "Duyuldu." and t.distinction is None and t.card is None


def test_never_ask_what_the_story_already_contains():
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, already=True)]))
    assert t.mode == "REVEAL" and "already_in_story" in t.tournament.route_reason


def test_third_party_mind_is_not_answerable_so_no_question():
    t = server._fifth_normalize(SESS, data([cand("c1", ua=0, le=3, disc=3)]))
    assert t.mode == "REVEAL"


def test_second_question_forbidden_after_answer():
    sess = dict(SESS, question="önceki soru", answer="cevap")
    t = server._fifth_normalize(sess, data([cand("c1", ua=3, le=3, disc=3)]))
    assert t.mode == "REVEAL" and t.card.route_path == "QUESTION_REVEAL"


def test_speculation_and_steering_reduce_rank_and_change_the_winner():
    c1 = cand("c1", es=3, jcv=3, disc=3, spec=3, steer=3, fact=None, q=None, opts=())   # rank 3
    c2 = cand("c2", es=2, jcv=2, disc=2, spec=0, steer=0, fact=None, q=None, opts=())   # rank 6
    t = server._fifth_normalize(SESS, data([c1, c2], winner="c1"))
    assert t.mode == "REVEAL" and t.distinction.startswith("c2")


def test_reveal_builds_a_fifth_card_with_core_distinction():
    t = server._fifth_normalize(SESS, data([cand("c1", fact=None, q=None, opts=())]))
    assert t.mode == "REVEAL" and t.card and t.card.distinction == t.distinction and t.card.title == "Başlık"
    assert t.card.take_with_you == "Yanında götür." and t.card.route_path == "REVEAL" and t.card.session_id == "s" and t.card.card_id
    assert t.card.still_open == "Bilinmiyor."   # falls back to the core's uncertainty when the card omits it


def test_scores_are_clamped_and_bad_scores_do_not_crash():
    c = cand("c1", fact=None, q=None, opts=()); c["scores"]["evidence_support"] = 99; c["scores"]["speculation_risk"] = "x"
    t = server._fifth_normalize(SESS, data([c]))
    assert t.tournament.candidates[0].scores.evidence_support == 3
