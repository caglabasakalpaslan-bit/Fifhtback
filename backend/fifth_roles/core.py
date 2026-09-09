"""CORE view. The Fifth Core call lives in server.py and is reused, not duplicated.
This module freezes the core output into CoreReveal. The route is the core's own `mode`
(CLOSE is a real core output since routing v0.1 was integrated into FIFTH_CORE_PROMPT)."""
import hashlib
from .contracts import CoreReveal


def core_hash(distinction, reveal, uncertain) -> str:
    return hashlib.sha256(f"{distinction or ''}\n{reveal or ''}\n{uncertain or ''}".encode("utf-8")).hexdigest()


def route_of(turn, sess=None) -> str:
    if turn.status != "done":
        return "QUESTION"
    return "CLOSE" if getattr(turn, "mode", None) == "CLOSE" else "REVEAL"


def freeze(turn, sess) -> CoreReveal:
    return CoreReveal(
        session_id=turn.session_id, route=route_of(turn, sess),
        distinction=turn.distinction, reveal=turn.reveal, uncertain=turn.uncertain, shape=getattr(turn, "shape", None),
        noticed=list(turn.noticed or []), candidates=list(turn.candidates or []),
        answered=bool((sess or {}).get("answer")),
        core_hash=core_hash(turn.distinction, turn.reveal, turn.uncertain),
    )
