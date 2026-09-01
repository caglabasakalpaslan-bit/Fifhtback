# Ambiguities & Open Semantic Conflicts

**Status:** documentation only. This is a register of places where Fifthback's current
data and code use one word for two things, or route meaning somewhere it does not
belong. Nothing here is fixed on this branch — each entry states what is observed,
why it matters, and what the candidate resolutions are, so the decision stays with
whoever owns the product.

Entries are ordered by how much they distort what a user sees.

---

## 1. "Sinyal" denotes three different things

**Observed.** The word *sinyal* is used for:

| Use | Code | Actually is |
| --- | --- | --- |
| An extracted label + verbatim evidence | `class Signal` | a fragment of one utterance |
| A line in the Pattern Room pool | `PATTERN_ROOM_SIGNALS`, `AddSignalsRequest.signals` | a whole short statement |
| An employee's stored story | `lib/mySignals.js`, `addSignal()` | a whole utterance plus its state |

`PATTERNS.legend` tells the user "Nokta büyüklüğü: kaç sinyalden oluştuğu", counting
the second kind. `EmployeeHome` shows the third kind. They are different objects with
different cardinality: one utterance yields up to four `Signal`s but exactly one
`mySignals` entry.

**Why it matters.** Any count of "signals" is ambiguous until you know which kind is
being counted, and the map legend and the employee's own screen currently use the same
word for objects that differ by a factor of up to four. A future feature that counts
across both would be wrong without any visible error.

**Candidates.**
- (a) Keep `Sinyal` for the extracted fragment only; rename the pool entries
  *Havuz Satırı* and the employee entries *Anlatı* (the naming used in `ontology.md`).
- (b) Keep one word in the UI, disambiguate only in code.
- (c) Leave as is and document the collision.

**Not decided here.** (a) is the option `ontology.md` is written against, because a
document about meaning cannot itself be ambiguous — but adopting it in the product is
a copy change and out of this branch's scope.

---

## 2. c1 carries two mechanisms and may be inflated by it

**Observed.** `c1` is defined as `karar gecikmesi + belirsiz sahiplik` and holds 9 of
the 24 pool lines — nearly double the next cluster. It is ranked 1 partly *because* of
that mass (`why_selected`: "En yüksek frekans (9 sinyal)"). But `c3` is defined as
`belirsiz sahiplik + devir sürtüşmesi`, so `belirsiz-sahiplik` is a member of both.

Lines 12 ("Son sözün kimde olduğundan kimse emin değil") and 3 and 16 (single-person
bottleneck) sit in c1 on the ownership half of its definition, and would sit equally
well in c3.

**Why it matters.** The pattern's rank, its pressure `repetition` component, and its
position on the Örüntü Haritası are all functions of that count. If three of the nine
lines belong to a neighbouring cluster, c1's dominance is partly a definitional
artefact rather than an observation. The engine's own `uncertain` field already says
something close to this: *"gecikmenin ne kadarı tek bir kişiden, ne kadarı tanımsız
süreçten kaynaklanıyor — bu ayrım henüz veriyle netleşmedi."*

**Candidates.**
- (a) Give each cluster exactly one primary mechanism, with secondaries listed but not
  used for membership.
- (b) Split c1 into decision-latency and ownership clusters and let the map show
  whether they actually pull together.
- (c) Keep the merge and state the overlap in `why_formed`.

**Note.** This is testable rather than a matter of taste: re-cluster with the two
mechanisms separated and see whether the lines redistribute. Protocol sketch in
`research-agent-brief.md`.

---

## 3. The adapter uses mechanism words the engine does not have

**Observed.** `PATTERN_ROOM_PROMPT` enumerates ten mechanisms. `data/stories.js`
labels the same clusters with different strings:

