"""STORYTELLER — owns expression. Runs only when the Skeptic passed exactly one candidate.
Gives the same insight a second, vivid language. The core is immutable; provenance is copied from
the record. Every factual statement about the myth must be supported by the retrieved record:
a deterministic screen first, then one fidelity check call; any unsupported claim → used=false."""
import json
import re
from typing import Callable, Tuple

from .contracts import CoreReveal, LibrarianCandidate, PatternRecord, Enrichment
from .skeptic import banned_register

MAX_WORDS = 90
STORYTELLER_PROMPT = """Sen "The Fifth" içindeki HİKÂYE ANLATICISI'sın. Çekirdek bir Açıklama verdi; o DOKUNULMAZ. Şüpheci tek bir kaydı onayladı. İşin: aynı ayrımı, o kaydın mitinin diliyle bir kez daha söylemek — ve hemen kişinin kendi durumuna geri dönmek.

KAYNAK SADAKATİ (en önemli kural): Mit hakkında söylediğin HER cümle sana verilen mit özetinde AÇIKÇA bulunmalı. Özette olmayan hiçbir şey ekleme: niyet/güdü ("bilinçli", "istedi", "amaçladı", "farkında değildi"), zaman sırası, sonuç, kaynağın yüklediği anlam. Kaynağın NE DEMEDİĞİNİ de söyleme ("mit hiçbir yerde ... demez" yasak). Özet yetmiyorsa daha az anlat; uydurma.

DİĞER KURALLAR:
- En fazla 90 kelime, 2–4 cümle. Günlük Türkçe; terapi/koçluk dili yok.
- Miti kısaca ve canlı anlat; sonra köprüyü kur: "ortak olan şu ayrım".
- ASLA "sen X gibisin" deme; kişiyi figürle özdeşleştirme.
- Mit KANIT değildir; "demek ki", "bu gösteriyor ki" yasak. Metaforu bilime çevirme.
- Kişi hakkında çekirdekte olmayan hiçbir iddia yok; tavsiye yok.

YALNIZCA şu JSON'u ver:
{"title": "≤6 kelime; figür adı geçebilir", "text": "≤90 kelime", "myth_id": "kullandığın mitin id'si (verilenlerden biri)"}"""

FIDELITY_PROMPT = """Sen bir KAYNAK DENETÇİSİsin. Sana bir mit hakkında bir KAYIT (özet + başlık) ve o mite dayanan kısa bir METİN verildi. Metindeki MİT HAKKINDAKİ her olgusal iddiayı çıkar (kişinin durumu hakkındaki cümleleri değil) ve her biri için kayıtta AÇIKÇA desteklenip desteklenmediğine karar ver. Şunlar özellikle desteklenmiş sayılmaz: kayıtta olmayan niyet/güdü, zaman sırası, sonuç, kaynağın yüklediği anlam, ve "kaynak şunu söylemez" türü olumsuz iddialar. Makul paraphrase desteklenmiş sayılır. Katı ol; şüphede desteklenmemiş de.

YALNIZCA şu JSON'u ver:
{"claims": [{"claim": "...", "category": "event|motive|intention|chronology|outcome|meaning|negative_claim", "supported": true|false, "evidence": "kayıttan kısa alıntı ya da null"}]}"""

# Deterministic screen: things the record can never support from a summary.
NEGATIVE_CLAIM = re.compile(r"(hiçbir yerde|hiç bir yerde|asla)\s.*\b(söylemez|demez|anlatmaz|yazmaz|geçmez)", re.IGNORECASE)
MOTIVE_WORDS = re.compile(r"\b(bilinçli|bilinçsiz|niyet|amaçla|strateji|farkında değil|farkındaydı|isteyerek|kasıtl)", re.IGNORECASE)


def _text(body): return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
def _json(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL); return json.loads(m.group(0) if m else raw)
def _wc(s): return len(re.findall(r"\S+", s or ""))


def deterministic_screen(text: str, myth: dict) -> list:
    problems = []
    if NEGATIVE_CLAIM.search(text or ""):
        problems.append("negative_claim_about_source")
    summary = (myth.get("summary") or "").lower()
    for m in MOTIVE_WORDS.finditer(text or ""):
        w = m.group(1).lower()[:6]
        if w not in summary:
            problems.append(f"motive_word_not_in_record:{m.group(1)}")
    return problems


def fidelity_check(text: str, myth: dict, call_model: Callable[[str, str], dict]) -> Tuple[dict, dict]:
    body = call_model(FIDELITY_PROMPT, json.dumps({"record": {"title": myth["title"], "summary": myth["summary"]}, "text": text}, ensure_ascii=False))
    out = _json(_text(body))
    claims = out.get("claims") or []
    unsupported = [c for c in claims if not c.get("supported")]
    return {"passed": len(unsupported) == 0, "claims": claims, "unsupported": unsupported}, {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}


def storyteller(core: CoreReveal, cand: LibrarianCandidate, rec: PatternRecord, call_model: Callable[[str, str], dict]) -> Tuple[Enrichment, dict]:
    material = json.dumps({
        "core_reveal_immutable": {"distinction": core.distinction, "reveal": core.reveal, "uncertain": core.uncertain},
        "approved_candidate": {"record_id": rec.record_id, "figure": rec.figure_name, "statement": rec.statement_tr, "structural_match": cand.structural_match,
                               "myths": [{"myth_id": m["myth_id"], "title": m["title"], "summary": m["summary"]} for m in rec.myths],
                               "misuse_warnings": rec.misuse_warnings},
    }, ensure_ascii=False)
    body = call_model(STORYTELLER_PROMPT, material)
    out = _json(_text(body))
    text, title, myth_id = str(out.get("text", "")).strip(), str(out.get("title", "")).strip(), out.get("myth_id")
    myth = next((m for m in rec.myths if m["myth_id"] == myth_id), None)
    meta = {"calls": 1, "usage": body.get("usage"), "model": body.get("model"), "fidelity_calls": 0}
    problems = []
    if not myth:
        problems.append("invented_source: myth_id not on the approved record")
    if not text or _wc(text) > MAX_WORDS:
        problems.append(f"length:{_wc(text)}>{MAX_WORDS}")
    b = banned_register(text + " " + title)
    if b:
        problems.append(f"banned_register:{b}")
    if re.search(r"demek ki|bu gösteriyor ki|kanıtl", text.lower()):
        problems.append("myth_as_evidence")
    fidelity = None
    if not problems:
        det = deterministic_screen(text, myth)
        fidelity = {"passed": not det, "deterministic": det, "claims": []}
        if not det:
            fid, fmeta = fidelity_check(text, myth, call_model)
            meta["fidelity_calls"] = 1
            meta["fidelity_usage"] = fmeta.get("usage")
            fidelity.update(fid)
        if not fidelity["passed"]:
            problems.append("source_fidelity_failed")
    if problems:
        return Enrichment(used=False, reason="storyteller_rejected: " + "; ".join(problems), record_id=rec.record_id, fidelity=fidelity), meta
    return Enrichment(
        used=True, type=rec.epistemic_type, title=title or (rec.figure_name or ""), text=text,
        figure_id=rec.figure_id, myth_id=myth["myth_id"], record_id=rec.record_id,
        source_refs=list(myth.get("sources", [])),
        disclaimer_tr="Hikâye senin değil; ortak olan sadece ayrım. Kanıt değil, başka bir dil.",
        fidelity=fidelity,
    ), meta
