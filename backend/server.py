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

İçinden şu sırayla düşün (bunları kimseye adım adım anlatma, sadece sonucunu ver):
1. FARK ET (NOTICE): Somut olarak ne olmuş, ne söylenmiş? Yorum değil, sinyal.
2. ÖRÜNTÜ (PATTERN): Bu sinyallerle uyuşabilecek 2-3 makul okuma nedir? Bunlar mercektir, gerçek değil. Yardımcı olabilecek mercekler: Kişi / Bağlam / İlişki / Toplum-Sistem; zıtlıklar (bekleyen-vazgeçen, yardım eden-tükenen); döngüler (aynı şeyin tekrar etmesi).
3. AYIRT ET (DISTINGUISH): Bilinseydi yargıyı GERÇEKTEN değiştirecek TEK eksik olgu var mı? Ayrım demek: cevabına göre okumalardan biri elenir demek.
4. KAPAT, SOR ya da AÇIKLA (CLOSE / QUESTION / REVEAL): Aşağıdaki kapıları SIRAYLA uygula; ilk tutan kapı kararı verir.

KAPI 1 — CLOSE (Kapat): Anlatıda çözülmemiş, yargı değiştirici bir gerilim YOKSA ve kişinin söylediği amaç zaten yerine gelmişse (paylaşmak, kaydetmek, bir anı işaretlemek), mode="CLOSE". Gerilim sinyalleri: kendine soru ("mı… mı", "bilmiyorum", "ayıramıyorum"), aynı anda zıt duygular ("hem… hem", "kızmadım ama"), tekrar/döngü, geri çekilme eylemi (susmak, kısa cevap vermek, teklif etmeyi bırakmak), söylenmemiş kırılma, beklenti-sonuç uyumsuzluğu. Bunlardan hiçbiri yoksa okuma üretme, ayrım üretme, soru sorma: 1-2 cümlelik sıcak bir kabul yaz, kişinin kendi kelimesini geri ver ve dur. Biçime uymak için sorun uydurma.

KAPI 2 — QUESTION (Sor): Şu dört koşulun HEPSİ sağlanıyorsa mode="QUESTION":
  Q1 En az iki makul okuma var ve bunlar FARKLI ayrımlara götürüyor (aynı ayrımın iki tonu değil).
  Q2 Bu okumalardan birini eleyecek TEK bir düşük zahmetli olgu var ve bu olgu kişinin bildiği bir şey: gözlemlenebilir bir olay, kendi eylemi, kendi deneyimi ya da basit bir karşı-olgu ("söyleseydin ne olurdu" değil, "söyledin mi"). Üçüncü kişinin niyeti/zihni sorulamaz; ama üçüncü kişinin kişinin GÖRDÜĞÜ davranışı sorulabilir. "Karşı taraf ne düşünüyor bilinemez" demek tek başına REVEAL gerekçesi DEĞİLDİR: kişinin elindeki gözlemlenebilir bir kanıt hâlâ ayırt ediyorsa sor.
  Q3 Sorduğun şey anlatıda ZATEN YOK. Anlatı bir şeyi söylemişse onu sorma; kişinin kendi kurduğu ikiliği ("istemiyorum mu korkuyorum mu") aynen geri sorma, onun bir kat altındaki olguyu sor.
  Q4 Düşük zahmet: tek soru, 2-4 seçenek, her seçenek tek satır (en fazla 8 kelime), bileşik soru yok.
  Q1-Q3 sağlanıp Q4 sağlanmıyorsa soruyu kısalt; REVEAL'a kaçma.

KAPI 3 — REVEAL (Açıkla): Gerilim var ama ya ayrım anlatının kendi sinyalleriyle zaten yeterince destekleniyor, ya da kalan bilinmeyen tonu değiştirir ama AYRIMIN KENDİSİNİ değiştirmez. O zaman mode="REVEAL": açıkla ve dur.

Eğer kişinin daha önce sorulmuş bir soruya verdiği yanıt varsa, mode KESİNLİKLE "REVEAL" ya da "CLOSE" olmalı; ikinci soru YASAK.

Açıklama (reveal) nasıl olmalı:
- 2-4 cümle, sıcak ama net, terapi dili değil, günlük Türkçe.
- İlk bakışta görünen okuma ile anlatıldığında ortaya çıkan karar değiştirici noktayı ayırsın. Örn. hissi: "Belki burada asıl ayrım X ile Y arasında." ya da "İlk bakışta X gibi görünüyor ama anlattığında karar değiştirici nokta Y." (Bu cümleleri kopyalama; anlama uydur.)
- Belirsizliği koru: emin olmadığın şeyi "belki", "gibi görünüyor" diye söyle. Bilinmeyeni açıkça söyle.
- Üçüncü kişiye sorumluluk yükleme; "genelde", "çoğunlukla" diye genelleme yapma; bilinçdışı motif dili kullanma.
- Kişiye tavsiye ya da görev verme. Sadece ayrımı görünür kıl.

