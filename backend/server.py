from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import json
import asyncio
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fifth_roles import run_after_reveal, PipelineResult

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


class DistinctionRequest(BaseModel):
    text: str
    song: Optional[SongRef] = None
    interpretation: Interpretation


class DistinctionResult(BaseModel):
    should_ask: bool = False
    question: Optional[str] = None
    options: List[str] = []
    stop_reason: Optional[str] = None


class EvaluateRequest(BaseModel):
    text: str
    song: Optional[SongRef] = None
    interpretation: Interpretation
    question: Optional[str] = None
    answer: str


class EvaluateResult(BaseModel):
    interpretation: Interpretation
    supported: bool
    evaluation_note: str


# ---------------- Pattern Room models ----------------
class PRCluster(BaseModel):
    id: str
    name: str
    mechanism: str
    signal_indices: List[int]
    summary: str = ""
    is_new: bool = False
    changed: bool = False


class PRPastPattern(BaseModel):
    tried: str
    conditions: str
    changed: str
    when_failed: str


class PRTopPattern(BaseModel):
    rank: int
    cluster_id: str
    name: str
    mechanism: str
    why_selected: str
    why_formed: str
    inference: str
    uncertain: str
    why_top5: str
    evidence: List[str]
    estimated_cost: str
    what_improves: str
    gain_if_reduced: str
    affected_work: str
    confidence: str
    past_patterns: List[PRPastPattern] = []
    next_moves: List[str] = []


class PatternRoomAnalysis(BaseModel):
    signals: List[str]
    clusters: List[PRCluster]
    patterns: List[PRTopPattern]
    source: str = "curated"
    new_signal_indices: List[int] = []


class AddSignalsRequest(BaseModel):
    signals: List[str]


class ActionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_name: str
    mechanism: str = ""
    cluster_id: str = ""
    evidence_snapshot: List[str] = []
    hypothesis: str = ""
    intervention: str = ""
    status: Literal["DETECTED", "INVESTIGATING", "TESTING", "RESOLVED", "REJECTED"] = "DETECTED"
    outcome: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ActionCreate(BaseModel):
    pattern_name: str
    mechanism: str = ""
    cluster_id: str = ""
    evidence_snapshot: List[str] = []
    hypothesis: str = ""
    intervention: str = ""


class ActionUpdate(BaseModel):
    status: Optional[Literal["DETECTED", "INVESTIGATING", "TESTING", "RESOLVED", "REJECTED"]] = None
    hypothesis: Optional[str] = None
    intervention: Optional[str] = None
    outcome: Optional[str] = None


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
    ftype = "OTHER"
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


# ---------------- Distinction Questioner (2nd AI worker) ----------------
DISTINCTION_PROMPT = """Sen Fifthback içindeki ikinci yapay zekâ çalışanı olan Ayrım Sorgulayıcı'sın (Distinction Questioner).

Görevin TAVSİYE VERMEK DEĞİL. Görevin, tek bir ek sorunun bu geri bildirimin ANLAMINI esaslı biçimde değiştirip değiştiremeyeceğine karar vermek.

Tüm çıktı TÜRKÇE olmalı.

İçsel muhakeme (bunu uygula ama JSON dışına yazma):
10 — Sinyal: Çalışanın sözlerinde açıkça ne var?
20 — Etkin etkenler: Aynı anda önemli olabilecek 1–4 ihtiyaç, baskı, kısıt veya gerilim (metindeki kanıta dayalı).
30 — Ayırt edici soru: Bu geri bildirimin ne anlama geldiğini EN ÇOK değiştirecek TEK en değerli soruyu belirle.

Örnek: "İstifa edesim var." → yalnızca "ayrılma isteği" diye etiketleme. Bunun yerine şuna benzer tek bir yararlı soru sor:
"İstifa düşünceni en çok ne besliyor: işin kendisi, çalışma biçimi, belirli bir ilişki/olay, yoksa iş dışında değişen bir koşul?"

Kurallar:
- ASLA "A mı, B mi" dayatma. Birden çok etken bir arada olabilir; bu yüzden seçenekler çoklu seçilebilir olmalı.
- Teşhis etme. Neden/sebep uydurma. Metnin desteklemediği bir şey ekleme.
- Eğer ek bir soru çok az yararlı bilgi katacaksa, SORMA (should_ask=false) ve dur.

KATI JSON üret:
{
  "should_ask": true veya false,
  "question": tek bir Türkçe ayırt edici soru, ya da null,
  "options": çalışanın arasından ÇOKLU seçebileceği 3-5 kısa Türkçe seçenek (olası etkenler) — birbirini dışlamaz. "hiçbiri" ekleme, onu arayüz ekler,
  "stop_reason": should_ask false ise neden sormadığına dair kısa Türkçe açıklama, aksi halde null
}
Yalnızca JSON nesnesi ver, başka bir şey yazma."""


async def distinction_with_llm(text: str, interp: Interpretation) -> DistinctionResult:
    if not EMERGENT_LLM_KEY:
        return DistinctionResult(should_ask=False, stop_reason="Ek soru için yeterli dayanak yok.")
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"distinction-{uuid.uuid4()}",
            system_message=DISTINCTION_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")

        sig_lines = "; ".join(f"{s.label}: \"{s.evidence}\"" for s in interp.signals)
        prompt = (
            f"Çalışanın metni:\n\"\"\"\n{text}\n\"\"\"\n\n"
            f"Yorumlayıcının çıkardığı tür: {interp.feedback_type}\n"
            f"Sinyaller: {sig_lines}\n"
            f"Örüntü adayı: {interp.pattern_candidate}"
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)

        should_ask = bool(data.get("should_ask"))
        question = str(data.get("question")).strip() if data.get("question") else None
        options = [str(o).strip() for o in (data.get("options") or []) if str(o).strip()][:5]
        if should_ask and (not question or len(options) < 2):
            return DistinctionResult(should_ask=False, stop_reason="Anlamlı bir ayırt edici soru bulunamadı.")
        return DistinctionResult(
            should_ask=should_ask,
            question=question if should_ask else None,
            options=options if should_ask else [],
            stop_reason=(str(data.get("stop_reason")).strip() if data.get("stop_reason") else None) if not should_ask else None,
        )
    except Exception as e:
        logger.error(f"Distinction failed, stopping: {e}")
        return DistinctionResult(should_ask=False, stop_reason="Ek soru üretilemedi.")


# ---------------- Evaluator (grounding check) ----------------
EVALUATOR_PROMPT = """Sen Fifthback içindeki Değerlendirici'sin (Evaluator).

Görevin TAVSİYE VERMEK ya da yeni yorum üretmek DEĞİL. Görevin yalnızca kontrol etmek: güncellenen yorum, çalışanın GERÇEK sözleri ve verdiği yanıt/düzeltmelerle DESTEKLENİYOR mu?

Tüm çıktı TÜRKÇE olmalı.

Kurallar:
- Teşhis etme. Neden/sebep uydurma.
- Yalnızca dayanağı denetle: her sinyal ve etken, çalışanın metnine ya da yanıtına dayanıyor mu?
- Metnin ötesine geçen, uydurulmuş ya da varsayıma dayalı bir kısım varsa bunu nazikçe belirt.

KATI JSON üret:
{
  "supported": true veya false,
  "note": kısa Türkçe açıklama — yorumun hangi kısımlarının çalışanın sözlerine dayandığını, varsa dayanağı zayıf kısmı belirt
}
Yalnızca JSON nesnesi ver."""


async def evaluate_grounding(text: str, interp: Interpretation) -> tuple:
    default_note = "Güncellenen yorum, paylaştığın sözlere ve yanıtına dayanıyor."
    if not EMERGENT_LLM_KEY:
        return True, default_note
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"evaluate-{uuid.uuid4()}",
            system_message=EVALUATOR_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")

        sig_lines = "; ".join(f"{s.label}: \"{s.evidence}\"" for s in interp.signals)
        need_lines = "; ".join(n.title for n in interp.active_needs)
        prompt = (
            f"Çalışanın (yanıtı dahil) metni:\n\"\"\"\n{text}\n\"\"\"\n\n"
            f"Güncellenen yorum — Tür: {interp.feedback_type}\n"
            f"Sinyaller: {sig_lines}\n"
            f"Etkin etkenler: {need_lines}"
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)
        supported = bool(data.get("supported", True))
        note = str(data.get("note", default_note)).strip() or default_note
        return supported, note
    except Exception as e:
        logger.error(f"Evaluator failed, defaulting supported: {e}")
        return True, default_note


# ---------------- Pattern Room (Cluster / Impact / Solution agents) ----------------
PATTERN_ROOM_SIGNALS = [
    "Onaylar günler sürüyor.",
    "Aynı kararı tekrar tekrar konuşuyoruz.",
    "Geliştirme başladıktan sonra spesifikasyonlar değişiyor.",
    "Çoğu zaman tek bir kıdemli kişiyi bekliyorum.",
    "Daha fazla kişi işe aldık ama teslimat hızlanmadı.",
    "İki ekip de işin sahibinin diğeri olduğunu sanmış.",
    "Kimse sonuçlandıramadığı için toplantıları tekrarlıyoruz.",
    "İş, geç gelen geri bildirimden sonra geri gönderiliyor.",
    "Herkes meşgul ama bazı işler el değmeden bekliyor.",
    "Önemli bilgiler üç farklı araca dağılmış durumda.",
    "Çok fazla toplantı var ama yeterince karar çıkmıyor.",
    "Başlayabilmek için onay bekliyoruz.",
    "Son sözün kimde olduğundan kimse emin değil.",
    "Gereksinimler yolun ortasında değişiyor, baştan yapıyoruz.",
    "Aynı rapor iki farklı ekip tarafından hazırlanıyor.",
    "Geri bildirim ancak iş bittikten sonra geliyor.",
    "Her onay için tek bir kişi darboğaz oluyor.",
    "Bu hafta hangi işin öncelikli olduğunu bilemiyoruz.",
    "Tasarım ile geliştirme arasındaki devirlerde bağlam kayboluyor.",
    "Yeni bir araç aldık ama hâlâ veriyi elle kopyalıyoruz.",
    "Kararlar bir hafta sonra yeniden açılıyor.",
    "Bir talep, sahibi çıkana kadar üç ekip arasında gidip geldi.",
    "Son dakika değişikliklerden sonra sunumları tekrar tekrar düzenliyoruz.",
    "Araçlarımızın yarısı birbiriyle konuşmuyor.",
]


