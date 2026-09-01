#!/usr/bin/env python3
"""Mechanism-naming evaluation for the existing Pattern Room LLM path.

Question measured
-----------------
"In how many of the 24 demo signals does the LLM correctly name the work-system
mechanism?"

Design constraints (all enforced below, not merely intended):
  * Uses the EXISTING ten-mechanism vocabulary from `PATTERN_ROOM_PROMPT`.
    No new ontology is defined here.
  * The model sees ONE raw signal per call. No cluster id, no cluster name, no
    ground truth, no sibling signals — isolation prevents the model from
    inferring cluster structure or sizes from co-occurrence.
  * The model may ABSTAIN. Being unsure is a recorded outcome, not a failure.
  * Multi-mechanism answers are supported; a signal may legitimately belong to
    more than one mechanism.
  * Mechanisms predicted outside ground truth are counted separately as false
    positives.

This file is EVALUATION ONLY. It imports `server` read-only and writes no
application state. It is not imported by the application.

Run (from /app/backend):
    python eval/mechanism_naming_eval.py
    python eval/mechanism_naming_eval.py --dry-run   # harness self-test, no LLM
"""
from __future__ import annotations

import os
import re
import sys
import json
import uuid
import asyncio
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # read-only: production signals + curated ground truth

# ---------------------------------------------------------------------------
# The existing vocabulary. These ten ids and labels are the ones enumerated in
# server.PATTERN_ROOM_PROMPT — reproduced here as an id<->label table only so
# that free-text model output can be normalised. No mechanism is added.
# ---------------------------------------------------------------------------
MECHANISMS: Dict[str, str] = {
    "karar-gecikmesi": "karar gecikmesi",
    "belirsiz-sahiplik": "belirsiz sahiplik",
    "devir-surtusmesi": "devir sürtüşmesi",
    "yeniden-is": "yeniden iş",
    "yetkinlik-uyumsuzlugu": "yetkinlik uyumsuzluğu",
    "kapasite-kisiti": "kapasite kısıtı",
    "bilgi-boslugu": "bilgi boşluğu",
    "surec-tekrari": "süreç tekrarı",
    "onceliklendirme-catismasi": "önceliklendirme çatışması",
    "arac-sistem-surtusmesi": "araç/sistem sürtüşmesi",
}
ABSTAIN = "UNKNOWN"


def _norm(text: str) -> str:
    return re.sub(r"[\s\-_/()]+", " ", (text or "").strip().lower())


_LABEL_LOOKUP = {_norm(v): k for k, v in MECHANISMS.items()}
_LABEL_LOOKUP.update({_norm(k): k for k in MECHANISMS})
# tolerate the English glosses and a couple of near-spellings the model may emit
_LABEL_LOOKUP.update({
    "decision latency": "karar-gecikmesi",
    "unclear ownership": "belirsiz-sahiplik",
    "handoff friction": "devir-surtusmesi",
    "rework": "yeniden-is",
    "yeniden is rework": "yeniden-is",
    "skill mismatch": "yetkinlik-uyumsuzlugu",
    "capacity constraint": "kapasite-kisiti",
    "information gap": "bilgi-boslugu",
    "process duplication": "surec-tekrari",
    "prioritisation conflict": "onceliklendirme-catismasi",
    "prioritization conflict": "onceliklendirme-catismasi",
    "tool system friction": "arac-sistem-surtusmesi",
})


def to_mechanism_id(raw: str) -> str | None:
    """Map free-text model output onto an existing mechanism id, or None."""
    n = _norm(raw)
    if not n:
        return None
    if n in {"unknown", "abstain", "bilinmiyor", "emin degilim", "emin değilim", "none"}:
        return ABSTAIN
    if n in _LABEL_LOOKUP:
        return _LABEL_LOOKUP[n]
    for key, mid in _LABEL_LOOKUP.items():  # substring fallback
        if key and (key in n or n in key):
            return mid
    return None


