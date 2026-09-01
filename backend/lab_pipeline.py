"""The Fifth Lab — daily scan pipeline.

Internal flow (adds no new dashboard surface):

    PRIVGATE SCOUT  ─┐
    FIFTHBACK SCOUT ─┼─→ EVIDENCE STORE ─→ PATTERN CHECK ─→ FALSIFIER ─→ FOUNDER DAILY
    CULTURE SCOUT   ─┘

Acquisition boundary
--------------------
Scouts never produce evidence. They ask the registered acquisition provider for
material actually retrieved from a public source, and normalise what comes back.
The model may extract, normalise, classify, cluster, compare and falsify. It may
not invent a source, URL, event, complaint, proverb occurrence, date, organiser
or recurrence count.

That is enforced structurally, not by prompt instruction:

  * every provenance field on a stored record is copied verbatim from the
    acquired item (`_seal_provenance`); model output for those keys is discarded;
  * interpretive fields are scanned for URLs and dates absent from the source
    text (`_scan_for_invented_refs`); a record carrying one is QUARANTINED
    rather than stored as evidence.

With no provider wired, a scan returns `no_verified_source_acquired` and writes
nothing. That is the honest empty state, and it is the default.
"""
from __future__ import annotations

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("fifthback.lab")

TRACKS = ("privgate", "fifthback", "culture")
Track = Literal["privgate", "fifthback", "culture"]

# Hypothesis only. Never canonical, never force-fitted; a case that does not sit
# on an axis is kept as an outlier with the axis left empty (INV-09).
EXPERIMENTAL_AXES = [
    "MEKAN ↔ ANLAM",
    "ZİHİN ↔ İŞ",
    "DUYGU ↔ PARA",
    "BEDEN ↔ İLİŞKİ",
]

