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


def cand(id, jcv=2, es=2, disc=2, ua=2, le=2, spec=0, steer=0, closure=1, fact="bir olgu", q="Soru?", opts=("a", "b"), already=False,
         known="unknown", converge=False, effects=None):
    if effects is None:   # by default the answers diverge: first option → pole_a, the rest → pole_b
        effects = [{"option": o, "target": "pole_a" if i == 0 else "pole_b", "change": "…"} for i, o in enumerate(opts)]
    return {"id": id, "distinction": f"{id} X ile Y arasında", "pole_a": "X", "pole_b": "Y", "evidence_from_story": "…",
            "missing_discriminating_fact": fact, "fact_already_in_story": already, "possible_question": q, "possible_options": list(opts),
            "already_known": known, "already_known_basis": None, "answer_effects": effects, "answers_converge": converge,
            "expected_information_gain": "…", "why_it_may_change_judgment": "…",
            "scores": {"evidence_support": es, "judgment_change_value": jcv, "discriminability": disc,
            "user_answerability": ua, "low_effort": le, "speculation_risk": spec, "steering_risk": steer, "closure_value": closure}}


def data(cands, winner="c1", **extra):
    d = {"noticed": ["a", "b"], "candidates": cands, "winner_id": winner, "ranking_reasons": "…", "proposed_mode": "REVEAL",
         "close": "Duyuldu.", "reveal": "İlk bakışta … ama asıl ayrım ….", "shape": "between_two", "uncertain": "Bilinmiyor.",
         "card": {"title": "Başlık", "why_it_matters": "Önemli.", "still_open": None, "take_with_you": "Yanında götür."}}
    d.update(extra); return d


SESS = {"session_id": "s", "nickname": "n", "avatar": "🦊", "door": "tell", "story": "…", "created_at": "t", "updated_at": "t"}


def test_question_comes_only_from_the_winner_not_a_contender():
    # c1 wins but has no missing fact; c2 (a near tie) has a perfect question. The question must NOT be asked:
    # a question that does not discriminate the winning distinction is irrelevant to the eventual card.
    t = server._fifth_normalize(SESS, data([cand("c1", fact=None, q=None, opts=()), cand("c2", ua=3, le=3, disc=3)]))
    assert t.mode == "REVEAL" and "blocked (no_missing_fact)" in t.tournament.route_reason
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3), cand("c2", fact=None, q=None, opts=())]))
    assert t.mode == "QUESTION" and t.tournament.question_from == "c1" and t.question_contract.candidate_id == "c1"


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
    assert t.mode == "REVEAL" and "already_known:stated" in t.tournament.route_reason


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


# ---------- tightened eligibility (already_known + convergence) ----------

def test_already_known_stated_or_implied_blocks_the_question():
    for known in ("stated", "implied"):
        t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, known=known)]))
        assert t.mode == "REVEAL" and f"already_known:{known}" in t.tournament.route_reason


def test_unchecked_already_known_blocks_the_question():
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, known=None)]))
    assert t.mode == "REVEAL" and "already_known:unchecked" in t.tournament.route_reason


def test_converging_answers_route_reveal():
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, converge=True)]))
    assert t.mode == "REVEAL" and "answers_converge" in t.tournament.route_reason
    same = [{"option": "a", "target": "pole_a", "change": "…"}, {"option": "b", "target": "pole_a", "change": "…"}]
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, effects=same)]))
    assert t.mode == "REVEAL" and "answers_converge:effects" in t.tournament.route_reason


def test_question_turn_persists_a_full_contract():
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, opts=("evet", "hayır"))]))
    qc = t.question_contract
    assert qc.winning_distinction == "c1 X ile Y arasında" and qc.pole_a == "X" and qc.pole_b == "Y"
    assert qc.missing_discriminating_fact == "bir olgu" and qc.question == "Soru?" and qc.options == ["evet", "hayır"]
    assert qc.expected_information_gain and [e.target for e in qc.what_each_answer_would_change] == ["pole_a", "pole_b"]


# ---------- QUESTION continuity (answer turn) ----------

def answered(answer="evet"):
    t = server._fifth_normalize(SESS, data([cand("c1", ua=3, le=3, disc=3, opts=("evet", "hayır"))]))
    return dict(SESS, question=t.question, options=t.options, answer=answer, question_contract=t.question_contract.model_dump())