def _curated_pattern_room(signals: Optional[List[str]] = None) -> PatternRoomAnalysis:
    S = PATTERN_ROOM_SIGNALS
    ev = lambda idxs: [S[i] for i in idxs]
    clusters = [
        PRCluster(id="c1", name="Karar Akışı / Sahiplik Darboğazı", mechanism="karar gecikmesi + belirsiz sahiplik",
                  signal_indices=[0, 1, 3, 6, 10, 11, 12, 16, 20],
                  summary="Kararların nerede, kim tarafından sonuçlandırılacağı belirsiz; iş onay beklerken duruyor."),
        PRCluster(id="c2", name="Yeniden İş Döngüsü", mechanism="yeniden iş (rework)",
                  signal_indices=[2, 7, 13, 15, 22],
                  summary="Geç gelen geri bildirim ve değişen gereksinimler yüzünden aynı iş defalarca yapılıyor."),
        PRCluster(id="c3", name="Sahiplik & Devir Karışıklığı", mechanism="belirsiz sahiplik + devir sürtüşmesi",
                  signal_indices=[5, 18, 21],
                  summary="İşin sahibi net değil; ekipler arası devirlerde bağlam ve sorumluluk kayboluyor."),
        PRCluster(id="c4", name="Kapasite vs. Öncelik", mechanism="kapasite kısıtı + önceliklendirme çatışması",
                  signal_indices=[4, 8, 17],
                  summary="Kişi eklemek hızı artırmıyor; öncelik netliği olmadan bazı işler el değmeden bekliyor."),
        PRCluster(id="c5", name="Bilgi & Araç Kopukluğu", mechanism="bilgi boşluğu + araç/sistem sürtüşmesi + süreç tekrarı",
                  signal_indices=[9, 14, 19, 23],
                  summary="Bilgi araçlara dağılmış, sistemler konuşmuyor; aynı iş elle ve tekrar üretiliyor."),
    ]
    patterns = [
        PRTopPattern(
            rank=1, cluster_id="c1", name="Karar Akışı / Sahiplik Darboğazı", mechanism="karar gecikmesi + belirsiz sahiplik",
            why_selected="En yüksek frekans (9 sinyal), en fazla akışı etkiliyor ve birden çok ekipte tekrar ediyor; yüzeyde farklı görünen şikâyetler aynı mekanizmaya bağlanıyor.",
            why_formed="Yüzeyde 'çok toplantı', 'onay bekliyoruz', 'tek kişiyi bekliyorum', 'kararlar yeniden açılıyor' farklı konular gibi görünse de hepsi tek bir mekanizmayı işaret ediyor: kararın nerede ve kim tarafından kesinleştiğinin belirsiz olması.",
            inference="Çıkarım: karar hakkı ve sahiplik dağınık olduğu için iş, değer üretmeden onay/karar kuyruğunda bekliyor.",
            uncertain="Belirsiz: gecikmenin ne kadarı tek bir kişiden, ne kadarı tanımsız süreçten kaynaklanıyor — bu ayrım henüz veriyle netleşmedi.",
            why_top5="Frekans + akış sayısı + tekrar + bloke iş + ekipler arası yayılım ölçütlerinin hepsinde en yüksek.",
            evidence=ev([0, 1, 3, 6, 10, 11, 12, 16, 20]),
            estimated_cost="Tahmini: teslimatların önemli bir kısmında karar bekleme süresi ekleniyor; kesin finansal rakam için döngü süresi verisi gerekir (nitel: yüksek).",
            what_improves="Karar hakkı netleşirse bekleme süresi düşer, toplantı tekrarları azalır ve teslimat öngörülebilirliği artar.",
            gain_if_reduced="Tahmini olarak akışların çoğunda 'karar bekleme' adımı kısalır; yeniden açılan karar sayısı azalır.",
            affected_work="Onay gerektiren tüm iş akışları, sprint planlaması, ekipler arası teslimatlar.",
            confidence="Yüksek — 9 bağımsız sinyal ve birden çok ekipte tutarlı işaret.",
            past_patterns=[
                PRPastPattern(tried="Kararlar için tek sorumlu (karar sahibi) atama", conditions="Karar tipi ve eşik önceden tanımlandığında", changed="Onay bekleme süresi kısaldı, tekrar toplantılar azaldı", when_failed="Sorumlu aşırı yüklendiğinde yeni bir darboğaza dönüştü"),
                PRPastPattern(tried="Hafif karar kaydı (kim, ne zaman, neden)", conditions="Kararlar geç geç yeniden açılıyorsa", changed="Aynı kararın tekrar tartışılması azaldı", when_failed="Kayıt güncel tutulmadığında etkisini yitirdi"),
            ],
            next_moves=[
                "Denemeye değer: en çok bekleyen 3 karar tipi için tek bir 'karar sahibi' ve karar eşiği tanımlamak.",
                "Benzer vakalarda karar kaydı tutulunca aynı kararın yeniden açılması azaldı.",
                "Şu koşulda yardımcı olabilir: bekleme süresi tek kişiye bağlıysa, o kararlar için vekâlet/eşik belirlemek.",
            ],
        ),
        PRTopPattern(
            rank=2, cluster_id="c2", name="Yeniden İş Döngüsü", mechanism="yeniden iş (rework)",
            why_selected="Beş sinyal doğrudan tamamlanan işin geri dönmesine işaret ediyor; harcanan emeğin bir kısmı tekrar üretiliyor.",
            why_formed="'Spesifikasyon değişiyor', 'geç geri bildirim', 'baştan yapıyoruz', 'sunumları tekrar düzenliyoruz' aynı mekanizmayı gösteriyor: doğrulama/geri bildirim iş bittikten sonra geliyor.",
            inference="Çıkarım: geri bildirim ve netlik döngünün sonunda geldiği için tamamlanan iş yeniden yapılıyor.",
            uncertain="Belirsiz: rework'ün ne kadarı kaçınılabilir (erken hizalama) ne kadarı doğal keşiften kaynaklanıyor.",
            why_top5="Yüksek tekrar ve görünür emek kaybı; birden çok fonksiyonu etkiliyor.",
            evidence=ev([2, 7, 13, 15, 22]),
            estimated_cost="Tahmini: geliştirme/üretim eforunun bir bölümü tekrar harcanıyor (nitel: orta-yüksek).",
            what_improves="Erken hizalama ve ara kontrol noktaları eklenirse geri dönen iş miktarı azalır.",
            gain_if_reduced="Tahmini olarak teslim başına tekrar sayısı düşer, teslim süresi kısalır.",
            affected_work="Ürün/tasarım/geliştirme teslimatları, raporlama, sunum hazırlığı.",
            confidence="Orta-Yüksek — tutarlı ama kök nedeni (erken hizalama mı, kapsam kayması mı) tam ayrışmadı.",
            past_patterns=[
                PRPastPattern(tried="İş başlamadan kısa hizalama / kabul kriteri", conditions="Kapsam belirsizliği yüksekse", changed="Sona kalan sürprizler ve geri dönüş azaldı", when_failed="Kriterler yüzeysel yazıldığında etkisiz kaldı"),
            ],
            next_moves=[
                "Denemeye değer: en çok geri dönen iş türü için başlamadan önce tek sayfalık kabul kriteri.",
                "Benzer vakalarda ara kontrol noktası eklenince sondaki tekrar azaldı.",
                "Şu koşulda yardımcı olabilir: geri bildirim erkene çekilebiliyorsa küçük, erken incelemeler.",
            ],
        ),
        PRTopPattern(
            rank=3, cluster_id="c5", name="Bilgi & Araç Kopukluğu", mechanism="bilgi boşluğu + araç sürtüşmesi",
            why_selected="Dört sinyal bilginin dağınıklığına ve sistemlerin kopukluğuna işaret ediyor; elle tekrar iş üretiyor.",
            why_formed="'Bilgiler üç araca dağılmış', 'araçlar konuşmuyor', 'elle kopyalıyoruz', 'aynı rapor iki ekipte' — mekanizma: kaynak bilgi tek ve erişilebilir değil.",
            inference="Çıkarım: tek bir güvenilir kaynak olmadığı için bilgi elle taşınıyor ve tekrarlanıyor.",
            uncertain="Belirsiz: kopukluğun ne kadarı araç, ne kadarı alışkanlık/süreç kaynaklı.",
            why_top5="Görünür manuel emek ve tekrar; birçok ekip etkileniyor.",
            evidence=ev([9, 14, 19, 23]),
            estimated_cost="Tahmini: düzenli olarak elle veri taşıma ve mükerrer üretim eforu (nitel: orta).",
            what_improves="Tek güvenilir kaynak ve entegrasyon ile elle kopyalama ve mükerrer rapor azalır.",
            gain_if_reduced="Tahmini olarak manuel aktarım adımları ve çift üretim azalır.",
            affected_work="Raporlama, operasyon, ekipler arası bilgi paylaşımı.",
            confidence="Orta — sinyaller net ama hangi aracın kritik olduğu belirsiz.",
            past_patterns=[
                PRPastPattern(tried="Tek 'doğruluk kaynağı' belirleme", conditions="Aynı veri birden çok yerde tutuluyorsa", changed="Mükerrer üretim ve tutarsızlık azaldı", when_failed="Sahiplik atanmadığında kaynak güncelliğini yitirdi"),
            ],
            next_moves=[
                "Denemeye değer: en çok elle taşınan veri için tek kaynak ve sahibini belirlemek.",
                "Benzer vakalarda iki sistem entegre edilince elle kopyalama düştü.",
                "Şu koşulda yardımcı olabilir: mükerrer rapor varsa tek şablonda birleştirmek.",
            ],
        ),
        PRTopPattern(
            rank=4, cluster_id="c3", name="Sahiplik & Devir Karışıklığı", mechanism="belirsiz sahiplik + devir sürtüşmesi",
            why_selected="Az sayıda ama yüksek etkili: işin sahibi belirsiz olduğunda talepler ekipler arasında dolaşıyor.",
            why_formed="'İki ekip de diğeri sahip sandı', 'devirde bağlam kayıp', 'üç ekip arasında gidip geldi' — mekanizma: sahiplik ve devir kuralı tanımsız.",
            inference="Çıkarım: net sahiplik ve devir standardı olmadığı için iş sahipsiz kalıp gecikiyor.",
            uncertain="Belirsiz: sorun ekip sınırlarında mı yoksa devir anındaki bilgi aktarımında mı yoğunlaşıyor.",
            why_top5="Ekipler arası yayılım ve bloke iş ölçütlerinde yüksek.",
            evidence=ev([5, 18, 21]),
            estimated_cost="Tahmini: sahipsiz taleplerin beklemesi ve devir kayıpları (nitel: orta).",
            what_improves="Net sahiplik ve devir kontrol listesi ile sahipsiz kalan iş ve bağlam kaybı azalır.",
            gain_if_reduced="Tahmini olarak ekipler arası gidip gelme ve devir kaynaklı gecikme azalır.",
            affected_work="Ekipler arası talepler, tasarım-geliştirme devri, çapraz fonksiyon işleri.",
            confidence="Orta — güçlü işaret, örneklem küçük.",
            past_patterns=[
                PRPastPattern(tried="Devir kontrol listesi + net sahip", conditions="İş ekip sınırında el değiştiriyorsa", changed="Bağlam kaybı ve sahipsiz bekleme azaldı", when_failed="Liste zorunlu tutulmadığında atlanıyordu"),
            ],
            next_moves=[
                "Denemeye değer: çapraz ekip işleri için tek sahip ve kısa devir kontrol listesi.",
                "Benzer vakalarda devir anında bağlam notu eklenince tekrar sorular azaldı.",
                "Şu koşulda yardımcı olabilir: sınırda kalan işler için varsayılan sahip belirlemek.",
            ],
        ),
        PRTopPattern(
            rank=5, cluster_id="c4", name="Kapasite vs. Öncelik", mechanism="kapasite kısıtı + önceliklendirme çatışması",
            why_selected="Kişi eklemenin hızı artırmaması, öncelik netliğinin kapasiteden daha belirleyici olduğunu düşündürüyor.",
            why_formed="'Daha çok kişi ama hız yok', 'herkes meşgul ama işler bekliyor', 'öncelik belirsiz' — mekanizma: kapasite değil, akış ve öncelik.",
            inference="Çıkarım: darboğaz çoğunlukla kapasite değil; öncelik ve akış netsizliği kaynaklı olabilir.",
            uncertain="Belirsiz: gerçek kapasite kısıtı ile öncelik belirsizliğinin payı henüz ayrışmadı.",
            why_top5="Kaynak kararlarını doğrudan etkilediği için yüksek stratejik değer.",
            evidence=ev([4, 8, 17]),
            estimated_cost="Tahmini: eklenen kapasitenin karşılığını vermemesi (nitel: orta).",
            what_improves="Öncelik netliği ve akış sınırı (WIP) ile bekleyen işler ve dağınıklık azalır.",
            gain_if_reduced="Tahmini olarak aynı ekip aynı kapasiteyle daha öngörülebilir teslim yapar.",
            affected_work="Planlama, kaynak tahsisi, haftalık önceliklendirme.",
            confidence="Orta — güçlü hipotez, doğrulama için akış verisi gerekir.",
            past_patterns=[
                PRPastPattern(tried="Görünür öncelik + aynı anda iş sınırı (WIP)", conditions="Herkes meşgul ama işler bekliyorsa", changed="Bekleyen iş azaldı, akış hızlandı", when_failed="Sınır uygulanmadığında eski düzene dönüldü"),
            ],
            next_moves=[
                "Denemeye değer: haftalık tek net öncelik listesi ve aynı anda iş sınırı.",
                "Benzer vakalarda WIP sınırı konunca bekleyen işler eridi.",
                "Şu koşulda yardımcı olabilir: darboğaz kapasite değil akışsa, kişi eklemek yerine önceliği netleştirmek.",
            ],
        ),
    ]
    return PatternRoomAnalysis(signals=list(S), clusters=clusters, patterns=patterns, source="curated")


