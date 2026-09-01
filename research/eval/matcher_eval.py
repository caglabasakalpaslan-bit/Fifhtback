#!/usr/bin/env python3
"""
Offline evaluation harness: current lexical matcher vs a proposed semantic fallback.

Reads backend/server.py as text. Imports nothing from it, runs no server, calls no
LLM, and changes no product behaviour. Ground truth is the product's own cluster
assignments in _curated_pattern_room, fixed in code long before this harness.

Modes
  A  lexical            exact copy of _match_prevalence (5-char stems, threshold 2)
  B  semantic fallback  match on mechanism space instead of prose
  C  A first, B only when A returns found=False

Conditions
  1  LLM present     interpretation.pattern_candidate carries a real mechanism label
  2  no key          _fallback_interpret sets pattern_candidate = first 6 input words

Scoring. False positives are counted as more serious than false negatives: a miss
tells someone "no match yet"; a false positive tells them they belong to a story
that is not theirs.
"""
import re
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2] / "backend" / "server.py"
SRC = SERVER.read_text(encoding="utf-8")

# ---------------------------------------------------------------- production matcher
# Verbatim from server.py::_match_prevalence
def stems(s: str) -> set:
    return {t[:5] for t in re.findall(r'\w+', s.lower(), re.UNICODE) if len(t) >= 5}

LEX_THRESHOLD = 2          # server.py: if best and best_score >= 2
SEM_THRESHOLD = 2          # the fallback must not be laxer than the thing it backs up

# ---------------------------------------------------------------- corpus + truth
POOL = re.findall(r'"([^"]+)"', re.search(r'PATTERN_ROOM_SIGNALS = \[(.*?)\n\]', SRC, re.S).group(1))
CLUSTERS = {}
for cid, name, mech, idxs, summary in re.findall(
        r'PRCluster\(id="(c\d)", name="([^"]+)", mechanism="([^"]+)",\s*'
        r'signal_indices=\[([\d, ]+)\],\s*summary="([^"]+)"', SRC):
    CLUSTERS[cid] = {"name": name, "mechanism": mech, "summary": summary,
                     "idx": [int(i) for i in idxs.split(",")]}
WHY = dict(re.findall(r'cluster_id="(c\d)".*?why_formed="([^"]+)"', SRC, re.S))
TRUTH = {i: cid for cid, c in CLUSTERS.items() for i in c["idx"]}

# The engine's own mechanism vocabulary (server.py PATTERN_ROOM_PROMPT). Not new
# ontology: this list is lifted from the prompt, unchanged.
VOCAB = ["karar gecikmesi", "belirsiz sahiplik", "devir sürtüşmesi", "yeniden iş",
         "yetkinlik uyumsuzluğu", "kapasite kısıtı", "bilgi boşluğu", "süreç tekrarı",
         "önceliklendirme çatışması", "araç/sistem sürtüşmesi"]

# Two clusters share a mechanism term, so confusing them is ambiguous, not wrong.
def ambiguous(a: str, b: str) -> bool:
    ta = set(re.findall(r'\w+', CLUSTERS[a]["mechanism"]))
    tb = set(re.findall(r'\w+', CLUSTERS[b]["mechanism"]))
    return len(ta & tb) >= 2

# ---------------------------------------------------------------- match targets
TARGET = {
    # A: what production actually compares against — cluster prose
    "prose":     lambda cid: f'{CLUSTERS[cid]["name"]} {CLUSTERS[cid]["summary"]}',
    # B1: mechanism string only. No leakage: written independently of the pool lines.
    "mechanism": lambda cid: CLUSTERS[cid]["mechanism"],
    # B2: mechanism + why_formed. LEAKY — why_formed quotes these very pool lines,
    # so this is an optimistic ceiling, not a generalisation estimate.
    "mech+why":  lambda cid: f'{CLUSTERS[cid]["mechanism"]} {WHY.get(cid, "")}',
}

def best_match(query: str, target_key: str, threshold: int):
    q = stems(query)
    scores = {cid: len(q & stems(TARGET[target_key](cid))) for cid in CLUSTERS}
    best = max(scores, key=lambda k: scores[k])
    return (best, scores[best]) if scores[best] >= threshold else (None, scores[best])

# ---------------------------------------------------------------- mechanism label
def label_no_key(text: str) -> str:
    """server.py::_fallback_interpret -> pattern_candidate = first 6 words."""
    return " ".join(text.split()[:6]) or "Genel geri bildirim"

def label_oracle(i: int) -> str:
    """Ceiling only: assumes the LLM names the mechanism perfectly. Not a measurement."""
    return CLUSTERS[TRUTH[i]]["mechanism"]

