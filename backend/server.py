from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fifthback")

FEEDBACK_TYPES = ["REQUEST", "TENSION", "PROBLEM", "SUGGESTION", "POSITIVE", "OTHER"]


# ---------------- Models ----------------
class Signal(BaseModel):
    label: str
    evidence: str


class SongRef(BaseModel):
    title: str
    artist: str


class InterpretRequest(BaseModel):
    text: str
    song: Optional[SongRef] = None


class Interpretation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    feedback_type: str
    signals: List[Signal]
    pattern_candidate: str
    song_note: Optional[str] = None


class ConfirmRequest(BaseModel):
    text: str
    song: Optional[SongRef] = None
    interpretation: Interpretation
    corrected: bool = False


class Pattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    feedback_type: str
    frequency: int
    affected_teams: List[str]
    unresolved_for: str
    blocker: str
    status: Literal["NEW", "ACTIVE", "STUCK", "RESOLVED"]
    summary: str = ""
    song_sentiment: Optional[str] = None
    seeded: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------- Feedback Interpreter (AI Worker) ----------------
SYSTEM_PROMPT = """You are the Feedback Interpreter, a careful, humane AI worker inside Fifthback, a privacy-protected corporate feedback system.

Your ONLY job is to reflect back what an employee actually said in their own words. You are a mirror, not a judge.

GOLDEN RULES (never break):
- NEVER force the feedback into an "A vs B" dilemma.
- NEVER diagnose the employee, their personality, or their mental state.
- NEVER invent hidden meaning, motives, or subtext that the text does not directly support.
- Only extract what the literal text supports. If unsure, extract less.

For the employee's text, produce STRICT JSON with these keys:
{
  "feedback_type": one of ["REQUEST","TENSION","PROBLEM","SUGGESTION","POSITIVE","OTHER"],
  "signals": array of 1 to 4 objects, each: {"label": short 2-5 word neutral name of the signal, "evidence": an EXACT verbatim quote copied from the employee's text that supports this signal},
  "pattern_candidate": one short phrase (max ~8 words) naming the recurring theme this could belong to, phrased neutrally,
  "song_note": if a song is provided, one short, gentle sentence on the emotional tone it adds; otherwise null
}

Requirements:
- "evidence" MUST be an exact substring of the employee text (verbatim). Do not paraphrase evidence.
- Between 1 and 4 signals only.
- Keep everything concise and non-clinical.
- Output ONLY the JSON object, no markdown, no commentary."""


def _fallback_interpret(text: str, song: Optional[SongRef]) -> Interpretation:
    """Deterministic extractor so the 60s demo never fails if the LLM is unavailable."""
    lower = text.lower()
    if any(w in lower for w in ["thank", "grateful", "appreciate", "great job", "love", "amazing", "kudos"]):
        ftype = "POSITIVE"
    elif any(w in lower for w in ["could we", "can we", "i'd like", "please", "request", "need access", "want to"]):
        ftype = "REQUEST"
    elif any(w in lower for w in ["what if", "we should", "suggest", "idea", "propose", "maybe we"]):
        ftype = "SUGGESTION"
    elif any(w in lower for w in ["conflict", "tension", "friction", "clash", "vs", "between", "disagree"]):
        ftype = "TENSION"
    elif any(w in lower for w in ["broken", "problem", "issue", "blocked", "can't", "cannot", "fail", "overwhelmed", "too many"]):
        ftype = "PROBLEM"
    else:
        ftype = "OTHER"

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    signals = []
    for s in sentences[:3]:
        label = " ".join(s.split()[:4]).strip(",.").title()
        signals.append(Signal(label=label or "Key point", evidence=s))
    if not signals:
        signals = [Signal(label="Employee note", evidence=text.strip()[:160])]

    pattern = " ".join(text.split()[:6])
    song_note = None
    if song:
        song_note = f"'{song.title}' by {song.artist} adds an emotional layer to how this was expressed."
    return Interpretation(feedback_type=ftype, signals=signals, pattern_candidate=pattern or "General feedback", song_note=song_note)


async def interpret_with_llm(text: str, song: Optional[SongRef]) -> Interpretation:
    if not EMERGENT_LLM_KEY:
        return _fallback_interpret(text, song)
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"interpret-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")

        prompt = f"Employee text:\n\"\"\"\n{text}\n\"\"\""
        if song:
            prompt += f"\n\nOptional song the employee chose to express themselves: \"{song.title}\" by {song.artist}"

        resp = await chat.send_message(UserMessage(text=prompt))
        raw = resp if isinstance(resp, str) else str(resp)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group(0) if match else raw)

        ftype = str(data.get("feedback_type", "OTHER")).upper()
        if ftype not in FEEDBACK_TYPES:
            ftype = "OTHER"
        signals = []
        for s in (data.get("signals") or [])[:4]:
            label = str(s.get("label", "")).strip()
            evidence = str(s.get("evidence", "")).strip()
            if label and evidence:
                signals.append(Signal(label=label, evidence=evidence))
        if not signals:
            return _fallback_interpret(text, song)
        return Interpretation(
            feedback_type=ftype,
            signals=signals,
            pattern_candidate=str(data.get("pattern_candidate", "General feedback")).strip() or "General feedback",
            song_note=data.get("song_note") or (f"'{song.title}' by {song.artist} colors this message." if song else None),
        )
    except Exception as e:
        logger.error(f"LLM interpret failed, using fallback: {e}")
        return _fallback_interpret(text, song)


