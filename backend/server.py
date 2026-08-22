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


class ActiveNeed(BaseModel):
    title: str
    detail: str


class Responsibility(BaseModel):
    organizational: List[str] = []
    personal: List[str] = []


class Channel(BaseModel):
    title: str
    detail: str
    tradeoff: str


class Prevalence(BaseModel):
    found: bool = False
    frequency: Optional[int] = None
    affected_teams: Optional[List[str]] = None
    unresolved_for: Optional[str] = None
    matched_title: Optional[str] = None


class InterpretRequest(BaseModel):
    text: str
    song: Optional[SongRef] = None


class Interpretation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    feedback_type: str
    signals: List[Signal]
    pattern_candidate: str
    song_note: Optional[str] = None
    active_needs: List[ActiveNeed] = []
    responsibility: Responsibility = Field(default_factory=Responsibility)
    channels: List[Channel] = []
    safety_note: Optional[str] = None
    prevalence: Optional[Prevalence] = None


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
SYSTEM_PROMPT = """Sen Fifthback adlı, gizliliği korunan bir kurumsal geri bildirim sisteminin içindeki dikkatli ve insancıl bir yapay zekâ çalışanı olan Geri Bildirim Yorumlayıcı'sın.

TEK görevin, bir çalışanın gerçekten söylediğini kendi sözleriyle ona geri yansıtmak ve olası yolları göstermektir. Sen bir aynasın, yargıç değil.

TÜM ÇIKTIYI TÜRKÇE ver (yalnızca "evidence" alanı çalışanın metninden birebir kopyalanır, o metin hangi dildeyse öyle kalır).

ALTIN KURALLAR (asla ihlal etme):
- Geri bildirimi ASLA "A mı, B mi" ikilemine zorlama; ihtiyaçlar aynı anda geçerli olabilir.
- Çalışanı, kişiliğini ya da ruh halini ASLA teşhis etme.
- Metnin doğrudan desteklemediği gizli anlam, saik veya alt metin ASLA uydurma.
- İstatistik, kıyaslama (benchmark) ya da şirket verisi ASLA uydurma.
- Yalnızca metnin desteklediğini çıkar. Emin değilsen daha az çıkar.

Çalışanın metni için ŞU anahtarlarla KATI JSON üret:
{
  "feedback_type": şunlardan biri ["REQUEST","TENSION","PROBLEM","SUGGESTION","POSITIVE","OTHER"],
  "signals": 1 ilâ 4 nesne, her biri: {"label": sinyalin kısa (2-5 kelime) nötr Türkçe adı, "evidence": çalışanın metninden bu sinyali destekleyen BİREBİR alıntı (metindeki gibi, değiştirmeden)},
  "pattern_candidate": bunun ait olabileceği tekrar eden temayı adlandıran kısa Türkçe ifade (en çok ~8 kelime),
  "active_needs": 1 ilâ 4 nesne, her biri: {"title": kısa Türkçe ihtiyaç başlığı, "detail": söylenene dayanan tek cümlelik Türkçe açıklama} — AYNI ANDA geçerli olabilecek birden çok ihtiyaç. Bunları asla bir "ya o ya bu" seçimi gibi sunma.
  "responsibility": {
     "organizational": kurumun/yönetimin üstlenebileceği 1-3 Türkçe madde — suçlama değil, olasılık olarak ifade et,
     "personal": çalışanın kendi alanındaki 1-3 Türkçe seçenek — kusur değil, seçenek olarak ifade et
  },
  "channels": 2 ilâ 4 nesne, her biri: {"title": Türkçe kanal/eylem adı, "detail": Türkçe açıklama, "tradeoff": dürüst bir Türkçe uyarı/dikkat noktası} — olası bir sonraki adımlar.
  "safety_note": metin bir yöneticiyle çatışma, korku, misilleme ya da güvenlik kaygısı ima ediyorsa; buradaki hiçbir adımın kimseyle yüzleşmeyi gerektirmediğini belirten nazik bir Türkçe not; aksi halde null,
  "song_note": bir şarkı verildiyse, kattığı duygusal tona dair kısa ve nazik tek bir Türkçe cümle; aksi halde null
}

Gereklilikler:
- "evidence" çalışanın metninin BİREBİR alt dizesi olmalı (değiştirilmeden).
- En fazla 4 sinyal.
- "channels" içinde kişiye ASLA tek yol olarak yöneticisiyle yüzleşmesini söyleme; her zaman daha güvenli alternatifler de sun.
- Her şeyi kısa ve klinik olmayan bir dille tut.
- YALNIZCA JSON nesnesini ver, markdown veya yorum ekleme."""


