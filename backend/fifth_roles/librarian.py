"""LIBRARIAN — owns memory. "Has humanity already described, named, narrated or modelled this
distinction somewhere else?" v0 corpus: backend/olympus/greek_olympians_v0_1.json only.

Two steps: lexical RECALL over Pattern Records (cheap, keyword-level, deliberately over-inclusive),
then one model call that keeps only candidates whose two poles map onto the core's two poles and
explains why each may fit. It may return zero. It never sees the story or the nickname."""
import json
import os
import re
from functools import lru_cache
from typing import Callable, Dict, List, Tuple

from .contracts import PatternRecord, LibrarianQuery, LibrarianCandidate, LibrarianOutput, CoreReveal

OLYMPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "olympus", "greek_olympians_v0_1.json")
CONFIDENCE_RANK = {"attested_archaic_classical": 5, "attested_hellenistic_roman": 4, "scholarly_inference": 3, "attested_late_or_orphic": 2, "unsourced_popular": 0}
_POLES = re.compile(r"^(?P<x>.+?)\s+ile\s+(?P<y>.+?)\s+arasında", re.IGNORECASE)
_TR = str.maketrans({"I": "ı", "İ": "i"})
_STOP = {"ile", "arasında", "bir", "ve", "ya", "da", "de", "mi", "mı", "mu", "mü", "için", "gibi", "ama", "daha", "çok", "olmak", "olması", "olan", "kendi", "şey", "bu", "ne", "değil", "kişi", "kişinin", "sen", "senin", "onun"}
MAX_CANDIDATES = 5


# ---------- corpus adapter ----------
def split_poles(statement: str) -> Tuple:
    m = _POLES.match((statement or "").strip())
    return (m.group("x").strip(" ,;—-"), m.group("y").strip(" ,;—-")) if m else (None, None)


def build_records(path: str = OLYMPUS_PATH) -> List[PatternRecord]:
    with open(path, encoding="utf-8") as f:
        world = json.load(f)
    out = []
    for fig in world["figures"]:
        fi, src = fig["fifth_interpretation"], fig["source_supported"]
        myths_by_id = {m["myth_id"]: m for m in src["major_myths"]}
        for t in fi["tensions"]:
            mids = set(t.get("from_myths", []))
            myths = [myths_by_id[m] for m in mids if m in myths_by_id]
            x, y = split_poles(t["statement"])
            reveal_mat = [r for r in fi["possible_reveal_material"] if r.get("tension_ref") == t["tension_id"]]
            bqs = [b for b in fi["boundary_questions"] if mids & set(b.get("from_myths", []))]
            tags = [m["confidence"] for m in myths]
            out.append(PatternRecord(
                record_id=f"{world['world_id']}:{fig['id']}:{t['tension_id']}", epistemic_type="mythic_parallel",
                world_id=world["world_id"], figure_id=fig["id"], figure_name=fig.get("name_tr") or fig["name"],
                title_tr=f"{fig.get('name_tr') or fig['name']} — {t['statement']}",
                encodes_distinction={"x": x, "y": y}, statement_tr=t["statement"], shape=t["shape"],
                mechanism_one_sentence=(f"{bqs[0]['turns_from']} → {bqs[0]['turns_into']}" if bqs else (t.get("note") or t["statement"])),
                portable_expressions_tr=[r["distinction"] for r in reveal_mat] + [r["fragment"] for r in reveal_mat],
                situations_tr=[s["situation"] for s in fi["recurring_human_situations"] if mids & set(s.get("from_myths", []))],
                boundary_questions_tr=[b["question"] for b in bqs],
                myths=[{"myth_id": m["myth_id"], "title": m["title"], "summary": m["summary"], "sources": m["sources"], "confidence": m["confidence"]} for m in myths],
                source_refs=src["source_references"],
                max_source_confidence=(max(tags, key=lambda c: CONFIDENCE_RANK.get(c, -1)) if tags else None),
                interpretation_confidence=fi["interpretation_confidence"]["level"],
                misuse_warnings=fig["overinterpretation_warnings"],
                human_reviewed=bool(fig.get("record_status", {}).get("human_reviewed")),
            ))
    return out


