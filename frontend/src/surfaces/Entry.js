import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PenLine, Mic, Compass, ArrowRight, Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { ENTRY, REFLECT } from "../data/copy";
import { DICTIONARY, STORY_BY_CLUSTER } from "../data/stories";
import { interpretFeedback } from "../lib/api";
import { addSignal } from "../lib/mySignals";
import { VoiceCapture } from "../components/VoiceCapture";
import { Welcome } from "./Welcome";
import { hasSeenWelcome } from "../lib/entryContext";

const PathButton = ({ icon: Icon, label, active, onClick, testId }) => (
  <button
    data-testid={testId}
    onClick={onClick}
    className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors ${
      active ? "border-[#1A1816] bg-[#1A1816] text-[#FAF8F5]" : "border-[#E7E0D8] bg-white text-[#57534E] hover:border-[#C9C0B6]"
    }`}
  >
    <Icon className="h-4 w-4" /> {label}
  </button>
);

export const Entry = ({ onSaved }) => {
  const [mode, setMode] = useState("write"); // write | speak | find
  // First visit gets one short welcome/context step before "Söyle".
  const [welcomed, setWelcomed] = useState(() => hasSeenWelcome());
  const [allPhrases, setAllPhrases] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [reflection, setReflection] = useState(null);

  const submit = async (value, clusterId = null) => {
    const t = (value ?? text).trim();
    if (!t) {
      toast("Bir cümle yeterli.");
      return;
    }
    setLoading(true);
    try {
      // EXISTING backend interpreter — not reimplemented here.
      const result = await interpretFeedback(t, null);
      const cid = clusterId;
      const story = cid ? STORY_BY_CLUSTER[cid] : null;
      addSignal({ text: t, clusterId: cid, storyTitle: story?.title || null, matched: Boolean(story) });
      setReflection({ story, interpretation: result });
      setText("");
      onSaved?.();
    } catch (e) {
      toast("Şu an gönderilemedi.", { description: "Bağlantıyı kontrol edip tekrar dene." });
    } finally {
      setLoading(false);
    }
  };

  if (!welcomed) return <Welcome onContinue={() => setWelcomed(true)} />;

  if (reflection) {
    const { story, interpretation } = reflection;
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="py-12 max-w-xl mx-auto" data-testid="entry-reflection">
        <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-[#8A847C]">{REFLECT.title}</p>
        {story ? (
          <>
            <h2 className="mt-3 font-serif text-3xl leading-tight text-[#1A1816]">{story.title}</h2>
            <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C]">{story.mechanism}</p>
            <p className="mt-4 text-[15px] leading-relaxed text-[#57534E]">
              Anlattığın, kurumda başkalarının da tarif ettiği bir hikâyeye yakın duruyor.
            </p>
          </>
        ) : (
          <>
            <h2 className="mt-3 font-serif text-3xl leading-tight text-[#1A1816]">Anlattığın kaydedildi.</h2>
            <p className="mt-4 text-[15px] leading-relaxed text-[#57534E]">
              Şu an bununla eşleşen bir hikâye yok. Benzer sinyaller geldikçe bunu göreceksin.
            </p>
          </>
        )}
        {interpretation?.pattern_candidate && (
          <p className="mt-4 rounded-xl border border-[#E7E0D8] bg-white px-4 py-3 text-[13px] text-[#8A847C]">
            Fifthback'in okuması: {interpretation.pattern_candidate}
          </p>
        )}
        <p className="mt-5 text-[13px] text-[#8A847C]">{REFLECT.enough}</p>
        <button
          data-testid="reflection-to-home"
          onClick={() => { setReflection(null); onSaved?.("home"); }}
          className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5]"
        >
          {REFLECT.toHome} <ArrowRight className="h-4 w-4" />
        </button>
      </motion.div>
    );
  }

  return (
    <div className="py-12 max-w-2xl mx-auto" data-testid="entry-surface">
      <h1 className="font-serif text-6xl leading-none text-[#1A1816]" data-testid="entry-title">{ENTRY.title}</h1>
      <p className="mt-3 text-[17px] text-[#57534E]">{ENTRY.sub}</p>

      <div className="mt-7 flex flex-wrap items-center gap-2">
        <PathButton icon={PenLine} label={ENTRY.paths.write} active={mode === "write"} onClick={() => setMode("write")} testId="path-write" />
        <PathButton icon={Mic} label={ENTRY.paths.speak} active={mode === "speak"} onClick={() => setMode("speak")} testId="path-speak" />
        <PathButton icon={Compass} label={ENTRY.paths.find} active={mode === "find"} onClick={() => setMode("find")} testId="path-find" />
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={mode} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-5">
          {mode === "write" && (
            <div>
              <textarea
                data-testid="entry-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={ENTRY.writePlaceholder}
                rows={5}
                className="w-full resize-none rounded-2xl border border-[#E7E0D8] bg-white p-5 font-serif text-lg leading-relaxed outline-none focus:border-[#C85A32]"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-[13px] text-[#8A847C]">{ENTRY.writeHint}</span>
                <button
                  data-testid="entry-submit"
                  onClick={() => submit()}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5] disabled:opacity-60"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />} {ENTRY.submit}
                </button>
              </div>
            </div>
          )}

          {mode === "speak" && <VoiceCapture onConfirm={(t) => submit(t)} onCancel={() => setMode("write")} />}

          {/* The phrases live here and only here — never duplicated below the fold. */}
          {mode === "find" && (
            <div data-testid="dictionary-full">
              <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-[#8A847C]">{ENTRY.dictionaryLabel}</p>
              <p className="mt-1 mb-3 text-[13px] text-[#8A847C]">{ENTRY.dictionaryHint}</p>
              {/* A short list first; the rest are here, one click away. Same routing. */}
              {(allPhrases ? DICTIONARY : DICTIONARY.filter((d) => d.featured)).map((d) => (
                <button
                  key={d.phrase}
                  data-testid="dictionary-phrase"
                  onClick={() => submit(d.phrase, d.cluster)}
                  className="block w-full text-left rounded-xl border border-[#E7E0D8] bg-white px-4 py-3 mb-2 font-serif text-[17px] text-[#1A1816] hover:border-[#C85A32] transition-colors"
                >
                  “{d.phrase}”
                </button>
              ))}
              {!allPhrases && (
                <button
                  data-testid="dictionary-more"
                  onClick={() => setAllPhrases(true)}
                  className="mt-1 inline-flex items-center gap-1.5 text-[13px] text-[#8A847C] hover:text-[#C85A32] transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" /> {ENTRY.dictionaryMore}
                </button>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

    </div>
  );
};
