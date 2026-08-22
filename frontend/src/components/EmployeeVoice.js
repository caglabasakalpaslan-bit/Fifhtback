import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Music4, Disc3, X, Sparkles, ArrowRight, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { interpretFeedback } from "../lib/api";
import { SONG_SUGGESTIONS, DEMO_PRESETS } from "../data/constants";
import { AiInterpreterCard } from "./AiInterpreterCard";

export const EmployeeVoice = ({ onConfirmed }) => {
  const [text, setText] = useState("");
  const [songOpen, setSongOpen] = useState(false);
  const [song, setSong] = useState({ title: "", artist: "" });
  const [loading, setLoading] = useState(false);
  const [interpretation, setInterpretation] = useState(null);

  const hasSong = song.title.trim() && song.artist.trim();

  const runInterpret = async (overrideText, overrideSong) => {
    const t = (overrideText ?? text).trim();
    if (!t) {
      toast("Tell us what's happening first.", { description: "Even a sentence is enough." });
      return;
    }
    setLoading(true);
    setInterpretation(null);
    try {
      const s = overrideSong !== undefined ? overrideSong : hasSong ? song : null;
      const result = await interpretFeedback(t, s);
      setInterpretation(result);
    } catch (e) {
      toast.error("The interpreter stumbled. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (preset) => {
    setText(preset.text);
    if (preset.song) {
      setSong(preset.song);
      setSongOpen(true);
    } else {
      setSong({ title: "", artist: "" });
      setSongOpen(false);
    }
    setInterpretation(null);
    runInterpret(preset.text, preset.song || null);
  };

  const reset = () => {
    setText("");
    setSong({ title: "", artist: "" });
    setSongOpen(false);
    setInterpretation(null);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start py-8 sm:py-12">
      {/* Left: the prompt */}
      <div className="lg:col-span-7 space-y-6">
        <div>
          <span className="text-xs font-mono uppercase tracking-[0.22em] text-[#C85A32] font-semibold">
            One question. No forms.
          </span>
          <h1 className="mt-3 font-serif text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tight leading-[1.05]">
            What's happening?
          </h1>
          <p className="mt-4 text-lg text-[#57534E] leading-relaxed max-w-xl">
            Write it however it lives in your head — a problem, a request, a bit of
            tension, an idea, or something good worth saying. We'll reflect it back,
            never twist it.
          </p>
        </div>

        <div className="rounded-2xl border border-[#E7E0D8] bg-white shadow-sm overflow-hidden">
          <textarea
            data-testid="input-whats-happening"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Start typing... it stays anonymous."
            rows={6}
            className="w-full resize-none px-5 py-4 text-base leading-relaxed bg-transparent outline-none placeholder:text-[#B8B0A6]"
          />

          {/* Song drawer */}
          <AnimatePresence>
            {songOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-[#F0EAE2] bg-[#FBF7F2] overflow-hidden"
              >
                <div className="px-5 py-4 space-y-3">
                  <div className="flex items-center gap-2 text-[#C85A32]">
                    <Disc3 className={`h-4 w-4 ${hasSong ? "vinyl-spin" : ""}`} />
                    <span className="text-xs font-mono uppercase tracking-[0.18em] font-semibold">
                      Express it with a song
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      data-testid="input-song-title"
                      value={song.title}
                      onChange={(e) => setSong({ ...song, title: e.target.value })}
                      placeholder="Song title"
                      className="rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]"
                    />
                    <input
                      data-testid="input-song-artist"
                      value={song.artist}
                      onChange={(e) => setSong({ ...song, artist: e.target.value })}
                      placeholder="Artist"
                      className="rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]"
                    />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {SONG_SUGGESTIONS.map((s) => (
                      <button
                        key={s.title}
                        data-testid={`song-suggestion-${s.title.replace(/\s+/g, "-").toLowerCase()}`}
                        onClick={() => setSong(s)}
                        className="text-[11px] rounded-full border border-[#E7E0D8] bg-white px-2.5 py-1 text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors"
                      >
                        {s.title}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex items-center justify-between px-4 py-3 border-t border-[#F0EAE2] bg-[#FDFCFA]">
            <button
              data-testid="toggle-song-btn"
              onClick={() => setSongOpen((v) => !v)}
              className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
                songOpen ? "text-[#C85A32]" : "text-[#8A847C] hover:text-[#57534E]"
              }`}
            >
              {songOpen ? <X className="h-4 w-4" /> : <Music4 className="h-4 w-4" />}
              {songOpen ? "Remove song" : "Express it with a song"}
            </button>
            <button
              data-testid="submit-feedback-btn"
              onClick={() => runInterpret()}
              disabled={loading}
              className="group flex items-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] transition-transform active:scale-[0.98] disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-[#C85A32]" />}
              {loading ? "Interpreting…" : "Interpret this"}
              {!loading && <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />}
            </button>
          </div>
        </div>

        {/* Demo presets */}
        <div className="rounded-2xl border border-dashed border-[#E7E0D8] bg-[#FBF7F2]/60 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A847C] font-semibold">
              60-second demo · one click
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {DEMO_PRESETS.map((p) => (
              <button
                key={p.key}
                data-testid={`demo-preset-${p.key}`}
                onClick={() => applyPreset(p)}
                className="text-xs rounded-full border border-[#E7E0D8] bg-white px-3 py-1.5 font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors active:scale-[0.98]"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right: interpreter */}
      <div className="lg:col-span-5 space-y-6 lg:sticky lg:top-24">
        <AnimatePresence mode="wait">
          {interpretation ? (
            <AiInterpreterCard
              key={interpretation.id}
              interpretation={interpretation}
              setInterpretation={setInterpretation}
              text={text}
              song={hasSong ? song : null}
              onConfirmed={() => {
                onConfirmed?.();
                reset();
              }}
            />
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-2xl border border-[#E7E0D8] bg-white p-6 shadow-sm"
            >
              <div className="flex items-center gap-2 text-[#3F6B56]">
                <ShieldCheck className="h-4 w-4" />
                <span className="text-xs font-mono uppercase tracking-[0.18em] font-semibold">
                  Feedback Interpreter
                </span>
              </div>
              <p className="mt-4 font-serif text-2xl leading-snug text-[#1A1816]">
                A quiet mirror, not a judge.
              </p>
              <ul className="mt-4 space-y-2.5 text-sm text-[#57534E]">
                <li className="flex gap-2"><span className="text-[#C85A32]">—</span> Reflects only what you actually said</li>
                <li className="flex gap-2"><span className="text-[#C85A32]">—</span> Never forces an "A vs B" dilemma</li>
                <li className="flex gap-2"><span className="text-[#C85A32]">—</span> Never diagnoses you or invents meaning</li>
                <li className="flex gap-2"><span className="text-[#C85A32]">—</span> You confirm before anything is kept</li>
              </ul>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
