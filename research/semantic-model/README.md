# research/semantic-model

Documentation only. Nothing in this directory is imported, executed or referenced by
the application, and this branch makes no change to any product surface, prompt,
endpoint or data file.

It writes down — precisely, and partly in machine-readable form — the meaning already
encoded in `backend/server.py` and `frontend/src/{data,lib}`, and names the places
where that meaning is currently inconsistent.

| File | What it is |
| --- | --- |
| [`ontology.md`](ontology.md) | Entities, relations, mechanism vocabulary with distinguishing tests, invariants, lifecycles |
| [`schema.json`](schema.json) | Machine-readable companion: entities, relations, mechanisms, invariants, provenance tiers, disclosure classes, gating rules, evidence grades |
| [`signal-mapping.md`](signal-mapping.md) | How a statement travels through the system; public-signal classification (P0–P3 × D0–D3); the full current pool → cluster → story → pattern mappings |
| [`obsidian-graph.md`](obsidian-graph.md) | Research vault layout, note types and frontmatter, typed-link conventions, Dataview queries, graph configuration, templates |
| [`ambiguities.md`](ambiguities.md) | Twelve open semantic conflicts found in the current model, each with impact and candidate resolutions — none applied |
| [`research-agent-brief.md`](research-agent-brief.md) | Mission, boundaries, evidence grades, method, six open research questions with falsifiers |

**Reading order:** `ontology.md` → `signal-mapping.md` → `ambiguities.md`. The other
three are reference.

**Authority.** Where this documentation and the code disagree, the code is correct and
the document is stale.

**Language.** Domain terms are Turkish, matching the product; prose is English,
matching the existing code comments.
