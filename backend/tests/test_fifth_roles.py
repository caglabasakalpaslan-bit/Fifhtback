"""Boundary tests for the four roles (no server, no network: call_model is faked).

1 QUESTION never reaches Librarian · 2 CLOSE never reaches Librarian · 3 Librarian may return zero
4 Skeptic may reject everything · 5 Storyteller cannot alter Core · 6 every used myth points to a real
Olympus record/source · 7 no external source becomes evidence about the user · 8 Claude unavailable →
no fake enrichment."""
import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fifth_roles.contracts import Enrichment  # noqa: E402
from fifth_roles.core import freeze, route_of, core_hash  # noqa: E402
from fifth_roles.librarian import olympus_records, build_query, prefilter, split_poles, mapping_grounded  # noqa: E402
from fifth_roles.pipeline import run_after_reveal  # noqa: E402


class Unavailable(Exception):
    pass


def turn(status="done", mode=None, distinction="Kırıldığını göstermek ile kırılmayı daha fazla yardımla örtmek arasında",
         reveal="İlk bakışta karşılıksız kalmak gibi görünüyor; anlattığında asıl kırılma, söylemek yerine daha çok vermek.",
         uncertain="Söylememenin arkasında ne olduğu bilinmiyor.", noticed=("Herkese yetişiyor.", "İlk kez kendi için istedi, iki gün bekledi.", "Kırıldı ama söylemedi."), shape="between_two"):
    mode = mode or ("REVEAL" if status == "done" else "QUESTION")
    done = status == "done" and mode == "REVEAL"
    return SimpleNamespace(session_id="s1", status=status, mode=mode, shape=shape if done else None,
                           distinction=distinction if done else None, reveal=reveal if done else None,
                           uncertain=uncertain if done else None, close="Sınavı kazandın ve yazdın. Kutlu olsun." if mode == "CLOSE" else None,
                           noticed=list(noticed), candidates=["Karşılıksız kalmak"])


TENSION_STORY = {"story": "Herkese yetişiyorum. İlk kez ben bir şey istedim, cevap iki gün gecikti. Kırıldım ama söylemedim.", "answer": "Onun için iki gün olağan"}
CLOSE_STORY = {"story": "Bugün çok iyi bir haber aldım, sınavı kazandım. Ailemi aradım, herkes çok mutlu oldu. Ben de mutluyum, sadece bunu bir yere yazmak istedim."}


def _body(obj):
    return {"content": [{"type": "text", "text": json.dumps(obj, ensure_ascii=False)}], "usage": {"input_tokens": 10, "output_tokens": 5}, "model": "fake"}


def fake_model(librarian=None, skeptic=None, storyteller=None, fidelity=None, raise_exc=None):
    calls = []

    def call(system, material):
        calls.append(system[:30])
        if raise_exc:
            raise raise_exc()
        if "KÜTÜPHANECİ" in system:
            return _body(librarian if librarian is not None else {"candidates": []})
        if "ŞÜPHECİ" in system:
            return _body(skeptic if skeptic is not None else {"evaluations": [], "passed": None})
        if "HİKÂYE ANLATICISI" in system:
            return _body(storyteller if storyteller is not None else {"title": "x", "text": "y", "myth_id": None})
        if "KAYNAK DENETÇİSİ" in system:
            return _body(fidelity if fidelity is not None else {"claims": [{"claim": "ok", "category": "event", "supported": True, "evidence": "..."}]})
        raise AssertionError("unknown role prompt")
    call.calls = calls
    return call


def first_recall_record():
    recs = olympus_records()
    core = freeze(turn(), TENSION_STORY)
    kept, _ = prefilter(core, build_query(core), recs)
    assert kept, "pre-filter should keep structurally two-sided, shape-compatible records"
    return next(r for r in kept if r.record_id.endswith("hephaestus_work_vs_belonging")) if any(r.record_id.endswith("hephaestus_work_vs_belonging") for r in kept) else kept[0]


def grounded_match(rec):
    """A mapping that references both the core poles and the record's own pole words (passes verification)."""
    rx, ry = rec.encodes_distinction.get("x") or rec.statement_tr, rec.encodes_distinction.get("y") or rec.mechanism_one_sentence
    return {"x": f"Kırıldığını göstermek → {rx}", "y": f"kırılmayı daha fazla yardımla örtmek → {ry}"}


