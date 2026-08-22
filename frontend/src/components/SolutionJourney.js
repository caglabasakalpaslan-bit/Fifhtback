import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check, Pencil, Quote, Tag, Sparkles, Disc3, Loader2, PartyPopper,
  Users, Clock, TrendingUp, Building2, User, GitBranch, ShieldCheck,
  ChevronLeft, ChevronRight, Plus, Send, AlertTriangle, Layers,
} from "lucide-react";
import { toast } from "sonner";
import { confirmFeedback } from "../lib/api";
import { TYPE_META } from "../data/constants";

const STEPS = [
  { key: "understand", title: "Seni nasıl anladık?", icon: Quote },
  { key: "prevalence", title: "Bu örüntü ne kadar yaygın?", icon: TrendingUp },
  { key: "tension", title: "Buradaki asıl gerilim ne?", icon: Layers },
  { key: "responsibility", title: "Kim ne yapabilir?", icon: GitBranch },
  { key: "closure", title: "Nasıl kapanabilir?", icon: ShieldCheck },
];

const slide = {
  enter: { opacity: 0, x: 24 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -24 },
};

export const SolutionJourney = ({ interpretation, setInterpretation, text, song, onConfirmed, onAddMore }) => {
  const [step, setStep] = useState(0);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(interpretation);
  const [adding, setAdding] = useState(false);
  const [extra, setExtra] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const meta = TYPE_META[interpretation.feedback_type] || TYPE_META.OTHER;
  const prevalence = interpretation.prevalence;

  const saveCorrection = () => {
    setInterpretation(draft);
    setEditing(false);
    toast("Teşekkürler — sana göre güncellendi.", { description: "Senin sözlerin, senin kararın." });
  };

  const submitAdd = () => {
    if (!extra.trim()) return;
    onAddMore?.(extra.trim());
    setAdding(false);
    setExtra("");
  };

  const confirm = async () => {
    setSaving(true);
    try {
      await confirmFeedback({ text, song, interpretation, corrected: false });
      setDone(true);
      toast.success("Duyuldu. Anonim örüntü havuzuna eklendi.", {
        description: "İsim yok, iz yok — yalnızca örüntü.",
      });
      setTimeout(() => onConfirmed?.(), 1500);
    } catch (e) {
      toast.error("Kaydedilemedi. Lütfen tekrar dene.");
    } finally {
      setSaving(false);
    }
  };

  const goCorrect = () => {
    setStep(0);
    setDraft(interpretation);
    setEditing(true);
    setAdding(false);
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

  const CurrentIcon = STEPS[step].icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#E7E0D8] bg-white shadow-sm overflow-hidden"
      data-testid="solution-journey"
    >
      {/* Header + stepper */}
      <div className="px-5 pt-5 pb-3 border-b border-[#F0EAE2]">
        <div className="flex items-center gap-2 text-[#3F6B56] mb-3">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D97706] opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#D97706]" />
          </span>
          <span className="text-xs font-mono uppercase tracking-[0.18em] font-semibold">
            Fifthback Çözüm Yolculuğu
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {STEPS.map((s, i) => (
            <button
              key={s.key}
              data-testid={`journey-step-dot-${i}`}
              onClick={() => { setStep(i); setEditing(false); setAdding(false); }}
              className="group flex-1"
              aria-label={s.title}
            >
              <div
                className={`h-1.5 rounded-full transition-colors ${
                  i === step ? "bg-[#C85A32]" : i < step ? "bg-[#3F6B56]" : "bg-[#E7E0D8]"
                }`}
              />
            </button>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-[#F4EFEA] flex items-center justify-center">
            <CurrentIcon className="h-4 w-4 text-[#C85A32]" />
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C]">
              Adım {step + 1} / {STEPS.length}
            </p>
            <h3 className="font-serif text-xl font-semibold text-[#1A1816] leading-tight">
              {STEPS[step].title}
            </h3>
          </div>
        </div>
      </div>

      {/* Step body */}
      <div className="px-5 py-5 min-h-[260px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={step + (editing ? "-edit" : "")}
            variants={slide}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
          >
            {/* STEP 0 — Understand */}
            {step === 0 && (
              <div className="space-y-5" data-testid="step-understand">
                <div>
                  <div className="flex items-center gap-1.5 mb-2 text-[#8A847C]">
                    <Tag className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-mono uppercase tracking-[0.14em]">Bunu şöyle anladık</span>
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
                </div>

                <div>
                  <div className="flex items-center gap-1.5 mb-2 text-[#8A847C]">
                    <Quote className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-mono uppercase tracking-[0.14em]">
                      Sinyaller · {interpretation.signals.length}
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
                  <p className="mt-3 text-xs text-[#8A847C] italic">
                    Yalnızca senin söylediklerini yansıtıyoruz — yorum katmıyoruz.
                  </p>
                </div>

                {editing && (
                  <div className="flex gap-2 pt-1">
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
                )}
              </div>
            )}

            {/* STEP 1 — Prevalence */}
            {step === 1 && (
              <div className="space-y-4" data-testid="step-prevalence">
                {prevalence?.found ? (
                  <>
                    <div className="rounded-lg border border-[#F0EAE2] bg-[#FDFCFA] p-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C] mb-1">
                        İlişkili örüntü
                      </p>
                      <p className="font-serif text-lg text-[#1A1816]">{prevalence.matched_title}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-lg border border-[#F0EAE2] p-3">
                        <div className="flex items-center gap-1.5 text-[#C85A32]">
                          <TrendingUp className="h-4 w-4" />
                          <span className="font-serif text-2xl">{prevalence.frequency}</span>
                        </div>
                        <p className="text-xs text-[#8A847C] mt-0.5">kez dile getirildi</p>
                      </div>
                      <div className="rounded-lg border border-[#F0EAE2] p-3">
                        <div className="flex items-center gap-1.5 text-[#57534E]">
                          <Clock className="h-4 w-4" />
                          <span className="font-medium">{prevalence.unresolved_for}</span>
                        </div>
                        <p className="text-xs text-[#8A847C] mt-0.5">çözülmeden geçen süre</p>
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5 text-[#8A847C] mb-1.5">
                        <Users className="h-3.5 w-3.5" />
                        <span className="text-[11px] font-mono uppercase tracking-[0.14em]">Etkilenen ekipler</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {prevalence.affected_teams.map((t) => (
                          <span key={t} className="rounded-md bg-[#F4EFEA] px-2.5 py-1 text-xs text-[#57534E]">{t}</span>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs text-[#8A847C] italic">
                      Buradaki sayılar yalnızca gerçek, anonim verilere dayanır — hiçbir kıyaslama uydurulmaz.
                    </p>
                  </>
                ) : (
                  <div className="rounded-xl border border-dashed border-[#E7E0D8] bg-[#FBF7F2]/60 p-6 text-center">
                    <TrendingUp className="h-6 w-6 text-[#B8B0A6] mx-auto mb-3" />
                    <p className="font-serif text-lg text-[#1A1816]">Henüz yeterli veri yok.</p>
                    <p className="mt-2 text-sm text-[#57534E] leading-relaxed">
                      Bunu şirket genelinde bir örüntüyle ilişkilendirecek kadar veri yok.
                      Sen ve başkaları paylaştıkça örüntüler kendiliğinden belirginleşir.
                    </p>
                    <p className="mt-3 text-xs text-[#8A847C] italic">
                      İstatistik ya da kıyaslama uydurmuyoruz.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* STEP 2 — Tension (co-active needs) */}
            {step === 2 && (
              <div className="space-y-3" data-testid="step-tension">
                <div className="flex items-start gap-2 rounded-lg bg-[#EDF5F0] border border-[#CDE3D6] px-3 py-2.5">
                  <Layers className="h-4 w-4 text-[#3F6B56] mt-0.5 shrink-0" />
                  <p className="text-xs text-[#3F6B56] leading-relaxed">
                    Bu bir “A mı, B mi?” seçimi değil — aşağıdaki ihtiyaçların hepsi aynı anda geçerli olabilir.
                  </p>
                </div>
                {interpretation.active_needs.map((n, i) => (
                  <div key={i} className="rounded-lg border border-[#F0EAE2] bg-[#FDFCFA] p-3" data-testid={`need-${i}`}>
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#F4EFEA] text-[11px] font-mono text-[#C85A32]">
                        {i + 1}
                      </span>
                      <p className="text-sm font-semibold text-[#1A1816]">{n.title}</p>
                    </div>
                    {n.detail && <p className="mt-1.5 text-sm text-[#57534E] leading-relaxed pl-7">{n.detail}</p>}
                  </div>
                ))}
              </div>
            )}

            {/* STEP 3 — Responsibility */}
            {step === 3 && (
              <div className="space-y-4" data-testid="step-responsibility">
                <p className="text-xs text-[#8A847C] italic">
                  Burada kimse suçlanmıyor — kurumun sorumluluğu ile senin kendi alanını ayrı ayrı gösteriyoruz.
                </p>
                <div className="rounded-lg border border-[#E0E7EC] bg-[#F5F8FA] p-4">
                  <div className="flex items-center gap-1.5 mb-2 text-[#334155]">
                    <Building2 className="h-4 w-4" />
                    <span className="text-[11px] font-mono uppercase tracking-[0.14em] font-semibold">Kurumun sorumluluğu</span>
                  </div>
                  <ul className="space-y-1.5">
                    {interpretation.responsibility.organizational.map((r, i) => (
                      <li key={i} className="flex gap-2 text-sm text-[#334155]">
                        <span className="text-[#64748B]">—</span> {r}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-[#DCE7E0] bg-[#EDF5F0] p-4">
                  <div className="flex items-center gap-1.5 mb-2 text-[#3F6B56]">
                    <User className="h-4 w-4" />
                    <span className="text-[11px] font-mono uppercase tracking-[0.14em] font-semibold">Senin alanın</span>
                  </div>
                  <ul className="space-y-1.5">
                    {interpretation.responsibility.personal.map((r, i) => (
                      <li key={i} className="flex gap-2 text-sm text-[#3F6B56]">
                        <span className="text-[#6B8F7C]">—</span> {r}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* STEP 4 — Closure */}
            {step === 4 && (
              <div className="space-y-3" data-testid="step-closure">
                {interpretation.safety_note && (
                  <div className="flex items-start gap-2 rounded-lg bg-[#EDF5F0] border border-[#CDE3D6] px-3 py-2.5" data-testid="safety-note">
                    <ShieldCheck className="h-4 w-4 text-[#3F6B56] mt-0.5 shrink-0" />
                    <p className="text-xs text-[#3F6B56] leading-relaxed">
                      <span className="font-semibold">Güvenlik notu: </span>{interpretation.safety_note}
                    </p>
                  </div>
                )}
                {interpretation.channels.map((c, i) => (
                  <div key={i} className="rounded-lg border border-[#F0EAE2] bg-[#FDFCFA] p-3" data-testid={`channel-${i}`}>
                    <p className="text-sm font-semibold text-[#1A1816]">{c.title}</p>
                    {c.detail && <p className="mt-1 text-sm text-[#57534E] leading-relaxed">{c.detail}</p>}
                    {c.tradeoff && (
                      <p className="mt-2 flex items-start gap-1.5 text-xs text-[#92400E]">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span><span className="font-medium">Dikkat: </span>{c.tradeoff}</span>
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Song note (always visible footer strip if present) */}
      {song && interpretation.song_note && (
        <div className="mx-5 mb-3 flex items-start gap-2 rounded-lg bg-[#FBF7F2] p-3">
          <Disc3 className="h-4 w-4 text-[#C85A32] vinyl-spin mt-0.5 shrink-0" />
          <p className="text-xs text-[#57534E] leading-relaxed">
            <span className="font-medium text-[#1A1816]">{song.title}</span> · {song.artist} — {interpretation.song_note}
          </p>
        </div>
      )}

      {/* Nav + actions */}
      <div className="border-t border-[#F0EAE2] bg-[#FDFCFA] px-5 py-4">
        {step < STEPS.length - 1 ? (
          <div className="flex items-center justify-between">
            <button
              data-testid="journey-back-btn"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm font-medium text-[#8A847C] disabled:opacity-40 hover:text-[#57534E] transition-colors"
            >
              <ChevronLeft className="h-4 w-4" /> Geri
            </button>
            <button
              data-testid="journey-next-btn"
              onClick={() => { setStep((s) => Math.min(STEPS.length - 1, s + 1)); setEditing(false); }}
              className="flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] active:scale-[0.98] transition-transform"
            >
              İleri <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {adding && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <textarea
                    data-testid="add-more-input"
                    value={extra}
                    onChange={(e) => setExtra(e.target.value)}
                    rows={3}
                    placeholder="Eklemek istediğin bir şey yaz — yeniden yorumlayalım."
                    className="w-full resize-none rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]"
                  />
                  <button
                    data-testid="submit-add-more-btn"
                    onClick={submitAdd}
                    className="mt-2 w-full rounded-full bg-[#C85A32] px-4 py-2 text-sm font-medium text-white active:scale-[0.98] transition-transform"
                  >
                    Ekle ve yeniden yorumla
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            <p className="font-serif text-lg text-[#1A1816]">Ne yapmak istersin?</p>
            <div className="grid grid-cols-1 gap-2">
              <button
                data-testid="confirm-interpretation-btn"
                onClick={confirm}
                disabled={saving}
                className="flex items-center justify-center gap-2 rounded-full bg-[#3F6B56] px-4 py-2.5 text-sm font-medium text-white active:scale-[0.98] transition-transform disabled:opacity-60"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Böyle gönder
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  data-testid="correct-interpretation-btn"
                  onClick={goCorrect}
                  disabled={saving}
                  className="flex items-center justify-center gap-1.5 rounded-full border border-[#E7E0D8] bg-white px-3 py-2.5 text-sm font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors"
                >
                  <Pencil className="h-4 w-4" /> Yanlış anlaşılanı düzelt
                </button>
                <button
                  data-testid="add-more-btn"
                  onClick={() => setAdding((v) => !v)}
                  disabled={saving}
                  className="flex items-center justify-center gap-1.5 rounded-full border border-[#E7E0D8] bg-white px-3 py-2.5 text-sm font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors"
                >
                  <Plus className="h-4 w-4" /> Bir şey ekle
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};
