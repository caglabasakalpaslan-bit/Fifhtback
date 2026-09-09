"""Four bounded pipeline roles around the existing Fifth Core.

CORE owns truth (the existing Fifth Core call in server.py — not duplicated here).
LIBRARIAN owns memory (retrieval over Pattern Records; Greek Olympus is the only corpus in v0).
SKEPTIC owns restraint (tries to kill every candidate; at most one survives; NONE is success).
STORYTELLER owns expression (a second language for the same insight; the core stays byte-identical).

Not an agent framework: four functions with typed inputs/outputs and one orchestrator (pipeline.py).
"""
from .pipeline import run_after_reveal  # noqa: F401
from .contracts import PipelineResult, Enrichment  # noqa: F401
