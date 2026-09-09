"""Orchestrator. CORE → (stop on QUESTION/CLOSE) → LIBRARIAN → SKEPTIC → STORYTELLER.
Counts calls, latency and tokens per role; verifies the core is byte-identical before and after."""
import time
from typing import Callable

from .contracts import PipelineResult, Enrichment, RoleTrace, LibrarianOutput, SkepticVerdict
from .core import freeze, core_hash
from .librarian import librarian, olympus_records
from .skeptic import skeptic
from .storyteller import storyteller


def _trace(meta: dict, t0: float, ran=True, **detail) -> RoleTrace:
    u = (meta or {}).get("usage") or {}
    return RoleTrace(ran=ran, calls=(meta or {}).get("calls", 0), latency_ms=int((time.perf_counter() - t0) * 1000),
                     input_tokens=u.get("input_tokens", 0), output_tokens=u.get("output_tokens", 0), model=(meta or {}).get("model"), detail=detail)


def run_after_reveal(turn, sess, call_model: Callable[[str, str], dict], records=None, unavailable_exc=Exception, bad_output_exc=Exception) -> PipelineResult:
    core = freeze(turn, sess)
    before = core.core_hash
    traces = {}
    t_all = time.perf_counter()

    def finish(enrichment, lib=None, sk=None):
        after = core_hash(turn.distinction, turn.reveal, turn.uncertain)
        res = PipelineResult(core_reveal=core, enrichment=enrichment, librarian=lib, skeptic=sk, trace=traces,
                             core_hash_before=before, core_hash_after=after, core_identical=(before == after and core.core_hash == after),
                             total_calls=sum(t.calls for t in traces.values()), total_latency_ms=int((time.perf_counter() - t_all) * 1000),
                             total_input_tokens=sum(t.input_tokens for t in traces.values()), total_output_tokens=sum(t.output_tokens for t in traces.values()))
        assert res.core_identical, "a later role altered the core"
        return res

    if core.route in ("QUESTION", "CLOSE"):
        return finish(Enrichment(used=False, reason=f"route_{core.route.lower()}_stops_pipeline"))
    if not core.distinction or not core.reveal or len(core.noticed) < 2:
        return finish(Enrichment(used=False, reason="core_too_thin_for_enrichment"))

    recs = records if records is not None else olympus_records()
    by_id = {r.record_id: r for r in recs}

    # LIBRARIAN
    t0 = time.perf_counter()
    try:
        lib, meta = librarian(core, call_model, recs)
    except unavailable_exc:
        traces["librarian"] = _trace({}, t0, error="model_unavailable")
        return finish(Enrichment(used=False, reason="model_unavailable"))
    except (bad_output_exc, ValueError, KeyError, TypeError) as e:
        traces["librarian"] = _trace({}, t0, error=f"bad_output:{e.__class__.__name__}")
        return finish(Enrichment(used=False, reason="librarian_bad_output"))
    traces["librarian"] = _trace(meta, t0, candidates=len(lib.candidates), recall_considered=lib.recall_considered)
    if not lib.candidates:
        return finish(Enrichment(used=False, reason="librarian_zero_candidates"), lib)

    # SKEPTIC
    t0 = time.perf_counter()
    try:
        sk, meta = skeptic(core, lib.candidates, by_id, call_model)
    except unavailable_exc:
        traces["skeptic"] = _trace({}, t0, error="model_unavailable")
        return finish(Enrichment(used=False, reason="model_unavailable"), lib)
    except (bad_output_exc, ValueError, KeyError, TypeError) as e:
        traces["skeptic"] = _trace({}, t0, error=f"bad_output:{e.__class__.__name__}")
        return finish(Enrichment(used=False, reason="skeptic_bad_output"), lib)
    traces["skeptic"] = _trace(meta, t0, passed=sk.passed, score=sk.score)
    if not sk.passed:
        return finish(Enrichment(used=False, reason="skeptic_none"), lib, sk)

    # STORYTELLER
    t0 = time.perf_counter()
    cand = next(c for c in lib.candidates if c.record_id == sk.passed)
    try:
        enr, meta = storyteller(core, cand, by_id[sk.passed], call_model)
    except unavailable_exc:
        traces["storyteller"] = _trace({}, t0, error="model_unavailable")
        return finish(Enrichment(used=False, reason="model_unavailable"), lib, sk)
    except (bad_output_exc, ValueError, KeyError, TypeError) as e:
        traces["storyteller"] = _trace({}, t0, error=f"bad_output:{e.__class__.__name__}")
        return finish(Enrichment(used=False, reason="storyteller_bad_output"), lib, sk)
    traces["storyteller"] = _trace(meta, t0, used=enr.used)
    return finish(enr, lib, sk)