@lru_cache(maxsize=1)
def olympus_records() -> List[PatternRecord]:
    return build_records()


# ---------- query (no user text) ----------
def situation_level(noticed: List[str]) -> List[str]:
    out = []
    for n in noticed:
        s = re.sub(r"[\"'“”‘’«»][^\"'“”‘’«»]*[\"'“”‘’«»]", "", n)
        s = re.sub(r"\s+", " ", s).strip(" .:;—-")
        if len(s) > 12:
            out.append(s)
    return out[:3]


def build_query(core: CoreReveal) -> LibrarianQuery:
    x, y = split_poles(core.distinction or "")
    return LibrarianQuery(distinction=core.distinction or "", poles={"x": x, "y": y},
                          structural_situation=situation_level(core.noticed), uncertain=core.uncertain,
                          noticed=list(core.noticed), candidates_rejected=list(core.candidates)[:3])


# ---------- structural pre-filter (no model) ----------
SHAPE_COMPATIBLE = {
    "between_two": {"between_two", "sequence", "gradient"},
    "gradient": {"gradient", "between_two"},
    "sequence": {"sequence", "between_two"},
    "open_question": {"open_question", "between_two", "sequence", "gradient"},
    None: {"between_two", "gradient", "sequence", "open_question"},
}


def tokens(text: str) -> List[str]:
    return [w[:5] for w in re.findall(r"[a-zçğıöşü]+", (text or "").translate(_TR).lower()) if len(w) >= 3 and w not in _STOP]


def prefilter(core: CoreReveal, q: LibrarianQuery, records: List[PatternRecord]) -> Tuple[List[PatternRecord], Dict]:
    """A record reaches the mapper only if the core distinction has two parseable poles, the record
    itself encodes a two-sided distinction (poles, or a mechanism 'from → into'), and the shapes are
    compatible. Nothing lexical here."""
    stats = {"total": len(records), "core_poles_parsed": bool(q.poles.get("x") and q.poles.get("y")), "excluded_shape": 0, "excluded_no_structure": 0, "kept": 0}
    if not stats["core_poles_parsed"]:
        stats["kept"] = 0
        return [], stats
    kept = []
    allowed = SHAPE_COMPATIBLE.get(core.shape, SHAPE_COMPATIBLE[None])
    for r in records:
        two_sided = bool(r.encodes_distinction.get("x") and r.encodes_distinction.get("y")) or ("→" in (r.mechanism_one_sentence or ""))
        if not two_sided:
            stats["excluded_no_structure"] += 1
            continue
        if r.shape not in allowed:
            stats["excluded_shape"] += 1
            continue
        kept.append(r)
    stats["kept"] = len(kept)
    return kept, stats


# ---------- structural mapping (one compact model call) ----------
LIBRARIAN_PROMPT = """Sen "The Fifth" içindeki KÜTÜPHANECİ'sin. Sana çekirdeğin çıkardığı bir AYRIM (iki kutup X ve Y, biçimi ve durumu) ve kısa KAYIT KARTLARI verildi. Her kartta bir ayrımın iki kutbu (x', y') ve mekanizması var. Sorun: "İnsanlık bu ayrımı başka bir yerde zaten anlatmış mı?"

Yalnızca YAPISAL eşleşme ararsın: X→x' VE Y→y' ikisi de birebir eşlenmeli ve eşlemeyi tek cümleyle yazabilmelisin. Kutuplardan biri eşlenmiyorsa aday DEĞİLDİR. Ortak kelime, ortak duygu, aynı konu, tanrı adı = eşleşme değildir. Kişi hakkında hiçbir şey bilmiyorsun. Yalnızca verilen record_id'leri kullan. En fazla 5 aday; SIFIR aday geçerli ve sık beklenen bir sonuçtur.

YALNIZCA şu JSON'u ver:
{"candidates": [{"record_id": "...", "structural_match": {"x": "çekirdek X → kayıt x' (kaydın kendi sözcükleriyle)", "y": "çekirdek Y → kayıt y' (kaydın kendi sözcükleriyle)"}, "why_it_may_fit": "tek cümle; yapı, konu değil"}]}"""