# ---------------------------------------------------------------- classification
def classify(i, predicted):
    t = TRUTH[i]
    if predicted is None:
        return "yanlis_negatif"
    if predicted == t:
        return "dogru"
    return "belirsiz" if ambiguous(predicted, t) else "yanlis_pozitif"

def run(mode, condition):
    out = []
    for i, line in enumerate(POOL):
        lex, _ = best_match(line, "prose", LEX_THRESHOLD)
        if mode == "A":
            pred = lex
        else:
            label = label_oracle(i) if condition == "llm" else label_no_key(line)
            target = "mechanism" if condition == "llm" else "mech+why"
            sem, _ = best_match(label, target, SEM_THRESHOLD)
            pred = sem if mode == "B" else (lex if lex else sem)
        out.append((i, classify(i, pred), pred))
    return out

def tally(rows):
    t = {"dogru": 0, "yanlis_negatif": 0, "yanlis_pozitif": 0, "belirsiz": 0}
    for _, cat, _ in rows:
        t[cat] += 1
    return t

def per_cluster(rows):
    d = {cid: {"dogru": 0, "n": len(c["idx"])} for cid, c in CLUSTERS.items()}
    for i, cat, _ in rows:
        if cat == "dogru":
            d[TRUTH[i]]["dogru"] += 1
    return d

# ---------------------------------------------------------------- report
def main():
    print(f"Korpus: {len(POOL)} ifade · {len(CLUSTERS)} küme · etiketler ürünün kendi kodundan")
    print(f"Eşikler: lexical={LEX_THRESHOLD} semantic={SEM_THRESHOLD} (fallback daha gevşek DEĞİL)\n")

    TR = {"dogru": "doğru", "yanlis_negatif": "yanlış neg", "yanlis_pozitif": "YANLIŞ POZ",
          "belirsiz": "belirsiz"}
    plans = [
        ("A  lexical (production)",            "A", "llm"),
        ("B  semantic tek başına  [LLM var]",  "B", "llm"),
        ("C  lexical + fallback   [LLM var]",  "C", "llm"),
        ("B  semantic tek başına  [NO-KEY]",   "B", "nokey"),
        ("C  lexical + fallback   [NO-KEY]",   "C", "nokey"),
    ]
    print(f"{'MOD':38s} {'doğru':>6s} {'yanlışN':>8s} {'YANLIŞP':>8s} {'belirsiz':>9s}")
    print("-" * 74)
    results = {}
    for title, mode, cond in plans:
        rows = run(mode, cond)
        t = tally(rows)
        results[title] = (rows, t)
        print(f"{title:38s} {t['dogru']:6d} {t['yanlis_negatif']:8d} "
              f"{t['yanlis_pozitif']:8d} {t['belirsiz']:9d}")

    print("\n" + "=" * 74)
    print("KÜME BAZINDA doğru/toplam")
    print("=" * 74)
    header = f"{'küme':6s} {'mekanizma':44s}"
    print(header + "  " + "  ".join(f"{k.split()[0]+k.split()[-1][:1]:>7s}" for k, _, _ in plans))
    for cid, c in CLUSTERS.items():
        cells = []
        for title, _, _ in plans:
            pc = per_cluster(results[title][0])[cid]
            cells.append(f"{pc['dogru']}/{pc['n']:>2d}".rjust(7))
        print(f"{cid:6s} {c['mechanism'][:44]:44s}  " + "  ".join(cells))

    print("\n" + "=" * 74)
    print("C1 AYRI — karar gecikmesi + belirsiz sahiplik (havuzun 9/24'ü, 1 numaralı örüntü)")
    print("=" * 74)
    for title, _, _ in plans:
        rows = results[title][0]
        c1 = [(i, cat, pred) for i, cat, pred in rows if TRUTH[i] == "c1"]
        ok = sum(1 for _, cat, _ in c1 if cat == "dogru")
        fp = sum(1 for _, cat, _ in c1 if cat == "yanlis_pozitif")
        print(f"  {title:38s} doğru {ok}/9   yanlış pozitif {fp}")

    print("\n" + "=" * 74)
    print("NO-KEY'DE SEMANTIC FALLBACK'E GİREN ETİKET (ilk 5 örnek)")
    print("=" * 74)
    for i in range(5):
        print(f"  ifade : {POOL[i]}")
        print(f"  etiket: {label_no_key(POOL[i])!r}")
    print("\n  -> etiket, girdinin kopyası. Yeni bilgi taşımıyor.")

if __name__ == "__main__":
    main()
