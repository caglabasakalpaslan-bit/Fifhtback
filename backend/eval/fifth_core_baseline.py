#!/usr/bin/env python3
"""Fifth Core baseline runner — records, does not tune.

Runs each story through the existing `fifth_core()` + `_fifth_normalize()` exactly as
`/api/fifth/start` and `/api/fifth/answer` do (minus the Mongo write). When the core asks
its single question, the first option is answered and the second turn is recorded; the
run asserts the contract (answer turn is ALWAYS a Reveal).

This file is EVALUATION ONLY: it imports `server` read-only and writes nothing to the app.

Run (from /app/backend):
    python eval/fifth_core_baseline.py                  # default 10-story file
    python eval/fifth_core_baseline.py --stories path.json
"""
from __future__ import annotations

import os
import sys
import json
import time
import uuid
import types
import asyncio
import argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# `server` needs a Mongo URL at import time (the client is lazy, nothing connects) and
# imports the `emergentintegrations` package for the older endpoints. Fifth Core does not
# use that package; when it is absent in the eval environment, register a stub so the
# module can be imported. Production is untouched by this.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "fifthback_eval")
try:
    import emergentintegrations.llm.chat  # noqa: F401
except ImportError:
    stub = types.ModuleType("emergentintegrations.llm.chat")
    stub.LlmChat = object
    stub.UserMessage = object
    sys.modules["emergentintegrations"] = types.ModuleType("emergentintegrations")
    sys.modules["emergentintegrations.llm"] = types.ModuleType("emergentintegrations.llm")
    sys.modules["emergentintegrations.llm.chat"] = stub

import server  # noqa: E402


def _turn_record(turn, data: dict, seconds: float) -> dict:
    return {
        "status": turn.status,
        "mode": turn.mode,
        "source": turn.source,
        "model": data.get("model"),
        "usage": data.get("usage"),
        "seconds": round(seconds, 2),
        "noticed": turn.noticed,
        "candidates": turn.candidates,
        "question": turn.question,
        "options": turn.options,
        "why_ask": turn.why_ask,
        "reveal": turn.reveal,
        "distinction": turn.distinction,
        "uncertain": turn.uncertain,
    }


async def run_story(item: dict) -> dict:
    sess = {
        "session_id": str(uuid.uuid4()),
        "nickname": "baseline",
        "avatar": "🦊",
        "door": "tell",
        "story": item["story"].strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "question",
    }
    t0 = time.perf_counter()
    data = await server.fifth_core(sess)
    turn = server._fifth_normalize(sess, data)
    rec = {"id": item["id"], "lens": item.get("lens"), "story": sess["story"],
           "turn1": _turn_record(turn, data, time.perf_counter() - t0), "turn2": None}

    if turn.status == "question":
        sess.update({"question": turn.question, "options": turn.options,
                     "answer": (turn.options[0] if turn.options else "Emin değilim")})
        t1 = time.perf_counter()
        data2 = await server.fifth_core(sess)
        turn2 = server._fifth_normalize(sess, data2)
        rec["turn2"] = _turn_record(turn2, data2, time.perf_counter() - t1)
        rec["turn2"]["answered_with"] = sess["answer"]
        rec["contract_ok"] = turn2.status == "done" and turn2.mode == "REVEAL"
    else:
        rec["contract_ok"] = turn.status == "done"
    return rec


def summarize(records: list) -> dict:
    t1 = [r["turn1"] for r in records]
    t2 = [r["turn2"] for r in records if r["turn2"]]
    all_turns = t1 + t2
    models = sorted({t["model"] for t in all_turns if t.get("model")})
    in_tok = sum((t.get("usage") or {}).get("input_tokens", 0) for t in all_turns)
    out_tok = sum((t.get("usage") or {}).get("output_tokens", 0) for t in all_turns)
    return {
        "stories": len(records),
        "turn1_question": sum(t["mode"] == "QUESTION" for t in t1),
        "turn1_reveal": sum(t["mode"] == "REVEAL" for t in t1),
        "turns_total": len(all_turns),
        "turns_from_llm": sum(t["source"] == "api" for t in all_turns),
        "turns_from_fallback": sum(t["source"] == "fallback" for t in all_turns),
        "contract_ok": sum(bool(r["contract_ok"]) for r in records),
        "models_seen": models,
        "avg_seconds_per_turn": round(sum(t["seconds"] for t in all_turns) / max(len(all_turns), 1), 2),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
    }


def write_markdown(path: str, meta: dict, summary: dict, records: list) -> None:
    lines = [f"# Fifth Core baseline — {meta['run_at']}", "",
             f"Model: `{server.FIFTH_MODEL}` · endpoint: `{server.ANTHROPIC_MESSAGES_URL}` · stories file: `{meta['stories_file']}`", "",
             "## Summary", ""]
    for k, v in summary.items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## Per story", ""]
    for r in records:
        t1, t2 = r["turn1"], r["turn2"]
        lines += [f"### {r['id']} ({r['lens']}) — turn1 {t1['mode']} · source {t1['source']} · {t1['seconds']}s",
                  "", f"> {r['story']}", ""]
        lines.append(f"- noticed: {t1['noticed']}")
        lines.append(f"- candidates: {t1['candidates']}")
        if t1["mode"] == "QUESTION":
            lines.append(f"- question: {t1['question']}")
            lines.append(f"- options: {t1['options']}")
            lines.append(f"- why_ask: {t1['why_ask']}")
        else:
            lines.append(f"- reveal: {t1['reveal']}")
            lines.append(f"- distinction: {t1['distinction']}")
            lines.append(f"- uncertain: {t1['uncertain']}")
        if t2:
            lines += ["", f"**turn2** (answered: “{t2['answered_with']}”) — {t2['mode']} · source {t2['source']} · {t2['seconds']}s",
                      f"- reveal: {t2['reveal']}", f"- distinction: {t2['distinction']}", f"- uncertain: {t2['uncertain']}"]
        lines.append(f"- contract_ok: {r['contract_ok']}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stories", default=os.path.join(HERE, "fifth_baseline_stories.json"))
    ap.add_argument("--out-dir", default=os.path.join(HERE, "results"))
    args = ap.parse_args()

    with open(args.stories, encoding="utf-8") as f:
        stories = json.load(f)["stories"]
    os.makedirs(args.out_dir, exist_ok=True)
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    meta = {"run_at": run_at, "stories_file": os.path.relpath(args.stories, os.path.dirname(HERE)),
            "model_requested": server.FIFTH_MODEL, "endpoint": server.ANTHROPIC_MESSAGES_URL}

    records = []
    for item in stories:
        rec = await run_story(item)
        records.append(rec)
        t1 = rec["turn1"]
        line = f"{rec['id']}: turn1={t1['mode']} src={t1['source']} model={t1['model']} {t1['seconds']}s"
        if rec["turn2"]:
            line += f" | turn2={rec['turn2']['mode']} src={rec['turn2']['source']} {rec['turn2']['seconds']}s"
        print(line + f" | contract_ok={rec['contract_ok']}", flush=True)

    summary = summarize(records)
    base = os.path.join(args.out_dir, f"fifth_core_baseline_{run_at}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "summary": summary, "records": records}, f, ensure_ascii=False, indent=2)
    write_markdown(base + ".md", meta, summary, records)
    print("\nSUMMARY", json.dumps(summary, ensure_ascii=False))
    print("wrote", base + ".json", "and .md")
    return 0 if summary["turns_from_fallback"] == 0 and summary["contract_ok"] == len(records) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
