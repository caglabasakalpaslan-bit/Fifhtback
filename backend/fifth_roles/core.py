"""CORE view. The Fifth Core call itself lives in server.py and is reused, not duplicated.
This module only (a) decides the route the later roles see, (b) freezes the core into CoreReveal.

The core prompt has no CLOSE output; routing v0.1 Gate 1 says CLOSE when the story carries no
judgment-changing tension. Until CLOSE is a core output, that gate is applied here, on the story
text only, so that QUESTION and CLOSE stop the pipeline before any other role runs."""
import hashlib
import re
from .contracts import CoreReveal

TENSION_MARKERS = [
    r"\bm[iıuü]\b.*\bm[iıuü]\b",                   # "… mi … mı" self-question
    r"bilmiyorum|ayıramıyorum|emin değilim",
    r"\bhem\b.*\bhem\b", r"\bama\b", r"\boysa\b",
    r"üçüncü kez|her hafta|her ay|yıl oldu|yıllardır|tekrar|yine",
    r"susuyorum|kısa cevap|teklif etmeyeceğim|çekil",
    r"söylemedim|söyleyemiyorum|anlatmadım",
    r"kimse .*(madı|medi)|niye danışmadın|beklemiyordum",
]


def core_hash(distinction, reveal, uncertain) -> str:
    return hashlib.sha256(f"{distinction or ''}\n{reveal or ''}\n{uncertain or ''}".encode("utf-8")).hexdigest()


def has_tension(story: str) -> bool:
    low = (story or "").lower()
    return any(re.search(p, low) for p in TENSION_MARKERS)


def route_of(turn, sess) -> str:
    if turn.status != "done":
        return "QUESTION"
    if not has_tension(sess.get("story") or sess.get("familiar") or ""):
        return "CLOSE"
    return "REVEAL"


def freeze(turn, sess) -> CoreReveal:
    return CoreReveal(
        session_id=turn.session_id, route=route_of(turn, sess),
        distinction=turn.distinction, reveal=turn.reveal, uncertain=turn.uncertain,
        noticed=list(turn.noticed or []), candidates=list(turn.candidates or []),
        answered=bool(sess.get("answer")),
        core_hash=core_hash(turn.distinction, turn.reveal, turn.uncertain),
    )