Kapanış (close) nasıl olmalı:
- 1-2 cümle. Kişinin söylediği duyguyu kendi kelimesiyle geri ver. Yeni okuma, ayrım, "ama", soru yok.

YASAKLAR:
- Teşhis yok (kişilik, bozukluk, "sen ... birisin" yok).
- Duyguları nesnel gerçek gibi sunma ("aslında öfkelisin" yok).
- Zorla denge kurma ("iki taraf da haklı" gibi boş cümleler yok).
- Aşırı soru yok: en fazla BİR soru, o da şart değilse hiç.
- Genel terapi/koçluk dili yok.
- Örüntüleri/atasözlerini evrensel yasa gibi sunma; onlar sadece mercek.
- Hikâye kartı verildiyse onu "senin hayatın" gibi ele alma; kişinin tanıdık dediği şey esas veridir.
- Gerilim olmayan yerde gerilim icat etme.

TÜM ÇIKTI TÜRKÇE. YALNIZCA şu KATI JSON nesnesini ver, başka hiçbir şey yazma:
{
  "mode": "CLOSE" ya da "QUESTION" ya da "REVEAL",
  "noticed": [anlatılandan 1-3 somut sinyal, her biri kısa tek cümle],
  "candidates": [mode CLOSE ise boş liste; aksi halde 1-3 kısa aday okuma/mercek; kesinlik iddiası olmadan],
  "close": mode CLOSE ise 1-2 cümlelik kabul, aksi halde null,
  "question": mode QUESTION ise tek kısa soru, aksi halde null,
  "options": mode QUESTION ise 2-4 kısa tek satırlık seçenek, aksi halde [],
  "why_ask": mode QUESTION ise bu sorunun hangi okumayı eleyeceğine dair tek cümle, aksi halde null,
  "reveal": mode REVEAL ise 2-4 cümlelik açıklama, aksi halde null,
  "distinction": mode REVEAL ise "X ile Y arasında" biçiminde asıl ayrımın tek satırlık adı, aksi halde null,
  "shape": mode REVEAL ise ayrımın biçimi: "between_two" (gerçek iki kutup) / "gradient" (aynı şeyin dozları) / "open_question" (temiz karşıtı yok) / "sequence" (birinin zamanla ötekine dönüşmesi), aksi halde null,
  "uncertain": mode REVEAL ise hâlâ bilinmeyen/emin olunmayan şeye dair tek cümle, aksi halde null
}"""


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


# ---------------- Fifth Core model access ----------------
# One model, one prompt, one request per turn. Credential resolution, in order:
#   1. an egress credential proxy (HTTPS_PROXY) — some runtimes attach the key at the proxy;
#   2. ANTHROPIC_API_KEY from the environment/secret store — sent as x-api-key;
#   3. neither → the core is honestly unavailable. No fake QUESTION/REVEAL is ever produced.
FIFTH_MODEL = "claude-sonnet-4-6"
ANTHROPIC_MESSAGES_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"


class FifthUnavailable(Exception):
    """The model could not be reached or refused our credential. Surfaced to the UI as 503."""


class FifthBadOutput(Exception):
    """The model answered but not with the strict JSON the core expects. Surfaced as 502."""


def _fifth_credentials() -> dict:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    return {"proxy": proxy, "api_key": api_key, "mode": "api_key" if api_key else ("proxy" if proxy else None)}


def fifth_model_status() -> dict:
    """Which credential path is configured (never the secret itself)."""
    c = _fifth_credentials()
    return {"model": FIFTH_MODEL, "credential_mode": c["mode"], "available": c["mode"] is not None}


def _fifth_http_call(material: str, system: str = None, max_tokens: int = 1024) -> dict:
    """One blocking POST to /v1/messages. Raises FifthUnavailable when there is no usable credential
    or the API refuses/cannot be reached. `system` defaults to FIFTH_CORE_PROMPT (the core call);
    the enrichment gate passes its own system prompt through the same credential path."""
    c = _fifth_credentials()
    if not c["mode"]:
        raise FifthUnavailable("no credential: neither HTTPS_PROXY nor ANTHROPIC_API_KEY is set")
    headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
    if c["api_key"]:
        headers["x-api-key"] = c["api_key"]
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True
    try:
        resp = requests.post(
            ANTHROPIC_MESSAGES_URL,
            headers=headers,
            json={
                "model": FIFTH_MODEL,
                "max_tokens": max_tokens,
                "system": system if system is not None else FIFTH_CORE_PROMPT,
                "messages": [{"role": "user", "content": material}],
            },
            # api.anthropic.com is often in NO_PROXY; naming the proxy explicitly is what lets a
            # credential proxy inject the key. Without a proxy the request goes direct.
            proxies={"https": c["proxy"]} if c["proxy"] else None,
            verify=ca_bundle,
            timeout=60,
        )
    except requests.RequestException as e:
        raise FifthUnavailable(f"network: {e.__class__.__name__}") from e
    if resp.status_code in (401, 403):
        raise FifthUnavailable(f"auth refused ({resp.status_code}) via {c['mode']}")
    if resp.status_code == 429 or resp.status_code >= 500:
        raise FifthUnavailable(f"api {resp.status_code}")
    if resp.status_code != 200:
        raise FifthBadOutput(f"api {resp.status_code}: {resp.text[:200]}")
    return resp.json()


async def fifth_core(sess: dict) -> dict:
    """ONE model interaction. Returns the parsed core JSON with source="api".
    Raises FifthUnavailable / FifthBadOutput instead of inventing output."""
    body = await asyncio.to_thread(_fifth_http_call, _fifth_material(sess))
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


def _fifth_normalize(sess: dict, data: dict) -> FifthTurn:
    """Enforce the three-output contract: CLOSE, QUESTION (only if none asked yet) or REVEAL."""
    mode = str(data.get("mode", "")).upper()
    question = str(data.get("question")).strip() if data.get("question") else None
    options = [str(o).strip() for o in (data.get("options") or []) if str(o).strip()][:4]
    reveal = str(data.get("reveal")).strip() if data.get("reveal") else None
    close = str(data.get("close")).strip() if data.get("close") else None
    already_asked = bool(sess.get("question"))
    meta = dict(session_id=sess["session_id"], nickname=sess["nickname"], avatar=sess["avatar"], door=sess["door"],
                noticed=[str(x) for x in (data.get("noticed") or [])][:3],
                source=data.get("source", "api"), kind=sess.get("kind", "anlat"), context=sess.get("context"),
                created_at=sess.get("created_at"), updated_at=sess.get("updated_at"))

    if mode == "CLOSE" and close:
        return FifthTurn(status="done", mode="CLOSE", close=close, candidates=[], **meta)

    if mode == "QUESTION" and not already_asked and question:
        return FifthTurn(
            status="question", mode="QUESTION",
            candidates=[str(x) for x in (data.get("candidates") or [])][:3],
            question=question, options=options,
            why_ask=str(data.get("why_ask")).strip() if data.get("why_ask") else None,
            **meta,
        )

    if not reveal:
        # The model asked a second question or returned nothing usable: stop honestly.
        reveal = (
            "Buraya kadar anlattıkların bir Açıklama için yeterli görünüyor ama net bir ayrım çıkaramadım. "
            "Bunu bir kesinlik olarak değil, şu anki sınırım olarak oku."
        )
    shape = data.get("shape") if data.get("shape") in ("between_two", "gradient", "open_question", "sequence") else None
    return FifthTurn(
        status="done", mode="REVEAL",
        candidates=[str(x) for x in (data.get("candidates") or [])][:3],
        reveal=reveal, shape=shape,
        distinction=str(data.get("distinction")).strip() if data.get("distinction") else None,
        uncertain=str(data.get("uncertain")).strip() if data.get("uncertain") else None,
        **meta,
    )


@api_router.get("/fifth/stories")
async def fifth_stories():
    return {"source": "prototype_seed", "avatars": FIFTH_AVATARS, "stories": FIFTH_STORY_CARDS}


def _fifth_turn_from_record(sess: dict) -> FifthTurn:
    """Rebuild the current turn from the stored session record (used to restore after refresh)."""
    return FifthTurn(
        session_id=sess["session_id"], nickname=sess["nickname"], avatar=sess["avatar"], door=sess["door"],
        status=sess.get("status", "question"), mode=sess.get("mode") or ("REVEAL" if sess.get("status") == "done" else "QUESTION"),
        noticed=sess.get("noticed") or [], candidates=sess.get("candidates") or [],
        question=sess.get("question"), options=sess.get("options") or [], why_ask=sess.get("why_ask"),
        reveal=sess.get("reveal"), distinction=sess.get("distinction"), shape=sess.get("shape"), uncertain=sess.get("uncertain"),
        close=sess.get("close"),
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


@api_router.get("/fifth/session/{session_id}", response_model=FifthTurn)
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
        await db.fifth_sessions.update_one({"session_id": session_id}, {"$set": {"enrichment": result.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}})
    return result


@api_router.post("/fifth/start", response_model=FifthTurn)
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
    })
    await db.fifth_sessions.insert_one(dict(sess))
    return turn


@api_router.post("/fifth/answer", response_model=FifthTurn)
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
