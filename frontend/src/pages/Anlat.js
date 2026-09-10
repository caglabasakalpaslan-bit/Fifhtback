import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Mic, MicOff, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { startFifth, describeFifthError } from "../lib/api";
import { getIdentity, saveIdentity, ensureUserRef, getDraft, setDraft, setCurrentSession, getCurrentSession, getExplorationContext } from "../lib/storage";
import { useSpeechInput } from "../hooks/useSpeechInput";
import { BackLink } from "../components/BackLink";
import { ModelUnavailable } from "../components/ModelUnavailable";

const AVATARS = ["🦊", "🐢", "🦉", "🐙", "🐺", "🌱"];

// ANLAT — one composer, two ways in (type or speak). Sends to the existing Fifth Core unchanged.
export const Anlat = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const identity = getIdentity();
  const [nickname, setNickname] = useState(identity?.nickname || "");
  const [avatar, setAvatar] = useState(identity?.avatar || AVATARS[0]);
  const [text, setText] = useState(getDraft());
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState(null);
  const textareaRef = useRef(null);
  const current = getCurrentSession();

  useEffect(() => { setDraft(text); }, [text]);

  const appendSpeech = useCallback((chunk) => {
    setText((t) => (t ? (t.endsWith(" ") || t.endsWith("\n") ? t : t + " ") : "") + chunk);
  }, []);
  const speech = useSpeechInput({ lang: "tr-TR", onFinal: appendSpeech });

  // A nickname is optional: the story is the only thing required. Without one the card says "Misafir".
  const canSend = text.trim().length > 0 && !loading;

  const send = async () => {
    if (!text.trim()) return toast("Önce anlat.", { description: "Yaz ya da mikrofona bas. Birkaç cümle yeter." });
    speech.stop();
    const id = saveIdentity({ nickname: nickname.trim() || "Misafir", avatar });
    setLoading(true); setFailure(null);
    try {
      const turn = await startFifth({
        nickname: id.nickname, avatar: id.avatar, door: "tell", story: text.trim(),
        user_ref: ensureUserRef(), kind: "anlat", context: getExplorationContext() || undefined,
      });
      setCurrentSession(turn);
      navigate(`/anlat/${turn.session_id}`, { state: { turn } });
    } catch (e) {
      const f = describeFifthError(e);
      if (f.kind === "invalid") toast(f.message || "Bir şey eksik.");
      else setFailure(f.kind);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto py-10 sm:py-14 space-y-8">
      <BackLink to="/" label="Kapılara dön" testId="anlat-back" />
      <div>
        <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#C85A32] font-semibold">Anlat</p>
        <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">Burası sesinin duyulduğu yer.</h1>
        <p className="mt-3 text-[#57534E]">Aklında nasıl duruyorsa öyle. Yaz ya da söyle; düzeltmene gerek yok.</p>
      </div>

      {current && current.status === "question" && location.state?.fromTurn !== true && (
        <button
          data-testid="anlat-resume"
          onClick={() => navigate(`/anlat/${current.session_id}`)}
          className="w-full text-left rounded-2xl border border-[#D9E7DF] bg-[#EDF5F0] px-5 py-4 text-sm text-[#3F6B56] hover:border-[#3F6B56]"
        >
          Yarım kalan bir hikâyen var — tek soruya cevap bekliyor. Devam et →
        </button>
      )}

      {!identity?.nickname && (
        <div data-testid="anlat-identity" className="rounded-2xl border border-[#E7E0D8] bg-white p-5 space-y-3">
          <p className="text-sm text-[#57534E]">Sana ne diyelim? Bir takma ad, bir avatar. İstersen boş bırak.</p>
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <input
              data-testid="anlat-nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="takma ad"
              maxLength={40}
              className="flex-1 rounded-full border border-[#E7E0D8] bg-white px-4 py-2.5 text-base outline-none focus:border-[#C85A32]"
            />
            <div className="flex gap-2">
              {AVATARS.map((a) => (
                <button key={a} data-testid={`anlat-avatar-${a}`} onClick={() => setAvatar(a)} aria-label={`avatar ${a}`}
                  className={`h-10 w-10 rounded-full text-xl border-2 ${avatar === a ? "border-[#C85A32] bg-[#FDF2EC]" : "border-[#E7E0D8] bg-white"}`}>
                  {a}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div data-testid="anlat-composer" className={`rounded-3xl border bg-white shadow-sm transition-colors ${speech.listening ? "border-[#C85A32]" : "border-[#E7E0D8]"}`}>
        <textarea
          ref={textareaRef}
          data-testid="anlat-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder={speech.supported ? "Yazmaya başla… ya da mikrofona bas." : "Yazmaya başla…"}
          className="w-full resize-none rounded-t-3xl bg-transparent px-5 py-5 text-base leading-relaxed outline-none placeholder:text-[#B8B0A6]"
        />
        {speech.listening && (
          <div className="px-5 pb-2 text-sm text-[#C85A32]" data-testid="anlat-listening">
            Dinliyor… {speech.interim && <span className="text-[#8A847C] italic">{speech.interim}</span>}
          </div>
        )}
        <div className="flex items-center justify-between gap-3 border-t border-[#F0EAE2] px-4 py-3">
          <div className="flex items-center gap-2">
            {speech.supported ? (
              <button
                type="button"
                data-testid="anlat-mic"
                onClick={speech.listening ? speech.stop : speech.start}
                aria-pressed={speech.listening}
                className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-medium transition-colors ${
                  speech.listening ? "border-[#C85A32] bg-[#FDF2EC] text-[#C85A32]" : "border-[#E7E0D8] text-[#57534E] hover:border-[#C85A32]"
                }`}
              >
                {speech.listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                {speech.listening ? "Durdur" : "Sesli anlat"}
              </button>
            ) : (
              <span className="text-xs text-[#B8B0A6]" data-testid="anlat-mic-unsupported">Bu tarayıcıda sesli anlatım yok.</span>
            )}
            {speech.error && <span className="text-xs text-[#B04D27]">Mikrofon açılamadı.</span>}
          </div>
          <button
            type="button"
            data-testid="anlat-send"
            disabled={!canSend}
            onClick={send}
            className="inline-flex items-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? "Dinliyor…" : "Anlat"}
            {!loading && <ArrowRight className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {loading && (
        <p data-testid="anlat-waiting" className="text-sm text-[#8A847C]">
          Dinliyor. Bu bir dakikaya kadar sürebilir; sayfayı kapatma.
        </p>
      )}

      {failure && <ModelUnavailable kind={failure} onRetry={send} retrying={loading} />}
    </motion.div>
  );
};
