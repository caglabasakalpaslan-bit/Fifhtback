"""SKEPTIC — owns restraint. Receives the untouched core and the Librarian's candidates and tries to
kill every one. At most one survives. NONE is a successful outcome.

Model call + deterministic post-checks the code can verify itself: the passed id must be a real
candidate, the score must clear the threshold, the source floor must hold, and the mapping must exist."""
import json
import re
from typing import Callable, Dict, List, Tuple

from .contracts import CoreReveal, LibrarianCandidate, SkepticVerdict, SkepticRejection, PatternRecord

THRESHOLD = 5
SOURCE_FLOOR = {"mythic_parallel": {"attested_archaic_classical", "attested_hellenistic_roman"}}
REVIEW_REQUIRED = {"fifth_coined", "lived_story"}
KILL_RULES = ["keyword_similarity", "invents_motive", "diagnoses_user", "new_evidence", "changes_core_distinction",
              "decorative", "longer_than_insight", "insufficient_source", "clever_not_useful"]

SKEPTIC_PROMPT = """Sen "The Fifth" içindeki ŞÜPHECİ'sin. Önünde çekirdeğin DOKUNULMAZ Açıklaması ve Kütüphaneci'nin adayları var. İşin her adayı ÖLDÜRMEYE çalışmak. Bir adayı şu gerekçelerden biriyle reddet (birden fazlasını yaz):
- keyword_similarity: sadece kelime/konu benzerliği, kutuplar gerçekten eşlenmiyor
- invents_motive: kişiye bir niyet/güdü atfediyor
- diagnoses_user: kişiyi tipliyor, etiketliyor, teşhis ediyor
- new_evidence: kişinin durumu hakkında çekirdekte olmayan bir iddia getiriyor
- changes_core_distinction: çekirdeğin ayrımını kaydırıyor ya da yeniden yazıyor
- decorative: süs; kaldırılsa hiçbir şey eksilmez
- longer_than_insight: açıklaması içgörüden uzun
- insufficient_source: kaynak desteği zayıf
- clever_not_useful: zekice ama kişinin durumuna geri dönmüyor

Puanla (0–7): pole_match 0–3, delta 0–2 (ad / sonuç örüntüsü / taşınabilir cümle ekliyor mu), usefulness 0–2. Toplam < 5 ise geçemez. En fazla BİR aday geçer; hiçbirinin geçmemesi iyi ve beklenen bir sonuçtur. Yalnızca verilen record_id'leri kullan. Çekirdeği asla değiştirme.

YALNIZCA şu JSON'u ver:
{"evaluations": [{"record_id": "...", "pole_match": 0-3, "delta": 0-2, "usefulness": 0-2, "kill": ["..."], "reason": "tek cümle", "speculation_risk": "low|medium|high"}],
 "passed": null | "record_id"}"""
BANNED = [r"\baslında sen\b", r"\bsen\s+\S+\s+birisin\b", r"\bgibisin\b", r"\bkişilik\b", r"\bbozukluk", r"\bsendrom", r"\bsevgi dili\b", r"\btravma", r"\bterap", r"\bteşhis", r"\byapmalısın\b", r"\bdenemelisin\b"]


def _text(body): return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
def _json(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL); return json.loads(m.group(0) if m else raw)


def banned_register(text: str):
    low = (text or "").lower()
    return next((p for p in BANNED if re.search(p, low)), None)


def post_check(passed_id, evaluations: List[dict], cands: Dict[str, LibrarianCandidate], recs: Dict[str, PatternRecord]) -> Tuple[bool, List[str], int, str]:
    """Code-side verification of the model's PASS. Returns (ok, reasons, score, risk)."""
    if passed_id not in cands:
        return False, ["invented_source: passed id not among candidates"], 0, None
    ev = next((e for e in evaluations if e.get("record_id") == passed_id), None)
    if not ev:
        return False, ["no_evaluation_for_passed"], 0, None
    reasons = []
    score = int(ev.get("pole_match", 0)) + int(ev.get("delta", 0)) + int(ev.get("usefulness", 0))
    if ev.get("kill"):
        reasons.append("kill:" + ",".join(ev["kill"]))
    if score < THRESHOLD:
        reasons.append(f"score_below_threshold:{score}<{THRESHOLD}")
    if int(ev.get("pole_match", 0)) < 2:
        reasons.append("pole_match_too_loose")
    rec = recs.get(passed_id)
    floor = SOURCE_FLOOR.get(rec.epistemic_type) if rec else None
    if rec and floor and rec.max_source_confidence not in floor:
        reasons.append(f"insufficient_source:{rec.max_source_confidence}")
    if rec and rec.epistemic_type in REVIEW_REQUIRED and not rec.human_reviewed:
        reasons.append("review_required")
    sm = cands[passed_id].structural_match
    if not sm.get("x") or not sm.get("y"):
        reasons.append("no_pole_mapping")
    return (not reasons), reasons, score, ev.get("speculation_risk")


def skeptic(core: CoreReveal, candidates: List[LibrarianCandidate], recs: Dict[str, PatternRecord], call_model: Callable[[str, str], dict]) -> Tuple[SkepticVerdict, dict]:
    if not candidates:
        return SkepticVerdict(passed=None, note="no candidates"), {"calls": 0}
    material = json.dumps({
        "core_reveal_immutable": {"distinction": core.distinction, "reveal": core.reveal, "uncertain": core.uncertain, "noticed": core.noticed},
        "candidates": [c.model_dump() | {"record_statement": recs[c.record_id].statement_tr, "myths": [{"myth_id": m["myth_id"], "title": m["title"], "summary": m["summary"], "confidence": m["confidence"]} for m in recs[c.record_id].myths][:3],
                                          "misuse_warnings": recs[c.record_id].misuse_warnings[:3]} for c in candidates if c.record_id in recs],
    }, ensure_ascii=False)
    body = call_model(SKEPTIC_PROMPT, material)
    out = _json(_text(body))
    evals = out.get("evaluations") or []
    rejections = [SkepticRejection(record_id=e.get("record_id", "?"), reasons=list(e.get("kill") or []) + ([e["reason"]] if e.get("reason") else [])) for e in evals]
    passed = out.get("passed")
    if not passed:
        return SkepticVerdict(passed=None, rejections=rejections, note="NONE"), {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
    ok, reasons, score, risk = post_check(passed, evals, {c.record_id: c for c in candidates}, recs)
    if not ok:
        rejections = [r for r in rejections if r.record_id != passed] + [SkepticRejection(record_id=passed, reasons=["post_check:" + "; ".join(reasons)])]
        return SkepticVerdict(passed=None, rejections=rejections, score=score, speculation_risk=risk, note="model passed one; code post-check killed it"), {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
    return SkepticVerdict(passed=passed, rejections=[r for r in rejections if r.record_id != passed], score=score, speculation_risk=risk, note="PASS"), {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
