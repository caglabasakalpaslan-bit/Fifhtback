# Research Agent Brief

**Status:** documentation only. A working brief for whoever — person or agent — takes
up research against this semantic model. It defines the mission, the boundaries, what
counts as evidence, and what a finished piece of work looks like.

Read `ontology.md` first. This brief assumes its vocabulary.

---

## 1. Mission

Improve the accuracy of Fifthback's semantic model: the mechanism vocabulary, the
mapping from what people say to which mechanism it is, and the honesty of what the
product claims to know.

The research is **about the domain** — how work systems produce friction, and how
people describe it — not about users, and never about individuals.

---

## 2. Boundaries

**In scope**

- The mechanism vocabulary: whether the ten terms are the right ten, whether each has a
  test that actually separates it from its neighbours, whether terms are missing.
- Classification accuracy: does a given statement land on the mechanism a careful
  reader would assign?
- The gaps recorded in `ambiguities.md`, in the order listed there.
- External public material (P3) as a source of vocabulary and hypotheses only, under
  the rules in `signal-mapping.md` §4.2.

**Out of scope**

- Any UI, copy, prompt, endpoint or data change. This branch and this brief produce
  documents and notes; product changes are proposed, never made here.
- Any modelling of people: performance, personality, motivation, engagement,
  sentiment about individuals. If a research question requires a person as a unit of
  analysis, the question is out of scope — reformulate it around the work system or
  drop it.
- Collecting new employee data. Work from what the product already holds, from P2
  demo material, and from P3 public material that passes the sensitivity screen.
- Cross-organisation comparison or benchmarking.

**Hard stops.** Stop and escalate rather than proceeding if a task would require:
scraping non-public or login-gated material; retaining an author handle or employer
name; analysing an identifiable individual; or introducing any number a user would see
that is not traceable to a field the engine produced.

---

## 3. Evidence grades

| Grade | Turkish | What it is | What it licenses |
| --- | --- | --- | --- |
| **E0** | tekil anlatı | One statement | Reflecting it back to its author. Nothing else. |
| **E1** | tekrar | Several independent statements of the same mechanism in one team | A candidate mechanism |
| **E2** | yayılım | The same mechanism from unrelated teams | Promoting a candidate mechanism to canonical |
| **E3** | dış doğrulama | A P3 corpus shows the same mechanism elsewhere | Confidence that the mechanism is real. **No mass.** |
| **E4** | müdahale sonucu | An Eylem reached RESOLVED or REJECTED with a recorded before/after | The only grade that can disconfirm a claim |

The asymmetry is deliberate: E0–E3 can only ever support, and E4 is the only grade
that can knock something down. A model that accumulates only supporting evidence is
not being tested.

---

## 4. Method

Every piece of work follows the same five steps, and every step is written down before
the next one begins.

1. **Question.** One sentence, answerable, about the work system. `60-Research/questions/`.
2. **Hypothesis with falsifier.** State what would have to be observed for the claim
   to be wrong — *before* looking. A hypothesis whose falsifier is written afterwards
   is a summary, not a test.
3. **Evidence.** Gather, classify each item by provenance and grade, and record what
   was looked at and rejected as well as what was kept. Absence of counter-evidence
   only counts if it was looked for.
4. **Verdict.** `supported` / `rejected` / `undetermined`. `undetermined` is a real
   outcome; forcing a verdict is worse than not having one.
5. **Consequence.** What changes: a vocabulary proposal, an ambiguity entry, a
   protocol for an intervention, or nothing. "Nothing" is a legitimate consequence and
   should be stated rather than left implied.

---

## 5. Open research questions

Ordered by expected value. Each names its falsifier, because a research question
without one produces an essay.

### RQ-1 — Is "the cost of speaking up" a missing mechanism?

**Why.** Five of fourteen dictionary phrases are about difficulty speaking, all routed
to an ownership cluster; `MANAGER.axes.voice` names the axis; `pressure.js` refuses to
measure it. The product has named a dimension it cannot represent
(`ambiguities.md` §4).

**Question.** Do statements about the difficulty of speaking describe a distinct
mechanism, or are they surface expressions of mechanisms already in the vocabulary
(unclear ownership, decision latency)?

**Approach.** Assemble statements about speaking difficulty from P2 dictionary phrases
and cleared P3 material. For each, apply the distinguishing tests of all ten existing
mechanisms. Count how many are fully explained by an existing mechanism.

**Falsifier.** If most such statements pass an existing mechanism's test cleanly, there
is no missing mechanism — the phrases are simply routed to the wrong existing one, and
the finding becomes a data fix rather than a vocabulary change.