# ---------------- Routes ----------------
@api_router.get("/")
async def root():
    return {"message": "Fifthback API"}


@api_router.post("/interpret", response_model=Interpretation)
async def interpret(req: InterpretRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Please share what's happening first.")
    return await interpret_with_llm(req.text.strip(), req.song)


@api_router.post("/feedback/confirm")
async def confirm_feedback(req: ConfirmRequest):
    doc = {
        "id": str(uuid.uuid4()),
        "text": req.text,
        "song": req.song.model_dump() if req.song else None,
        "interpretation": req.interpretation.model_dump(),
        "corrected": req.corrected,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.feedback.insert_one({k: v for k, v in doc.items()})

    # Fold the confirmed feedback into the anonymized pattern pool.
    interp = req.interpretation
    candidate = interp.pattern_candidate.strip()
    existing = await db.patterns.find_one(
        {"feedback_type": interp.feedback_type, "seeded": False,
         "title": {"$regex": f"^{re.escape(candidate)}$", "$options": "i"}}
    )
    if existing:
        await db.patterns.update_one({"id": existing["id"]}, {"$inc": {"frequency": 1}})
    else:
        song_sentiment = interp.song_note if req.song else None
        pattern = Pattern(
            title=candidate or "New signal",
            feedback_type=interp.feedback_type,
            frequency=1,
            affected_teams=["Aggregating…"],
            unresolved_for="just now",
            blocker="Awaiting manager triage",
            status="NEW",
            summary=interp.signals[0].evidence if interp.signals else "",
            song_sentiment=song_sentiment,
            seeded=False,
        )
        await db.patterns.insert_one(pattern.model_dump())
    return {"ok": True}


@api_router.get("/patterns", response_model=List[Pattern])
async def get_patterns():
    docs = await db.patterns.find({}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda d: (d.get("seeded", False), d.get("created_at", "")), reverse=True)
    return [Pattern(**d) for d in docs]


SEED_PATTERNS = [
    {
        "title": "Design ↔ Engineering handoff friction",
        "feedback_type": "TENSION", "frequency": 14,
        "affected_teams": ["Design", "Engineering", "Product"],
        "unresolved_for": "2 months", "blocker": "No shared spec ritual before sprint start",
        "status": "STUCK",
        "summary": "Repeated mismatch between delivered designs and what engineering can build in the sprint window.",
        "song_sentiment": "Several submissions paired this with tense, high-pressure tracks.",
        "seeded": True,
    },
    {
        "title": "Meeting overload eroding focus time",
        "feedback_type": "PROBLEM", "frequency": 22,
        "affected_teams": ["Engineering", "Customer Support", "Operations"],
        "unresolved_for": "6 weeks", "blocker": "No agreed no-meeting blocks across teams",
        "status": "ACTIVE",
        "summary": "People report fragmented days with little uninterrupted time for deep work.",
        "song_sentiment": "Often expressed with restless, overwhelmed melodies.",
        "seeded": True,
    },
    {
        "title": "Silent onboarding gaps for new hires",
        "feedback_type": "REQUEST", "frequency": 9,
        "affected_teams": ["People", "Engineering"],
        "unresolved_for": "3 weeks", "blocker": "Onboarding owner not assigned",
        "status": "NEW",
        "summary": "New joiners quietly asking for clearer first-week guidance and access.",
        "song_sentiment": None,
        "seeded": True,
    },
    {
        "title": "Recognition for behind-the-scenes work",
        "feedback_type": "POSITIVE", "frequency": 11,
        "affected_teams": ["Customer Support", "Operations"],
        "unresolved_for": "ongoing", "blocker": "None — reinforce and scale",
        "status": "RESOLVED",
        "summary": "Gratitude threads highlighting quiet, reliable contributors who keep things running.",
        "song_sentiment": "Warm, uplifting tracks accompanied these notes.",
        "seeded": True,
    },
    {
        "title": "Async-first documentation habit",
        "feedback_type": "SUGGESTION", "frequency": 7,
        "affected_teams": ["Product", "Engineering", "Design"],
        "unresolved_for": "4 weeks", "blocker": "Tooling agreement pending",
        "status": "ACTIVE",
        "summary": "Employees suggest defaulting to written decisions so context isn't lost in calls.",
        "song_sentiment": None,
        "seeded": True,
    },
]


@app.on_event("startup")
async def seed_patterns():
    count = await db.patterns.count_documents({"seeded": True})
    if count == 0:
        for p in SEED_PATTERNS:
            await db.patterns.insert_one(Pattern(**p).model_dump())
        logger.info("Seeded demo patterns.")


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
