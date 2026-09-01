import React, { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PenLine, Mic, Compass, ArrowRight, ArrowLeft, Loader2, Plus } from "lucide-react";
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
  // Set when the person picks a story starter, so the phrase keeps its cluster
  // through the edit step. Cleared as soon as they type something else.
  const [pendingCluster, setPendingCluster] = useState(null);
  // One action, one interpretation. Without this, a burst of clicks fired a
  // request each; they resolved together, every one wrote a card, and only the
  // last was ever shown.
  const inFlight = useRef(false);

  const submit = async (value, clusterId = null) => {
    const t = (value ?? text).trim();
    if (!t) {
      toast("Bir cümle yeterli.");
      return;
    }
    if (inFlight.current) return;
    inFlight.current = true;
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
      inFlight.current = false;
      setLoading(false);
    }
  };

  // A starter fills the writing field instead of firing a request, so the click
  // has an instant, visible result and nothing can pile up behind it.
  const pickStarter = (phrase, cluster) => {
    setText(phrase);
    setPendingCluster(cluster ?? null);
    setMode("write");
  };

  if (!welcomed) return <Welcome onContinue={() => setWelcomed(true)} />;

  if (reflection) {
    const { story, interpretation } = reflection;
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="py-12 max-w-xl mx-auto" data-testid="entry-reflection">
        {/* Leaving the result must never feel like losing it. */}
        <button
          data-testid="reflection-back"
          onClick={() => setReflection(null)}
          className="inline-flex items-center gap-1.5 text-[13px] text-[#8A847C] hover:text-[#C85A32] transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {REFLECT.back}
        </button>

        <p className="mt-6 text-[13px] text-[#8A847C]">{REFLECT.title}</p>

        {story ? (
          <>
            {/* The human sentence leads. The internal wording waits below. */}
            <h2 className="mt-2 font-serif text-[28px] leading-snug text-[#1A1816]" data-testid="reflection-plain">
              {story.plain || story.title}
            </h2>
            <p className="mt-5 text-[15px] leading-relaxed text-[#3A3632]">{REFLECT.similarLead}</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-[#8A847C]">{REFLECT.similarCaveat}</p>
          </>
        ) : (
          <>
            <h2 className="mt-2 font-serif text-[28px] leading-snug text-[#1A1816]" data-testid="reflection-plain">
              {REFLECT.noneLead}
            </h2>
            <p className="mt-5 text-[15px] leading-relaxed text-[#3A3632]">{REFLECT.noneBody}</p>
          </>
        )}

        {interpretation?.pattern_candidate && (
          <p className="mt-5 text-[15px] leading-relaxed text-[#3A3632]">
            {interpretation.pattern_candidate}
          </p>
        )}

        {/* Taxonomy is available, never the hero. */}
        {story && (
          <details className="mt-6 group" data-testid="reflection-technical">
            <summary className="cursor-pointer list-none text-[13px] text-[#8A847C] hover:text-[#C85A32] transition-colors">
              {REFLECT.technical}
            </summary>
            <p className="mt-2 text-[13px] text-[#57534E]">{story.mechanism}</p>
            <p className="mt-1 text-[13px] text-[#8A847C]">{story.title}</p>
          </details>
        )}

        <p className="mt-6 text-[13px] text-[#8A847C]">{REFLECT.enough}</p>
        <button
          data-testid="reflection-to-home"
          onClick={() => { setReflection(null); onSaved?.("home"); }}
          className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5]"
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
                onChange={(e) => { setText(e.target.value); setPendingCluster(null); }}
                placeholder={ENTRY.writePlaceholder}
                rows={5}
                className="w-full resize-none rounded-2xl border border-[#E7E0D8] bg-white p-5 font-serif text-lg leading-relaxed outline-none focus:border-[#C85A32]"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-[13px] text-[#8A847C]">{ENTRY.writeHint}</span>
                <button
                  data-testid="entry-submit"
                  onClick={() => submit(undefined, pendingCluster)}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5] disabled:opacity-60"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />} {ENTRY.submit}
                </button>
              </div>
            </div>
          )}

          {mode === "speak" && <VoiceCapture onConfirm={(t) => submit(t, null)} onCancel={() => setMode("write")} />}

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
                  disabled={loading}
                  onClick={() => pickStarter(d.phrase, d.cluster)}
                  className="block w-full text-left rounded-xl border border-[#E7E0D8] bg-white px-4 py-3 mb-2 font-serif text-[17px] text-[#1A1816] hover:border-[#C85A32] transition-colors disabled:opacity-50"
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
