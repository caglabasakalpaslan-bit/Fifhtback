#!/usr/bin/env python3
"""Distinction-card run: 10 baseline cases (+ optional edge cases) through the REAL core with the
tournament, then LIBRARIAN → SKEPTIC → STORYTELLER after completed REVEALs. Reports candidates,
winner, ranking reasons, route, question, Fifth Card, enrichment, latency and tokens."""
from __future__ import annotations
import os, sys, json, time, uuid, types, asyncio, argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017"); os.environ.setdefault("DB_NAME", "fifthback_eval")
try:
    import emergentintegrations.llm.chat  # noqa
except ImportError:
    stub = types.ModuleType("emergentintegrations.llm.chat"); stub.LlmChat = object; stub.UserMessage = object
    sys.modules["emergentintegrations"] = types.ModuleType("e"); sys.modules["emergentintegrations.llm"] = types.ModuleType("e.l"); sys.modules["emergentintegrations.llm.chat"] = stub
import server  # noqa: E402
from fifth_roles import run_after_reveal  # noqa: E402

FOUNDER_ROUTES = {"b01": "QUESTION", "b02": "QUESTION", "b03": "QUESTION", "b04": "REVEAL", "b05": "QUESTION",
                  "b06": "REVEAL", "b07": "QUESTION", "b08": "QUESTION", "b09": "QUESTION", "b10": "CLOSE"}


def counting():
    st = {"calls": 0, "in": 0, "out": 0}
    def call(system, material):
        body = server._fifth_http_call(material, system=system, max_tokens=1500)
        st["calls"] += 1; u = body.get("usage") or {}; st["in"] += u.get("input_tokens", 0); st["out"] += u.get("output_tokens", 0)
        return body
    return call, st


async def core_with_retry(sess, rec, attempts=4):
    """Retries: bad output once more, transient API unavailability with backoff. The UI would show
    'Tekrar dene' in both cases; here the retries are counted so the report stays honest."""
    delay = 5
    for i in range(attempts):
        try:
            return await server.fifth_core(sess)
        except (server.FifthBadOutput, server.FifthUnavailable) as e:
            rec.setdefault("core_retries", []).append(str(e)); rec["core_calls"] += 1
            if i == attempts - 1:
                raise
            await asyncio.sleep(delay); delay *= 2


def counting_with_retry():
    st = {"calls": 0, "in": 0, "out": 0, "retries": []}
    def call(system, material):
        delay = 5
        for i in range(4):
            try:
                body = server._fifth_http_call(material, system=system, max_tokens=1500)
                st["calls"] += 1; u = body.get("usage") or {}; st["in"] += u.get("input_tokens", 0); st["out"] += u.get("output_tokens", 0)
                return body
            except server.FifthUnavailable as e:
                st["calls"] += 1; st["retries"].append(str(e))
                if i == 3:
                    raise
                time.sleep(delay); delay *= 2
    return call, st


def tournament_view(t):
    if not t: return None
    return {"winner_id": t.winner_id, "ranking_reasons": t.ranking_reasons, "proposed_mode": t.proposed_mode, "routed_mode": t.routed_mode,
            "route_reason": t.route_reason, "question_from": t.question_from,
            "candidates": [{"id": c.id, "distinction": c.distinction, "evidence": c.evidence_from_story, "missing_fact": c.missing_discriminating_fact,
                            "fact_already_in_story": c.fact_already_in_story, "possible_question": c.possible_question, "options": c.possible_options,
                            "why": c.why_it_may_change_judgment, "scores": c.scores.model_dump(), "rank": c.rank} for c in t.candidates]}