# Copied verbatim from the acquired source onto every stored record.
PROVENANCE_FIELDS = (
    "source_url", "source_type", "observed_at", "published_at", "track", "raw_excerpt",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- contracts --
class RawSourceItem(BaseModel):
    """One item as actually retrieved from a public source.

    This is the ONLY way material enters the pipeline. Whoever produces it —
    an in-process provider or an external research runner posting to
    /api/lab/ingest — is asserting that it was really retrieved.
    """
    track: Track
    source_url: str
    source_type: str
    observed_at: str
    published_at: Optional[str] = None
    raw_excerpt: str
    situation: str = ""
    provenance_status: Literal["VERIFIED", "UNVERIFIED"] = "UNVERIFIED"


class EvidenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    track: Track
    # -- provenance, sealed from the source --
    source_url: str
    source_type: str
    observed_at: str
    published_at: Optional[str] = None
    raw_excerpt: str
    situation: str = ""
    provenance_status: Literal["VERIFIED", "UNVERIFIED", "QUARANTINED"] = "UNVERIFIED"
    # -- interpretation, produced by the normaliser --
    normalized: Dict[str, Any] = Field(default_factory=dict)
    normalization_method: Literal["llm", "structural", "none"] = "none"
    needs_interpretation: bool = False
    outlier: bool = False
    candidate_axes: List[str] = Field(default_factory=list)
    integrity_flags: List[str] = Field(default_factory=list)
    ingested_at: str = Field(default_factory=_now)


class ScoutResult(BaseModel):
    track: Track
    status: Literal["ok", "no_verified_source_acquired"]
    provider: str
    acquired: int = 0
    stored: int = 0
    quarantined: int = 0
    records: List[EvidenceRecord] = Field(default_factory=list)
    note: str = ""


class PatternVerdict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str
    track: Track
    relation: Literal["NEW", "REINFORCES", "WEAKENS", "CONTRADICTION"]
    pattern_key: str
    pattern_label: str
    rationale: str
    cross_domain: bool = False
    same_tension_other_domain: List[str] = Field(default_factory=list)
    same_proverb_different_choice: List[str] = Field(default_factory=list)
    different_proverbs_same_tension: List[str] = Field(default_factory=list)
    method: Literal["llm", "structural"] = "structural"
    created_at: str = Field(default_factory=_now)


class CounterexampleSearch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis: str
    falsifier: str                    # written before looking (research brief §4.2)
    scope_examined: str
    examined_count: int
    counterexample_ids: List[str] = Field(default_factory=list)
    outlier_ids: List[str] = Field(default_factory=list)
    verdict: Literal["supported", "rejected", "undetermined"] = "undetermined"
    confidence: Literal["WEAK", "SUPPORTED", "STRONG"] = "WEAK"
    note: str = ""
    created_at: str = Field(default_factory=_now)


class FounderSignal(BaseModel):
    what_changed: str
    strongest_pattern: str
    cross_product_connection: Optional[str] = None
    decision_needed: str
    next_action: str
    independent_cases: int
    domains: int
    counterexamples: int
    outliers: int
    confidence: Literal["WEAK", "SUPPORTED", "STRONG"]


class FounderDaily(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(default_factory=_now)
    status: Literal["ok", "no_verified_source_acquired"]
    signals: List[FounderSignal] = Field(default_factory=list)
    note: str = ""


class ScanReport(BaseModel):
    run_id: str
    started_at: str
    finished_at: str
    status: Literal["ok", "no_verified_source_acquired"]
    provider: str
    scouts: List[ScoutResult]
    pattern_verdicts: List[PatternVerdict]
    falsification: List[CounterexampleSearch]
    founder_daily: FounderDaily


# ------------------------------------------------------- acquisition layer --
class AcquisitionProvider:
    """Source acquisition. Subclass to connect a real search/fetch capability.

    `acquire` must return only material that was actually retrieved. Returning
    model-composed items is a contract violation, not a fallback.
    """
    name = "abstract"
    available = False

    async def acquire(self, track: str, limit: int = 20) -> List[RawSourceItem]:
        raise NotImplementedError


class NullAcquisitionProvider(AcquisitionProvider):
    """Default. No verified web/search/fetch capability is wired in this runtime.

    Acquires nothing, so a scan reports `no_verified_source_acquired` instead of
    inventing evidence.
    """
    name = "none"
    available = False

    async def acquire(self, track: str, limit: int = 20) -> List[RawSourceItem]:
        return []


class IngestQueueProvider(AcquisitionProvider):
    """Holds items posted to /api/lab/ingest by an external research runner.

    Source-agnostic: the scouts cannot tell whether an item arrived here or from
    a live fetch provider, which is what keeps acquisition swappable.
    """
    name = "ingest"
    available = True

    def __init__(self) -> None:
        self._queue: Dict[str, List[RawSourceItem]] = {t: [] for t in TRACKS}

    def offer(self, items: List[RawSourceItem]) -> int:
        for item in items:
            self._queue[item.track].append(item)
        return len(items)

    def pending(self) -> Dict[str, int]:
        return {t: len(v) for t, v in self._queue.items()}

    async def acquire(self, track: str, limit: int = 20) -> List[RawSourceItem]:
        taken, self._queue[track] = self._queue[track][:limit], self._queue[track][limit:]
        return taken


class CompositeProvider(AcquisitionProvider):
    """Tries each provider in order; the first to yield anything wins the track."""
    name = "composite"

    def __init__(self, providers: List[AcquisitionProvider]) -> None:
        self.providers = providers

    @property
    def available(self) -> bool:  # type: ignore[override]
        return any(p.available for p in self.providers)

    async def acquire(self, track: str, limit: int = 20) -> List[RawSourceItem]:
        for p in self.providers:
            if not p.available:
                continue
            items = await p.acquire(track, limit)
            if items:
                self.name = f"composite:{p.name}"
                return items
        return []


INGEST_PROVIDER = IngestQueueProvider()
_PROVIDERS: List[AcquisitionProvider] = [INGEST_PROVIDER, NullAcquisitionProvider()]


def register_provider(provider: AcquisitionProvider, first: bool = True) -> None:
    """Connect a real acquisition capability (search/fetch) without touching scouts."""
    _PROVIDERS.insert(0 if first else len(_PROVIDERS) - 1, provider)


def active_provider() -> CompositeProvider:
    return CompositeProvider(list(_PROVIDERS))


# --------------------------------------------------- provenance enforcement --
_URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.I)
_DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})\b")
_COUNT_RE = re.compile(r"\b\d+\s*(?:kez|kere|defa|times|kişi|katılımcı)\b", re.I)


def _seal_provenance(record: Dict[str, Any], raw: RawSourceItem) -> Dict[str, Any]:
    """Provenance comes from the acquired source. Model values for these keys are dropped."""
    for field in PROVENANCE_FIELDS:
        record[field] = getattr(raw, field)
    return record


