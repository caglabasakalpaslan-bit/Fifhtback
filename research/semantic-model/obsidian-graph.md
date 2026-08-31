# Obsidian Graph Schema

**Status:** documentation only. A vault specification for holding Fifthback research
in the same vocabulary the product uses. No vault is created by this branch and
nothing here is read by the application.

The goal is narrow: make the research vault and the codebase say the same words, so a
mechanism discussed in a note is the same object as a mechanism in
`PATTERN_ROOM_PROMPT`, not a lookalike.

---

## 1. Design constraints

The vault inherits the product's commitments, not just its vocabulary:

1. **No person notes.** There is no note type for an employee, and none may be added.
   A note about "how the design team hands off work" is a mechanism note; a note about
   a named designer is out of scope for this vault entirely.
2. **Verbatim quotes stay at D0.** A note may hold a verbatim P0 quote only if the
   vault itself is private to the person who wrote it. A shared vault holds
   paraphrases (INV-06).
3. **Provenance is frontmatter, not prose.** Every note carrying an observation
   declares `provenance` and `disclosure`. A note without them is treated as
   unclassified and excluded from any aggregate query.
4. **The graph shows mechanism structure.** Link colours and folders are chosen so
   that a glance at the graph answers "what mechanisms do we believe in, and what
   holds them up?" — not "how many notes are there?".

---

## 2. Vault layout

```
fifthback-research/
├── 00-Inbox/            unclassified capture; must be emptied, not accumulated
├── 10-Signals/          individual observations (P0/P1/P2/P3)
├── 20-Mechanisms/       one note per mechanism in the controlled vocabulary
├── 30-Stories/          one note per cluster + its human-facing story
├── 40-Patterns/         promoted patterns with mass, spread, status
├── 50-Actions/          falsifiable interventions
├── 60-Research/
│   ├── questions/       open questions
│   ├── hypotheses/      testable claims with falsifiers
│   └── protocols/       how a given claim gets tested
├── 70-Sources/          external public material (P3) after the sensitivity screen
├── 90-Meta/
│   ├── ontology.md      symlink or copy of research/semantic-model/ontology.md
│   └── vocabulary.md    the mechanism list, kept in sync with schema.json
└── _templates/
```

Folders carry meaning here: `10-Signals` and `70-Sources` are the only folders that
may hold external or raw language, and they are the only two subject to the
sensitivity screen.

---

## 3. Note types and frontmatter

Field types: `str`, `enum`, `int`, `date`, `list[link]`, `bool`.

### 3.1 Signal — `10-Signals/`

```yaml
---
type: signal
id: sig-2026-0031
provenance: P0          # P0 | P1 | P2 | P3
disclosure: D0          # D0 | D1 | D2 | D3
captured: 2026-08-31
mechanism: "[[karar-gecikmesi]]"     # 0..n
cluster: "[[c1-karar-akisi]]"        # 0..1
evidence_grade: E0
verbatim: false         # true only in a private vault
tags: [signal]
---
```

`verbatim: true` is a claim with consequences: it asserts the body contains an exact
quote, which means the note may not be shared, exported or synced to a shared vault.
Default `false`.

### 3.2 Mechanism — `20-Mechanisms/`

One note per entry in the controlled vocabulary. These are the hubs of the graph.

```yaml
---
type: mechanism
id: karar-gecikmesi
tr: "karar gecikmesi"
en: "decision latency"
test: "Is the work waiting on a decision that exists but has not been made?"
confusable_with: ["[[belirsiz-sahiplik]]", "[[bilgi-boslugu]]"]
clusters: ["[[c1-karar-akisi]]"]
status: canonical       # canonical | candidate | retired
tags: [mechanism]
---
```

Body sections, in this order:

1. **Ayırt edici test** — the distinguishing question, expanded.
2. **Yüzeyde nasıl görünür** — the surface complaints that usually carry it.
3. **Karıştığı mekanizmalar** — for each confusable neighbour, the question that
   separates them.
4. **Karşı kanıt** — what would make us retire this mechanism.

Section 4 is not optional. A mechanism with no stated counter-evidence is a label.

`status: candidate` is how a new mechanism enters: proposed, linked from signals,
promoted to `canonical` only once it has survived §6's promotion rule.

### 3.3 Story / Cluster — `30-Stories/`

```yaml
---
type: story
id: c1-karar-akisi
cluster: c1
engine_name: "Karar Akışı / Sahiplik Darboğazı"
story_title: "Kararlar bir yerde takılıyor."
mechanism: ["[[karar-gecikmesi]]", "[[belirsiz-sahiplik]]"]
signal_count: 9
tags: [story, cluster]
---
```

