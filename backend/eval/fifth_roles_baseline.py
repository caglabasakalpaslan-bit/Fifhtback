#!/usr/bin/env python3
"""Four-role baseline: the 10 stories through the REAL core, then LIBRARIAN → SKEPTIC → STORYTELLER.
Records route, core distinction, candidates, verdicts, storyteller text, source trace, core hash identity,
Claude calls, latency and tokens. Evaluation only; imports server read-only (stubs the private LLM package)."""
from __future__ import annotations
import os, sys, json, time, uuid, types, asyncio
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


def call_counting():
    st = {"calls": 0, "in": 0, "out": 0}
    def call(system, material):
        body = server._fifth_http_call(material, system=system, max_tokens=1500)
        st["calls"] += 1; u = body.get("usage") or {}; st["in"] += u.get("input_tokens", 0); st["out"] += u.get("output_tokens", 0)
        return body
    return call, st


async def run_story(item):
    sess = {"session_id": str(uuid.uuid4()), "nickname": "baseline", "avatar": "🦊", "door": "tell", "story": item["story"].strip(), "kind": "anlat",
            "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(), "status": "question"}
    rec = {"id": item["id"], "story": sess["story"], "core_calls": 0, "core_tokens": {"in": 0, "out": 0}, "core_latency_ms": 0}
    t0 = time.perf_counter(); data = await server.fifth_core(sess); turn = server._fifth_normalize(sess, data)
    rec["core_calls"] += 1; rec["core_tokens"]["in"] += data["usage"]["input_tokens"]; rec["core_tokens"]["out"] += data["usage"]["output_tokens"]
    rec["turn1"] = {"mode": turn.mode, "question": turn.question, "options": turn.options, "why_ask": turn.why_ask, "close": turn.close}
    rec["founder_route"] = FOUNDER_ROUTES.get(item["id"]); rec["core_route_turn1"] = turn.mode; rec["route_match"] = (turn.mode == rec["founder_route"])
    if turn.status == "question":
        sess.update({"question": turn.question, "options": turn.options, "answer": turn.options[0] if turn.options else "Emin değilim"})
        data = await server.fifth_core(sess); turn = server._fifth_normalize(sess, data)
        rec["core_calls"] += 1; rec["core_tokens"]["in"] += data["usage"]["input_tokens"]; rec["core_tokens"]["out"] += data["usage"]["output_tokens"]
        rec["answered_with"] = sess["answer"]
    rec["core_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["core"] = {"mode": turn.mode, "distinction": turn.distinction, "shape": turn.shape, "reveal": turn.reveal, "close": turn.close, "uncertain": turn.uncertain, "noticed": turn.noticed, "source": turn.source}
    call, st = call_counting()
    res = await asyncio.to_thread(run_after_reveal, turn, sess, call, None, server.FifthUnavailable, server.FifthBadOutput)
    rec["route"] = res.core_reveal.route
    rec["librarian"] = res.librarian.model_dump() if res.librarian else None
    rec["skeptic"] = res.skeptic.model_dump() if res.skeptic else None
    rec["enrichment"] = res.enrichment.model_dump()
    rec["core_identical"] = res.core_identical
    rec["roles_calls"] = st["calls"]; rec["roles_tokens"] = {"in": st["in"], "out": st["out"]}; rec["roles_latency_ms"] = res.total_latency_ms
    rec["total_calls"] = rec["core_calls"] + st["calls"]
    rec["trace"] = {k: v.model_dump() for k, v in res.trace.items()}
    return rec


async def main():
    stories = json.load(open(os.path.join(HERE, "fifth_baseline_stories.json"), encoding="utf-8"))["stories"]
    out = {"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"), "model": server.FIFTH_MODEL, "records": []}
    for it in stories:
        r = await run_story(it); out["records"].append(r)
        e = r["enrichment"]
        fid = (e.get("fidelity") or {}).get("passed")
        print(f"{r['id']}: founder={r['founder_route']} core_turn1={r['core_route_turn1']} match={r['route_match']} final={r['route']} core_calls={r['core_calls']} roles_calls={r['roles_calls']} lib={len((r['librarian'] or {}).get('candidates', []))} fidelity={fid} "
              f"skeptic={(r['skeptic'] or {}).get('passed')} used={e['used']} reason={e.get('reason')} identical={r['core_identical']} "
              f"latency={r['core_latency_ms']}+{r['roles_latency_ms']}ms", flush=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    path = os.path.join(HERE, "results", f"fifth_roles_baseline_{out['run_at']}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    used = sum(1 for r in out["records"] if r["enrichment"]["used"])
    matches = sum(1 for r in out["records"] if r["route_match"])
    print(f"\nSUMMARY route_matches={matches}/10 enrichments_used={used}/10 core_identical={all(r['core_identical'] for r in out['records'])} wrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