def _scan_for_invented_refs(normalized: Dict[str, Any], raw: RawSourceItem) -> List[str]:
    """Flag URLs, dates or recurrence counts in interpretation absent from the source.

    The model is allowed to say what a source means. It is not allowed to
    introduce a reference the source does not contain.
    """
    haystack = f"{raw.raw_excerpt}\n{raw.situation}\n{raw.source_url}\n{raw.published_at or ''}"
    flags: List[str] = []

    def _walk(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return " ".join(_walk(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(_walk(v) for v in value)
        return ""

    text = _walk(normalized)
    for url in set(_URL_RE.findall(text)):
        if url not in haystack:
            flags.append(f"invented_url:{url}")
    for date in set(_DATE_RE.findall(text)):
        if date not in haystack:
            flags.append(f"invented_date:{date}")
    for count in set(_COUNT_RE.findall(text)):
        if count not in haystack:
            flags.append(f"invented_recurrence:{count}")
    return flags


# ------------------------------------------------------------- normalisers --
# Track schemas. A field the source does not support stays None — never guessed.
PRIVGATE_FIELDS = (
    "organizer", "join_mechanics", "visibility", "venue_disclosure",
    "capacity", "coordination_patterns",
)
FIFTHBACK_FIELDS = (
    "declared_state", "lived_state", "owner_ambiguity",
    "next_action_ambiguity", "recurrence",
)
CULTURE_FIELDS = (
    "proverb", "real_situation", "actors", "affected_party", "core_tension",
    "what_happened_before", "action_supported", "function", "competing_proverb",
    "candidate_axes", "direction_a_to_b", "fixed_variable", "adjustable_variable",
)
TRACK_FIELDS = {
    "privgate": PRIVGATE_FIELDS,
    "fifthback": FIFTHBACK_FIELDS,
    "culture": CULTURE_FIELDS,
}


def _structural_normalize(raw: RawSourceItem) -> Dict[str, Any]:
    """No-LLM path. Leaves every interpretive field unfilled rather than guessing.

    An unmeasured thing is displayed as unmeasured (INV-09); the record is stored
    with `needs_interpretation` so it is visible as awaiting a normaliser.
    """
    return {field: None for field in TRACK_FIELDS[raw.track]}


def _looks_unfilled(normalized: Dict[str, Any]) -> bool:
    return not any(v for v in normalized.values())


async def _llm_normalize(raw: RawSourceItem, llm) -> Optional[Dict[str, Any]]:
    """Extract the track schema from the source text only. Returns None on failure."""
    if llm is None:
        return None
    try:
        return await llm(raw)
    except Exception as exc:  # a normaliser failure must not fabricate
        logger.error("lab: normaliser failed for %s: %s", raw.source_url, exc)
        return None


# ------------------------------------------------------------------ scouts --
class Scout:
    """Source-agnostic. Identical for all three tracks apart from its schema."""

    def __init__(self, track: Track) -> None:
        self.track = track

    async def run(self, provider: AcquisitionProvider, llm=None, limit: int = 20) -> ScoutResult:
        raw_items = await provider.acquire(self.track, limit)
        if not raw_items:
            return ScoutResult(
                track=self.track, status="no_verified_source_acquired",
                provider=getattr(provider, "name", "unknown"),
                note="Doğrulanmış kamusal kaynak alınamadı; kayıt üretilmedi.",
            )

        records: List[EvidenceRecord] = []
        quarantined = 0
        for raw in raw_items:
            normalized = await _llm_normalize(raw, llm)
            method: Literal["llm", "structural", "none"] = "llm"
            if normalized is None:
                normalized = _structural_normalize(raw)
                method = "structural"

            flags = _scan_for_invented_refs(normalized, raw)
            payload: Dict[str, Any] = {
                "track": self.track,
                "normalized": normalized,
                "normalization_method": method,
                "needs_interpretation": _looks_unfilled(normalized),
                "integrity_flags": flags,
                "outlier": bool(normalized.get("outlier")) if isinstance(normalized, dict) else False,
                "candidate_axes": [
                    a for a in (normalized.get("candidate_axes") or [])
                    if a in EXPERIMENTAL_AXES
                ] if isinstance(normalized, dict) else [],
                "situation": raw.situation,
                "provenance_status": raw.provenance_status,
            }
            _seal_provenance(payload, raw)

            if flags:
                payload["provenance_status"] = "QUARANTINED"
                quarantined += 1
            records.append(EvidenceRecord(**payload))

        return ScoutResult(
            track=self.track, status="ok",
            provider=getattr(provider, "name", "unknown"),
            acquired=len(raw_items),
            stored=len([r for r in records if r.provenance_status != "QUARANTINED"]),
            quarantined=quarantined,
            records=records,
        )


PRIVGATE_SCOUT = Scout("privgate")
FIFTHBACK_SCOUT = Scout("fifthback")
CULTURE_SCOUT = Scout("culture")
