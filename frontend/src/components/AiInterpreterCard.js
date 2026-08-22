import React, { useState } from "react";
import { motion } from "framer-motion";
import { Check, Pencil, Quote, Tag, Sparkles, Disc3, Loader2, PartyPopper } from "lucide-react";
import { toast } from "sonner";
import { confirmFeedback } from "../lib/api";
import { TYPE_META } from "../data/constants";

const container = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};
const item = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } };

export const AiInterpreterCard = ({ interpretation, setInterpretation, text, song, onConfirmed }) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [draft, setDraft] = useState(interpretation);

  const meta = TYPE_META[interpretation.feedback_type] || TYPE_META.OTHER;

  const saveCorrection = () => {
    setInterpretation(draft);
    setEditing(false);
    toast("Teşekkürler — sana göre güncellendi.", { description: "Senin sözlerin, senin kararın." });
  };

  const confirm = async (corrected) => {
    setSaving(true);
    try {
      await confirmFeedback({ text, song, interpretation, corrected });
      setDone(true);
      toast.success("Duyuldu. Anonim örüntü havuzuna eklendi.", {
        description: "İsim yok, iz yok — yalnızca örüntü.",
      });
      setTimeout(() => onConfirmed?.(), 1400);
    } catch (e) {
      toast.error("Kaydedilemedi. Lütfen tekrar dene.");
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] p-8 text-center shadow-sm"
        data-testid="confirmation-state"
      >
        <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-[#3F6B56] flex items-center justify-center">
          <PartyPopper className="h-6 w-6 text-white" />
        </div>
        <h3 className="font-serif text-2xl text-[#1A1816]">Duyuldu ve anonim kaldı.</h3>
        <p className="mt-2 text-sm text-[#57534E]">
          Geri bildirimin daha büyük bir örüntünün parçası oldu — hiçbir kimlik eklenmeden.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="rounded-2xl border border-[#E7E0D8] bg-white shadow-sm overflow-hidden"
      data-testid="interpreter-card"
    >
      <div className="flex items-center justify-between px-5 pt-5">
        <div className="flex items-center gap-2 text-[#3F6B56]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D97706] opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D97706]" />
          </span>
          <span className="text-xs font-mono uppercase tracking-[0.18em] font-semibold">
            Geri Bildirim Yorumlayıcı
          </span>
        </div>
        {!editing && (
          <button
            data-testid="edit-interpretation-btn"
            onClick={() => { setDraft(interpretation); setEditing(true); }}
            className="flex items-center gap-1 text-xs text-[#8A847C] hover:text-[#C85A32] transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" /> Düzenle
          </button>
        )}
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Type */}
        <motion.div variants={item}>
          <div className="flex items-center gap-1.5 mb-2 text-[#8A847C]">
            <Tag className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Bunu şöyle anladık</span>
          </div>
          {editing ? (
            <div className="flex flex-wrap gap-1.5" data-testid="type-editor">
              {Object.keys(TYPE_META).map((k) => (
                <button
                  key={k}
                  onClick={() => setDraft({ ...draft, feedback_type: k })}
                  className={`text-xs rounded-full border px-3 py-1 font-medium transition-colors ${
                    draft.feedback_type === k ? TYPE_META[k].badge : "bg-white text-[#8A847C] border-[#E7E0D8]"
                  }`}
                >
                  {TYPE_META[k].label}
                </button>
              ))}
            </div>
          ) : (
            <span
              data-testid="feedback-type-badge"
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold ${meta.badge}`}
            >
              <span className="h-2 w-2 rounded-full" style={{ background: meta.dot }} />
              {meta.label}
            </span>
          )}
        </motion.div>

        {/* Signals */}
        <motion.div variants={item}>
          <div className="flex items-center gap-1.5 mb-2 text-[#8A847C]">
            <Quote className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">
              Aktif sinyaller · {interpretation.signals.length}
            </span>
          </div>
          <div className="space-y-3" data-testid="signals-list">
            {(editing ? draft : interpretation).signals.map((s, i) => (
              <div key={i} className="rounded-lg border border-[#F0EAE2] bg-[#FDFCFA] p-3">
                {editing ? (
                  <input
                    value={draft.signals[i].label}
                    onChange={(e) => {
                      const ns = [...draft.signals];
                      ns[i] = { ...ns[i], label: e.target.value };
                      setDraft({ ...draft, signals: ns });
                    }}
                    className="w-full text-sm font-semibold text-[#1A1816] bg-transparent outline-none border-b border-dashed border-[#E7E0D8] pb-1"
                  />
                ) : (
                  <p className="text-sm font-semibold text-[#1A1816]">{s.label}</p>
                )}
                <p className="mt-2 font-mono text-xs text-[#92400E] bg-amber-50/80 border-l-2 border-amber-500 px-3 py-2 rounded-r-md leading-relaxed">
                  "{s.evidence}"
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Pattern candidate */}
        <motion.div variants={item}>
          <div className="flex items-center gap-1.5 mb-2 text-[#8A847C]">
            <Sparkles className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Örüntü adayı</span>
          </div>
          <p className="text-sm text-[#57534E] italic">"{interpretation.pattern_candidate}"</p>
        </motion.div>

        {song && interpretation.song_note && (
          <motion.div variants={item} className="flex items-start gap-2 rounded-lg bg-[#FBF7F2] p-3">
            <Disc3 className="h-4 w-4 text-[#C85A32] vinyl-spin mt-0.5 shrink-0" />
            <p className="text-xs text-[#57534E] leading-relaxed">
              <span className="font-medium text-[#1A1816]">{song.title}</span> · {song.artist} — {interpretation.song_note}
            </p>
          </motion.div>
        )}
      </div>

      {/* Confirm / correct */}
      <motion.div variants={item} className="border-t border-[#F0EAE2] bg-[#FDFCFA] px-5 py-4">
        {editing ? (
          <div className="flex gap-2">
            <button
              data-testid="save-correction-btn"
              onClick={saveCorrection}
              className="flex-1 rounded-full bg-[#1A1816] px-4 py-2.5 text-sm font-medium text-[#FAF8F5] active:scale-[0.98] transition-transform"
            >
              Düzeltmemi kaydet
            </button>
            <button
              onClick={() => setEditing(false)}
              className="rounded-full border border-[#E7E0D8] px-4 py-2.5 text-sm font-medium text-[#57534E]"
            >
              Vazgeç
            </button>
          </div>
        ) : (
          <>
            <p className="font-serif text-lg text-[#1A1816] mb-3">Seni doğru anladık mı?</p>
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                data-testid="confirm-interpretation-btn"
                onClick={() => confirm(false)}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 rounded-full bg-[#3F6B56] px-4 py-2.5 text-sm font-medium text-white active:scale-[0.98] transition-transform disabled:opacity-60"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Evet, doğru
              </button>
              <button
                data-testid="correct-interpretation-btn"
                onClick={() => { setDraft(interpretation); setEditing(true); }}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 rounded-full border border-[#E7E0D8] bg-white px-4 py-2.5 text-sm font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors"
              >
                <Pencil className="h-4 w-4" /> Tam değil — düzelt
              </button>
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  );
};