| Cluster | Engine mechanism | Adapter's secondary label |
| --- | --- | --- |
| c1 | karar gecikmesi + belirsiz sahiplik | `karar gecikmesi · belirsiz sahiplik` ✅ |
| c2 | yeniden iş (rework) | `yeniden iş · geç geri bildirim` ⚠️ |
| c3 | belirsiz sahiplik + devir sürtüşmesi | `belirsiz sahiplik · devir sürtüşmesi` ✅ |
| c4 | kapasite kısıtı + önceliklendirme çatışması | `öncelik belirsizliği · akış tıkanması` ⚠️ |
| c5 | bilgi boşluğu + araç/sistem sürtüşmesi + süreç tekrarı | `bilgi boşluğu · araç kopukluğu` ⚠️ |

*geç geri bildirim*, *akış tıkanması*, *öncelik belirsizliği* and *araç kopukluğu* are
not in the engine's vocabulary. Some are paraphrases (*araç kopukluğu* ≈ *araç/sistem
sürtüşmesi*); *öncelik belirsizliği* is a genuinely different claim from *önceliklendirme
çatışması* — ambiguity is not the same as conflict, and c4's own evidence supports the
conflict reading more than the ambiguity one.

**Why it matters.** When the live Claude re-analysis runs, it returns mechanism strings
from the engine's vocabulary. The adapter's labels are static and keyed by cluster id,
so after a re-analysis the secondary label shown to the user can describe a mechanism
the engine no longer assigned. The failure is silent.

**Candidates.**
- (a) Adopt the ten canonical ids from `schema.json` and have the adapter render a
  label for an id rather than storing its own string.
- (b) Keep the adapter strings but derive them from the engine's mechanism text.
- (c) Accept the drift, since the label is secondary and small.

---

## 4. The İş Hayatı Sözlüğü routes voice-safety phrases into an ownership cluster

**Observed.** Five of the fourteen dictionary phrases are about the difficulty of
speaking up, and all five are routed to `c3` — whose story title is
*"İşin sahibi kim, belli değil."*

| Phrase | Routed to | What it is about |
| --- | --- | --- |
| Söylesem olmuyor, sussam gönlüm razı değil. | c3 | cost of speaking |
| Herkes biliyor ama kimse söylemiyor. | c3 | collective silence |
| Bir şey yanlış ama adını koyamıyorum. | c3 | inability to name |
| Bunu yöneticime söylesem yanlış anlaşılır. | c3 | fear of being misread |
| Ben mi abartıyorum, yoksa gerçekten böyle mi? | c3 | self-doubt / need for validation |

A person who picks *"Bunu yöneticime söylesem yanlış anlaşılır."* is shown
*"İşin sahibi kim, belli değil."* — a sentence about handoffs.

**Why it matters.** This is the entry point of the whole product. The first thing
Fifthback does with the most vulnerable category of input is mislabel it, in the one
interaction where being understood is the entire promise.

It compounds with a second gap: `MANAGER.axes.voice` declares *"Konuşma kolaylığı"* as
an axis, and `pressure.js` hardcodes `speakingCost: null` in both adapters with the
comment *"never measured by the engine — must not be invented"*. The dimension is
named in the UI, never measured, and has no mechanism in the vocabulary — so the
phrases have nowhere correct to go. c3 is absorbing them as a catch-all.

**Candidates.**
- (a) Add a mechanism for the cost of speaking up (`konusma-maliyeti`) and route
  these phrases to it. This is an addition to the *domain model*, and it needs
  evidence, not just a name — see `research-agent-brief.md` RQ-1.
- (b) Route them to `c_new` (awaiting clustering) rather than to a wrong cluster.
  Honest, and much cheaper.
- (c) Give the dictionary its own non-clustering path so a phrase leads to a reflection
  rather than a mechanism.

**Assessment.** (b) is available immediately and costs nothing but a data edit; (a) is
the real answer but should not be invented without evidence. Both are out of scope for
this branch, which only records the finding.

---

## 5. Three lifecycles, overlapping state names, different owners

**Observed.**

| Lifecycle | States | Owner |
| --- | --- | --- |
| Employee story | NEW → MATCHED → FOLLOWING → SHARED → MOVING → RESOLVED | the person |
| Manager pattern | NEW → ACTIVE → STUCK → RESOLVED | the organisation |
| Action board | DETECTED → INVESTIGATING → TESTING → RESOLVED / REJECTED | whoever runs the intervention |