# ---------------------------------------------------------------------------
# Ground truth, derived from production (not hand-copied): each signal inherits
# the mechanism set of the curated cluster that contains it.
# ---------------------------------------------------------------------------
def build_ground_truth() -> List[dict]:
    signals: List[str] = list(server.PATTERN_ROOM_SIGNALS)
    curated = server._curated_pattern_room()
    rows: Dict[int, dict] = {}
    for cluster in curated.clusters:
        ids: Set[str] = set()
        for part in re.split(r"[+,]", cluster.mechanism):
            mid = to_mechanism_id(part)
            if mid and mid != ABSTAIN:
                ids.add(mid)
        if not ids:
            raise SystemExit(f"Küme '{cluster.id}' mekanizması çözümlenemedi: {cluster.mechanism!r}")
        for idx in cluster.signal_indices:
            rows[idx] = {
                "index": idx,
                "signal": signals[idx],
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "ground_truth": sorted(ids),
            }
    missing = [i for i in range(len(signals)) if i not in rows]
    if missing:
        raise SystemExit(f"Kümelenmemiş sinyal indeksleri: {missing}")
    return [rows[i] for i in sorted(rows)]


# ---------------------------------------------------------------------------
# Prompt: vocabulary + one raw signal. Nothing else.
# ---------------------------------------------------------------------------
EVAL_SYSTEM_PROMPT = """Sen bir iş-sistemi analiz motorusun. Sana TEK bir anonim iş-sistemi sinyali verilecek.

Görevin: bu sinyalin altında yatan iş-sistemi MEKANİZMASINI adlandırmak.

Bu bir çalışan değerlendirmesi DEĞİLDİR. Kişilik, motivasyon, yetkinlik veya duygu teşhisi YAPMA. Yalnızca iş sisteminin sürtünmesini adlandır.

Yalnızca şu mekanizma sözlüğünü kullan:
- karar-gecikmesi: iş, verilmemiş bir kararı bekliyor.
- belirsiz-sahiplik: işi tek bir taraf sahiplense ilerleyecek; sahibi belli değil.
- devir-surtusmesi: kayıp, iki taraf arasındaki devir anında yaşanıyor.
- yeniden-is: bitmiş iş yeniden yapılıyor.
- yetkinlik-uyumsuzlugu: iş, yapısal olarak o yetkinliğe sahip olmayan tarafa yönlendirilmiş.
- kapasite-kisiti: daha fazla el işi gerçekten ilerletirdi.
- bilgi-boslugu: gereken bilgi bir yerde var ama bulunamıyor.
- surec-tekrari: aynı çıktı paralelde iki kez üretiliyor.
- onceliklendirme-catismasi: herkes meşgulken belirli işler el değmeden bekliyor.
- arac-sistem-surtusmesi: sürtünme, bilgiyi sistemler arasında taşırken sürüyor.

Kurallar:
- Sinyal birden fazla mekanizmaya ait olabilir; o zaman birden fazla yaz.
- Sözlükte olmayan bir mekanizma UYDURMA.
- Emin değilsen "UNKNOWN" ver. Emin olmamak geçerli bir cevaptır; zorlama tahmin verme.
- Yalnızca sinyalin metninin desteklediğini söyle.

KATI JSON ver, başka hiçbir şey ekleme:
{"mechanisms": ["mekanizma-id", ...], "abstain": true/false, "confidence": "Yüksek/Orta/Düşük", "reason": "tek cümle Türkçe gerekçe"}

abstain true ise "mechanisms" boş liste olmalı."""