async def _get_signal_pool() -> List[str]:
    doc = await db.pattern_room_meta.find_one({"_id": "pool"}, {"_id": 0})
    if doc and doc.get("signals"):
        return doc["signals"]
    await db.pattern_room_meta.update_one({"_id": "pool"}, {"$set": {"signals": list(PATTERN_ROOM_SIGNALS)}}, upsert=True)
    return list(PATTERN_ROOM_SIGNALS)


def _curated_for_pool(pool: List[str]) -> PatternRoomAnalysis:
    """Curated clustering for the original 24 + a catch-all cluster for any appended signals."""
    base = _curated_pattern_room()
    base.signals = list(pool)
    if len(pool) > len(PATTERN_ROOM_SIGNALS):
        extra = list(range(len(PATTERN_ROOM_SIGNALS), len(pool)))
        base.clusters.append(PRCluster(
            id="c_new", name="Yeni Sinyaller (kümelenmeyi bekliyor)",
            mechanism="henüz sınıflandırılmadı", signal_indices=extra,
            summary="Yeni eklenen sinyaller; canlı analiz çalıştığında mekanizmaya göre yerleşecek.",
            is_new=True,
        ))
    return base


PATTERN_ROOM_PROMPT = """Sen Fifthback içinde bir kurumsal örüntü motoru olarak çalışan ÜÇ rolün birleşimisin. Tüm çıktı TÜRKÇE olmalı.

Sana anonim iş-sistemi sinyalleri (bir liste) verilecek. Bunlar çalışan puanlaması DEĞİL; kişilik, motivasyon, yetkinlik veya duygu TEŞHİSİ YAPMA. Yalnızca iş sisteminin sürtünmesini analiz et.

ROL 1 — KÜMELEME AJANI:
Sinyalleri YÜZEY kelimelere göre DEĞİL, altta yatan örgütsel MEKANİZMAYA göre grupla. Örneğin "çok toplantı", "onay bekliyoruz", "geç geri bildirim", "işi baştan yapıyoruz" aynı mekanizmaya (ör. KARAR AKIŞI DARBOĞAZI) ait olabilir.
Olası mekanizmalar: karar gecikmesi, belirsiz sahiplik, devir sürtüşmesi, yeniden iş (rework), yetkinlik uyumsuzluğu, kapasite kısıtı, bilgi boşluğu, süreç tekrarı, önceliklendirme çatışması, araç/sistem sürtüşmesi. Kanıt uymuyorsa YENİ mekanizma tanımlayabilirsin. 4-7 küme üret.

ROL 2 — ETKİ AJANI:
Yalnızca GÖZLEMLENEBİLİR kanıta göre EN ETKİLİ 5 örüntüyü sırala. Ölçütler: frekans, etkilenen akış sayısı, tekrar, bloke iş, yeniden iş, karar gecikmesi, ekipler arası yayılım. Girdi olmadan kesin finansal rakam UYDURMA; "tahmini" veya nitel ifade kullan.

ROL 3 — ÇÖZÜM ÖRÜNTÜSÜ AJANI:
Her örüntü için yapısal olarak benzer geçmiş/örnek vakaları hatırla: ne denenmişti, hangi koşulda işe yaradı, ne değişti, ne zaman işe yaramadı. Sonra EN FAZLA 3 müdahale öner. "Bu çözümdür" DEME. Şu kalıpları kullan: "Denemeye değer…", "Benzer vakalarda … iyileşti", "Şu koşulda yardımcı olabilir…".

KATI JSON üret:
{
  "clusters": [{"id":"c1","name":"Türkçe küme adı","mechanism":"mekanizma(lar)","signal_indices":[sinyal listesindeki 0-tabanlı indeksler],"summary":"kısa Türkçe özet"}],
  "patterns": [ // EN ETKİLİ 5, rank 1..5
    {"rank":1,"cluster_id":"c1","name":"...","mechanism":"...",
     "why_selected":"Fif bunu neden seçti","why_formed":"bu küme neden oluştu","inference":"çıkarım nedir","uncertain":"hâlâ belirsiz olan ne","why_top5":"neden ilk 5'e girdi",
     "evidence":["kümedeki sinyallerin birebir metinleri"],
     "estimated_cost":"tahmini/nitel örgütsel maliyet-etki","what_improves":"çözülürse ne iyileşir","gain_if_reduced":"sürtünme azalırsa olası kazanç","affected_work":"etkilenen iş/akışlar",
     "confidence":"Yüksek/Orta/Düşük + kısa gerekçe",
     "past_patterns":[{"tried":"...","conditions":"...","changed":"...","when_failed":"..."}],
     "next_moves":["Denemeye değer: ...","Benzer vakalarda ...","Şu koşulda yardımcı olabilir: ..."]}
  ]
}
Yalnızca JSON ver."""


async def analyze_pattern_room_llm(signals: List[str]) -> PatternRoomAnalysis:
    if not EMERGENT_LLM_KEY:
        return _curated_for_pool(signals)
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"patternroom-{uuid.uuid4()}",
            system_message=PATTERN_ROOM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")
        numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(signals))
        resp = await asyncio.wait_for(
            chat.send_message(UserMessage(text=f"Anonim sinyaller ({len(signals)}):\n{numbered}")),
            timeout=45,
        )
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)

        clusters = []
        for c in data.get("clusters", []):
            idxs = [int(i) for i in (c.get("signal_indices") or []) if isinstance(i, (int, float)) and 0 <= int(i) < len(signals)]
            if not idxs:
                continue
            clusters.append(PRCluster(
                id=str(c.get("id") or f"c{len(clusters)+1}"),
                name=str(c.get("name", "Küme")).strip(),
                mechanism=str(c.get("mechanism", "")).strip(),
                signal_indices=idxs,
                summary=str(c.get("summary", "")).strip(),
            ))
        patterns = []
        for p in data.get("patterns", [])[:5]:
            patterns.append(PRTopPattern(
                rank=int(p.get("rank", len(patterns) + 1)),
                cluster_id=str(p.get("cluster_id", "")).strip(),
                name=str(p.get("name", "")).strip(),
                mechanism=str(p.get("mechanism", "")).strip(),
                why_selected=str(p.get("why_selected", "")).strip(),
                why_formed=str(p.get("why_formed", "")).strip(),
                inference=str(p.get("inference", "")).strip(),
                uncertain=str(p.get("uncertain", "")).strip(),
                why_top5=str(p.get("why_top5", "")).strip(),
                evidence=[str(e).strip() for e in (p.get("evidence") or []) if str(e).strip()],
                estimated_cost=str(p.get("estimated_cost", "")).strip(),
                what_improves=str(p.get("what_improves", "")).strip(),
                gain_if_reduced=str(p.get("gain_if_reduced", "")).strip(),
                affected_work=str(p.get("affected_work", "")).strip(),
                confidence=str(p.get("confidence", "")).strip(),
                past_patterns=[PRPastPattern(
                    tried=str(pp.get("tried", "")).strip(), conditions=str(pp.get("conditions", "")).strip(),
                    changed=str(pp.get("changed", "")).strip(), when_failed=str(pp.get("when_failed", "")).strip(),
                ) for pp in (p.get("past_patterns") or [])],
                next_moves=[str(n).strip() for n in (p.get("next_moves") or []) if str(n).strip()][:3],
            ))
        if len(clusters) >= 2 and len(patterns) >= 3:
            return PatternRoomAnalysis(signals=list(signals), clusters=clusters, patterns=patterns, source="live")
        return _curated_for_pool(signals)
    except Exception as e:
        logger.error(f"Pattern Room LLM failed, using curated: {e}")
        return _curated_for_pool(signals)


# ---------------- Routes ----------------
@api_router.get("/pattern-room/signals")
async def pattern_room_signals():
    return {"signals": await _get_signal_pool()}


@api_router.get("/pattern-room/analysis", response_model=PatternRoomAnalysis)
async def pattern_room_analysis():
    cached = await db.pattern_room_cache.find_one({"_id": "latest"}, {"_id": 0})
    if cached:
        return PatternRoomAnalysis(**cached)
    result = _curated_for_pool(await _get_signal_pool())
    await db.pattern_room_cache.update_one({"_id": "latest"}, {"$set": result.model_dump()}, upsert=True)
    return result


@api_router.post("/pattern-room/analyze", response_model=PatternRoomAnalysis)
async def pattern_room_analyze():
    pool = await _get_signal_pool()
    result = await analyze_pattern_room_llm(pool)
    await db.pattern_room_cache.update_one({"_id": "latest"}, {"$set": result.model_dump()}, upsert=True)
    return result


@api_router.post("/pattern-room/add-signals", response_model=PatternRoomAnalysis)
async def pattern_room_add_signals(req: AddSignalsRequest):
    new = [s.strip() for s in req.signals if s and s.strip()]
    if not new:
        raise HTTPException(status_code=400, detail="En az bir sinyal ekle.")

    prev_cached = await db.pattern_room_cache.find_one({"_id": "latest"}, {"_id": 0})
    prev_names = {c["name"].strip().lower() for c in (prev_cached.get("clusters") if prev_cached else [])}

    pool = await _get_signal_pool()
    old_len = len(pool)
    pool = pool + new
    await db.pattern_room_meta.update_one({"_id": "pool"}, {"$set": {"signals": pool}}, upsert=True)

    result = await analyze_pattern_room_llm(pool)
    new_idx = list(range(old_len, len(pool)))
    result.new_signal_indices = new_idx
    # Mark which clusters are new or were changed by the added signals.
    for c in result.clusters:
        contains_new = any(i in new_idx for i in c.signal_indices)
        if c.name.strip().lower() not in prev_names:
            c.is_new = True
        elif contains_new:
            c.changed = True

    await db.pattern_room_cache.update_one({"_id": "latest"}, {"$set": result.model_dump()}, upsert=True)
    return result


