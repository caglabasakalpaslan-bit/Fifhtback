"""Typed inputs/outputs of the four roles. No role may write to another role's input."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

Route = Literal["QUESTION", "REVEAL", "CLOSE"]


# ---------- CORE (owned by server.py; this is the frozen view the other roles receive) ----------
class CoreReveal(BaseModel):
    session_id: str
    route: Route
    distinction: Optional[str] = None
    reveal: Optional[str] = None
    uncertain: Optional[str] = None
    shape: Optional[str] = None           # between_two | gradient | open_question | sequence, from the core
    noticed: List[str] = []
    candidates: List[str] = []            # readings the core considered (used only to avoid re-importing eliminated ones)
    answered: bool = False
    core_hash: str                        # sha256(distinction, reveal, uncertain) — verified before and after


# ---------- LIBRARIAN ----------
class PatternRecord(BaseModel):
    record_id: str
    epistemic_type: Literal["named_concept", "mythic_parallel", "proverb", "lived_story", "system_analogy", "fifth_coined"]
    world_id: str
    figure_id: Optional[str] = None
    figure_name: Optional[str] = None
    title_tr: str
    encodes_distinction: Dict[str, Optional[str]]
    statement_tr: str
    shape: Literal["between_two", "gradient", "open_question", "sequence"]
    mechanism_one_sentence: str
    portable_expressions_tr: List[str] = []
    situations_tr: List[str] = []
    boundary_questions_tr: List[str] = []
    myths: List[Dict[str, Any]] = []      # {myth_id, title, summary, sources[], confidence}
    source_refs: List[Dict[str, Any]] = []
    max_source_confidence: Optional[str] = None
    interpretation_confidence: str = "plausible"
    misuse_warnings: List[str] = []
    human_reviewed: bool = False


class LibrarianQuery(BaseModel):
    """What leaves the Core for the Librarian. Never the story, never the nickname."""
    distinction: str
    poles: Dict[str, Optional[str]]
    structural_situation: List[str] = []  # noticed signals at situation level (quotes stripped)
    uncertain: Optional[str] = None
    noticed: List[str] = []
    candidates_rejected: List[str] = []


class LibrarianCandidate(BaseModel):
    record_id: str
    figure_id: Optional[str]
    myth_ids: List[str]
    source_refs: List[str]
    epistemic_type: str
    structural_match: Dict[str, str]      # {"x": "core X → record x'", "y": "core Y → record y'"}
    why_it_may_fit: str
    recall_score: float                   # lexical recall score (not a judgement)


class LibrarianOutput(BaseModel):
    candidates: List[LibrarianCandidate] = Field(default_factory=list, max_length=5)
    recall_considered: int = 0            # records that passed the structural pre-filter and were shown to the mapper
    prefilter: Dict[str, Any] = {}        # why records were excluded before any model call
    dropped_by_verification: List[Dict[str, Any]] = []   # mapper output the code refused (no pole grounding / unknown id)
    query_sent: Dict[str, Any] = {}


# ---------- SKEPTIC ----------
class SkepticRejection(BaseModel):
    record_id: str
    reasons: List[str]


class SkepticVerdict(BaseModel):
    passed: Optional[str] = None          # record_id or None
    rejections: List[SkepticRejection] = []
    score: int = 0                        # 0–7 for the passed candidate, else 0
    speculation_risk: Optional[Literal["low", "medium", "high"]] = None
    note: Optional[str] = None


# ---------- STORYTELLER ----------
class Enrichment(BaseModel):
    used: bool
    type: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    figure_id: Optional[str] = None
    myth_id: Optional[str] = None
    record_id: Optional[str] = None
    source_refs: List[str] = []
    label_tr: str = "Başka bir dilde"
    disclaimer_tr: Optional[str] = None
    reason: Optional[str] = None          # why not used, when used == False
    fidelity: Optional[Dict[str, Any]] = None   # source-fidelity post-check: {"passed": bool, "claims": [...], "deterministic": [...]}


# ---------- PIPELINE ----------
class RoleTrace(BaseModel):
    ran: bool = False
    calls: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: Optional[str] = None
    detail: Dict[str, Any] = {}


class PipelineResult(BaseModel):
    version: str = "four-role-v0"
    core_reveal: CoreReveal
    enrichment: Enrichment
    librarian: Optional[LibrarianOutput] = None
    skeptic: Optional[SkepticVerdict] = None
    trace: Dict[str, RoleTrace] = {}
    core_hash_before: str
    core_hash_after: str
    core_identical: bool
    total_calls: int = 0
    total_latency_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
