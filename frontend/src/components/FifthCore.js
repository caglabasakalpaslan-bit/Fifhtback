import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Loader2, PenLine, BookOpen, RotateCcw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { getFifthStories, startFifth, answerFifth } from "../lib/api";

// The Fifth — first working prototype.
// Screen flow: identity → two doors → (story | card + "tanıdık gelen") → at most ONE question → Reveal → stop.
// All reasoning lives in ONE backend call; this component only sequences screens.

const DEFAULT_AVATARS = ["🦊", "🐢", "🦉", "🐙", "🐺", "🌱"];

const Label = ({ children }) => (
  <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#C85A32] font-semibold">{children}</span>
);

const PrimaryBtn = ({ children, loading, testId, ...props }) => (
  <button
    data-testid={testId}
    disabled={loading || props.disabled}
    {...props}
    className="group inline-flex items-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] transition-transform active:scale-[0.98] disabled:opacity-50"
  >
    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-[#C85A32]" />}
    {children}
    {!loading && <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />}
  </button>
);

const fade = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 } };

export const FifthCore = () => {
  const [step, setStep] = useState("identity"); // identity | doors | tell | find | turn
  const [nickname, setNickname] = useState("");
  const [avatars, setAvatars] = useState(DEFAULT_AVATARS);
  const [avatar, setAvatar] = useState(DEFAULT_AVATARS[0]);
  const [door, setDoor] = useState(null);
  const [story, setStory] = useState("");
  const [cards, setCards] = useState([]);
  const [card, setCard] = useState(null);
  const [familiar, setFamiliar] = useState("");
  const [turn, setTurn] = useState(null); // backend FifthTurn
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getFifthStories()
      .then((d) => {
        setCards(d.stories || []);
        if (d.avatars?.length) setAvatars(d.avatars);
      })
      .catch(() => {});
  }, []);

  const reset = () => {
    setStep("doors");
    setDoor(null);
    setStory("");
    setCard(null);
    setFamiliar("");
    setTurn(null);
    setAnswer("");
  };

  const begin = async () => {
    const payload = { nickname: nickname.trim(), avatar, door };
    if (door === "tell") {
      if (!story.trim()) return toast("Önce hikâyeni anlat.", { description: "Birkaç cümle yeterli." });
      payload.story = story.trim();
    } else {
      if (!card) return toast("Önce bir hikâye seç.");
      if (!familiar.trim()) return toast("Burada sana tanıdık gelen neydi?");
      payload.story_card_id = card.id;
      payload.familiar = familiar.trim();
    }
    setLoading(true);
    try {
      const t = await startFifth(payload);
      setTurn(t);
      setStep("turn");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Çekirdek takıldı. Tekrar dene.");
    } finally {
      setLoading(false);
    }
  };

  const reply = async (text) => {
    const a = (text ?? answer).trim();
    if (!a) return toast("Bir seçenek seç ya da kısaca yaz.");
    setLoading(true);
    try {
      const t = await answerFifth(turn.session_id, a);
      setTurn(t);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Çekirdek takıldı. Tekrar dene.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 sm:py-16">
      <AnimatePresence mode="wait">
        {/* ---------- SCREEN 1: identity ---------- */}
        {step === "identity" && (
          <motion.section key="identity" {...fade} className="space-y-8">
            <div>
              <Label>The Fifth · prototip</Label>
              <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">
                Sana ne diyelim?
              </h1>
              <p className="mt-3 text-[#57534E]">Bir takma ad ve bir avatar. Test değil, oyun.</p>
            </div>
            <input
              data-testid="fifth-nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="takma ad"
              maxLength={40}
              className="w-full rounded-2xl border border-[#E7E0D8] bg-white px-5 py-4 text-lg outline-none focus:border-[#C85A32]"
            />
            <div className="flex flex-wrap gap-3">
              {avatars.map((a) => (
                <button
                  key={a}
                  data-testid={`fifth-avatar-${a}`}
                  onClick={() => setAvatar(a)}
                  className={`h-14 w-14 rounded-full text-2xl border-2 transition-transform active:scale-95 ${
                    avatar === a ? "border-[#C85A32] bg-[#FDF2EC]" : "border-[#E7E0D8] bg-white hover:border-[#C85A32]"
                  }`}
                  aria-label={`avatar ${a}`}
                >
                  {a}
                </button>
              ))}
            </div>
            <PrimaryBtn testId="fifth-identity-next" disabled={!nickname.trim()} onClick={() => setStep("doors")}>
              Devam
            </PrimaryBtn>
          </motion.section>
        )}

        {/* ---------- SCREEN 2: two doors ---------- */}
        {step === "doors" && (
          <motion.section key="doors" {...fade} className="space-y-8">
            <div>
              <Label>{avatar} {nickname}</Label>
              <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">
                İki kapı var.
              </h1>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                data-testid="fifth-door-tell"
                onClick={() => { setDoor("tell"); setStep("tell"); }}
                className="text-left rounded-2xl border border-[#E7E0D8] bg-white p-6 shadow-sm hover:border-[#C85A32] transition-colors"
              >
                <PenLine className="h-5 w-5 text-[#C85A32]" />
                <div className="mt-4 font-serif text-2xl">Hikâyemi anlatacağım</div>
                <div className="mt-1 text-sm text-[#8A847C]">Olanı olduğu gibi yaz.</div>
              </button>
              <button
                data-testid="fifth-door-find"
                onClick={() => { setDoor("find"); setStep("find"); }}
                className="text-left rounded-2xl border border-[#E7E0D8] bg-white p-6 shadow-sm hover:border-[#3F6B56] transition-colors"
              >
                <BookOpen className="h-5 w-5 text-[#3F6B56]" />
                <div className="mt-4 font-serif text-2xl">Bir hikâyede kendimi bulacağım</div>
                <div className="mt-1 text-sm text-[#8A847C]">Birkaç kısa hikâye; tanıdık geleni seç.</div>
              </button>
            </div>
          </motion.section>
        )}

        {/* ---------- DOOR A: tell my story ---------- */}
        {step === "tell" && (
          <motion.section key="tell" {...fade} className="space-y-6">
            <div>
              <Label>Hikâyemi anlatacağım</Label>
              <h1 className="mt-3 font-serif text-3xl sm:text-4xl font-medium tracking-tight">Ne oldu?</h1>
              <p className="mt-2 text-[#57534E]">Aklında nasıl duruyorsa öyle. Düzeltmene gerek yok.</p>
            </div>
            <textarea
              data-testid="fifth-story"
              value={story}
              onChange={(e) => setStory(e.target.value)}
              rows={7}
              placeholder="Yazmaya başla…"
              className="w-full resize-none rounded-2xl border border-[#E7E0D8] bg-white px-5 py-4 text-base leading-relaxed outline-none focus:border-[#C85A32] placeholder:text-[#B8B0A6]"
            />
            <div className="flex items-center justify-between">
              <button onClick={reset} className="text-sm text-[#8A847C] hover:text-[#57534E]">← Kapılara dön</button>
              <PrimaryBtn testId="fifth-submit-story" loading={loading} onClick={begin}>
                {loading ? "Dinliyor…" : "Anlat"}
              </PrimaryBtn>
            </div>
          </motion.section>
        )}

        {/* ---------- DOOR B: find myself in a story ---------- */}
        {step === "find" && (
          <motion.section key="find" {...fade} className="space-y-6">
            <div>
              <Label>Bir hikâyede kendimi bulacağım</Label>
              <h1 className="mt-3 font-serif text-3xl sm:text-4xl font-medium tracking-tight">Hangisi tanıdık?</h1>
              <p className="mt-2 text-sm text-[#8A847C]">Prototip içerik · bunlar mercek, hüküm değil.</p>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {cards.map((c) => (
                <button
                  key={c.id}
                  data-testid={`fifth-card-${c.id}`}
                  onClick={() => setCard(c)}
                  className={`text-left rounded-2xl border p-5 transition-colors ${
                    card?.id === c.id ? "border-[#3F6B56] bg-[#EDF5F0]" : "border-[#E7E0D8] bg-white hover:border-[#3F6B56]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-serif text-xl">{c.title}</span>
                    <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-[#8A847C]">{c.lens}</span>
                  </div>
                  <p className="mt-2 text-sm text-[#57534E] leading-relaxed">{c.text}</p>
                </button>
              ))}
              {cards.length === 0 && <p className="text-sm text-[#8A847C]">Hikâyeler yükleniyor…</p>}
            </div>
            <AnimatePresence>
              {card && (
                <motion.div {...fade} className="space-y-3">
                  <p className="font-serif text-2xl">Burada sana tanıdık gelen ne?</p>
                  <textarea
                    data-testid="fifth-familiar"
                    value={familiar}
                    onChange={(e) => setFamiliar(e.target.value)}
                    rows={3}
                    placeholder="Bir iki cümle yeter…"
                    className="w-full resize-none rounded-2xl border border-[#E7E0D8] bg-white px-5 py-3 text-base outline-none focus:border-[#3F6B56] placeholder:text-[#B8B0A6]"
                  />
                </motion.div>
              )}
            </AnimatePresence>
            <div className="flex items-center justify-between">
              <button onClick={reset} className="text-sm text-[#8A847C] hover:text-[#57534E]">← Kapılara dön</button>
              <PrimaryBtn testId="fifth-submit-familiar" loading={loading} disabled={!card} onClick={begin}>
                {loading ? "Dinliyor…" : "Devam"}
              </PrimaryBtn>
            </div>
          </motion.section>
        )}

        {/* ---------- TURN: one question, or the Reveal ---------- */}
        {step === "turn" && turn && (
          <motion.section key={`turn-${turn.status}`} {...fade} className="space-y-6">
            {turn.noticed?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {turn.noticed.map((n, i) => (
                  <span key={i} className="text-xs rounded-full border border-[#E7E0D8] bg-white px-3 py-1 text-[#57534E]">{n}</span>
                ))}
              </div>
            )}

            {turn.status === "question" ? (
              <div className="rounded-2xl border border-[#E7E0D8] bg-white p-6 shadow-sm space-y-5" data-testid="fifth-question">
                <Label>Tek soru</Label>
                <p className="font-serif text-2xl sm:text-3xl leading-snug">{turn.question}</p>
                {turn.why_ask && <p className="text-sm text-[#8A847C]">{turn.why_ask}</p>}
                <div className="flex flex-wrap gap-2">
                  {turn.options.map((o) => (
                    <button
                      key={o}
                      data-testid="fifth-option"
                      disabled={loading}
                      onClick={() => reply(o)}
                      className="rounded-full border border-[#E7E0D8] bg-white px-4 py-2 text-sm font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors disabled:opacity-50"
                    >
                      {o}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    data-testid="fifth-answer"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && reply()}
                    placeholder="ya da kısaca yaz…"
                    className="flex-1 rounded-full border border-[#E7E0D8] bg-white px-4 py-2 text-sm outline-none focus:border-[#C85A32]"
                  />
                  <PrimaryBtn testId="fifth-submit-answer" loading={loading} onClick={() => reply()}>
                    {loading ? "…" : "Gönder"}
                  </PrimaryBtn>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-[#E7E0D8] bg-[#FBF7F2] p-6 sm:p-8 shadow-sm space-y-5" data-testid="fifth-reveal">
                <Label>Açıklama</Label>
                {turn.distinction && (
                  <p className="text-sm font-mono uppercase tracking-[0.12em] text-[#3F6B56]">{turn.distinction}</p>
                )}
                <p className="font-serif text-2xl sm:text-3xl leading-snug">{turn.reveal}</p>
                {turn.uncertain && (
                  <p className="text-sm text-[#8A847C] border-t border-[#E7E0D8] pt-4">Emin olunmayan: {turn.uncertain}</p>
                )}
                {turn.source === "fallback" && (
                  <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#B04D27]">yedek çıktı · model erişilemedi</p>
                )}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-sm text-[#8A847C]">Burada duruyoruz, {nickname}.</span>
                  <button
                    data-testid="fifth-restart"
                    onClick={reset}
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-[#57534E] hover:text-[#1A1816]"
                  >
                    <RotateCcw className="h-4 w-4" /> Başka bir hikâye
                  </button>
                </div>
              </div>
            )}
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
};
