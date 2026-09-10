import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, ArrowRight, RotateCcw, Copy, Check, BookmarkCheck } from "lucide-react";
import { toast } from "sonner";
import { answerFifth, getFifthSession, describeFifthError } from "../lib/api";
import { FifthCardView } from "../components/FifthCardView";
import { setCurrentSession, clearCurrentSession, clearDraft, getCurrentSession, saveCardRecord, cardToText } from "../lib/storage";
import { BackLink } from "../components/BackLink";
import { ModelUnavailable } from "../components/ModelUnavailable";

const Label = ({ children, color = "#C85A32" }) => (
  <span className="text-[11px] font-mono uppercase tracking-[0.2em] font-semibold" style={{ color }}>{children}</span>
);

// Copies the finished turn as plain text. Clipboard can be unavailable (http, old browsers): say so, don't fail silently.
const CopyButton = ({ turn }) => {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(cardToText(turn));
      setDone(true); setTimeout(() => setDone(false), 2000);
    } catch {
      toast("Kopyalanamadı.", { description: "Tarayıcı izin vermedi. Metni seçip kopyalayabilirsin." });
    }
  };
  return (
    <button data-testid="turn-copy" onClick={copy} className="inline-flex items-center gap-1.5 text-sm font-medium text-[#57534E] hover:text-[#1A1816]">
      {done ? <Check className="h-4 w-4 text-[#3F6B56]" /> : <Copy className="h-4 w-4" />} {done ? "Kopyalandı" : "Kopyala"}
    </button>
  );
};

const DoneActions = ({ turn, onNew, onHome }) => (
  <div className="pt-2 space-y-3">
    <div className="flex items-center gap-1.5 text-xs text-[#3F6B56]" data-testid="turn-saved">
      <BookmarkCheck className="h-4 w-4" /> Kartlarım'a kaydedildi. Bu tarayıcıda durur.
    </div>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <span className="text-sm text-[#8A847C]">{turn.mode === "CLOSE" ? `Eklenecek bir şey yok, ${turn.nickname}.` : `Burada duruyoruz, ${turn.nickname}.`}</span>
      <div className="flex flex-wrap items-center gap-4">
        <CopyButton turn={turn} />
        <button data-testid="turn-new-story" onClick={onNew} className="inline-flex items-center gap-1.5 text-sm font-medium text-[#57534E] hover:text-[#1A1816]">
          <RotateCcw className="h-4 w-4" /> Yeni bir hikâye
        </button>
        <button data-testid="turn-home" onClick={onHome} className="text-sm font-medium text-[#57534E] hover:text-[#1A1816]">Kartlarım</button>
      </div>
    </div>
  </div>
);