def adata(effect="confirms_pole_a", **extra):
    d = {"answer_effect": effect, "what_changed": "'evet' yanıtı X kutbunu güçlendirdi.",
         "updated": {"distinction": "X' ile Y arasında", "pole_a": "X'", "pole_b": "Y", "confidence": "pole_a", "confidence_note": "…"},
         "switch": {"needed": False, "reason": None, "candidates": [], "winner_id": None},
         "proposed_mode": "REVEAL", "close": "Duyuldu.", "reveal": "Yanıtınla …", "shape": "between_two", "uncertain": None,
         "card": {"title": "Başlık", "why_it_matters": "Önemli.", "still_open": None, "take_with_you": "Yanında götür."}}
    d.update(extra); return d


def test_answer_turn_updates_the_contract_distinction_and_the_card_shows_the_effect():
    t = server._fifth_normalize(answered(), adata())
    c = t.tournament.continuity
    assert t.mode == "REVEAL" and c.mode == "updated" and not c.fresh_tournament_ran
    assert c.old_winner == "c1 X ile Y arasında" and c.new_winner == "X' ile Y arasında" and c.switch_reason is None
    assert c.predicted_effect == "pole_a" and c.confidence == "pole_a" and not c.answer_discarded
    assert t.card.distinction == "X' ile Y arasında" and t.card.answer_effect == c.what_changed and t.card.route_path == "QUESTION_REVEAL"
    assert t.tournament.question_from == "c1" and t.question_contract.candidate_id == "c1"


def test_switch_is_refused_unless_the_answer_invalidates_or_adds_new_information():
    sw = {"needed": True, "reason": "…", "candidates": [cand("n1")], "winner_id": "n1"}
    t = server._fifth_normalize(answered(), adata("reshapes", switch=sw))
    c = t.tournament.continuity
    assert c.mode == "updated" and c.switch_refused and c.new_winner == "X' ile Y arasında"


def test_switch_with_permitted_effect_records_old_new_and_reason():
    sw = {"needed": True, "reason": "Yanıt ilk kutbu imkânsız kıldı; kalan gerilim başka yerde.", "candidates": [cand("n1", jcv=3), cand("n2", jcv=1)], "winner_id": "n1"}
    t = server._fifth_normalize(answered(), adata("invalidates", switch=sw))
    c = t.tournament.continuity
    assert c.mode == "switched" and c.fresh_tournament_ran and c.old_winner == "c1 X ile Y arasında" and c.new_winner == "n1 X ile Y arasında"
    assert c.switch_reason.startswith("Yanıt") and t.card.distinction == "n1 X ile Y arasında" and "switched" in t.tournament.route_reason


def test_silent_switch_is_rejected_as_bad_output():
    sw = {"needed": True, "reason": "", "candidates": [cand("n1")], "winner_id": "n1"}
    with pytest.raises(server.FifthBadOutput):
        server._fifth_normalize(answered(), adata("new_information", switch=sw))
    with pytest.raises(server.FifthBadOutput):
        server._fifth_normalize(answered(), adata("bogus_effect"))


def test_no_effect_is_recorded_as_a_discarded_answer_not_hidden():
    t = server._fifth_normalize(answered(), adata("no_effect"))
    assert t.mode == "REVEAL" and t.tournament.continuity.answer_discarded


def test_close_after_answer_only_when_the_tension_dissolved():
    t = server._fifth_normalize(answered(), adata("confirms_pole_b", proposed_mode="CLOSE"))
    assert t.mode == "REVEAL"
    t = server._fifth_normalize(answered(), adata("invalidates", proposed_mode="CLOSE"))
    assert t.mode == "CLOSE" and t.close == "Duyuldu."


def test_answer_material_carries_the_contract_and_no_tournament_framing():
    m = server._fifth_answer_material(answered("hayır"))
    assert "SORU SÖZLEŞMESİ" in m and "kazanan ayrım: c1 X ile Y arasında" in m and "[Kişinin yanıtı] hayır" in m
    assert "\"hayır\" → pole_b" in m and "ikinci soru sorulamaz" not in m.lower()
