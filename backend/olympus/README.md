# The Fifth Olympus — v0.1 (content / data layer only)

First exploratory world for **KENDİNİ BUL**: Greek Olympus. This directory holds content and
definitions only. Nothing here is wired to production code, `FIFTH_CORE_PROMPT`, routing, or the
frontend. It exists so a later, highly visual exploration UX has a structured, source-honest layer
to stand on.

## What The Fifth is doing here — and not doing

- A figure is a **story doorway**, not a human category. The product never says "you are Athena".
- This is **not** a personality typing system. No scores, no types, no "your top gods".
- A user may know nothing about Greek gods. Every figure carries a 3–6 word `short_label` and a
  one-sentence intro so they can choose a door without homework.
- Worlds are **not** forced to twelve items. Olympus has twelve because ancient lists mostly do;
  Hestia is kept as a documented alternate (see below). A future world may have 6, 8 or 20.

## Files

| File | What it is |
|---|---|
| `schema.json` | JSON Schema (2020-12) for one figure. Three layers, kept apart: `source_supported` (LAYER 1), `fifth_interpretation` (LAYER 2), `ux_story` (LAYER 3). |
| `greek_olympians_v0_1.json` | 12 Olympians + Hestia, populated against the schema. 97 myth entries, 69 story doors, all cross-references validated. |
| `awareness_events_v0_1.json` | Event model for the future Farkındalık Haritası. Definition only; no collector exists. |

## The three layers

1. **SOURCE-SUPPORTED MYTHOLOGY** (`source_supported`): domains, epithets, major myths with named
   ancient sources, related figures, and an `evidence_status`. Every claim carries a confidence tag:
   `attested_archaic_classical`, `attested_hellenistic_roman`, `attested_late_or_orphic`,
   `scholarly_inference`, or `unsourced_popular`. Contradictory versions are kept as `variants`,
   never merged.
2. **FIFTH INTERPRETATION** (`fifth_interpretation`): recurring human situations, tensions,
   constructive and costly expressions, boundary questions, candidate Fifth questions and Reveal
   material. Every item points back to a `myth_id`. Tensions have a `shape`
   (`between_two`, `gradient`, `open_question`, `sequence`) — **polarity is not required** and was
   not invented for symmetry. `costly_expressions` record who bears the cost; in most myths it is
   others, and the record says so instead of inventing a self-cost.
3. **UX / STORY IDEA** (`ux_story`): the know-nothing orientation hint, source-attested visual
   motifs for a future 3D scene, and 3–6 `story_doors` per figure: second-person Turkish situations
   a user can recognise without knowing the myth. Each door names the myths and the tension it is
   derived from, and the `perspective` it puts the user in (the figure, the other party, a witness).
   No door is written from the position of a perpetrator of sexual violence.

## Hestia

Ancient lists of the Twelve are not stable. The Parthenon east frieze shows Dionysus and omits
Hestia; other lists include her. The often-repeated story that she "gave up her seat to Dionysus"
has **no located ancient source** (it appears in modern handbooks) and is tagged
`unsourced_popular`. Hestia is therefore recorded with `membership.status = "alternate"`, fully
populated, and honestly thin: she has almost no narrative in the sources, and her record says so
rather than padding.

## How this relates to Fifth Core

Story doors, candidate questions and Reveal material are written to be compatible with
Routing Rule v0.1 (QUESTION only when a low-effort fact the user knows discriminates two readings;
never ask what the story already says; CLOSE when there is no unresolved tension). They are
**content**, not prompt changes. Wiring a door into `/api/fifth/start` is a separate, later decision.

## Validation

`greek_olympians_v0_1.json` was validated against `schema.json` and checked for: every
`from_myths` / `derived_from_myths` id existing in that figure's `major_myths`; every
`tension_ref` existing in that figure's `tensions`; 3–6 word labels; no identity phrasing
("sen … gibisin") in doors. Re-run the same checks whenever content changes.

## Status

- Content authored from primary sources listed per figure; **not yet human-reviewed**
  (`record_status.human_reviewed = false` on every record).
- Known thin spots are declared in each `evidence_status` and in the summary the Founder received
  with this commit (Ares' constructive side rests on a late hymn; Arachne and punished-Medusa are
  Ovid only; Apollo-as-sun and Artemis-as-moon are late; Dionysus' "foreign late arrival" is refuted
  by Linear B; Cupid & Psyche is a Latin novel).
