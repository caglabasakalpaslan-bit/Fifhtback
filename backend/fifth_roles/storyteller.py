"""STORYTELLER — owns expression. Runs only when the Skeptic passed exactly one candidate.
Gives the same insight a second, vivid language. The core is immutable; the output is a separate
optional layer with provenance copied from the record (never model-authored)."""
import json
import re
from typing import Callable, Tuple

from .contracts import CoreReveal, LibrarianCandidate, PatternRecord, Enrichment
from .skeptic import banned_register

MAX_WORDS = 90
STORYTELLER_PROMPT = """Sen "The Fifth" içindeki HİKÂYE ANLATICISI'sın. Çekirdek bir Açıklama verdi; o DOKUNULMAZ, sen ona bir şey ekleyemez ya da ondan bir şey çıkaramazsın. Şüpheci tek bir kaydı onayladı. İşin: aynı ayrımı, o kaydın mitinin diliyle bir kez daha söylemek — ve hemen kişinin kendi durumuna geri dönmek.

KURALLAR:
- En fazla 90 kelime, 2–4 cümle. Günlük Türkçe; terapi/koçluk dili yok.
- Miti kısaca, canlı anlat; sonra köprüyü kur: "ortak olan şu ayrım".
- ASLA "sen X gibisin" deme; kişiyi figürle özdeşleştirme; figürü kişinin hayatı gibi ele alma.
- Mit KANIT değildir; "demek ki", "bu gösteriyor ki" yasak. Metaforu bilime çevirme.
- Kişi hakkında çekirdekte olmayan hiçbir iddia yok; niyet/güdü atfetme; tavsiye yok.
- Yalnızca sana verilen mit özetine dayan; kaynak, olay, isim uydurma.

YALNIZCA şu JSON'u ver:
{"title": "≤6 kelime; figür adı geçebilir", "text": "≤90 kelime", "myth_id": "kullandığın mitin id'si (verilenlerden biri)"}"""


def _text(body): return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
def _json(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL); return json.loads(m.group(0) if m else raw)
def _wc(s): return len(re.findall(r"\S+", s or ""))


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
    meta = {"calls": 1, "usage": body.get("usage"), "model": body.get("model")}
    if problems:
        return Enrichment(used=False, reason="storyteller_rejected: " + "; ".join(problems), record_id=rec.record_id), meta
    return Enrichment(
        used=True, type=rec.epistemic_type, title=title or (rec.figure_name or ""), text=text,
        figure_id=rec.figure_id, myth_id=myth["myth_id"], record_id=rec.record_id,
        source_refs=list(myth.get("sources", [])),
        disclaimer_tr="Hikâye senin değil; ortak olan sadece ayrım. Kanıt değil, başka bir dil.",
    ), meta