def _fallback_interpret(text: str, song: Optional[SongRef]) -> Interpretation:
    """Deterministic Turkish extractor so the demo never fails if the LLM is unavailable."""
    lower = text.lower()
    if any(w in lower for w in ["teşekkür", "tesekkur", "minnet", "harika", "müthiş", "mutesekkir", "takdir"]):
        ftype = "POSITIVE"
    elif any(w in lower for w in ["talep", "rica", "istiyorum", "lütfen", "lutfen", "erişim", "erisim", "ihtiyacım"]):
        ftype = "REQUEST"
    elif any(w in lower for w in ["öneri", "oneri", "belki", "yapsak", "fikir", "önermek"]):
        ftype = "SUGGESTION"
    elif any(w in lower for w in ["gerginlik", "sürtüşme", "surtusme", "çatışma", "catisma", "anlaşamıyor", "gerilim"]):
        ftype = "TENSION"
    elif any(w in lower for w in ["sorun", "problem", "bozuk", "engel", "yapamıyorum", "yetişemiyorum", "çok fazla", "bunal"]):
        ftype = "PROBLEM"
    else:
        ftype = "OTHER"

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    signals = []
    for s in sentences[:3]:
        label = " ".join(s.split()[:4]).strip(",.").capitalize()
        signals.append(Signal(label=label or "Önemli nokta", evidence=s))
    if not signals:
        signals = [Signal(label="Çalışan notu", evidence=text.strip()[:160])]

    needs = [ActiveNeed(title=s.label, detail=s.evidence) for s in signals[:3]]
    responsibility = Responsibility(
        organizational=["Bu konuyu görünür kılıp bir sahiplenen belirlemek."],
        personal=["Neye ihtiyacın olduğunu kendi sözlerinle paylaşmayı sürdürmek."],
    )
    channels = [
        Channel(title="Anonim olarak paylaş",
                detail="Bunu isim vermeden örüntü havuzuna ekle.",
                tradeoff="Doğrudan bir yanıt daha yavaş gelebilir."),
        Channel(title="Bir ekip arkadaşınla konuş",
                detail="Güvendiğin biriyle bunu paylaşmak durumu netleştirebilir.",
                tradeoff="Herkes için uygun ya da güvenli olmayabilir."),
    ]
    song_note = None
    if song:
        song_note = f"'{song.title}' — {song.artist}, bunun nasıl ifade edildiğine duygusal bir katman ekliyor."
    pattern = " ".join(text.split()[:6])
    return Interpretation(
        feedback_type=ftype, signals=signals,
        pattern_candidate=pattern or "Genel geri bildirim",
        song_note=song_note, active_needs=needs,
        responsibility=responsibility, channels=channels, safety_note=None,
    )


async def interpret_with_llm(text: str, song: Optional[SongRef]) -> Interpretation:
    if not EMERGENT_LLM_KEY:
        return _fallback_interpret(text, song)
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"interpret-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")

        prompt = f"Çalışanın metni:\n\"\"\"\n{text}\n\"\"\""
        if song:
            prompt += f"\n\nÇalışanın kendini ifade etmek için seçtiği şarkı: \"{song.title}\" - {song.artist}"

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

        needs = []
        for n in (data.get("active_needs") or [])[:4]:
            t = str(n.get("title", "")).strip()
            d = str(n.get("detail", "")).strip()
            if t:
                needs.append(ActiveNeed(title=t, detail=d))

        resp_data = data.get("responsibility") or {}
        responsibility = Responsibility(
            organizational=[str(x).strip() for x in (resp_data.get("organizational") or []) if str(x).strip()][:3],
            personal=[str(x).strip() for x in (resp_data.get("personal") or []) if str(x).strip()][:3],
        )

        channels = []
        for c in (data.get("channels") or [])[:4]:
            t = str(c.get("title", "")).strip()
            if t:
                channels.append(Channel(
                    title=t,
                    detail=str(c.get("detail", "")).strip(),
                    tradeoff=str(c.get("tradeoff", "")).strip(),
                ))

        interp = _fallback_interpret(text, song)
        return Interpretation(
            feedback_type=ftype,
            signals=signals,
            pattern_candidate=str(data.get("pattern_candidate", "Genel geri bildirim")).strip() or "Genel geri bildirim",
            song_note=data.get("song_note") or (interp.song_note if song else None),
            active_needs=needs or interp.active_needs,
            responsibility=responsibility if (responsibility.organizational or responsibility.personal) else interp.responsibility,
            channels=channels or interp.channels,
            safety_note=(str(data.get("safety_note")).strip() if data.get("safety_note") else None),
        )
    except Exception as e:
        logger.error(f"LLM interpret failed, using fallback: {e}")
        return _fallback_interpret(text, song)