`engine_name` is kept verbatim from the backend so that a rename in code shows up here
as a mismatch rather than silently diverging.

### 3.4 Pattern — `40-Patterns/`

```yaml
---
type: pattern
id: pat-c1
cluster: "[[c1-karar-akisi]]"
mechanism: ["[[karar-gecikmesi]]", "[[belirsiz-sahiplik]]"]
status: ACTIVE          # NEW | ACTIVE | STUCK | RESOLVED
frequency: 9
affected_teams: 3
unresolved_for: "3 ay"
pressure_band: high     # high | medium | low | none
coverage: 0.5
tags: [pattern]
---
```

`coverage` is required whenever `pressure_band` is present. A band without its
coverage is an incomplete statement (INV-09), and the query in §5.3 exists to catch
notes that omit it.

### 3.5 Action — `50-Actions/`

```yaml
---
type: action
id: act-0007
pattern: "[[pat-c1]]"
status: TESTING         # DETECTED | INVESTIGATING | TESTING | RESOLVED | REJECTED
hypothesis: "Naming a single decision owner for the top 3 waiting decision types shortens wait time."
falsifier: "Wait time unchanged or worse after 4 weeks with the owner named."
intervention: "..."
outcome: ""
tags: [action]
---
```

`falsifier` is required at creation, not at conclusion. An action whose falsifier is
written after the outcome is known is not a test.

### 3.6 Question — `60-Research/questions/`

```yaml
---
type: question
id: q-004
status: open            # open | answered | abandoned
mechanism: ["[[belirsiz-sahiplik]]"]
tags: [question]
---
```

### 3.7 Hypothesis — `60-Research/hypotheses/`

```yaml
---
type: hypothesis
id: h-011
question: "[[q-004]]"
mechanism: ["[[belirsiz-sahiplik]]"]
status: testing         # proposed | testing | supported | rejected
falsifier: "..."
evidence_grade: E2      # E0 | E1 | E2 | E3 | E4
tags: [hypothesis]
---
```

`status: rejected` is a successful outcome and should appear in the vault regularly.
A hypotheses folder with no rejections is evidence that nothing is being tested.

### 3.8 Source — `70-Sources/`

External public (P3) material that has passed the sensitivity screen in
`signal-mapping.md` §4.2.

```yaml
---
type: source
id: src-0012
provenance: P3
disclosure: D3
accessed: 2026-08-31
sensitivity: cleared    # cleared | excluded
mechanism: ["[[surec-tekrari]]"]
contributes_mass: false # always false for P3 — G-03
tags: [source, external]
---
```

`contributes_mass: false` is stated explicitly rather than implied, so that a query
summing evidence can filter on it and a reviewer can see the barrier is in place.

---

## 4. Link semantics

Obsidian links are untyped. Two conventions restore the typing from `ontology.md` §3:

**Frontmatter links are typed by their key.** `mechanism:`, `cluster:`, `pattern:`,
`question:`, `confusable_with:` each correspond to a named relation. These are the
links that carry meaning for queries.

**Body links are typed by their heading.** Inside a note body, a wikilink means
whatever the section it sits under means:

| Heading | Relation |
| --- | --- |
| `## Dayanak` | this note is supported by the linked note |
| `## Çelişki` | this note contradicts the linked note |
| `## Ayrım` | this note is distinguished from the linked note |
| `## Sonraki` | this note leads to the linked note |

A `## Çelişki` section is worth more than any other in the vault: it is where the
model gets corrected. Notes with no contradiction links tend to be notes nobody
argued with.

**Forbidden links** (mirroring the forbidden relations in `ontology.md` §3):

- Any link to a note about an identifiable person — there is no such note type.
- A link asserting exclusivity between two needs.
- A link from a `70-Sources/` note into a `40-Patterns/` note's evidence. External
  material informs mechanisms; it does not evidence a pattern (G-03).

---

## 5. Dataview queries

These reconstruct the product's own views from notes, which is the check that the
vault and the code still agree.

### 5.1 Mechanism strength

```dataview
TABLE
  length(filter(file.inlinks, (l) => l.type = "signal")) AS "Sinyal",
  status AS "Durum",
  test AS "Ayırt edici test"
FROM "20-Mechanisms"
SORT length(file.inlinks) DESC
```

### 5.2 Signals that reached no mechanism

The most informative query in the vault: unclustered signals are where the vocabulary
is missing a term.