def compact_card(r: PatternRecord) -> dict:
    """~30 tokens per record instead of ~450: id, shape, poles, mechanism."""
    return {"id": r.record_id, "shape": r.shape, "x": r.encodes_distinction.get("x") or r.statement_tr, "y": r.encodes_distinction.get("y") or "", "mech": r.mechanism_one_sentence[:120]}


def _text(body: dict) -> str:
    return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(m.group(0) if m else raw)


def mapping_grounded(sm: Dict[str, str], q: LibrarianQuery, r: PatternRecord) -> Tuple[bool, str]:
    """Both mapping strings must actually reference the record's own pole/mechanism words AND the core's
    pole words. Otherwise the 'mapping' is free association and the candidate is dropped."""
    rec_side = set(tokens(" ".join(v for v in r.encodes_distinction.values() if v)) + tokens(r.mechanism_one_sentence) + tokens(r.statement_tr))
    core_side = set(tokens(q.poles.get("x") or "") + tokens(q.poles.get("y") or ""))
    for side in ("x", "y"):
        t = set(tokens(sm.get(side, "")))
        if not (t & rec_side):
            return False, f"{side}: mapping does not reference the record"
        if not (t & core_side):
            return False, f"{side}: mapping does not reference the core pole"
    return True, "ok"


def librarian(core: CoreReveal, call_model: Callable[[str, str], dict], records: List[PatternRecord] = None) -> Tuple[LibrarianOutput, dict]:
    """Returns (output, usage-ish dict). Raises whatever call_model raises (the pipeline maps it)."""
    records = records if records is not None else olympus_records()
    q = build_query(core)
    q_sent = {"contains_story_text": False, "contains_nickname": False, "fields": list(q.model_dump().keys())}
    kept, stats = prefilter(core, q, records)
    if not kept:
        return LibrarianOutput(candidates=[], recall_considered=0, prefilter=stats, query_sent=q_sent), {"calls": 0}
    by_id = {r.record_id: r for r in kept}
    payload = {"core": {"distinction": q.distinction, "x": q.poles.get("x"), "y": q.poles.get("y"), "shape": core.shape,
                        "situation": q.structural_situation, "uncertain": q.uncertain, "not_these_readings": q.candidates_rejected},
               "records": [compact_card(r) for r in kept]}
    body = call_model(LIBRARIAN_PROMPT, json.dumps(payload, ensure_ascii=False))
    out = _json(_text(body))
    cands, dropped = [], []
    for c in (out.get("candidates") or [])[:MAX_CANDIDATES]:
        r = by_id.get(c.get("record_id"))
        sm = c.get("structural_match") or {}
        if not r:
            dropped.append({"record_id": c.get("record_id"), "why": "not in pre-filtered set (unknown or excluded id)"}); continue
        if not sm.get("x") or not sm.get("y"):
            dropped.append({"record_id": r.record_id, "why": "missing pole mapping"}); continue
        ok, why = mapping_grounded(sm, q, r)
        if not ok:
            dropped.append({"record_id": r.record_id, "why": why}); continue
        cands.append(LibrarianCandidate(
            record_id=r.record_id, figure_id=r.figure_id, myth_ids=[m["myth_id"] for m in r.myths],
            source_refs=sorted({s for m in r.myths for s in m.get("sources", [])}), epistemic_type=r.epistemic_type,
            structural_match={"x": sm["x"], "y": sm["y"]}, why_it_may_fit=str(c.get("why_it_may_fit", "")).strip(),
            recall_score=0.0,
        ))
    return LibrarianOutput(candidates=cands, recall_considered=len(kept), prefilter=stats, dropped_by_verification=dropped, query_sent=q_sent), {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