def _match_prevalence(text: str, pattern_candidate: str, patterns: List[dict]) -> Prevalence:
    """Match against real seeded patterns only. Never fabricate numbers.
    Uses 5-char stem prefixes to be robust to Turkish suffixes."""
    def stems(s: str) -> set:
        return {t[:5] for t in re.findall(r'\w+', s.lower(), re.UNICODE) if len(t) >= 5}

    base = stems(f"{text} {pattern_candidate}")
    best, best_score = None, 0
    for p in patterns:
        ptoks = stems(f"{p.get('title','')} {p.get('summary','')}")
        score = len(base & ptoks)
        if score > best_score:
            best, best_score = p, score
    if best and best_score >= 2:
        return Prevalence(
            found=True, frequency=best["frequency"], affected_teams=best["affected_teams"],
            unresolved_for=best["unresolved_for"], matched_title=best["title"],
        )
    return Prevalence(found=False)


# ---------------- Routes ----------------
@api_router.get("/")
async def root():
    return {"message": "Fifthback API"}


@api_router.post("/interpret", response_model=Interpretation)
async def interpret(req: InterpretRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Lütfen önce neler olduğunu paylaş.")
    interp = await interpret_with_llm(req.text.strip(), req.song)
    seeded = await db.patterns.find({"seeded": True}, {"_id": 0}).to_list(200)
    interp.prevalence = _match_prevalence(req.text.strip(), interp.pattern_candidate, seeded)
    return interp


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
            title=candidate or "Yeni sinyal",
            feedback_type=interp.feedback_type,
            frequency=1,
            affected_teams=["Toplanıyor…"],
            unresolved_for="az önce",
            blocker="Yönetici değerlendirmesi bekleniyor",
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
        "title": "Tasarım ↔ Yazılım devir sürtüşmesi",
        "feedback_type": "TENSION", "frequency": 14,
        "affected_teams": ["Tasarım", "Yazılım", "Ürün"],
        "unresolved_for": "2 ay", "blocker": "Sprint başlamadan önce ortak spesifikasyon ritüeli yok",
        "status": "STUCK",
        "summary": "Teslim edilen tasarımlar ile yazılımın sprint süresinde yapabildikleri arasında sürekli uyumsuzluk.",
        "song_sentiment": "Birçok bildirim bunu gergin, yüksek baskılı parçalarla eşleştirdi.",
        "seeded": True,
    },
    {
        "title": "Toplantı yoğunluğu odaklanmayı aşındırıyor",
        "feedback_type": "PROBLEM", "frequency": 22,
        "affected_teams": ["Yazılım", "Müşteri Destek", "Operasyon"],
        "unresolved_for": "6 hafta", "blocker": "Ekipler arası kararlaştırılmış toplantısız zaman blokları yok",
        "status": "ACTIVE",
        "summary": "İnsanlar günlerinin parçalandığını ve derin çalışma için kesintisiz zaman kalmadığını bildiriyor.",
        "song_sentiment": "Çoğunlukla huzursuz, bunalmış ezgilerle ifade edildi.",
        "seeded": True,
    },
    {
        "title": "Yeni çalışanlar için sessiz işe alışma boşlukları",
        "feedback_type": "REQUEST", "frequency": 9,
        "affected_teams": ["İnsan Kaynakları", "Yazılım"],
        "unresolved_for": "3 hafta", "blocker": "İşe alışma sorumlusu atanmadı",
        "status": "NEW",
        "summary": "Yeni başlayanlar ilk hafta için daha net yönlendirme ve erişim talep ediyor.",
        "song_sentiment": None,
        "seeded": True,
    },
    {
        "title": "Perde arkası çalışmanın takdir edilmesi",
        "feedback_type": "POSITIVE", "frequency": 11,
        "affected_teams": ["Müşteri Destek", "Operasyon"],
        "unresolved_for": "sürüyor", "blocker": "Yok — pekiştir ve yaygınlaştır",
        "status": "RESOLVED",
        "summary": "İşleri sessizce yürüten güvenilir katkı sağlayanları öne çıkaran teşekkür mesajları.",
        "song_sentiment": "Bu notlara sıcak, moral veren parçalar eşlik etti.",
        "seeded": True,
    },
    {
        "title": "Önce-yazılı (async) dokümantasyon alışkanlığı",
        "feedback_type": "SUGGESTION", "frequency": 7,
        "affected_teams": ["Ürün", "Yazılım", "Tasarım"],
        "unresolved_for": "4 hafta", "blocker": "Araç konusunda anlaşma bekleniyor",
        "status": "ACTIVE",
        "summary": "Çalışanlar, bağlam görüşmelerde kaybolmasın diye kararların varsayılan olarak yazılı olmasını öneriyor.",
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