def test_index_builds_from_olympus_dataset():
    recs = olympus_records()
    assert len(recs) == 45 and all(r.myths for r in recs) and all(r.epistemic_type == "mythic_parallel" for r in recs)
    assert split_poles("A ile B arasında") == ("A", "B") and split_poles("Bir soru") == (None, None)


def test_1_question_never_reaches_librarian():
    call = fake_model()
    res = run_after_reveal(turn(status="question"), TENSION_STORY, call)
    assert res.core_reveal.route == "QUESTION" and res.enrichment.used is False and call.calls == [] and res.librarian is None


def test_2_close_never_reaches_librarian():
    call = fake_model()
    t = turn(mode="CLOSE")                       # CLOSE is the core's own output now
    assert route_of(t, CLOSE_STORY) == "CLOSE" and t.close and t.distinction is None
    res = run_after_reveal(t, CLOSE_STORY, call)
    assert res.core_reveal.route == "CLOSE" and res.enrichment.used is False and call.calls == [] and res.librarian is None


def test_2b_route_is_the_core_mode_not_a_story_heuristic():
    # a tension-free story with a REVEAL from the core is still REVEAL: no downstream override
    assert route_of(turn(), CLOSE_STORY) == "REVEAL"


def test_prefilter_requires_two_sided_structure_and_compatible_shape():
    recs = olympus_records()
    core = freeze(turn(shape="gradient"), TENSION_STORY)
    kept, stats = prefilter(core, build_query(core), recs)
    assert stats["core_poles_parsed"] and stats["kept"] == len(kept) and all(r.shape in ("gradient", "between_two") for r in kept)
    assert stats["excluded_shape"] > 0
    # unparseable core distinction → nothing reaches the mapper
    core2 = freeze(turn(distinction="Bir soru işareti"), TENSION_STORY)
    kept2, stats2 = prefilter(core2, build_query(core2), recs)
    assert kept2 == [] and stats2["core_poles_parsed"] is False


def test_mapping_must_be_grounded_in_both_sides():
    rec = first_recall_record(); core = freeze(turn(), TENSION_STORY); q = build_query(core)
    assert mapping_grounded(grounded_match(rec), q, rec)[0]
    assert not mapping_grounded({"x": "tamamen alakasız serbest çağrışım", "y": "başka bir şey"}, q, rec)[0]
    # a Librarian mapping that is free association is dropped before the Skeptic ever sees it
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": {"x": "serbest çağrışım", "y": "yine öyle"}, "why_it_may_fit": "?"}]})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.librarian.candidates == [] and res.librarian.dropped_by_verification and len(call.calls) == 1


def test_3_librarian_may_return_zero():
    call = fake_model(librarian={"candidates": []})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.librarian is not None and res.librarian.candidates == [] and res.enrichment.used is False
    assert res.enrichment.reason == "librarian_zero_candidates" and len(call.calls) == 1  # skeptic never called


def test_4_skeptic_may_reject_everything():
    rec = first_recall_record()
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 1, "delta": 0, "usefulness": 0, "kill": ["keyword_similarity", "decorative"], "reason": "sadece kelime"}], "passed": None})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.skeptic.passed is None and res.enrichment.used is False and res.enrichment.reason == "skeptic_none" and len(call.calls) == 2


def test_4b_skeptic_post_check_kills_weak_pass():
    rec = first_recall_record()
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 1, "delta": 1, "usefulness": 1, "kill": [], "reason": "zayıf"}], "passed": rec.record_id})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.skeptic.passed is None and "post_check" in res.skeptic.rejections[-1].reasons[0] and res.enrichment.used is False


def test_5_6_storyteller_cannot_alter_core_and_myth_is_real():
    rec = first_recall_record()
    myth_id = rec.myths[0]["myth_id"]
    t = turn()
    before = core_hash(t.distinction, t.reveal, t.uncertain)
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 3, "delta": 2, "usefulness": 2, "kill": [], "reason": "yapısal", "speculation_risk": "low"}], "passed": rec.record_id},
                      storyteller={"title": "Bir hikâye", "text": "Kısa bir mit; ortak olan ayrım şu.", "myth_id": myth_id,
                                   "core_reveal": {"distinction": "DEĞİŞTİRİLDİ"}})   # a later role trying to write the core
    res = run_after_reveal(t, TENSION_STORY, call)
    assert res.enrichment.used is True and res.core_identical and res.core_hash_after == before
    assert res.core_reveal.distinction == t.distinction and t.distinction != "DEĞİŞTİRİLDİ"
    assert res.enrichment.myth_id == myth_id and res.enrichment.record_id == rec.record_id and res.enrichment.figure_id == rec.figure_id
    assert res.enrichment.source_refs == list(rec.myths[0]["sources"]) and len(call.calls) == 4   # + fidelity check
    assert res.enrichment.fidelity["passed"] is True