`NEW` appears in two of them meaning different things; `RESOLVED` appears in all three
meaning three different things — the person considers it settled, the organisation
closed the pattern, or an intervention was confirmed to work.

**Why it matters.** "Çözüldü" shown on an employee's own story and "RESOLVED" on a
manager pattern are not the same claim, and an employee reading the former may
reasonably believe the organisation acted. The current UI keeps them on separate
surfaces, which contains the problem without resolving it.

**Candidates.**
- (a) Rename per owner: employee `KAPANDI`, org `ÇÖZÜLDÜ`, action `DOĞRULANDI`.
- (b) Keep names, never render two lifecycles on one surface (the current de facto
  rule, undocumented until now).
- (c) Model an explicit mapping between them, so an employee story can show that the
  organisation's pattern moved.

---

## 6. `yetkinlik uyumsuzluğu` is the one mechanism that can score people

**Observed.** The mechanism list in `PATTERN_ROOM_PROMPT` includes *yetkinlik
uyumsuzluğu* (skill mismatch), inside a prompt that opens by forbidding exactly that:
*"Bunlar çalışan puanlaması DEĞİL; kişilik, motivasyon, yetkinlik veya duygu TEŞHİSİ
YAPMA."*

The same prompt forbids diagnosing *yetkinlik* and offers *yetkinlik uyumsuzluğu* as a
clustering mechanism four lines later. No curated cluster uses it, so the tension has
never surfaced — but a live re-analysis is free to assign it.

**Why it matters.** It is the single opening through which the product could produce
output that reads as a judgement about people, which is the one thing it promises never
to do (INV-03). A cluster named *"Yetkinlik Uyumsuzluğu"* shown to a manager is a
performance claim about a team, however carefully worded.