async def ask_llm(signal: str, model: str, timeout: float) -> dict:
    """One isolated call through the same LlmChat path production uses."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"mecheval-{uuid.uuid4()}",
        system_message=EVAL_SYSTEM_PROMPT,
    ).with_model("anthropic", model)
    resp = await asyncio.wait_for(
        chat.send_message(UserMessage(text=f"Sinyal:\n\"\"\"\n{signal}\n\"\"\"")),
        timeout=timeout,
    )
    raw = resp if isinstance(resp, str) else str(resp)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(m.group(0) if m else raw)


def _stub(signal: str) -> dict:
    """--dry-run only: deterministic keyword stub so the harness can be tested
    without an LLM. Its answers are NOT a measurement of anything."""
    s = signal.lower()
    if "onay" in s or "karar" in s:
        return {"mechanisms": ["karar-gecikmesi"], "abstain": False, "confidence": "Orta", "reason": "stub"}
    if "sahib" in s or "devir" in s:
        return {"mechanisms": ["belirsiz-sahiplik", "devir-surtusmesi"], "abstain": False, "confidence": "Orta", "reason": "stub"}
    if "araç" in s or "arac" in s or "veri" in s:
        return {"mechanisms": ["arac-sistem-surtusmesi"], "abstain": False, "confidence": "Orta", "reason": "stub"}
    if "baştan" in s or "tekrar" in s or "geri gönder" in s:
        return {"mechanisms": ["yeniden-is"], "abstain": False, "confidence": "Orta", "reason": "stub"}
    return {"mechanisms": [], "abstain": True, "confidence": "Düşük", "reason": "stub abstain"}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score(gt: List[str], predicted: List[str], abstained: bool) -> str:
    """DOĞRU  : at least one hit and NO mechanism outside ground truth
       KISMEN : at least one hit but also >=1 mechanism outside ground truth
       YANLIŞ : no hit at all
       ABSTAIN: model declined"""
    if abstained or not predicted:
        return "ABSTAIN"
    gts, ps = set(gt), set(predicted)
    hits, extras = ps & gts, ps - gts
    if not hits:
        return "YANLIŞ"
    return "DOĞRU" if not extras else "KISMEN"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="harness self-test, no LLM calls")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--out", default="eval_mechanism_naming.json")
    args = ap.parse_args()

    rows = build_ground_truth()
    print(f"Değerlendirilecek sinyal sayısı: {len(rows)}  |  model: "
          f"{'STUB (dry-run)' if args.dry_run else args.model}\n", flush=True)

    if not args.dry_run and not os.environ.get("EMERGENT_LLM_KEY"):
        print("HATA: EMERGENT_LLM_KEY tanımlı değil. Gerçek ölçüm yapılamaz.", file=sys.stderr)
        return 2

    sem = asyncio.Semaphore(args.concurrency)

    async def one(row: dict) -> dict:
        async with sem:
            try:
                data = _stub(row["signal"]) if args.dry_run else await ask_llm(
                    row["signal"], args.model, args.timeout)
                err = ""
            except Exception as exc:
                data, err = {"mechanisms": [], "abstain": True, "confidence": "", "reason": ""}, str(exc)

            mapped, unknown = [], []
            for raw in (data.get("mechanisms") or []):
                mid = to_mechanism_id(str(raw))
                if mid in (None, ABSTAIN):
                    unknown.append(str(raw))
                else:
                    mapped.append(mid)
            mapped = sorted(set(mapped))
            abstained = bool(data.get("abstain")) or not mapped
            verdict = "HATA" if err else score(row["ground_truth"], mapped, abstained)
            return {
                **row,
                "llm_prediction": mapped or ([ABSTAIN] if abstained else []),
                "unmapped_output": unknown,
                "abstain": abstained,
                "confidence": data.get("confidence", ""),
                "reason": data.get("reason", ""),
                "false_positives": sorted(set(mapped) - set(row["ground_truth"])),
                "verdict": verdict,
                "error": err,
            }

    results = await asyncio.gather(*(one(r) for r in rows))
    results = sorted(results, key=lambda r: r["index"])

    # ---------------- report ----------------
    counts = {k: 0 for k in ("DOĞRU", "KISMEN", "YANLIŞ", "ABSTAIN", "HATA")}
    for r in results:
        counts[r["verdict"]] += 1
    fp_total = sum(len(r["false_positives"]) for r in results)
    fp_rows = sum(1 for r in results if r["false_positives"])

    W = 100
    print("=" * W)
    print("MEKANİZMA ADLANDIRMA DEĞERLENDİRMESİ — ÖZET")
    print("=" * W)
    print(f"Toplam sinyal        : {len(results)}")
    print(f"Doğru mekanizma      : {counts['DOĞRU']}")
    print(f"Kısmen doğru         : {counts['KISMEN']}")
    print(f"Yanlış mekanizma     : {counts['YANLIŞ']}")
    print(f"Abstain / bilinmiyor : {counts['ABSTAIN']}")
    if counts["HATA"]:
        print(f"Hata (çağrı başarısız): {counts['HATA']}")
    print(f"Yanlış pozitif (toplam adet) : {fp_total}   (etkilenen sinyal: {fp_rows})")
    scored = len(results) - counts["HATA"]
    if scored:
        print(f"Kesin isabet oranı   : {counts['DOĞRU']}/{scored} = {counts['DOĞRU']/scored:.0%}")
        print(f"En az bir isabet     : {(counts['DOĞRU']+counts['KISMEN'])}/{scored} = "
              f"{(counts['DOĞRU']+counts['KISMEN'])/scored:.0%}")

    print("\n" + "=" * W)
    print("KÜME BAZINDA SONUÇ")
    print("=" * W)
    print(f"{'Küme':<34}{'n':>3}{'Doğru':>7}{'Kısmi':>7}{'Yanlış':>8}{'Abstain':>9}{'YP':>5}")
    by_cluster: Dict[str, List[dict]] = {}
    for r in results:
        by_cluster.setdefault(f"{r['cluster_id']} {r['cluster_name']}", []).append(r)
    for name in sorted(by_cluster):
        rs = by_cluster[name]
        c = {k: sum(1 for x in rs if x["verdict"] == k) for k in counts}
        fp = sum(len(x["false_positives"]) for x in rs)
        print(f"{name[:33]:<34}{len(rs):>3}{c['DOĞRU']:>7}{c['KISMEN']:>7}"
              f"{c['YANLIŞ']:>8}{c['ABSTAIN']:>9}{fp:>5}")

    c1 = [r for r in results if r["cluster_id"] == "c1"]
    if c1:
        c1c = {k: sum(1 for x in c1 if x["verdict"] == k) for k in counts}
        print("\n" + "=" * W)
        print("c1 — KARAR AKIŞI / SAHİPLİK DARBOĞAZI (ayrıca istendi)")
        print("=" * W)
        print(f"c1 sinyal sayısı     : {len(c1)}  (havuzun {len(c1)/len(results):.0%}'ı)")
        print(f"Doğru / Kısmi / Yanlış / Abstain : "
              f"{c1c['DOĞRU']} / {c1c['KISMEN']} / {c1c['YANLIŞ']} / {c1c['ABSTAIN']}")
        print(f"c1 yanlış pozitif    : {sum(len(x['false_positives']) for x in c1)}")
        gt_only = {"karar-gecikmesi": 0, "belirsiz-sahiplik": 0, "her ikisi": 0}
        for r in c1:
            p = set(r["llm_prediction"])
            if {"karar-gecikmesi", "belirsiz-sahiplik"} <= p:
                gt_only["her ikisi"] += 1
            elif "karar-gecikmesi" in p:
                gt_only["karar-gecikmesi"] += 1
            elif "belirsiz-sahiplik" in p:
                gt_only["belirsiz-sahiplik"] += 1
        print(f"c1 içinde model dağılımı: yalnız karar-gecikmesi={gt_only['karar-gecikmesi']}, "
              f"yalnız belirsiz-sahiplik={gt_only['belirsiz-sahiplik']}, her ikisi={gt_only['her ikisi']}")
        print("Not: c1 iki mekanizmalı olduğu için tek mekanizma veren cevap da DOĞRU sayılır")
        print("     (tahmin ⊆ ground truth). Bu, RQ-2'deki c1/c3 örtüşmesi sorusuna girdi sağlar.")

    print("\n" + "=" * W)
    print("ÖRNEK BAZINDA SONUÇ")
    print("=" * W)
    for r in results:
        print(f"\n[{r['index']:>2}] {r['cluster_id']}  —  {r['verdict']}")
        print(f"  signal         : {r['signal']}")
        print(f"  ground_truth   : {', '.join(r['ground_truth'])}")
        print(f"  llm_prediction : {', '.join(r['llm_prediction']) or '—'}"
              f"{'   [güven: ' + r['confidence'] + ']' if r['confidence'] else ''}")
        if r["false_positives"]:
            print(f"  YANLIŞ POZİTİF : {', '.join(r['false_positives'])}")
        if r["unmapped_output"]:
            print(f"  sözlük dışı    : {', '.join(r['unmapped_output'])}")
        if r["reason"]:
            print(f"  gerekçe        : {r['reason']}")
        if r["error"]:
            print(f"  HATA           : {r['error']}")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "STUB" if args.dry_run else args.model,
        "dry_run": args.dry_run,
        "totals": {**counts, "false_positives": fp_total, "false_positive_rows": fp_rows},
        "results": results,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\nJSON çıktı: {os.path.abspath(args.out)}")
    if args.dry_run:
        print("\nUYARI: --dry-run stub ile çalıştı. Bu sayılar ÖLÇÜM DEĞİLDİR;")
        print("       yalnızca harness'in uçtan uca çalıştığını gösterir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