// The one question, or the Reveal. State comes from navigation, then sessionStorage, then the server.
// The four-role enrichment endpoint still exists on the backend but is NOT called from the public product.
export const AnlatTurn = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const cached = getCurrentSession();
  const [turn, setTurn] = useState(location.state?.turn || (cached?.session_id === sessionId ? cached : null));
  const isReturnVisit = !location.state?.turn;   // opened later (link, refresh, history) rather than right after the Reveal
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState(null);
  const [missing, setMissing] = useState(false);
  const [pendingAnswer, setPendingAnswer] = useState(null);

  useEffect(() => {
    if (turn) return;
    getFifthSession(sessionId).then((t) => { setTurn(t); setCurrentSession(t); }).catch(() => setMissing(true));
  }, [sessionId, turn]);

  // Every finished turn is saved to the user's list (idempotent by session_id).
  useEffect(() => { if (turn?.status === "done") saveCardRecord(turn); }, [turn]);

  const reply = async (text) => {
    const a = (text ?? answer).trim();
    if (!a) return toast("Bir seçenek seç ya da kısaca yaz.");
    setLoading(true); setFailure(null); setPendingAnswer(a);
    try {
      const t = await answerFifth(sessionId, a);
      setTurn(t); setCurrentSession(t);
    } catch (e) {
      const f = describeFifthError(e);
      if (f.kind === "done") { toast(f.message); getFifthSession(sessionId).then(setTurn).catch(() => {}); }
      else setFailure(f.kind);
    } finally {
      setLoading(false);
    }
  };

  const newStory = () => { clearCurrentSession(); clearDraft(); navigate("/anlat", { state: { fromTurn: true } }); };
  const toCards = () => navigate("/kartlarim");

  if (missing) {
    return (
      <div className="max-w-2xl mx-auto py-14 space-y-6">
        <BackLink to="/anlat" label="Anlat'a dön" />
        <p className="font-serif text-2xl">Bu hikâye bulunamadı.</p>
        <p className="text-sm text-[#8A847C]">Bağlantı eski olabilir. Yeni bir hikâye anlatabilirsin.</p>
      </div>
    );
  }
  if (!turn) {
    return <div className="max-w-2xl mx-auto py-14 text-sm text-[#8A847C] inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Hikâye yükleniyor…</div>;
  }

  return (
    <div className="max-w-2xl mx-auto py-10 sm:py-14 space-y-6">
      <BackLink to="/anlat" label="Anlat'a dön" testId="turn-back" />
      <div className="flex items-center gap-2 text-sm text-[#8A847C]"><span>{turn.avatar}</span><span>{turn.nickname}</span></div>

      {turn.noticed?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {turn.noticed.map((n, i) => (
            <span key={i} className="text-xs rounded-full border border-[#E7E0D8] bg-white px-3 py-1 text-[#57534E]">{n}</span>
          ))}
        </div>
      )}

      <AnimatePresence mode="wait">
        {turn.status === "question" ? (
          <motion.div key="q" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            className="rounded-2xl border border-[#E7E0D8] bg-white p-6 shadow-sm space-y-5" data-testid="fifth-question">
            <Label>Tek soru</Label>
            <p className="font-serif text-2xl sm:text-3xl leading-snug">{turn.question}</p>
            {turn.why_ask && <p className="text-sm text-[#8A847C]">{turn.why_ask}</p>}
            <div className="flex flex-wrap gap-2">
              {turn.options.map((o) => (
                <button key={o} data-testid="fifth-option" disabled={loading} onClick={() => reply(o)}
                  className="rounded-full border border-[#E7E0D8] bg-white px-4 py-2 text-sm font-medium text-left text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors disabled:opacity-50">
                  {o}
                </button>
              ))}
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <input data-testid="fifth-answer" value={answer} onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && reply()} placeholder="ya da kısaca yaz…"
                className="flex-1 rounded-full border border-[#E7E0D8] bg-white px-4 py-2.5 text-base sm:text-sm outline-none focus:border-[#C85A32]" />
              <button data-testid="fifth-submit-answer" disabled={loading} onClick={() => reply()}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] disabled:opacity-50">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />} Gönder
              </button>
            </div>
            {loading && <p data-testid="turn-waiting" className="text-sm text-[#8A847C]">Yanıtın işleniyor. Bu bir dakikaya kadar sürebilir; sayfayı kapatma.</p>}
            {failure && <ModelUnavailable kind={failure} onRetry={() => reply(pendingAnswer)} retrying={loading} draftKept={false} />}
          </motion.div>
        ) : turn.mode === "CLOSE" ? (
          <motion.div key="c" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-[#E7E0D8] bg-white p-6 sm:p-8 shadow-sm space-y-5" data-testid="fifth-close">
            <Label color="#8A847C">Duyuldu</Label>
            <p className="font-serif text-2xl sm:text-3xl leading-snug">{turn.close}</p>
            <DoneActions turn={turn} onNew={newStory} onHome={toCards} />
          </motion.div>
        ) : (
          <motion.div key="r" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-[#E7E0D8] bg-[#FBF7F2] p-6 sm:p-8 shadow-sm space-y-5" data-testid="fifth-reveal">
            <Label color="#3F6B56">Açıklama</Label>
            {turn.card ? (
              <FifthCardView card={turn.card} enrichment={null} isReturnVisit={isReturnVisit} />
            ) : (
              <>
                {turn.distinction && <p className="text-sm font-mono uppercase tracking-[0.12em] text-[#3F6B56]">{turn.distinction}</p>}
                <p className="font-serif text-2xl sm:text-3xl leading-snug">{turn.reveal}</p>
                {turn.uncertain && <p className="text-sm text-[#8A847C] border-t border-[#E7E0D8] pt-4">Emin olunmayan: {turn.uncertain}</p>}
              </>
            )}
            <DoneActions turn={turn} onNew={newStory} onHome={toCards} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