async def run_story(item):
    now = datetime.now(timezone.utc).isoformat()
    sess = {"session_id": str(uuid.uuid4()), "nickname": "baseline", "avatar": "🦊", "door": "tell", "story": item["story"].strip(), "kind": "anlat", "created_at": now, "updated_at": now, "status": "question"}
    rec = {"id": item["id"], "kind": item.get("kind"), "expected_note": item.get("expected_note"), "founder_route": FOUNDER_ROUTES.get(item["id"]), "story": sess["story"],
           "core_calls": 0, "core_tokens": {"in": 0, "out": 0}}
    t0 = time.perf_counter()
    data = await core_with_retry(sess, rec)
    turn = server._fifth_normalize(sess, data)
    rec["core_calls"] += 1; rec["core_tokens"]["in"] += data["usage"]["input_tokens"]; rec["core_tokens"]["out"] += data["usage"]["output_tokens"]
    rec["turn1"] = {"mode": turn.mode, "question": turn.question, "options": turn.options, "why_ask": turn.why_ask, "close": turn.close, "tournament": tournament_view(turn.tournament)}
    rec["core_route_turn1"] = turn.mode; rec["route_match"] = (turn.mode == rec["founder_route"]) if rec["founder_route"] else None
    if turn.status == "question":
        sess.update({"question": turn.question, "options": turn.options, "answer": turn.options[0] if turn.options else "Emin değilim"})
        data = await core_with_retry(sess, rec); turn = server._fifth_normalize(sess, data)
        rec["core_calls"] += 1; rec["core_tokens"]["in"] += data["usage"]["input_tokens"]; rec["core_tokens"]["out"] += data["usage"]["output_tokens"]
        rec["answered_with"] = sess["answer"]; rec["turn2_tournament"] = tournament_view(turn.tournament)
    rec["core_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["final_mode"] = turn.mode
    rec["core"] = {"distinction": turn.distinction, "shape": turn.shape, "reveal": turn.reveal, "close": turn.close, "uncertain": turn.uncertain, "noticed": turn.noticed}
    rec["card"] = turn.card.model_dump() if turn.card else None
    call, st = counting_with_retry()
    res = await asyncio.to_thread(run_after_reveal, turn, sess, call, None, server.FifthUnavailable, server.FifthBadOutput)
    rec["roles_retries"] = st["retries"]
    rec["route"] = res.core_reveal.route
    rec["librarian"] = res.librarian.model_dump() if res.librarian else None
    rec["skeptic"] = res.skeptic.model_dump() if res.skeptic else None
    rec["enrichment"] = res.enrichment.model_dump()
    rec["core_identical"] = res.core_identical
    rec["roles_calls"] = st["calls"]; rec["roles_tokens"] = {"in": st["in"], "out": st["out"]}; rec["roles_latency_ms"] = res.total_latency_ms
    rec["total_calls"] = rec["core_calls"] + st["calls"]
    return rec


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--edge", action="store_true"); a = ap.parse_args()
    stories = json.load(open(os.path.join(HERE, "fifth_baseline_stories.json"), encoding="utf-8"))["stories"]
    if a.edge:
        stories += json.load(open(os.path.join(HERE, "fifth_edge_cases.json"), encoding="utf-8"))["stories"]
    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"), "model": server.FIFTH_MODEL, "records": []}
    for it in stories:
        try:
            r = await run_story(it)
        except Exception as ex:   # keep the run going; report the failure per story
            out["records"].append({"id": it["id"], "founder_route": FOUNDER_ROUTES.get(it["id"]), "error": f"{ex.__class__.__name__}: {ex}", "route_match": None, "enrichment": {"used": False}, "core_identical": None})
            print(f"{it['id']}: ERROR {ex.__class__.__name__}: {ex}", flush=True); continue
        out["records"].append(r); e = r["enrichment"]
        print(f"{r['id']}: founder={r['founder_route']} core_turn1={r['core_route_turn1']} match={r['route_match']} final={r['final_mode']} "
              f"cands={len((r['turn1']['tournament'] or {}).get('candidates', []))} proposed={(r['turn1']['tournament'] or {}).get('proposed_mode')} "
              f"lib={len((r['librarian'] or {}).get('candidates', []))} skeptic={(r['skeptic'] or {}).get('passed')} used={e['used']} identical={r['core_identical']} "
              f"calls={r['total_calls']} latency={r['core_latency_ms']}+{r['roles_latency_ms']}ms", flush=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    path = os.path.join(HERE, "results", f"fifth_card_baseline_{out['run_at']}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    base = [r for r in out["records"] if r["founder_route"]]
    print(f"\nSUMMARY route_matches={sum(1 for r in base if r['route_match'])}/{len(base)} enrichments_used={sum(1 for r in out['records'] if r['enrichment']['used'])}/{len(out['records'])} "
          f"core_identical={all(r['core_identical'] for r in out['records'])} wrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