**Caution.** A mechanism about speaking sits close to modelling people. It must be
formulated as a property of the system ("what happens to a statement when it is made")
and never as a property of a person ("who speaks up"). If it cannot be formulated that
way, it does not enter the vocabulary.

### RQ-2 — Does the c1 / c3 mechanism overlap inflate c1's rank?

**Why.** `belirsiz-sahiplik` belongs to both clusters; c1 holds 9 of 24 lines and is
ranked 1 partly on that count (`ambiguities.md` §2).

**Approach.** Re-classify all 24 pool lines against single primary mechanisms using
the distinguishing tests, blind to current membership. Compare the resulting
distribution with the curated one.

**Falsifier.** If the blind re-classification reproduces roughly the current
distribution (c1 ≈ 9), the concentration is real and the entry can be closed.

### RQ-3 — What is the false-negative rate of stem-based prevalence matching?

**Why.** `_match_prevalence` matches on 5-character stems with a threshold of 2, in a
product whose clustering explicitly rejects surface-word grouping. A false negative
shows a person the empty state — telling them, in effect, that they are alone
(`ambiguities.md` §10).

**Approach.** Take a set of interpretations (P2 material is sufficient — this is a
property of the matcher, not of any person). Assign each to a seeded pattern by hand
using mechanism reasoning. Run the matcher. Count misses, and inspect what kind of
rewording causes them.

**Falsifier.** A low miss rate on realistic phrasings closes the question. A high one
makes it the most costly silent error in the product.

**Note.** This question needs no product change to answer, and its answer changes what
`ambiguities.md` §10 recommends.

### RQ-4 — Do the distinguishing tests actually separate the mechanisms?

**Why.** The tests in `ontology.md` §4 were written for this model. Untested, they are
just more prose.

**Approach.** Two independent classifiers assign mechanisms to the same set of
statements using only the tests. Measure agreement. Every disagreement names the pair
of mechanisms that failed to separate.

**Falsifier.** High agreement means the tests work. Concentrated disagreement on one
pair means those two mechanisms are one mechanism, or need a better test.

### RQ-5 — Does the model have anywhere to put things that work?

**Why.** `POSITIVE` is a valid `feedback_type`; two dictionary phrases and two seeded
patterns are positive; every mechanism in the vocabulary names a friction
(`ambiguities.md` §9).

**Question.** Should positive statements cluster by *the mechanism that made the good
outcome possible* — which would reuse the same vocabulary inverted — or does praise
need its own structure?

**Falsifier.** If positive statements can be assigned to an existing mechanism's
inverse without strain, no new structure is needed.

### RQ-6 — Which mechanisms does external public material name that we do not?

**Why.** Vocabulary gaps are easier to see from outside one organisation. This is the
one question P3 material is genuinely well suited to.

**Approach.** From cleared P3 sources, extract mechanism claims and map each onto the
ten. Record the residue.

**Falsifier.** An empty residue means the vocabulary is adequate at this scope.

**Strict rule.** Findings here may propose vocabulary. They may never enter any count,
pool, cluster or evidence list (G-03).

---

## 6. Output format

Findings live in the Obsidian vault described in `obsidian-graph.md`, using its note
types and frontmatter. Beyond that:

- **A finding is a note, not a message.** If it is not in the vault with frontmatter,
  it did not happen.
- **Every observation note carries `provenance` and `disclosure`.** Unclassified notes
  sit in `00-Inbox` and are excluded from every aggregate query until classified.
- **Every hypothesis carries a `falsifier` at creation.**
- **Paraphrase by default.** `verbatim: true` is permitted only in a private vault and
  is never synced or exported.
- **Proposals are proposals.** A vocabulary change is written as a candidate mechanism
  note with `status: candidate` and the evidence behind it. It becomes canonical only
  under the promotion rule in `obsidian-graph.md` §6.

A completed research cycle produces, at minimum: the question note, the hypothesis note
with its falsifier and verdict, the signal or source notes that were examined, and one
line in `ambiguities.md` if the finding changes what is written there.

---

## 7. Working rules

1. **Report what you find, including nothing.** "The vocabulary was adequate" is a
   result. Padding a null result into a recommendation is the main way this kind of
   work goes wrong.
2. **Prefer the cheap honest fix.** Where a wrong mapping can be corrected by routing
   to `c_new` instead of inventing a mechanism, say so; a new mechanism is a claim
   about the world and needs E2 evidence.
3. **Never fill a gap with a plausible value.** The product's whole posture is that an
   unmeasured thing is displayed as unmeasured (INV-09). Research inherits that.
4. **Treat the code as the source of truth.** Where this documentation and the code
   disagree, the code is correct and the document is stale — fix the document and note
   the date.
5. **Escalate rather than interpret** any question that would require a person as the
   unit of analysis, or any external material that fails the sensitivity screen.
