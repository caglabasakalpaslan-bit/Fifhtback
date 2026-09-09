"""LIBRARIAN — owns memory. "Has humanity already described, named, narrated or modelled this
distinction somewhere else?" v0 corpus: backend/olympus/greek_olympians_v0_1.json only.

Two steps: lexical RECALL over Pattern Records (cheap, keyword-level, deliberately over-inclusive),
then one model call that keeps only candidates whose two poles map onto the core's two poles and
explains why each may fit. It may return zero. It never sees the story or the nickname."""
import json
import math
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
RECALL_K = 8
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


# ---------- recall ----------
def tokens(text: str) -> List[str]:
    return [w[:5] for w in re.findall(r"[a-zçğıöşü]+", (text or "").translate(_TR).lower()) if len(w) >= 3 and w not in _STOP]


def recall(q: LibrarianQuery, records: List[PatternRecord], k: int = RECALL_K) -> List[Tuple[PatternRecord, float]]:
    q_pole = set(tokens(" ".join(v for v in q.poles.values() if v)) or tokens(q.distinction))
    q_sit, q_unc, q_rej = set(tokens(" ".join(q.structural_situation))), set(tokens(q.uncertain or "")), set(tokens(" ".join(q.candidates_rejected)))
    scored = []
    for r in records:
        r_pole = set(tokens(" ".join(v for v in r.encodes_distinction.values() if v)) or tokens(r.statement_tr))
        r_port, r_bound, r_sit = set(tokens(" ".join(r.portable_expressions_tr))), set(tokens(" ".join(r.boundary_questions_tr))), set(tokens(" ".join(r.situations_tr)))
        s = (3.0 * len(q_pole & r_pole) + 2.0 * len(q_pole & r_port) + 1.5 * len((q_pole | q_unc) & r_bound)
             + 1.0 * len(q_sit & (r_sit | r_port)) + 0.5 * len(q_unc & (r_port | r_pole)) - 1.0 * len(q_rej & r_pole))
        s = round(s / math.sqrt(1 + len(r_pole | r_port | r_bound | r_sit)), 3)
        if s > 0:
            scored.append((r, s))
    scored.sort(key=lambda t: -t[1])
    return scored[:k]


# ---------- structural mapping (one model call) ----------
LIBRARIAN_PROMPT = """Sen "The Fifth" içindeki KÜTÜPHANECİ'sin. Sana çekirdeğin çıkardığı bir AYRIM ve bir kayıt listesi verildi. Sorun şu: "İnsanlık bu ayrımı başka bir yerde zaten anlatmış, adlandırmış ya da modellemiş mi?" Yalnızca YAPISAL eşleşme ararsın: kaydın iki kutbu çekirdeğin iki kutbuna tek tek eşlenebiliyor mu? Tanrı adı, ortak kelime, ortak duygu, aynı konu = eşleşme DEĞİLDİR.

Kişi hakkında hiçbir şey bilmiyorsun ve bilmemelisin; yorum yapmazsın, kanıt üretmezsin. Yalnızca sana verilen record_id'leri kullanabilirsin. En fazla 5 aday döndür; SIFIR aday döndürmek geçerli ve sık beklenen bir sonuçtur.

YALNIZCA şu JSON'u ver:
{"candidates": [{"record_id": "...", "structural_match": {"x": "çekirdek X → kayıt x'", "y": "çekirdek Y → kayıt y'"}, "why_it_may_fit": "tek cümle, yapıyı anlatan"}]}"""


def render_record(r: PatternRecord) -> dict:
    return {"record_id": r.record_id, "figure": r.figure_name, "shape": r.shape, "poles": r.encodes_distinction, "statement": r.statement_tr,
            "mechanism": r.mechanism_one_sentence, "portable_expressions": r.portable_expressions_tr[:3], "situations": r.situations_tr[:3],
            "boundary_questions": r.boundary_questions_tr[:2],
            "myths": [{"myth_id": m["myth_id"], "title": m["title"], "summary": m["summary"], "confidence": m["confidence"]} for m in r.myths][:3]}


def _text(body: dict) -> str:
    return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(m.group(0) if m else raw)


def librarian(core: CoreReveal, call_model: Callable[[str, str], dict], records: List[PatternRecord] = None) -> Tuple[LibrarianOutput, dict]:
    """Returns (output, usage-ish dict). Raises whatever call_model raises (the pipeline maps it)."""
    records = records if records is not None else olympus_records()
    q = build_query(core)
    q_sent = q.model_dump()
    hits = recall(q, records)
    if not hits:
        return LibrarianOutput(candidates=[], recall_considered=0, query_sent={"contains_story_text": False, "contains_nickname": False, "fields": list(q_sent)}), {"calls": 0}
    by_id = {r.record_id: r for r, _ in hits}
    body = call_model(LIBRARIAN_PROMPT, json.dumps({"core": q_sent, "records": [render_record(r) for r, _ in hits]}, ensure_ascii=False))
    out = _json(_text(body))
    cands = []
    for c in (out.get("candidates") or [])[:MAX_CANDIDATES]:
        r = by_id.get(c.get("record_id"))
        sm = c.get("structural_match") or {}
        if not r or not sm.get("x") or not sm.get("y"):
            continue  # not in the recall set (invented) or no pole mapping → not a candidate
        cands.append(LibrarianCandidate(
            record_id=r.record_id, figure_id=r.figure_id, myth_ids=[m["myth_id"] for m in r.myths],
            source_refs=sorted({s for m in r.myths for s in m.get("sources", [])}), epistemic_type=r.epistemic_type,
            structural_match={"x": sm["x"], "y": sm["y"]}, why_it_may_fit=str(c.get("why_it_may_fit", "")).strip(),
            recall_score=next(s for rr, s in hits if rr.record_id == r.record_id),
        ))
    return LibrarianOutput(candidates=cands, recall_considered=len(hits), query_sent={"contains_story_text": False, "contains_nickname": False, "fields": list(q_sent)}), {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
