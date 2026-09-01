# External experiments — status and policy

Recorded as project context. This file is documentation; it changes no product
behaviour and nothing in the application reads it.

**Canonical source of truth: GitHub, branch `claude/fifthback-control-room`.**
No external tool is a dependency for Fifthback's progress. Verified: no reference
to any external experiment platform exists anywhere in `frontend/`, `backend/`,
or the research documents.

---

## Lovable — visual research only

Status: **moodboard / visual research.** Not a code source. Nothing in this
repository depends on it, and nothing should.

Principles kept, because they proved useful and are already implemented here:

- warm editorial visual language, not a SaaS dashboard;
- a human feeling rather than an admin console;
- meaningful spatial language — proximity and density carry meaning
  (Örüntü Haritası, sıkışıklık bands);
- a different visual and conversational job per surface — Söyle asks, Benim
  Alanım reflects, Yönetici Görünümü aggregates, Örüntü Haritası situates.

These are design principles, not artefacts to import.

## Taskade — archived research prototype

Status: **archived.** The Signal Research Studio contributes *workflow design*,
not product data.

Useful learning — the agent chain:

```
Research Lead → Public Signal Miner → Evidence/Deduplication Auditor → Semantic Mapper
```

Pilot result: **0 accepted real signals**, because no verifiable candidates were
collected.

Consequences for this repository:

1. Taskade produced **no canonical data**. Nothing from it may enter the pool,
   `evidence[]`, `frequency`, or any count a user sees.
2. Future Fifthback work must not require Taskade to proceed.
3. The zero-yield pilot is evidence about the **P3 / dış kamusal** tier described
   in `research/semantic-model/signal-mapping.md` §4.2: that tier has no
   implementation in the product, and the one attempt to source material for it
   returned nothing. Its elaborate intake rules remain unexercised.
4. `research/semantic-model/research-agent-brief.md` should be read as workflow
   design of the same shape, not as a plan of record.

Nothing is deleted. Both experiments stay available as reference.