```dataview
LIST
FROM "10-Signals"
WHERE !mechanism OR length(mechanism) = 0
SORT captured DESC
```

### 5.3 Pressure claims missing their coverage

```dataview
TABLE pressure_band, coverage
FROM "40-Patterns"
WHERE pressure_band AND pressure_band != "none" AND !coverage
```

Any row returned here is an INV-09 violation in note form.

### 5.4 Provenance audit — anything above its ceiling

```dataview
TABLE provenance, disclosure
FROM "10-Signals" OR "70-Sources"
WHERE (provenance = "P0" OR provenance = "P1") AND disclosure = "D3"
```

Should always be empty (G-01).

### 5.5 External material claiming mass

```dataview
TABLE contributes_mass
FROM "70-Sources"
WHERE contributes_mass = true
```

Should always be empty (G-03).

### 5.6 Hypotheses without a falsifier

```dataview
LIST
FROM "60-Research/hypotheses"
WHERE !falsifier
```

### 5.7 Open questions by mechanism

```dataview
TABLE status, mechanism
FROM "60-Research/questions"
WHERE status = "open"
SORT mechanism ASC
```

---

## 6. Graph view configuration

**Colour groups** (Graph view → Groups):

| Query | Colour | Reads as |
| --- | --- | --- |
| `tag:#mechanism` | strong amber | the hubs — the model's load-bearing claims |
| `tag:#signal` | pale grey | the mass |
| `tag:#story OR tag:#pattern` | teal | what a user would see |
| `tag:#action` | green | things being tested |
| `tag:#hypothesis` | violet | things being argued |
| `tag:#source` | dashed / muted | external, never counted |
| `path:00-Inbox` | red | unclassified backlog |

**How to read the resulting graph**

- A mechanism node with many pale signals and no violet hypothesis is *asserted but
  untested*.
- A dense cloud of signals with no mechanism hub is a **missing term** in the
  vocabulary — the highest-value finding the vault can produce.
- Red inbox nodes lingering across sessions mean classification is not keeping up, and
  unclassified material is precisely what leaks past the gating rules.
- Two mechanism hubs joined by many shared signals are candidates for a merge, or a
  sign the distinguishing test between them does not work in practice.

**Promotion rule for a candidate mechanism.** A `status: candidate` mechanism becomes
`canonical` when it has: at least E2 evidence (the same mechanism from unrelated
teams), a distinguishing test that separates it from every neighbour in
`confusable_with`, and a written counter-evidence section. Until then it stays a
candidate — visible in the graph, excluded from any aggregate.

---

## 7. Templates

Templater/core-templates files for `_templates/`. Each is the frontmatter block from
§3 plus the required body headings.

### `_templates/signal.md`

```markdown
---
type: signal
id: sig-{{date:YYYY}}-
provenance: P0
disclosure: D0
captured: {{date:YYYY-MM-DD}}
mechanism:
cluster:
evidence_grade: E0
verbatim: false
tags: [signal]
---

## Ne söylendi

## Hangi mekanizma, neden

## Ayrım
<!-- which neighbouring mechanism this is NOT, and why -->
```

### `_templates/mechanism.md`

```markdown
---
type: mechanism
id:
tr:
en:
test:
confusable_with:
clusters:
status: candidate
tags: [mechanism]
---

## Ayırt edici test

## Yüzeyde nasıl görünür

## Karıştığı mekanizmalar

## Karşı kanıt
<!-- what would make us retire this mechanism -->
```

### `_templates/hypothesis.md`

```markdown
---
type: hypothesis
id: h-
question:
mechanism:
status: proposed
falsifier:
evidence_grade: E0
tags: [hypothesis]
---

## İddia

## Yanlışlayan gözlem
<!-- must be written before any evidence is gathered -->

## Dayanak

## Çelişki
```

### `_templates/action.md`

```markdown
---
type: action
id: act-
pattern:
status: DETECTED
hypothesis:
falsifier:
intervention:
outcome:
tags: [action]
---

## Hipotez

## Yanlışlayan sonuç

## Müdahale

## Sonuç
```

### `_templates/source.md`

```markdown
---
type: source
id: src-
provenance: P3
disclosure: D3
accessed: {{date:YYYY-MM-DD}}
sensitivity: cleared
mechanism:
contributes_mass: false
tags: [source, external]
---

## Hassasiyet taraması
<!-- each check from signal-mapping.md 4.2, with its verdict -->

## Paraphrase
<!-- the mechanism in our own words; no quotation -->

## Ne işe yarar / ne işe yaramaz
<!-- vocabulary or hypothesis only; never mass -->
```