**Candidates.**
- (a) Remove it from the vocabulary.
- (b) Keep it, narrowed in the prompt to routing/structure ("work routed to a team
  without the capability"), never to individuals or teams as actors.
- (c) Keep it, and gate any cluster assigned to it from the manager view.

**Assessment.** (b) is the reading `ontology.md` §4 documents, with an explicit warning
attached. It is a prompt change and therefore out of scope here.

---

## 7. Unsharing does not retract mass

**Observed.** `HOME.visibility.unshare` lets a person withdraw a shared story. The
pool (`pattern_room_meta.pool`) is a list of strings addressed by index, and cluster
membership is `signal_indices` into that list. There is no per-item removal path, and
removing an entry would silently re-point every cluster's indices.

**Why it matters.** The share control implies reversibility. What is reversible today
is visibility of the person's own copy, not the contribution already folded into an
aggregate. That gap is not stated anywhere in the copy.

**Candidates.**
- (a) State the limit plainly in the unshare copy ("Paylaşımdan çekmek, daha önce
  oluşmuş toplu görünümü değiştirmez").
- (b) Make the pool addressable by id rather than index so retraction is possible.
- (c) Buffer newly shared items until a threshold so retraction is possible during a
  window.

**Note.** (a) is a copy change and (b) a data-model change; both are out of scope here.
The entry exists so the promise and the mechanism are compared in writing.

---

## 8. `STORY_BY_PATTERN_TITLE` is keyed by an exact title string

**Observed.** The mapping from seeded manager patterns to human story titles is keyed
by the full pattern title, e.g. `"Toplantı yoğunluğu odaklanmayı aşındırıyor"`. Any
edit to a seeded title in `backend/server.py` — including whitespace or a changed
character — drops the mapping.

**Why it matters.** The fallback is benign (the backend title is shown instead, per
INV-07), so the failure is invisible: the product keeps working and quietly stops
speaking human language on that card.

**Candidates.** Key by pattern id; or keep title keys and add a check that every seeded
title has a mapping.

---

## 9. Three seeded patterns name mechanisms the vocabulary does not contain

**Observed.** Of the five seeded manager patterns:

- *Toplantı yoğunluğu odaklanmayı aşındırıyor* — attention fragmentation.
- *Yeni çalışanlar için sessiz işe alışma boşlukları* — onboarding gap.
- *Perde arkası çalışmanın takdir edilmesi* — recognition of invisible work
  (POSITIVE).
- *Önce-yazılı (async) dokümantasyon alışkanlığı* — a working practice (POSITIVE).

None maps onto the ten mechanisms. Two are positive and by construction cannot: every
mechanism in the vocabulary names a friction.

**Why it matters.** The Örüntü Haritası places nodes by mechanism-stem similarity.
Patterns whose mechanism is not in the vocabulary have nothing to be similar *to*, so
their position on the map is arbitrary rather than meaningful — while looking exactly
as meaningful as the rest.

**Candidates.**
- (a) Extend the vocabulary with the missing friction mechanisms (attention
  fragmentation, onboarding gap) — subject to evidence.
- (b) Introduce a separate positive vocabulary (*işleyen şeyler*) rather than forcing
  praise through a friction model.
- (c) Exclude patterns with no vocabulary mechanism from the map, and say why.

---

## 10. Prevalence matching is lexical, in a product that rejects lexical grouping

**Observed.** `_match_prevalence` matches an interpretation to a seeded pattern by
5-character stem overlap with a threshold of 2 shared stems. The same technique places
nodes on the Örüntü Haritası. Meanwhile `PATTERN_ROOM_PROMPT` instructs clustering
*"YÜZEY kelimelere göre DEĞİL, altta yatan örgütsel MEKANİZMAYA göre"*.

So clustering is mechanism-based, and the two things a user sees most directly —
"is this common here?" and "what sits near what on the map" — are word-based.

**Why it matters.** Two statements describing the same mechanism in different words
(*"onay bekliyoruz"* and *"kimse karar veremiyor"*) share no 5-char stems and will not
match. The false-negative is invisible: the user simply sees the honest empty state and
concludes they are alone. That is the most costly possible error for this product, and
it is silent.

The threshold of 2 also makes false positives cheap in Turkish, where common stems
recur across unrelated statements.

**Candidates.**
- (a) Match on mechanism instead: run the interpretation's `pattern_candidate` through
  mechanism assignment, then match cluster to cluster.
- (b) Keep stem matching as a fast path, fall back to a mechanism check before
  reporting `found=false`.
- (c) Keep as is; measure the false-negative rate first.

**Note.** (c) is the honest first step and needs no code change: sample real
interpretations, assign mechanisms by hand, count how many true matches the stem
matcher misses. Protocol in `research-agent-brief.md` RQ-3.

---

## 11. Coverage is computed but rarely reaches the reader

**Observed.** `computePressure` returns `coverage` — the fraction of the four
components actually present — and the refocus pass replaced the explicit "2/4 boyut"
readout with the sentence *"Elimizdeki bilgiyle yapılan bir okuma"*, plus a single
caveat at the foot of the manager page.

For pattern-room patterns, `spread` and `duration` are always null, so coverage is at
most 0.5 — every such band is derived from half the model.

**Why it matters.** "Sıkışıklık yüksek" at coverage 0.5 and at coverage 1.0 are
materially different claims presented identically. The refocus change was a legitimate
copy simplification; the effect is that the strength of the claim is no longer visible
per card.

**Candidates.**
- (a) Show coverage only when it is below a threshold (e.g. < 0.75).
- (b) Restore a compact per-card indicator.
- (c) Keep the page-level caveat and treat coverage as internal.

---

## 12. Terminology drift between the ontology and the product surface

Terms this document introduces (`Havuz Satırı`, `Anlatı`, mechanism ids like
`karar-gecikmesi`) do **not** appear in the product. That is intentional for now —
this branch does not touch copy — but it creates a second vocabulary.

If the ids in `schema.json` are ever adopted in code, this file should record the
date and the mapping, so that notes written under the old vocabulary remain readable.
Until then, `schema.json` is a description of the code, and where the two disagree,
**the code is correct and this document is stale**.