def test_6b_invented_myth_or_record_is_rejected():
    rec = first_recall_record()
    # storyteller cites a myth the record does not have
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 3, "delta": 2, "usefulness": 2, "kill": [], "reason": "ok"}], "passed": rec.record_id},
                      storyteller={"title": "x", "text": "y", "myth_id": "zeus_invented_episode"})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.enrichment.used is False and "invented_source" in res.enrichment.reason
    # librarian names a record that is not in the corpus/recall set → dropped, zero candidates
    call2 = fake_model(librarian={"candidates": [{"record_id": "greek_olympus:nobody:made_up", "structural_match": {"x": "a", "y": "b"}, "why_it_may_fit": "?"}]})
    res2 = run_after_reveal(turn(), TENSION_STORY, call2)
    assert res2.librarian.candidates == [] and res2.enrichment.used is False
    # skeptic passes an id that was never a candidate → invented source
    call3 = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                       skeptic={"evaluations": [], "passed": "greek_olympus:nobody:made_up"})
    res3 = run_after_reveal(turn(), TENSION_STORY, call3)
    assert res3.skeptic.passed is None and res3.enrichment.used is False


def test_7_no_external_source_becomes_evidence():
    core = freeze(turn(), TENSION_STORY)
    q = build_query(core).model_dump()
    dumped = json.dumps(q, ensure_ascii=False)
    assert TENSION_STORY["story"] not in dumped and "tilki" not in dumped        # no story text, no nickname leaves the core
    rec = first_recall_record()
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 3, "delta": 2, "usefulness": 2, "kill": [], "reason": "ok"}], "passed": rec.record_id},
                      storyteller={"title": "x", "text": "Mit böyle der; demek ki sen aslında sen kırılgansın.", "myth_id": rec.myths[0]["myth_id"]})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.enrichment.used is False and ("banned_register" in res.enrichment.reason or "myth_as_evidence" in res.enrichment.reason)


def test_9_source_fidelity_negative_claim_is_rejected_deterministically():
    rec = first_recall_record(); myth_id = rec.myths[0]["myth_id"]
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 3, "delta": 2, "usefulness": 2, "kill": [], "reason": "ok"}], "passed": rec.record_id},
                      storyteller={"title": "x", "text": "Mit hiçbir yerde onun bunu bilinçli bir strateji olarak kurduğunu söylemez. Ortak ayrım şu.", "myth_id": myth_id})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.enrichment.used is False and "source_fidelity_failed" in res.enrichment.reason
    assert "negative_claim_about_source" in res.enrichment.fidelity["deterministic"] and len(call.calls) == 3  # fidelity call not even needed


def test_9b_source_fidelity_unsupported_claim_from_checker_is_rejected():
    rec = first_recall_record(); myth_id = rec.myths[0]["myth_id"]
    call = fake_model(librarian={"candidates": [{"record_id": rec.record_id, "structural_match": grounded_match(rec), "why_it_may_fit": "yapı"}]},
                      skeptic={"evaluations": [{"record_id": rec.record_id, "pole_match": 3, "delta": 2, "usefulness": 2, "kill": [], "reason": "ok"}], "passed": rec.record_id},
                      storyteller={"title": "x", "text": "Kısa bir mit; sonunda herkes barıştı. Ortak ayrım şu.", "myth_id": myth_id},
                      fidelity={"claims": [{"claim": "sonunda herkes barıştı", "category": "outcome", "supported": False, "evidence": None}]})
    res = run_after_reveal(turn(), TENSION_STORY, call)
    assert res.enrichment.used is False and "source_fidelity_failed" in res.enrichment.reason and res.enrichment.fidelity["unsupported"]


def test_8_unavailable_model_gives_no_fake_enrichment():
    call = fake_model(raise_exc=Unavailable)
    res = run_after_reveal(turn(), TENSION_STORY, call, unavailable_exc=Unavailable)
    assert res.enrichment.used is False and res.enrichment.reason == "model_unavailable" and res.core_identical
    assert res.enrichment.text is None and res.enrichment.myth_id is None


def test_contract_shape_when_unused():
    e = Enrichment(used=False, reason="skeptic_none").model_dump()
    assert e["used"] is False and e["text"] is None and e["source_refs"] == []