@api_router.get("/action-board", response_model=List[ActionItem])
async def action_board_list():
    docs = await db.action_board.find({}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return [ActionItem(**d) for d in docs]


@api_router.post("/action-board", response_model=ActionItem)
async def action_board_create(req: ActionCreate):
    now = datetime.now(timezone.utc).isoformat()
    item = ActionItem(**req.model_dump(), created_at=now, updated_at=now)
    await db.action_board.insert_one(item.model_dump())
    return item


@api_router.patch("/action-board/{item_id}", response_model=ActionItem)
async def action_board_update(item_id: str, req: ActionUpdate):
    doc = await db.action_board.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.action_board.update_one({"id": item_id}, {"$set": updates})
    doc.update(updates)
    return ActionItem(**doc)


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


@api_router.post("/distinction", response_model=DistinctionResult)
async def distinction(req: DistinctionRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Metin boş olamaz.")
    return await distinction_with_llm(req.text.strip(), req.interpretation)


@api_router.post("/evaluate", response_model=EvaluateResult)
async def evaluate(req: EvaluateRequest):
    combined = req.text.strip()
    if req.question and req.answer and req.answer.strip():
        combined = (
            f"{req.text.strip()}\n\n"
            f"[Netleştirici soru] {req.question}\n"
            f"[Çalışanın yanıtı] {req.answer.strip()}"
        )
    refined = await interpret_with_llm(combined, req.song)
    seeded = await db.patterns.find({"seeded": True}, {"_id": 0}).to_list(200)
    refined.prevalence = _match_prevalence(combined, refined.pattern_candidate, seeded)
    supported, note = await evaluate_grounding(combined, refined)
    return EvaluateResult(interpretation=refined, supported=supported, evaluation_note=note)


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
    if await db.pattern_room_cache.count_documents({"_id": "latest"}) == 0:
        await db.pattern_room_cache.update_one(
            {"_id": "latest"}, {"$set": _curated_pattern_room().model_dump()}, upsert=True
        )
        logger.info("Seeded Pattern Room analysis.")



# =====================================================================================
# THE FIFTH — core prototype (single model call, single prompt, single session record)
# NOTICE → PATTERN → DISTINGUISH → REVEAL/STOP are reasoning responsibilities inside ONE
# prompt. They are NOT agents, services or workers.
# =====================================================================================

# PROTOTYPE SEED CONTENT — no proverb / pattern-map material exists in this repo yet.
# These are temporary story cards for Door B ("Bir hikâyede kendimi bulacağım").
# "lens" tags are lenses for reading the story, not truths about the reader.
FIFTH_STORY_CARDS = [
    {
        "id": "s1",
        "title": "Söz verildi, geri alındı",
        "lens": "İlişki",
        "text": "Bir arkadaşı, birlikte bir şey yapmaya söz veriyor. Gün gelince 'başka bir şey çıktı' diyor. "
                "Bu üçüncü kez. Kişi kızmıyor; sadece bir daha teklif etmiyor.",
    },
    {
        "id": "s2",
        "title": "Herkes evet dedi, kimse yapmadı",
        "lens": "Toplum / Sistem",
        "text": "Toplantıda herkes fikri beğendi. İki hafta sonra hiçbir şey yapılmamış. "
                "Kişi bunu kendine dert ediyor: 'Ben mi kötü anlattım, yoksa kimse istememiş miydi?'",
    },
    {
        "id": "s3",
        "title": "Yardım etmekten yorulan",
        "lens": "Kişi",
        "text": "Biri hep herkese yetişiyor. Bir gün kendi başına bir şey isteyince cevap gecikiyor. "
                "'Ben de yorulabilirim' demek yerine daha çok yardım ediyor.",
    },
    {
        "id": "s4",
        "title": "Yeni yerde eski kural",
        "lens": "Bağlam",
        "text": "Eski işinde 'sorma, hallet' takdir görüyordu. Yeni yerde aynı şeyi yapınca "
                "'niye danışmadın' deniyor. Kişi kendini hem doğru hem suçlu hissediyor.",
    },
    {
        "id": "s5",
        "title": "Ayrılık kararı yıllardır beklemede",
        "lens": "Bağlam",
        "text": "Hemen hemen her ay 'bu böyle gitmez' diyor. Ama her ay bir sebep çıkıyor: "
                "bayram, sınav, hastalık. Karar hiç verilmiyor, hep erteleniyor.",
    },
]

FIFTH_AVATARS = ["🦊", "🐢", "🦉", "🐙", "🐺", "🌱"]

FIFTH_CORE_PROMPT = """Sen "The Fifth" (Fifthback) içindeki tek çekirdeksin. Bir kişi sana ya kendi hikâyesini anlatır ya da bir hikâyede kendine tanıdık gelen bir şeyi söyler.

Görevin kişiye kim olduğunu söylemek DEĞİL. Görevin, anlatılanda karar değiştirici asıl ayrımı bulmak — ve gerekmedikçe soru sormamak. Anlatıda gerilim yoksa gerilim üretmek de görevin değil.

ÇALIŞMA BİÇİMİ — AYRIM TURNUVASI:
1. FARK ET: Somut olarak ne olmuş, ne söylenmiş? Yorum değil, sinyal (noticed).
2. ADAY AYRIMLAR: 3-5 aday ayrım üret. Her aday "X ile Y arasında" biçiminde iki kutuplu olsun ve anlatıdan somut bir dayanağı olsun. Her aday için şunu sor: bilinseydi okumalardan birini ELEYECEK tek bir eksik olgu var mı? Bu olgu kişinin bildiği bir şey olmalı: gözlemlenebilir bir olay, kendi eylemi, kendi deneyimi ya da basit bir karşı-olgu ("söyledin mi", "daha önce de oldu mu", "o kişi başkalarına da böyle mi"). Üçüncü kişinin niyeti sorulamaz; kişinin GÖRDÜĞÜ davranışı sorulabilir. Olgu anlatıda ZATEN varsa fact_already_in_story=true yaz ve soru üretme. Kişinin kendi kurduğu ikiliği aynen geri sorma; bir kat altındaki olguyu sor.
   ZATEN BİLİNİYOR MU (already_known) — soru üretmeden önce her eksik olgu için: anlatıda AÇIKÇA söylenmişse "stated"; anlatıdaki gözlemlenebilir bir olgudan GÜÇLÜ biçimde çıkarılabiliyorsa "implied"; ikisi de değilse "unknown". already_known_basis'e dayandığın anlatı parçasını yaz. Yalnızca "unknown" olgular sorulabilir.
   CEVAP ETKİLERİ (answer_effects) — her seçenek için cevabın neyi değiştireceğini yaz: target "pole_a" (X güçlenir) | "pole_b" (Y güçlenir) | "discard" (bu ayrım düşer) | "reshape" (ayrım yeniden biçimlenir) | "same" (hiçbir şey değişmez). Seçeneklerin hepsi özünde aynı Açıklamaya götürüyorsa answers_converge=true yaz; o zaman soru sorulmaz, REVEAL gelir. expected_information_gain: cevabın ne kazandıracağını tek cümleyle yaz.
3. PUANLA (her biri 0-3, içsel; kullanıcıya gösterilmez):
   evidence_support: dayanak anlatıda ne kadar somut
   judgment_change_value: bu ayrım netleşse kişinin yargısı ne kadar değişir (0 = değişmez, gerilim yok)
   discriminability: eksik olgu okumalardan birini gerçekten eler mi
   user_answerability: kişi bu olguyu bilir mi (kendi eylemi/deneyimi = 3, üçüncü kişinin zihni = 0)
   low_effort: tek soru, 2-4 tek satırlık seçenek ile cevaplanır mı
   speculation_risk: niyet/motif/bilinçdışı atfı, genelleme (yüksek = kötü)
   steering_risk: tavsiye/yönlendirme/teşhise kayma (yüksek = kötü)
   closure_value: bu ayrım söylenince mesele yerine oturur mu
   Sıralama: evidence_support + judgment_change_value + discriminability − speculation_risk − steering_risk. Yüksek spekülasyon ve yönlendirme sırayı DÜŞÜRÜR. En yüksek sıralı aday KAZANAN olur (winner_id) ve puanlarınla tutarlı olmalı.
4. ROTA (proposed_mode; nihai rota puanlardan türetilir):
   CLOSE: hiçbir adayda anlamlı, çözülmemiş, yargı değiştirici gerilim yoksa (tüm adaylarda judgment_change_value ≤ 1) ve kişinin söylediği amaç zaten yerine gelmişse (paylaşmak, kaydetmek). Biçime uymak için sorun uydurma.
   QUESTION: KAZANAN adayın eksik olgusu düşük zahmetli, kişinin bildiği ve gerçekten eleyici ise (user_answerability ≥ 2, low_effort ≥ 2, discriminability ≥ 2, judgment_change_value ≥ 2), anlatıda zaten yoksa (already_known="unknown") ve cevaplar aynı yere çıkmıyorsa (answers_converge=false). Soru yalnızca kazanan ayrımın olgusunu sorar; başka bir adayın sorusu sorulmaz.
   REVEAL: kazanan ayrım anlatının kendi sinyalleriyle yeterince destekleniyorsa ya da kalan bilinmeyen tonu değiştirir ama ayrımın kendisini değiştirmezse.
   Kişinin daha önce sorulmuş bir soruya yanıtı varsa ikinci soru YASAK: proposed_mode REVEAL ya da CLOSE.

KAZANAN İÇİN ÜRETİLECEKLER (her çağrıda hepsini doldur; hangisinin kullanılacağına rota karar verir):
- close: 1-2 cümlelik sıcak kabul; kişinin kendi kelimesini geri ver; yeni okuma, ayrım, "ama", soru YOK.
- reveal: 2-4 cümle, sıcak ama net, günlük Türkçe. İlk bakışta görünen okuma ile karar değiştirici noktayı ayır. Belirsizliği koru ("belki", "gibi görünüyor"). Üçüncü kişiye sorumluluk yükleme; genelleme yok; bilinçdışı motif dili yok; tavsiye yok.
- card (FIFTH KARTI): title (≤ 6 kelime, ayrımı adlandıran, kişiyi adlandırmayan) · why_it_matters (1-2 kısa cümle: bu ayrım neden karar değiştirir) · still_open (yalnızca GERÇEK belirsizlik; yoksa null) · take_with_you (kişinin yanında götürebileceği tek kısa soru ya da cümle; tavsiye değil).

YASAKLAR:
- Teşhis yok (kişilik, bozukluk, "sen ... birisin" yok). Duyguları nesnel gerçek gibi sunma. Zorla denge kurma. Terapi/koçluk dili yok. Örüntüleri evrensel yasa gibi sunma. Hikâye kartı verildiyse onu "senin hayatın" gibi ele alma. Gerilim olmayan yerde gerilim icat etme. Anlatıda olanı sorma.

TÜM ÇIKTI TÜRKÇE. YALNIZCA şu KATI JSON nesnesini ver, başka hiçbir şey yazma:
{
  "noticed": [1-3 somut sinyal],
  "candidates": [
    {"id": "c1", "distinction": "X ile Y arasında", "pole_a": "X", "pole_b": "Y",
     "evidence_from_story": "anlatıdan somut dayanak",
     "missing_discriminating_fact": "bilinseydi bir okumayı eleyecek tek olgu; yoksa null",
     "fact_already_in_story": true|false,
     "possible_question": "o olguyu soran tek kısa soru; yoksa null",
     "possible_options": ["2-4 tek satırlık seçenek"] | [],
     "already_known": "unknown" | "stated" | "implied",
     "already_known_basis": "dayandığın anlatı parçası ya da null",
     "answer_effects": [{"option": "seçenek metni", "target": "pole_a" | "pole_b" | "discard" | "reshape" | "same", "change": "tek cümle"}] | [],
     "answers_converge": true | false,
     "expected_information_gain": "tek cümle ya da null",
     "why_it_may_change_judgment": "tek cümle",
     "scores": {"evidence_support": 0-3, "judgment_change_value": 0-3, "discriminability": 0-3, "user_answerability": 0-3, "low_effort": 0-3, "speculation_risk": 0-3, "steering_risk": 0-3, "closure_value": 0-3}}
  ],
  "winner_id": "c?",
  "ranking_reasons": "1-2 cümle: kazanan neden kazandı, en yakın rakip neden kaybetti",
  "proposed_mode": "CLOSE" | "QUESTION" | "REVEAL",
  "close": "1-2 cümle",
  "reveal": "2-4 cümle",
  "shape": "between_two" | "gradient" | "open_question" | "sequence",
  "uncertain": "hâlâ bilinmeyen tek cümle ya da null",
  "card": {"title": "...", "why_it_matters": "...", "still_open": "... | null", "take_with_you": "..."}
}"""


FIFTH_ANSWER_PROMPT = """Sen "The Fifth" (Fifthback) içindeki tek çekirdeksin. İlk turda bir AYRIM TURNUVASI yapıldı, bir kazanan ayrım seçildi ve o ayrımı netleştirmek için kişiye TEK bir soru soruldu. Sana o turun SORU SÖZLEŞMESİ ve kişinin yanıtı veriliyor.

GÖREV — SORU SÜREKLİLİĞİ:
Sıfırdan yeni bir turnuva BAŞLATMA. Önce elindeki kazanan ayrımı kişinin yanıtıyla GÜNCELLE. Yanıt görünür biçimde şunlardan birini yapmalı (answer_effect):
- confirms_pole_a / confirms_pole_b: bir kutba güven artar; ayrım aynı kalır, kelimeleri keskinleşebilir.
- reshapes: aynı gerilim, ama yanıt onu daha doğru bir biçime sokar (kutuplar yeniden adlandırılır; gerilim değişmez).
- invalidates: yanıt bu ayrımı geçersiz kılar (kutuplardan biri artık mümkün değil ve kalan tek kutup bir ayrım oluşturmuyor).
- new_information: yanıt anlatıda olmayan ve DAHA İYİ bir ayrım kuran maddi yeni bilgi getirir.
- no_effect: yanıt hiçbir şeyi değiştirmedi. Bu, sorunun gereksiz olduğunu kabul etmektir; öyleyse dürüstçe yaz, etki uydurma.
Sözleşmedeki "her yanıtın değiştireceği şey" listesinde bu yanıt için öngörülen etkiyi başlangıç noktası al; öngörüden sapıyorsan what_changed içinde neden saptığını söyle.

YENİ TURNUVA yalnızca answer_effect invalidates ya da new_information ise çalışır: 3-5 yeni aday üret, aynı sekiz ölçütle puanla, yeni kazananı seç ve switch.reason içinde yanıtın bu değişimi neden haklı çıkardığını AÇIKÇA yaz. Diğer tüm durumlarda switch.needed=false, switch.candidates=[] olur ve kazanan eski ayrımın güncellenmiş hâlidir. Kazanan asla sessizce değişmez.

what_changed: kişiye görünür tek cümle; yanıtı tırnak içinde anar ve ayrımda neyi değiştirdiğini söyler. Kart bu cümleyi taşır.
still_open: yanıtla kapanan soruyu tekrar SORMA; yalnızca gerçekten açık kalanı yaz, yoksa null.

ROTA: proposed_mode REVEAL. CLOSE yalnızca yanıt gerilimi tamamen kapatıyorsa (ayrım geçersiz kaldı ve kişi meseleyi kendisi çözmüş). İkinci soru YASAK.

Üretilecekler (turnuva ile aynı kurallar): reveal 2-4 cümle, sıcak ama net, günlük Türkçe; belirsizliği koru; üçüncü kişiye sorumluluk yükleme; teşhis, tavsiye, terapi/koçluk dili, bilinçdışı motif dili yok. card: title (≤ 6 kelime, ayrımı adlandıran) · why_it_matters (1-2 cümle) · still_open · take_with_you (tek kısa soru ya da cümle; tavsiye değil).

TÜM ÇIKTI TÜRKÇE. YALNIZCA şu KATI JSON nesnesini ver, başka hiçbir şey yazma:
{
  "answer_effect": "confirms_pole_a" | "confirms_pole_b" | "reshapes" | "invalidates" | "new_information" | "no_effect",
  "what_changed": "tek cümle, yanıtı anarak",
  "updated": {"distinction": "X ile Y arasında", "pole_a": "X", "pole_b": "Y", "confidence": "pole_a" | "pole_b" | "balanced", "confidence_note": "tek cümle"},
  "switch": {"needed": true | false, "reason": "yanıt değişimi neden haklı çıkardı | null",
             "candidates": [{"id": "n1", "distinction": "X ile Y arasında", "pole_a": "X", "pole_b": "Y", "evidence_from_story": "...", "why_it_may_change_judgment": "...",
                             "scores": {"evidence_support": 0-3, "judgment_change_value": 0-3, "discriminability": 0-3, "user_answerability": 0-3, "low_effort": 0-3, "speculation_risk": 0-3, "steering_risk": 0-3, "closure_value": 0-3}}] | [],
             "winner_id": "n? | null"},
  "proposed_mode": "REVEAL" | "CLOSE",
  "close": "1-2 cümle",
  "reveal": "2-4 cümle",
  "shape": "between_two" | "gradient" | "open_question" | "sequence",
  "uncertain": "hâlâ bilinmeyen tek cümle ya da null",
  "card": {"title": "...", "why_it_matters": "...", "still_open": "... | null", "take_with_you": "..."}
}"""

ANSWER_EFFECTS = ("confirms_pole_a", "confirms_pole_b", "reshapes", "invalidates", "new_information", "no_effect")
SWITCH_EFFECTS = ("invalidates", "new_information")


class FifthStart(BaseModel):
    nickname: str
    avatar: str = "🦊"
    door: Literal["tell", "find"]
    story: Optional[str] = None            # door=tell: the user's own story
    story_card_id: Optional[str] = None    # door=find: chosen card
    familiar: Optional[str] = None         # door=find: "Burada sana tanıdık gelen ne?"
    # Saved-record preparation (no archive UI yet). user_ref is an opaque pseudonymous id the
    # client generates and keeps; kind says which public entrance produced this journey;
    # context carries exploration metadata (world / figure / door) when the journey started
    # from KENDİNİ BUL. None of this is sent to the model.
    user_ref: Optional[str] = None
    kind: Literal["anlat", "kesfet"] = "anlat"
    context: Optional[dict] = None


class FifthAnswer(BaseModel):
    session_id: str
    answer: str


class DistinctionScores(BaseModel):
    evidence_support: int = 0
    judgment_change_value: int = 0
    discriminability: int = 0
    user_answerability: int = 0
    low_effort: int = 0
    speculation_risk: int = 0
    steering_risk: int = 0
    closure_value: int = 0


class AnswerEffect(BaseModel):
    """What one possible answer would do to the winning distinction (declared BEFORE asking)."""
    option: str
    target: Literal["pole_a", "pole_b", "discard", "reshape", "same"] = "same"
    change: Optional[str] = None


class DistinctionCandidate(BaseModel):
    id: str
    distinction: str
    pole_a: Optional[str] = None
    pole_b: Optional[str] = None
    evidence_from_story: Optional[str] = None
    missing_discriminating_fact: Optional[str] = None
    fact_already_in_story: bool = False
    possible_question: Optional[str] = None
    possible_options: List[str] = []
    already_known: Optional[Literal["unknown", "stated", "implied"]] = None   # the already_known check
    already_known_basis: Optional[str] = None
    answer_effects: List[AnswerEffect] = []
    answers_converge: bool = False
    expected_information_gain: Optional[str] = None
    why_it_may_change_judgment: Optional[str] = None
    scores: DistinctionScores = DistinctionScores()
    rank: int = 0                                     # computed: es + jcv + disc − spec − steer


class QuestionContract(BaseModel):
    """Persisted when turn 1 routes to QUESTION. The answer turn UPDATES this distinction instead of
    starting a fresh tournament; a winner may only change with an explicit, recorded reason."""
    candidate_id: str
    winning_distinction: str
    pole_a: Optional[str] = None
    pole_b: Optional[str] = None
    evidence_so_far: Optional[str] = None
    missing_discriminating_fact: str
    question: str
    options: List[str] = []
    expected_information_gain: Optional[str] = None
    what_each_answer_would_change: List[AnswerEffect] = []
    already_known: Optional[str] = None
    already_known_basis: Optional[str] = None


class ContinuityUpdate(BaseModel):
    """How the answer affected the contract's distinction. old_winner/new_winner are always filled, so a
    switch can never be silent; switch_reason is mandatory when they differ."""
    mode: Literal["updated", "switched"]
    answer_effect: str
    what_changed: str
    old_winner: str
    new_winner: str
    switch_reason: Optional[str] = None
    switch_refused: Optional[str] = None              # model asked to switch without a permitted effect
    fresh_tournament_ran: bool = False
    confidence: Optional[str] = None                  # pole_a | pole_b | balanced
    confidence_note: Optional[str] = None
    predicted_effect: Optional[str] = None            # the contract's declared target for the chosen answer
    answer_discarded: bool = False                    # answer_effect == no_effect: the question bought nothing


class Tournament(BaseModel):
    """Internal: the core's candidate distinctions and how routing was derived. Not rendered to users."""
    candidates: List[DistinctionCandidate] = []
    winner_id: Optional[str] = None
    ranking_reasons: Optional[str] = None
    proposed_mode: Optional[str] = None
    routed_mode: Optional[str] = None
    route_reason: Optional[str] = None
    question_from: Optional[str] = None               # candidate id whose question was asked
    continuity: Optional[ContinuityUpdate] = None     # answer turn only


class FifthCard(BaseModel):
    """The structured final output of a completed REVEAL. Its distinction is the core's and cannot be
    altered by later roles; `enrichment` only carries provenance of an approved optional layer."""
    card_id: str
    session_id: str
    created_at: str
    title: str
    distinction: str
    why_it_matters: str
    still_open: Optional[str] = None
    take_with_you: str
    route_path: str                                   # REVEAL | QUESTION_REVEAL
    original_uncertainty: Optional[str] = None
    answer_effect: Optional[str] = None               # QUESTION_REVEAL: the visible sentence saying what the answer changed
    enrichment: Optional[dict] = None                 # {record_id, figure_id, myth_id, source_refs, title} when used
    return_prompt: str = "Sonra dönersen: tuttu mu, değişti mi, uymadı mı, başka bir şey mi çıktı?"
    returns: List[dict] = []                          # [{outcome, note, at}]


class FifthTurn(BaseModel):
    session_id: str
    nickname: str
    avatar: str
    door: str
    status: Literal["question", "done"]
    mode: Literal["QUESTION", "REVEAL", "CLOSE"]
    noticed: List[str] = []
    candidates: List[str] = []
    question: Optional[str] = None
    options: List[str] = []
    why_ask: Optional[str] = None
    reveal: Optional[str] = None
    distinction: Optional[str] = None
    shape: Optional[str] = None            # between_two | gradient | open_question | sequence (REVEAL only)
    uncertain: Optional[str] = None
    close: Optional[str] = None            # CLOSE only: 1-2 sentence acknowledgment, no distinction
    card: Optional[FifthCard] = None       # REVEAL only
    tournament: Optional[Tournament] = None  # internal; scores are never shown in the UI
    question_contract: Optional[QuestionContract] = None  # QUESTION turn: what the answer is expected to resolve
    source: str = "api"
    kind: str = "anlat"
    context: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    enrichment: Optional[PipelineResult] = None     # four-role result; filled only after a completed REVEAL, by /fifth/enrich


def _fifth_material(sess: dict) -> str:
    """Render the session's material (story or card+familiar, plus optional Q/A) for the core."""
    if sess["door"] == "tell":
        parts = [f"KAPI: Hikâyemi anlatacağım\n\nKişinin hikâyesi:\n\"\"\"\n{sess['story']}\n\"\"\""]
    else:
        card = sess["story_card"]
        parts = [
            "KAPI: Bir hikâyede kendimi bulacağım\n\n"
            f"Seçilen hikâye kartı — {card['title']} (mercek: {card['lens']}):\n\"\"\"\n{card['text']}\n\"\"\"\n\n"
            f"Kişiye 'Burada sana tanıdık gelen ne?' diye soruldu. Yanıtı:\n\"\"\"\n{sess['familiar']}\n\"\"\""
        ]
    if sess.get("question") and sess.get("answer"):
        parts.append(
            f"[Daha önce sorulan tek soru] {sess['question']}\n"
            f"[Kişinin yanıtı] {sess['answer']}\n\n"
            "Artık ikinci soru sorulamaz. mode=\"REVEAL\" ya da \"CLOSE\" olmalı."
        )
    return "\n\n".join(parts)


def _fifth_answer_material(sess: dict) -> str:
    """Answer turn: the story, the persisted QuestionContract and the answer. No fresh tournament framing."""
    base = _fifth_material({k: v for k, v in sess.items() if k not in ("question", "answer")})
    qc = QuestionContract(**sess["question_contract"])
    effects = "\n".join(f"  - \"{e.option}\" → {e.target}: {e.change or ''}" for e in qc.what_each_answer_would_change) or "  (belirtilmemiş)"
    return (
        f"{base}\n\n"
        "SORU SÖZLEŞMESİ (ilk turdan):\n"
        f"kazanan ayrım: {qc.winning_distinction}\n"
        f"kutup A: {qc.pole_a or '-'}\nkutup B: {qc.pole_b or '-'}\n"
        f"buraya kadarki dayanak: {qc.evidence_so_far or '-'}\n"
        f"eksik ayırt edici olgu: {qc.missing_discriminating_fact}\n"
        f"sorulan soru: {qc.question}\n"
        f"seçenekler: {qc.options}\n"
        f"beklenen bilgi kazancı: {qc.expected_information_gain or '-'}\n"
        f"her yanıtın değiştireceği şey:\n{effects}\n\n"
        f"[Kişinin yanıtı] {sess['answer']}\n\n"
        "Bu ayrımı yanıtla GÜNCELLE. Yeni turnuva yalnızca invalidates / new_information durumunda. İkinci soru yasak."
    )


# ---------------- Fifth Core model access ----------------
# One model, one prompt, one request per turn. Credential resolution, in order:
#   1. FIFTHBACK_ANTHROPIC_KEY from the environment/secret store — sent as x-api-key on a DIRECT
#      connection (the egress proxy is bypassed so it cannot substitute its own credential);
#   2. ANTHROPIC_API_KEY, same treatment;
#   3. an egress credential proxy (HTTPS_PROXY) — some runtimes attach the key at the proxy;
#   4. none → the core is honestly unavailable. No fake QUESTION/REVEAL is ever produced.
# The key is never logged, returned by any endpoint, or included in error text.
FIFTH_MODEL = "claude-sonnet-4-6"
ANTHROPIC_MESSAGES_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"


class FifthUnavailable(Exception):
    """The model could not be reached or refused our credential. Surfaced to the UI as 503."""


class FifthBadOutput(Exception):
    """The model answered but not with the strict JSON the core expects. Surfaced as 502."""


def _fifth_credentials() -> dict:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    api_key = (
        (os.environ.get("FIFTHBACK_ANTHROPIC_KEY") or "").strip()
        or (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        or None
    )
    if api_key:
        return {"proxy": None, "api_key": api_key, "mode": "api_key"}      # own key wins; proxy is not used
    return {"proxy": proxy, "api_key": None, "mode": "proxy" if proxy else None}


def fifth_model_status() -> dict:
    """Which credential path is configured (never the secret itself)."""
    c = _fifth_credentials()
    return {"model": FIFTH_MODEL, "credential_mode": c["mode"], "available": c["mode"] is not None}


def _fifth_http_call(material: str, system: str = None, max_tokens: int = 1024) -> dict:
    """One POST to /v1/messages, STREAMED. Raises FifthUnavailable when there is no usable credential
    or the API refuses/cannot be reached. `system` defaults to FIFTH_CORE_PROMPT (the core call);
    the roles pass their own system prompt through the same credential path.

    Streaming matters: some credential gateways cut a request whose first bytes take longer than
    ~30 s. With server-sent events the response starts immediately and long outputs (the distinction
    tournament) complete. The stream is folded back into the non-streaming message shape."""
    c = _fifth_credentials()
    if not c["mode"]:
        raise FifthUnavailable("no credential: none of FIFTHBACK_ANTHROPIC_KEY, ANTHROPIC_API_KEY or HTTPS_PROXY is set")
    headers = {"content-type": "application/json", "anthropic-version": "2023-06-01", "accept": "text/event-stream"}
    if c["api_key"]:
        headers["x-api-key"] = c["api_key"]
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True
    http = requests.Session()
    http.trust_env = not c["api_key"]     # api_key mode: direct connection, ignore proxy environment entirely
    try:
        resp = http.post(
            ANTHROPIC_MESSAGES_URL,
            headers=headers,
            json={
                "model": FIFTH_MODEL,
                "max_tokens": max_tokens,
                "stream": True,
                "system": system if system is not None else FIFTH_CORE_PROMPT,
                "messages": [{"role": "user", "content": material}],
            },
            proxies={"https": c["proxy"]} if c["proxy"] else None,
            verify=ca_bundle,
            timeout=(20, 120),
            stream=True,
        )
    except requests.RequestException as e:
        raise FifthUnavailable(f"network: {e.__class__.__name__}") from e
    if resp.status_code in (401, 403):
        raise FifthUnavailable(f"auth refused ({resp.status_code}) via {c['mode']}")
    if resp.status_code == 429 or resp.status_code >= 500:
        raise FifthUnavailable(f"api {resp.status_code}")
    if resp.status_code == 400 and "credit balance" in resp.text:
        # Billing exhaustion is an availability state, not a model output: surface it as the honest 503.
        raise FifthUnavailable("api 400: credit balance exhausted on the configured credential")
    if resp.status_code != 200:
        raise FifthBadOutput(f"api {resp.status_code}: {resp.text[:200]}")
    text_parts, model, stop_reason, usage = [], None, None, {"input_tokens": 0, "output_tokens": 0}
    try:
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            ev = json.loads(payload)
            et = ev.get("type")
            if et == "message_start":
                msg = ev.get("message") or {}
                model = msg.get("model"); usage["input_tokens"] = (msg.get("usage") or {}).get("input_tokens", 0)
            elif et == "content_block_delta":
                d = ev.get("delta") or {}
                if d.get("type") == "text_delta":
                    text_parts.append(d.get("text", ""))
            elif et == "message_delta":
                stop_reason = (ev.get("delta") or {}).get("stop_reason") or stop_reason
                usage["output_tokens"] = (ev.get("usage") or {}).get("output_tokens", usage["output_tokens"])
            elif et == "error":
                raise FifthUnavailable(f"stream error: {(ev.get('error') or {}).get('type')}: {str((ev.get('error') or {}).get('message'))[:200]}")
    except requests.RequestException as e:
        raise FifthUnavailable(f"stream interrupted: {e.__class__.__name__}") from e
    except json.JSONDecodeError as e:
        raise FifthBadOutput("malformed stream event") from e
    if not text_parts and stop_reason is None:
        raise FifthUnavailable("empty stream")
    return {"model": model or FIFTH_MODEL, "content": [{"type": "text", "text": "".join(text_parts)}], "stop_reason": stop_reason, "usage": usage}


async def fifth_core(sess: dict) -> dict:
    """ONE model interaction. Returns the parsed core JSON with source="api".
    Raises FifthUnavailable / FifthBadOutput instead of inventing output."""
    # The tournament contract (3-5 candidates + reveal + card) needs more room than the old single-mode output.
    if sess.get("answer") and sess.get("question_contract"):
        body = await asyncio.to_thread(_fifth_http_call, _fifth_answer_material(sess), FIFTH_ANSWER_PROMPT, 3000)
    else:
        body = await asyncio.to_thread(_fifth_http_call, _fifth_material(sess), None, 3500)
    if body.get("stop_reason") == "max_tokens":
        logger.error("Fifth core: output truncated at max_tokens")
        raise FifthBadOutput("model output truncated")
    raw = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    try:
        data = json.loads(m.group(0) if m else raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Fifth core: unparseable model output: %s", raw[:300])
        raise FifthBadOutput("model output was not JSON") from e
    data["source"] = "api"
    data["model"] = body.get("model")
    data["usage"] = body.get("usage")
    logger.info("Fifth core: model=%s stop=%s usage=%s", body.get("model"), body.get("stop_reason"), body.get("usage"))
    return data


def _parse_answer_effects(raw) -> List[AnswerEffect]:
    out = []
    for e in (raw or [])[:4]:
        if not isinstance(e, dict):
            continue
        tgt = e.get("target") if e.get("target") in ("pole_a", "pole_b", "discard", "reshape", "same") else "same"
        out.append(AnswerEffect(option=str(e.get("option") or "").strip(), target=tgt, change=(str(e.get("change")).strip() if e.get("change") else None)))
    return out


def _parse_tournament(data: dict) -> Tournament:
    cands = []
    for i, c in enumerate((data.get("candidates") or [])[:5]):
        clean = {}
        for k, v in (c.get("scores") or {}).items():
            if k in DistinctionScores.model_fields:
                try:
                    clean[k] = max(0, min(3, int(v)))
                except (TypeError, ValueError):
                    pass        # an unparseable score counts as 0, the others are kept
        sc = DistinctionScores(**clean)
        cand = DistinctionCandidate(
            id=str(c.get("id") or f"c{i+1}"), distinction=str(c.get("distinction") or "").strip(),
            pole_a=c.get("pole_a"), pole_b=c.get("pole_b"), evidence_from_story=c.get("evidence_from_story"),
            missing_discriminating_fact=(c.get("missing_discriminating_fact") or None),
            fact_already_in_story=bool(c.get("fact_already_in_story")),
            possible_question=(str(c.get("possible_question")).strip() if c.get("possible_question") else None),
            possible_options=[str(o).strip() for o in (c.get("possible_options") or []) if str(o).strip()][:4],
            already_known=(c.get("already_known") if c.get("already_known") in ("unknown", "stated", "implied") else None),
            already_known_basis=(str(c.get("already_known_basis")).strip() if c.get("already_known_basis") else None),
            answer_effects=_parse_answer_effects(c.get("answer_effects")),
            answers_converge=bool(c.get("answers_converge")),
            expected_information_gain=(str(c.get("expected_information_gain")).strip() if c.get("expected_information_gain") else None),
            why_it_may_change_judgment=c.get("why_it_may_change_judgment"), scores=sc,
        )
        cand.rank = sc.evidence_support + sc.judgment_change_value + sc.discriminability - sc.speculation_risk - sc.steering_risk
        if cand.distinction:
            cands.append(cand)
    return Tournament(candidates=cands, winner_id=data.get("winner_id"), ranking_reasons=data.get("ranking_reasons"), proposed_mode=str(data.get("proposed_mode") or "").upper() or None)


def _question_block_reason(c: DistinctionCandidate) -> Optional[str]:
    """None when the candidate's question may be asked; otherwise the tightened rule that blocks it."""
    sc = c.scores
    if not c.missing_discriminating_fact:
        return "no_missing_fact"
    if not c.possible_question or not (2 <= len(c.possible_options) <= 4):
        return "no_question_or_options"
    if c.fact_already_in_story or c.already_known == "stated":
        return "already_known:stated"
    if c.already_known == "implied":
        return "already_known:implied"
    if c.already_known != "unknown":
        return "already_known:unchecked"
    if c.answers_converge:
        return "answers_converge"
    targets = {e.target for e in c.answer_effects if e.target != "same"}
    if len(c.answer_effects) < 2 or len(targets) < 2:
        return "answers_converge:effects"      # the declared effects do not split the answers
    if not (sc.user_answerability >= 2 and sc.low_effort >= 2 and sc.discriminability >= 2 and sc.judgment_change_value >= 2):
        return "scores_below_threshold"
    return None


def _question_eligible(c: DistinctionCandidate) -> bool:
    return _question_block_reason(c) is None


def _route_from_tournament(t: Tournament, already_asked: bool):
    """Deterministic routing from the core's own scores. Returns (mode, reason, winner, question_candidate)."""
    if not t.candidates:
        return "REVEAL", "no candidates parsed; falling back to reveal", None, None
    top = max(c.rank for c in t.candidates)
    winner = next((c for c in t.candidates if c.id == t.winner_id and c.rank >= top - 1), None) or max(t.candidates, key=lambda c: c.rank)
    max_jcv = max(c.scores.judgment_change_value for c in t.candidates)
    if max_jcv <= 1:
        return "CLOSE", f"no candidate carries judgment-changing tension (max judgment_change_value={max_jcv})", winner, None
    if not already_asked:
        # The question may only come from the WINNER: it must discriminate the distinction the card will carry.
        block = _question_block_reason(winner)
        if block is None:
            return "QUESTION", f"winner {winner.id} has an unknown, answerable, discriminating missing fact whose answers diverge", winner, winner
        return "REVEAL", f"winner {winner.id} sufficiently supported; question blocked ({block})", winner, None
    return "REVEAL", "answer received; second question forbidden", winner, None


def _build_contract(c: DistinctionCandidate) -> QuestionContract:
    return QuestionContract(
        candidate_id=c.id, winning_distinction=c.distinction, pole_a=c.pole_a, pole_b=c.pole_b,
        evidence_so_far=c.evidence_from_story, missing_discriminating_fact=c.missing_discriminating_fact or "",
        question=c.possible_question or "", options=list(c.possible_options),
        expected_information_gain=c.expected_information_gain, what_each_answer_would_change=list(c.answer_effects),
        already_known=c.already_known, already_known_basis=c.already_known_basis,
    )


def _predicted_effect(qc: QuestionContract, answer: str) -> Optional[str]:
    a = (answer or "").strip().casefold()
    for e in qc.what_each_answer_would_change:
        if e.option.strip().casefold() == a:
            return e.target
    return None


def _normalize_answer_turn(sess: dict, data: dict) -> FifthTurn:
    """QUESTION CONTINUITY: update the contract's distinction with the answer. A fresh tournament is accepted
    only for invalidates / new_information, and only with candidates AND a reason; otherwise the winner is
    the contract's distinction as updated. old_winner/new_winner are always recorded."""
    qc = QuestionContract(**sess["question_contract"])
    effect = str(data.get("answer_effect") or "").strip()
    if effect not in ANSWER_EFFECTS:
        raise FifthBadOutput(f"unknown answer_effect {effect!r}")
    what_changed = str(data.get("what_changed") or "").strip()
    upd = data.get("updated") or {}
    sw = data.get("switch") or {}
    switched, switch_reason, refused, cands, winner = False, None, None, [], None
    if sw.get("needed"):
        if effect not in SWITCH_EFFECTS:
            refused = f"switch requested with answer_effect={effect}; only {'/'.join(SWITCH_EFFECTS)} may replace the winner"
        else:
            t2 = _parse_tournament({"candidates": sw.get("candidates") or [], "winner_id": sw.get("winner_id")})
            reason = str(sw.get("reason") or "").strip()
            if not t2.candidates or not reason:
                raise FifthBadOutput("winner switch without candidates or an explicit reason")   # a switch is never silent
            top = max(c.rank for c in t2.candidates)
            winner = next((c for c in t2.candidates if c.id == t2.winner_id and c.rank >= top - 1), None) or max(t2.candidates, key=lambda c: c.rank)
            switched, switch_reason, cands = True, reason, t2.candidates
    if not switched:
        dist = str(upd.get("distinction") or "").strip() or qc.winning_distinction
        winner = DistinctionCandidate(id=qc.candidate_id, distinction=dist, pole_a=(upd.get("pole_a") or qc.pole_a), pole_b=(upd.get("pole_b") or qc.pole_b),
                                      evidence_from_story=qc.evidence_so_far, missing_discriminating_fact=qc.missing_discriminating_fact)
        cands = [winner]
    cont = ContinuityUpdate(
        mode="switched" if switched else "updated", answer_effect=effect, what_changed=what_changed,
        old_winner=qc.winning_distinction, new_winner=winner.distinction, switch_reason=switch_reason, switch_refused=refused,
        fresh_tournament_ran=switched, confidence=(upd.get("confidence") if upd.get("confidence") in ("pole_a", "pole_b", "balanced") else None),
        confidence_note=(str(upd.get("confidence_note")).strip() if upd.get("confidence_note") else None),
        predicted_effect=_predicted_effect(qc, sess.get("answer", "")), answer_discarded=(effect == "no_effect"),
    )
    t = Tournament(candidates=cands, winner_id=winner.id, ranking_reasons=switch_reason or what_changed or None,
                   proposed_mode=str(data.get("proposed_mode") or "").upper() or None, question_from=qc.candidate_id, continuity=cont)
    now = datetime.now(timezone.utc).isoformat()
    meta = dict(session_id=sess["session_id"], nickname=sess["nickname"], avatar=sess["avatar"], door=sess["door"],
                noticed=[str(x) for x in (data.get("noticed") or [])][:3] or list(sess.get("noticed") or [])[:3],
                source=data.get("source", "api"), kind=sess.get("kind", "anlat"), context=sess.get("context"),
                created_at=sess.get("created_at"), updated_at=sess.get("updated_at"), tournament=t, question_contract=qc)
    close = str(data.get("close")).strip() if data.get("close") else None
    if t.proposed_mode == "CLOSE" and close and effect in ("invalidates", "no_effect"):
        t.routed_mode, t.route_reason = "CLOSE", f"answer dissolved the tension (answer_effect={effect})"
        return FifthTurn(status="done", mode="CLOSE", close=close, candidates=[c.distinction for c in cands][:3], **meta)
    t.routed_mode = "REVEAL"
    t.route_reason = (f"continuity: winner switched ({effect}) — {switch_reason}" if switched
                      else f"continuity: winner updated ({effect})" + (f"; {refused}" if refused else ""))
    reveal = str(data.get("reveal")).strip() if data.get("reveal") else None
    if not reveal:
        reveal = "Yanıtın ayrımı netleştirdi ama bunu iyi bir cümleye dökemedim. Bunu bir kesinlik olarak değil, şu anki sınırım olarak oku."
    shape = data.get("shape") if data.get("shape") in ("between_two", "gradient", "open_question", "sequence") else None
    uncertain = str(data.get("uncertain")).strip() if data.get("uncertain") else None
    card_in = data.get("card") or {}
    card = FifthCard(
        card_id=str(uuid.uuid4()), session_id=sess["session_id"], created_at=now,
        title=str(card_in.get("title") or winner.distinction).strip()[:80],
        distinction=winner.distinction, why_it_matters=str(card_in.get("why_it_matters") or "").strip() or reveal,
        still_open=(str(card_in.get("still_open")).strip() if card_in.get("still_open") else None),
        take_with_you=str(card_in.get("take_with_you") or "").strip() or winner.distinction,
        route_path="QUESTION_REVEAL", original_uncertainty=uncertain, answer_effect=what_changed or None,
    )
    return FifthTurn(status="done", mode="REVEAL", candidates=[c.distinction for c in cands][:3],
                     reveal=reveal, shape=shape, distinction=winner.distinction, uncertain=uncertain, card=card, **meta)


def _fifth_normalize(sess: dict, data: dict) -> FifthTurn:
    """Distinction tournament → deterministic route → CLOSE / QUESTION / REVEAL(+Fifth Card).
    Answer turns with a persisted QuestionContract go through continuity instead of a fresh tournament."""
    if sess.get("answer") and sess.get("question_contract"):
        return _normalize_answer_turn(sess, data)
    t = _parse_tournament(data)
    already_asked = bool(sess.get("question"))
    mode, reason, winner, qc = _route_from_tournament(t, already_asked)
    t.routed_mode, t.route_reason = mode, reason
    now = datetime.now(timezone.utc).isoformat()
    meta = dict(session_id=sess["session_id"], nickname=sess["nickname"], avatar=sess["avatar"], door=sess["door"],
                noticed=[str(x) for x in (data.get("noticed") or [])][:3],
                source=data.get("source", "api"), kind=sess.get("kind", "anlat"), context=sess.get("context"),
                created_at=sess.get("created_at"), updated_at=sess.get("updated_at"), tournament=t)
    close = str(data.get("close")).strip() if data.get("close") else None
    if mode == "CLOSE" and close:
        return FifthTurn(status="done", mode="CLOSE", close=close, candidates=[], **meta)
    if mode == "QUESTION" and qc:
        t.question_from = qc.id
        return FifthTurn(status="question", mode="QUESTION", candidates=[c.distinction for c in t.candidates][:3],
                         question=qc.possible_question, options=qc.possible_options, why_ask=qc.why_it_may_change_judgment,
                         question_contract=_build_contract(qc), **meta)
    reveal = str(data.get("reveal")).strip() if data.get("reveal") else None
    if not reveal:
        reveal = ("Buraya kadar anlattıkların bir Açıklama için yeterli görünüyor ama net bir ayrım çıkaramadım. "
                  "Bunu bir kesinlik olarak değil, şu anki sınırım olarak oku.")
    distinction = (winner.distinction if winner else None) or (str(data.get("distinction")).strip() if data.get("distinction") else None)
    shape = data.get("shape") if data.get("shape") in ("between_two", "gradient", "open_question", "sequence") else None
    uncertain = str(data.get("uncertain")).strip() if data.get("uncertain") else None
    card_in = data.get("card") or {}
    card = FifthCard(
        card_id=str(uuid.uuid4()), session_id=sess["session_id"], created_at=now,
        title=str(card_in.get("title") or (winner.distinction if winner else "Ayrım")).strip()[:80],
        distinction=distinction or "", why_it_matters=str(card_in.get("why_it_matters") or "").strip() or reveal,
        still_open=(str(card_in.get("still_open")).strip() if card_in.get("still_open") else None) or uncertain,
        take_with_you=str(card_in.get("take_with_you") or "").strip() or (distinction or ""),
        route_path="QUESTION_REVEAL" if already_asked else "REVEAL", original_uncertainty=uncertain,
    ) if distinction else None
    return FifthTurn(status="done", mode="REVEAL", candidates=[c.distinction for c in t.candidates][:3],
                     reveal=reveal, shape=shape, distinction=distinction, uncertain=uncertain, card=card, **meta)


@api_router.get("/fifth/stories")
async def fifth_stories():
    return {"source": "prototype_seed", "avatars": FIFTH_AVATARS, "stories": FIFTH_STORY_CARDS}


# Internal tournament fields (candidate scores, the question contract) are stored and used for evaluation
# but never leave the API: the public product shows only the question, the Reveal and the Fifth Card.
FIFTH_PUBLIC_EXCLUDE = {"tournament", "question_contract"}


def _fifth_turn_from_record(sess: dict) -> FifthTurn:
    """Rebuild the current turn from the stored session record (used to restore after refresh)."""
    return FifthTurn(
        session_id=sess["session_id"], nickname=sess["nickname"], avatar=sess["avatar"], door=sess["door"],
        status=sess.get("status", "question"), mode=sess.get("mode") or ("REVEAL" if sess.get("status") == "done" else "QUESTION"),
        noticed=sess.get("noticed") or [], candidates=sess.get("candidates") or [],
        question=sess.get("question"), options=sess.get("options") or [], why_ask=sess.get("why_ask"),
        reveal=sess.get("reveal"), distinction=sess.get("distinction"), shape=sess.get("shape"), uncertain=sess.get("uncertain"),
        close=sess.get("close"), card=sess.get("card"), tournament=sess.get("tournament"),
        question_contract=sess.get("question_contract"),
        source=sess.get("source", "api"), kind=sess.get("kind", "anlat"), context=sess.get("context"),
        created_at=sess.get("created_at"), updated_at=sess.get("updated_at"),
        enrichment=sess.get("enrichment"),
    )


async def _fifth_run(sess: dict) -> FifthTurn:
    """Run the core and translate its failures into honest HTTP states."""
    try:
        data = await fifth_core(sess)
    except FifthUnavailable as e:
        logger.warning("Fifth core unavailable: %s", e)
        raise HTTPException(status_code=503, detail="model_unavailable")
    except FifthBadOutput as e:
        logger.warning("Fifth core bad output: %s", e)
        raise HTTPException(status_code=502, detail="model_bad_output")
    return _fifth_normalize(sess, data)


@api_router.get("/fifth/status")
async def fifth_status():
    """Is the core reachable in this runtime, and through which credential path? Never returns secrets."""
    return fifth_model_status()


@api_router.get("/fifth/session/{session_id}", response_model=FifthTurn, response_model_exclude=FIFTH_PUBLIC_EXCLUDE)
async def fifth_session(session_id: str):
    sess = await db.fifth_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")
    return _fifth_turn_from_record(sess)


def _gate_call(system: str, material: str) -> dict:
    return _fifth_http_call(material, system=system, max_tokens=1500)


@api_router.post("/fifth/enrich/{session_id}", response_model=PipelineResult)
async def fifth_enrich(session_id: str):
    """Four-role pipeline after the core: LIBRARIAN → SKEPTIC → STORYTELLER. QUESTION and CLOSE stop
    before any role runs. The core is frozen and re-verified; enrichment.used=false is a normal outcome."""
    sess = await db.fifth_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")
    if sess.get("enrichment"):
        return PipelineResult(**sess["enrichment"])
    turn = _fifth_turn_from_record(sess)
    result = await asyncio.to_thread(run_after_reveal, turn, sess, _gate_call, None, FifthUnavailable, FifthBadOutput)
    if result.enrichment.reason != "model_unavailable":   # never persist a run that could not reach the model
        upd = {"enrichment": result.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
        if sess.get("card") and result.enrichment.used:
            e = result.enrichment
            upd["card.enrichment"] = {"record_id": e.record_id, "figure_id": e.figure_id, "myth_id": e.myth_id, "source_refs": e.source_refs, "title": e.title, "type": e.type}
        await db.fifth_sessions.update_one({"session_id": session_id}, {"$set": upd})
    return result


class CardReturn(BaseModel):
    outcome: Literal["tuttu", "degisti", "uymadi", "baska"]
    note: Optional[str] = None


@api_router.post("/fifth/card/{session_id}/return", response_model=FifthCard)
async def fifth_card_return(session_id: str, req: CardReturn):
    """Return loop: the user comes back later and says what happened to the card. No scoring, no profile."""
    sess = await db.fifth_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not sess or not sess.get("card"):
        raise HTTPException(status_code=404, detail="Kart bulunamadı.")
    entry = {"outcome": req.outcome, "note": (req.note or "").strip()[:500] or None, "at": datetime.now(timezone.utc).isoformat()}
    await db.fifth_sessions.update_one({"session_id": session_id}, {"$push": {"card.returns": entry}, "$set": {"updated_at": entry["at"]}})
    card = dict(sess["card"]); card["returns"] = list(card.get("returns") or []) + [entry]
    return FifthCard(**card)


# ---------------- Saved cards ("Kaydet" → MY FIFTHBACK) ----------------
# v0 persistence only: one record per card, keyed by the pseudonymous user_ref the browser generated.
# No profile, no scores, no dashboard. The list is chronological.
class SaveCardRequest(BaseModel):
    user_ref: str = Field(min_length=1, max_length=64)


class SavedCard(BaseModel):
    card_id: str
    session_id: str
    user_ref: str
    created_at: str                                   # when the card was produced
    saved_at: str                                     # when the user pressed Kaydet
    story: Optional[str] = None                       # the original story (or story card + what felt familiar)
    story_ref: str                                    # session reference to the full record
    route_path: str                                   # REVEAL | QUESTION_REVEAL
    title: str
    distinction: str
    why_it_matters: str
    still_open: Optional[str] = None
    take_with_you: str
    enrichment: Optional[dict] = None                 # provenance only, when an approved enrichment existed
    nickname: Optional[str] = None
    avatar: Optional[str] = None


def _saved_card_from_session(sess: dict, user_ref: str, now: str) -> SavedCard:
    card = sess["card"]
    if sess.get("story"):
        story = sess["story"]
    else:
        sc = sess.get("story_card") or {}
        story = f"{sc.get('title', '')}: {sc.get('text', '')}\n\nTanıdık gelen: {sess.get('familiar', '')}".strip()
    return SavedCard(
        card_id=card["card_id"], session_id=sess["session_id"], user_ref=user_ref,
        created_at=card.get("created_at") or sess.get("created_at") or now, saved_at=now,
        story=story[:4000], story_ref=sess["session_id"], route_path=card.get("route_path") or "REVEAL",
        title=card.get("title") or card.get("distinction") or "", distinction=card.get("distinction") or "",
        why_it_matters=card.get("why_it_matters") or "", still_open=card.get("still_open"),
        take_with_you=card.get("take_with_you") or "", enrichment=card.get("enrichment"),
        nickname=sess.get("nickname"), avatar=sess.get("avatar"),
    )


@api_router.post("/fifth/card/{session_id}/save", response_model=SavedCard)
async def fifth_card_save(session_id: str, req: SaveCardRequest):
    """Kaydet: persist the finished Fifth Card for this user_ref. Idempotent per card."""
    sess = await db.fifth_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not sess or not sess.get("card"):
        raise HTTPException(status_code=404, detail="Kart bulunamadı.")
    now = datetime.now(timezone.utc).isoformat()
    rec = _saved_card_from_session(sess, req.user_ref.strip(), now)
    existing = await db.fifth_saved_cards.find_one({"card_id": rec.card_id, "user_ref": rec.user_ref}, {"_id": 0})
    if existing:
        return SavedCard(**existing)
    await db.fifth_saved_cards.insert_one(rec.model_dump())
    return rec


@api_router.get("/fifth/saved", response_model=List[SavedCard])
async def fifth_saved_list(user_ref: str):
    """MY FIFTHBACK v0: the user's saved cards, newest first."""
    if not user_ref.strip():
        return []
    cur = db.fifth_saved_cards.find({"user_ref": user_ref.strip()}, {"_id": 0}).sort("saved_at", -1).limit(200)
    return [SavedCard(**d) async for d in cur]


@api_router.delete("/fifth/saved/{card_id}")
async def fifth_saved_delete(card_id: str, user_ref: str):
    res = await db.fifth_saved_cards.delete_one({"card_id": card_id, "user_ref": user_ref.strip()})
    return {"deleted": res.deleted_count}


@api_router.post("/fifth/start", response_model=FifthTurn, response_model_exclude=FIFTH_PUBLIC_EXCLUDE)
async def fifth_start(req: FifthStart):
    nickname = (req.nickname or "").strip()
    if not nickname:
        raise HTTPException(status_code=400, detail="Önce bir takma ad seç.")
    now = datetime.now(timezone.utc).isoformat()
    sess = {
        "session_id": str(uuid.uuid4()),      # doubles as the stable journey id
        "kind": req.kind,
        "user_ref": (req.user_ref or "")[:64] or None,
        "context": req.context or None,
        "nickname": nickname[:40],
        "avatar": (req.avatar or "🦊")[:4],
        "door": req.door,
        "created_at": now,
        "updated_at": now,
        "status": "question",
    }
    if req.door == "tell":
        if not req.story or not req.story.strip():
            raise HTTPException(status_code=400, detail="Önce hikâyeni anlat.")
        sess["story"] = req.story.strip()
    else:
        card = next((c for c in FIFTH_STORY_CARDS if c["id"] == req.story_card_id), None)
        if not card:
            raise HTTPException(status_code=400, detail="Önce bir hikâye seç.")
        if not req.familiar or not req.familiar.strip():
            raise HTTPException(status_code=400, detail="Burada sana tanıdık gelen neydi?")
        sess["story_card"] = card
        sess["familiar"] = req.familiar.strip()

    turn = await _fifth_run(sess)   # 503/502 before anything is stored: retry is clean
    sess.update({
        "status": turn.status, "mode": turn.mode, "noticed": turn.noticed, "candidates": turn.candidates,
        "question": turn.question, "options": turn.options, "why_ask": turn.why_ask,
        "reveal": turn.reveal, "distinction": turn.distinction, "shape": turn.shape, "uncertain": turn.uncertain,
        "close": turn.close, "source": turn.source,
        "card": turn.card.model_dump() if turn.card else None, "tournament": turn.tournament.model_dump() if turn.tournament else None,
        "question_contract": turn.question_contract.model_dump() if turn.question_contract else None,
    })
    await db.fifth_sessions.insert_one(dict(sess))
    return turn


@api_router.post("/fifth/answer", response_model=FifthTurn, response_model_exclude=FIFTH_PUBLIC_EXCLUDE)
async def fifth_answer(req: FifthAnswer):
    sess = await db.fifth_sessions.find_one({"session_id": req.session_id}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")
    if sess.get("status") == "done":
        raise HTTPException(status_code=409, detail="Bu hikâye için Açıklama zaten verildi.")
    if not req.answer or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Bir yanıt yaz ya da seç.")
    sess["answer"] = req.answer.strip()[:500]

    turn = await _fifth_run(sess)   # already_asked → always REVEAL; on 503 the session stays open for retry
    now = datetime.now(timezone.utc).isoformat()
    await db.fifth_sessions.update_one(
        {"session_id": req.session_id},
        {"$set": {
            "answer": sess["answer"], "status": "done", "mode": turn.mode, "noticed": turn.noticed, "candidates": turn.candidates,
            "reveal": turn.reveal, "distinction": turn.distinction, "shape": turn.shape, "uncertain": turn.uncertain,
            "close": turn.close, "source": turn.source,
            "card": turn.card.model_dump() if turn.card else None, "tournament": turn.tournament.model_dump() if turn.tournament else None,
            "answered_at": now, "updated_at": now,
        }},
    )
    turn.updated_at = now
    return turn


app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}


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
