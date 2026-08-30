import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2, Sparkles, ShieldCheck, ArrowRight, Trophy, Waypoints,
  Brain, Activity, History, Compass, Quote, HelpCircle, TrendingUp,
  Plus, X, ClipboardList, LayoutGrid, Link2, Save, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "./ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";
import {
  getPatternRoom, reanalyzePatternRoom, addPatternRoomSignals,
  getActionBoard, createAction, updateAction,
} from "../lib/api";
import { CLUSTER_COLORS } from "../data/constants";

const STATUSES = ["DETECTED", "INVESTIGATING", "TESTING", "RESOLVED", "REJECTED"];
const STATUS_TR = {
  DETECTED: "Tespit edildi", INVESTIGATING: "İnceleniyor", TESTING: "Test ediliyor",
  RESOLVED: "Çözüldü", REJECTED: "Reddedildi",
};
const STATUS_CLS = {
  DETECTED: "bg-blue-50 text-blue-700 border-blue-200",
  INVESTIGATING: "bg-amber-50 text-amber-700 border-amber-200",
  TESTING: "bg-violet-50 text-violet-700 border-violet-200",
  RESOLVED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  REJECTED: "bg-rose-50 text-rose-700 border-rose-200",
};

const stagger = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};
const pop = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

export const PatternRoom = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [openRank, setOpenRank] = useState(null);
  const [tab, setTab] = useState("room"); // room | board
  const [selectedClusterId, setSelectedClusterId] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addText, setAddText] = useState("");
  const [adding, setAdding] = useState(false);
  const [board, setBoard] = useState([]);
  const [movedRanks, setMovedRanks] = useState([]);

  useEffect(() => {
    getPatternRoom()
      .then(setData)
      .catch(() => toast.error("Analiz yüklenemedi."))
      .finally(() => setLoading(false));
    // Run once on mount to load the cached analysis.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshBoard = () => getActionBoard().then(setBoard).catch(() => {});
  useEffect(() => {
    if (tab === "board") refreshBoard();
    // refreshBoard is a stable inline fetch; only `tab` should re-trigger it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  // signalIndex -> cluster order index (for coloring)
  const signalCluster = useMemo(() => {
    const map = {};
    (data?.clusters || []).forEach((c, ci) => c.signal_indices.forEach((si) => { map[si] = ci; }));
    return map;
  }, [data]);

  const clusterOrder = useMemo(() => {
    const map = {};
    (data?.clusters || []).forEach((c, ci) => { map[c.id] = ci; });
    return map;
  }, [data]);

  const colorFor = (ci) => CLUSTER_COLORS[((ci ?? 0) % CLUSTER_COLORS.length + CLUSTER_COLORS.length) % CLUSTER_COLORS.length];

  const runReanalyze = async () => {
    setReanalyzing(true);
    toast("Fif sinyalleri yeniden kümeliyor…", { description: "Canlı analiz biraz sürebilir." });
    try {
      const res = await reanalyzePatternRoom();
      setData(res);
      toast.success("Canlı analiz tamamlandı.");
    } catch (e) {
      toast.error("Canlı analiz başarısız oldu.");
    } finally {
      setReanalyzing(false);
    }
  };

  const openPattern = data?.patterns?.find((p) => p.rank === openRank) || null;

  const submitAddSignals = async () => {
    const lines = addText.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) { toast("Her satıra bir sinyal yaz."); return; }
    setAdding(true);
    toast("Fif yeni sinyalleri mevcut havuza katıp yeniden kümeliyor…");
    try {
      const res = await addPatternRoomSignals(lines);
      setData(res);
      setAddText("");
      setShowAdd(false);
      setSelectedClusterId(null);
      const changed = res.clusters.filter((c) => c.is_new || c.changed);
      toast.success(`${lines.length} sinyal eklendi.`, {
        description: changed.length
          ? `Etkilenen küme: ${changed.map((c) => c.name).join(", ")}`
          : "Kümeler güncellendi.",
      });
    } catch (e) {
      toast.error("Sinyaller eklenemedi.");
    } finally {
      setAdding(false);
    }
  };

  const moveToBoard = async (p) => {
    try {
      await createAction({
        pattern_name: p.name,
        mechanism: p.mechanism,
        cluster_id: p.cluster_id,
        evidence_snapshot: p.evidence,
        hypothesis: p.inference,
        intervention: p.next_moves?.[0] || "",
      });
      setMovedRanks((r) => [...r, p.rank]);
      toast.success("Aksiyon panosuna taşındı.", { description: "Durum: Tespit edildi" });
      if (tab === "board") refreshBoard();
    } catch (e) {
      toast.error("Panoya taşınamadı.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-[#8A847C]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  const selCluster = data.clusters.find((c) => c.id === selectedClusterId) || null;
  const selSet = new Set(selCluster ? selCluster.signal_indices : []);
  const selPattern = selCluster ? data.patterns.find((p) => p.cluster_id === selCluster.id) : null;
  const selColor = selCluster ? colorFor(clusterOrder[selCluster.id]) : null;
  const newSet = new Set(data.new_signal_indices || []);

  return (
    <div className="py-8 sm:py-10" data-testid="pattern-room">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div>
          <span className="text-xs font-mono uppercase tracking-[0.28em] text-[#C85A32] font-semibold">
            Fifthback — Pattern Room
          </span>
          <h1 className="mt-2 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">
            Yüzeydeki gürültü, alttaki mekanizma.
          </h1>
          <p className="mt-3 text-base text-[#57534E] max-w-2xl leading-relaxed">
            Fif, anonim sinyalleri kelimeye göre değil, altta yatan iş-sistemi mekanizmasına göre kümeler.
            Farklı görünen şikâyetler çoğu zaman aynı darboğaza işaret eder.
          </p>
        </div>
        <div className="flex flex-col items-start md:items-end gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-full border border-[#E7E0D8] bg-white p-1">
              <button
                data-testid="pr-tab-room"
                onClick={() => setTab("room")}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${tab === "room" ? "bg-[#1A1816] text-[#FAF8F5]" : "text-[#57534E]"}`}
              >
                <LayoutGrid className="h-3.5 w-3.5" /> Oda
              </button>
              <button
                data-testid="pr-tab-board"
                onClick={() => setTab("board")}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${tab === "board" ? "bg-[#1A1816] text-[#FAF8F5]" : "text-[#57534E]"}`}
              >
                <ClipboardList className="h-3.5 w-3.5" /> Aksiyon Panosu
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid="pr-add-signals-btn"
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 rounded-full border border-[#E7E0D8] bg-white px-4 py-2.5 text-sm font-medium text-[#57534E] hover:border-[#C85A32] hover:text-[#C85A32] transition-colors"
            >
              <Plus className="h-4 w-4" /> Sinyal ekle
            </button>
            <button
              data-testid="pr-reanalyze-btn"
              onClick={runReanalyze}
              disabled={reanalyzing}
              className="flex items-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] active:scale-[0.98] transition-transform disabled:opacity-60"
            >
              {reanalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-[#C85A32]" />}
              {reanalyzing ? "Fif kümeliyor…" : "Fif ile yeniden analiz et"}
            </button>
          </div>
          <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C]" data-testid="pr-source">
            Kaynak: {data.source === "live" ? "canlı AI" : "hazır demo analizi"} · {data.signals.length} sinyal
          </span>
        </div>
      </div>

      {/* Add signals modal */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="max-w-lg bg-[#FAF8F5] border-[#E7E0D8]" data-testid="pr-add-dialog">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl text-left">Anonim sinyal ekle</DialogTitle>
            <DialogDescription className="text-left text-[#8A847C]">
              Her satıra bir sinyal yaz. Fif bunları mevcut havuza katıp yüzey kelimeye göre değil,
              altta yatan mekanizmaya göre yeniden kümeler.
            </DialogDescription>
          </DialogHeader>
          <textarea
            data-testid="pr-add-textarea"
            value={addText}
            onChange={(e) => setAddText(e.target.value)}
            rows={6}
            placeholder={"Onaylar hâlâ çok yavaş.\nKimin karar vereceği belli değil.\n..."}
            className="w-full resize-none rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]"
          />
          <button
            data-testid="pr-add-submit-btn"
            onClick={submitAddSignals}
            disabled={adding}
            className="w-full flex items-center justify-center gap-2 rounded-full bg-[#C85A32] px-4 py-2.5 text-sm font-medium text-white active:scale-[0.98] transition-transform disabled:opacity-60"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            {adding ? "Ekleniyor ve kümeleniyor…" : "Ekle ve yeniden kümele"}
          </button>
        </DialogContent>
      </Dialog>

      {/* 3-column room */}
      {tab === "room" && (<>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* LEFT — incoming pile */}
        <div className="lg:col-span-3">
          <div className="flex items-center gap-1.5 mb-3 text-[#8A847C]">
            <Waypoints className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Gelen sinyaller · {data.signals.length}</span>
          </div>
          <div className="rounded-2xl border border-[#E7E0D8] bg-white/70 p-3 max-h-[640px] overflow-y-auto no-scrollbar">
            <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-2">
              {data.signals.map((s, i) => {
                const col = colorFor(signalCluster[i]);
                const dimmed = selectedClusterId && !selSet.has(i);
                const lit = selectedClusterId && selSet.has(i);
                return (
                  <motion.div
                    key={i}
                    variants={pop}
                    data-testid={`pr-signal-${i}`}
                    className={`signal-float rounded-lg border ${col.border} ${col.bg} px-2.5 py-1.5 text-xs text-[#3A3632] leading-snug transition-all duration-300 ${dimmed ? "opacity-20" : "opacity-100"} ${lit ? "ring-2 ring-offset-1" : ""}`}
                    style={{ animationDelay: `${(i % 7) * 0.4}s`, ...(lit ? { boxShadow: `0 0 0 2px ${col.solid}` } : {}) }}
                  >
                    <span className="inline-block h-1.5 w-1.5 rounded-full mr-1.5 align-middle" style={{ background: col.dot }} />
                    {s}
                    {newSet.has(i) && (
                      <span className="ml-1.5 rounded-full bg-[#C85A32] px-1.5 py-0.5 text-[9px] font-mono uppercase text-white align-middle">yeni</span>
                    )}
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </div>

        {/* CENTER — clusters + FF Cam */}
        <div className="lg:col-span-4">
          {selCluster && selColor && (
            <motion.div
              initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
              data-testid="pr-why-together"
              className={`mb-3 rounded-2xl border ${selColor.border} ${selColor.bg} p-4`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[11px] font-mono uppercase tracking-[0.16em] font-semibold ${selColor.text}`}>
                  Neden birlikte? · FF Cam
                </span>
                <button data-testid="pr-why-close" onClick={() => setSelectedClusterId(null)} className="text-[#8A847C] hover:text-[#1A1816]">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="text-sm text-[#3A3632] leading-relaxed">{selPattern?.why_formed || selCluster.summary}</p>
              <div className="mt-3 space-y-2 text-xs">
                <div>
                  <span className="font-semibold text-[#2F5344]">Doğrudan kanıt · </span>
                  <span className="text-[#57534E]">{selCluster.signal_indices.length} sinyal bu mekanizmaya bağlandı.</span>
                </div>
                {selPattern?.inference && (
                  <div><span className="font-semibold text-[#334155]">AI çıkarımı · </span><span className="text-[#57534E]">{selPattern.inference}</span></div>
                )}
                {selPattern?.uncertain && (
                  <div><span className="font-semibold text-[#92400E]">Belirsizlik · </span><span className="text-[#57534E]">{selPattern.uncertain}</span></div>
                )}
              </div>
              {selPattern && (
                <button
                  data-testid="pr-why-detail-btn"
                  onClick={() => setOpenRank(selPattern.rank)}
                  className="mt-3 flex items-center gap-1 text-sm font-medium text-[#C85A32]"
                >
                  Tüm detayı aç <ArrowRight className="h-4 w-4" />
                </button>
              )}
            </motion.div>
          )}
          <div className="flex items-center gap-1.5 mb-3 text-[#8A847C]">
            <Brain className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Mekanizmaya göre kümeler · {data.clusters.length}</span>
          </div>
          <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-3">
            {data.clusters.map((c, ci) => {
              const col = colorFor(ci);
              const isSel = selectedClusterId === c.id;
              return (
                <motion.button
                  key={c.id}
                  variants={pop}
                  data-testid={`pr-cluster-${c.id}`}
                  onClick={() => setSelectedClusterId(isSel ? null : c.id)}
                  className={`w-full text-left rounded-2xl border ${col.border} ${col.bg} p-4 transition-all active:scale-[0.99] hover:shadow-sm ${isSel ? "ring-2 ring-offset-1" : ""}`}
                  style={isSel ? { boxShadow: `0 0 0 2px ${col.solid}` } : {}}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-mono uppercase tracking-[0.16em] font-semibold ${col.text}`}>
                      {c.mechanism}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {c.is_new && <span className="rounded-full bg-[#C85A32] px-1.5 py-0.5 text-[9px] font-mono uppercase text-white">yeni</span>}
                      {c.changed && <span className="rounded-full bg-[#D97706] px-1.5 py-0.5 text-[9px] font-mono uppercase text-white">güncellendi</span>}
                      <span className={`text-xs font-mono ${col.text}`}>{c.signal_indices.length} sinyal</span>
                    </div>
                  </div>
                  <h3 className="mt-1 font-serif text-lg font-semibold text-[#1A1816] leading-snug">{c.name}</h3>
                  {c.summary && <p className="mt-1 text-xs text-[#57534E] leading-relaxed">{c.summary}</p>}
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {c.signal_indices.map((si) => (
                      <span key={si} className="h-2 w-2 rounded-full" style={{ background: col.dot }} title={data.signals[si]} />
                    ))}
                  </div>
                </motion.button>
              );
            })}
          </motion.div>
        </div>

        {/* RIGHT — Top 5 */}
        <div className="lg:col-span-5">
          <div className="flex items-center gap-1.5 mb-3 text-[#8A847C]">
            <Trophy className="h-3.5 w-3.5" />
            <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Top 5 örüntü · etkiye göre</span>
          </div>
          <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-3" data-testid="pr-top5">
            {data.patterns.map((p) => {
              const col = colorFor(clusterOrder[p.cluster_id]);
              return (
                <motion.div
                  key={p.rank}
                  variants={pop}
                  data-testid={`pr-top-pattern-${p.rank}`}
                  onMouseEnter={() => setSelectedClusterId(p.cluster_id)}
                  className="rounded-2xl border border-[#E7E0D8] bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
                  style={{ borderLeft: `4px solid ${col.solid}` }}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-serif text-lg font-semibold" style={{ background: col.solid, color: "#FAF8F5" }}>
                      {p.rank}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-serif text-lg font-semibold text-[#1A1816] leading-snug">{p.name}</h3>
                      <span className={`inline-block mt-1 text-[10px] font-mono uppercase tracking-[0.14em] ${col.text}`}>{p.mechanism}</span>
                      <p className="mt-1.5 text-sm text-[#57534E] leading-relaxed line-clamp-2">{p.why_selected}</p>
                      <div className="mt-2.5 flex items-center justify-between">
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#8A847C]">
                          <Activity className="h-3 w-3" /> {p.confidence.split("—")[0].trim()}
                        </span>
                        <button
                          data-testid={`pr-open-${p.rank}`}
                          onClick={() => setOpenRank(p.rank)}
                          className="group flex items-center gap-1 text-sm font-medium text-[#C85A32]"
                        >
                          Aç <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </div>

      {/* Privacy line */}
      <div className="mt-6 flex items-center gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-3">
        <ShieldCheck className="h-4 w-4 text-[#3F6B56] shrink-0" />
        <p className="text-sm text-[#3F6B56]">
          Bu bir çalışan değerlendirmesi değildir. Kişilik, motivasyon, yetkinlik ya da duygu analiz edilmez —
          yalnızca iş sisteminin sürtünmesi incelenir.
        </p>
      </div>
      </>)}

      {tab === "board" && (
        <ActionBoardView board={board} refreshBoard={refreshBoard} />
      )}

      {/* Detail dialog */}
      <Dialog open={openRank !== null} onOpenChange={(o) => !o && setOpenRank(null)}>
        <DialogContent className="max-w-2xl bg-[#FAF8F5] border-[#E7E0D8]" data-testid="pr-detail-dialog">
          {openPattern && (() => {
            const col = colorFor(clusterOrder[openPattern.cluster_id]);
            return (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full font-serif text-sm font-semibold" style={{ background: col.solid, color: "#FAF8F5" }}>
                      {openPattern.rank}
                    </span>
                    <span className={`text-[10px] font-mono uppercase tracking-[0.16em] ${col.text}`}>{openPattern.mechanism}</span>
                  </div>
                  <DialogTitle className="font-serif text-2xl text-left">{openPattern.name}</DialogTitle>
                  <DialogDescription className="text-left text-[#8A847C]">
                    Fif bunu neden seçti: {openPattern.why_selected}
                  </DialogDescription>
                </DialogHeader>

                <Tabs defaultValue="cam" className="mt-1">
                  <TabsList className="grid grid-cols-4 bg-[#F4EFEA]">
                    <TabsTrigger value="cam" data-testid="pr-tab-cam"><Brain className="h-3.5 w-3.5 mr-1" /> Fifthback</TabsTrigger>
                    <TabsTrigger value="impact" data-testid="pr-tab-impact"><TrendingUp className="h-3.5 w-3.5 mr-1" /> Etki</TabsTrigger>
                    <TabsTrigger value="past" data-testid="pr-tab-past"><History className="h-3.5 w-3.5 mr-1" /> Geçmiş</TabsTrigger>
                    <TabsTrigger value="next" data-testid="pr-tab-next"><Compass className="h-3.5 w-3.5 mr-1" /> Hamle</TabsTrigger>
                  </TabsList>

                  <div className="max-h-[52vh] overflow-y-auto no-scrollbar mt-4 pr-1">
                    <TabsContent value="cam" className="space-y-4">
                      <Field icon={HelpCircle} label="Bu küme neden oluştu?">{openPattern.why_formed}</Field>
                      <div>
                        <FieldLabel icon={Quote}>Bunu destekleyen sinyaller</FieldLabel>
                        <div className="space-y-1.5">
                          {openPattern.evidence.map((e, i) => (
                            <p key={i} className="font-mono text-xs text-[#3A3632] bg-white border border-[#F0EAE2] rounded-md px-3 py-1.5">“{e}”</p>
                          ))}
                        </div>
                      </div>
                      <Field icon={Brain} label="Çıkarım nedir?">{openPattern.inference}</Field>
                      <Field icon={HelpCircle} label="Hâlâ belirsiz olan ne?" tone="amber">{openPattern.uncertain}</Field>
                      <Field icon={Trophy} label="Neden Top 5'e girdi?">{openPattern.why_top5}</Field>
                    </TabsContent>

                    <TabsContent value="impact" className="space-y-4">
                      <Field icon={Activity} label="Hangi işler etkileniyor?">{openPattern.affected_work}</Field>
                      <Field icon={TrendingUp} label="Tahmini örgütsel maliyet / etki" tone="amber">{openPattern.estimated_cost}</Field>
                      <Field icon={Sparkles} label="Çözülürse ne iyileşir?" tone="sage">{openPattern.what_improves}</Field>
                      <Field icon={ArrowRight} label="Sürtünme azalırsa olası kazanç" tone="sage">{openPattern.gain_if_reduced}</Field>
                      <Field icon={Activity} label="Güven / belirsizlik">{openPattern.confidence}</Field>
                    </TabsContent>

                    <TabsContent value="past" className="space-y-3">
                      {openPattern.past_patterns.length === 0 && (
                        <p className="text-sm text-[#8A847C]">Benzer geçmiş vaka bulunamadı.</p>
                      )}
                      {openPattern.past_patterns.map((pp, i) => (
                        <div key={i} className="rounded-lg border border-[#F0EAE2] bg-white p-3 space-y-1.5">
                          <p className="text-sm"><span className="font-semibold text-[#1A1816]">Denenen: </span><span className="text-[#57534E]">{pp.tried}</span></p>
                          <p className="text-sm"><span className="font-semibold text-[#3F6B56]">İşe yaradığı koşul: </span><span className="text-[#57534E]">{pp.conditions}</span></p>
                          <p className="text-sm"><span className="font-semibold text-[#1A1816]">Ne değişti: </span><span className="text-[#57534E]">{pp.changed}</span></p>
                          <p className="text-sm"><span className="font-semibold text-[#9F1239]">İşe yaramadığı durum: </span><span className="text-[#57534E]">{pp.when_failed}</span></p>
                        </div>
                      ))}
                    </TabsContent>

                    <TabsContent value="next" className="space-y-2.5">
                      <p className="text-xs text-[#8A847C] italic mb-1">En fazla 3 test edilebilir hamle — bunlar reçete değil, denenecek hipotezlerdir.</p>
                      {openPattern.next_moves.map((n, i) => (
                        <div key={i} data-testid={`pr-next-move-${i}`} className="flex items-start gap-2 rounded-lg border border-[#E9BCA6] bg-[#FDF2EC] px-3 py-2.5">
                          <Compass className="h-4 w-4 text-[#C85A32] mt-0.5 shrink-0" />
                          <p className="text-sm text-[#3A3632] leading-relaxed">{n}</p>
                        </div>
                      ))}
                    </TabsContent>
                  </div>
                </Tabs>

                <button
                  data-testid="pr-move-to-board-btn"
                  onClick={() => moveToBoard(openPattern)}
                  disabled={movedRanks.includes(openPattern.rank)}
                  className="mt-4 w-full flex items-center justify-center gap-2 rounded-full bg-[#1A1816] px-4 py-2.5 text-sm font-medium text-[#FAF8F5] active:scale-[0.98] transition-transform disabled:opacity-60"
                >
                  {movedRanks.includes(openPattern.rank)
                    ? <><CheckCircle2 className="h-4 w-4 text-[#3F6B56]" /> Panoya eklendi</>
                    : <><Link2 className="h-4 w-4 text-[#C85A32]" /> Aksiyon panosuna taşı</>}
                </button>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const FieldLabel = ({ icon: Icon, children }) => (
  <div className="flex items-center gap-1.5 mb-1.5 text-[#8A847C]">
    <Icon className="h-3.5 w-3.5" />
    <span className="text-[11px] font-mono uppercase tracking-[0.14em]">{children}</span>
  </div>
);

const Field = ({ icon, label, children, tone }) => {
  const toneCls = tone === "amber"
    ? "bg-amber-50 border-amber-200 text-amber-900"
    : tone === "sage"
    ? "bg-[#EDF5F0] border-[#CDE3D6] text-[#2F5344]"
    : "bg-white border-[#F0EAE2] text-[#3A3632]";
  return (
    <div>
      <FieldLabel icon={icon}>{label}</FieldLabel>
      <p className={`text-sm leading-relaxed rounded-lg border px-3 py-2.5 ${toneCls}`}>{children}</p>
    </div>
  );
};

const BoardCard = ({ item, onSaved }) => {
  const [status, setStatus] = useState(item.status);
  const [hypothesis, setHypothesis] = useState(item.hypothesis || "");
  const [intervention, setIntervention] = useState(item.intervention || "");
  const [outcome, setOutcome] = useState(item.outcome || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await updateAction(item.id, { status, hypothesis, intervention, outcome });
      onSaved(updated);
      toast.success("Kaydedildi.");
    } catch (e) {
      toast.error("Kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  const fmt = (iso) => { try { return new Date(iso).toLocaleString("tr-TR"); } catch { return iso; } };

  return (
    <div className="rounded-2xl border border-[#E7E0D8] bg-white p-4 shadow-sm" data-testid={`board-card-${item.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-semibold text-[#1A1816] leading-snug">{item.pattern_name}</h3>
          {item.mechanism && <span className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#8A847C]">{item.mechanism}</span>}
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${STATUS_CLS[status]}`}>{STATUS_TR[status]}</span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {STATUSES.map((s) => (
          <button
            key={s}
            data-testid={`board-status-${item.id}-${s}`}
            onClick={() => setStatus(s)}
            className={`text-[11px] rounded-full border px-2.5 py-1 font-medium transition-colors ${status === s ? STATUS_CLS[s] : "bg-white text-[#8A847C] border-[#E7E0D8]"}`}
          >
            {STATUS_TR[s]}
          </button>
        ))}
      </div>

      <div className="mt-3 space-y-2">
        <div>
          <FieldLabel icon={Brain}>Hipotez (yanlış olabilir)</FieldLabel>
          <textarea data-testid={`board-hypothesis-${item.id}`} value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} rows={2}
            className="w-full resize-none rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]" />
        </div>
        <div>
          <FieldLabel icon={Compass}>Seçilen müdahale</FieldLabel>
          <input value={intervention} onChange={(e) => setIntervention(e.target.value)}
            className="w-full rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]" />
        </div>
        <div>
          <FieldLabel icon={History}>Sonuç / düzeltme {status === "REJECTED" && "(neden yanlıştı?)"}</FieldLabel>
          <textarea data-testid={`board-outcome-${item.id}`} value={outcome} onChange={(e) => setOutcome(e.target.value)} rows={2}
            placeholder={status === "REJECTED" ? "Bu örüntü neden yanlış çıktı?" : "Ne gözlemlendi?"}
            className="w-full resize-none rounded-lg border border-[#E7E0D8] bg-white px-3 py-2 text-sm outline-none focus:border-[#C85A32]" />
        </div>
      </div>

      {item.evidence_snapshot?.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs text-[#8A847C] cursor-pointer">Kanıt anlık görüntüsü · {item.evidence_snapshot.length}</summary>
          <div className="mt-1.5 space-y-1">
            {item.evidence_snapshot.map((e, i) => (
              <p key={i} className="font-mono text-[11px] text-[#3A3632] bg-[#FDFCFA] border border-[#F0EAE2] rounded px-2 py-1">“{e}”</p>
            ))}
          </div>
        </details>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[10px] font-mono text-[#8A847C]">Oluşturma: {fmt(item.created_at)} · Güncelleme: {fmt(item.updated_at)}</span>
        <button data-testid={`board-save-${item.id}`} onClick={save} disabled={saving}
          className="flex items-center gap-1.5 rounded-full bg-[#1A1816] px-4 py-2 text-sm font-medium text-[#FAF8F5] active:scale-[0.98] transition-transform disabled:opacity-60">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Kaydet
        </button>
      </div>
    </div>
  );
};

const ActionBoardView = ({ board, refreshBoard }) => {
  const onSaved = () => refreshBoard();
  const counts = STATUSES.reduce((a, s) => ({ ...a, [s]: board.filter((b) => b.status === s).length }), {});
  return (
    <div data-testid="pr-action-board">
      <div className="flex items-center gap-1.5 mb-3 text-[#8A847C]">
        <ClipboardList className="h-3.5 w-3.5" />
        <span className="text-[11px] font-mono uppercase tracking-[0.16em]">Aksiyon panosu · {board.length} örüntü</span>
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {STATUSES.map((s) => (
          <span key={s} className={`rounded-full border px-3 py-1 text-xs font-medium ${STATUS_CLS[s]}`}>{STATUS_TR[s]} · {counts[s]}</span>
        ))}
      </div>
      {board.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#E7E0D8] bg-white/60 py-16 text-center text-[#8A847C]">
          Henüz takip edilen örüntü yok. Bir örüntüyü açıp “Aksiyon panosuna taşı” de.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {board.map((item) => <BoardCard key={item.id} item={item} onSaved={onSaved} />)}
        </div>
      )}
      <div className="mt-4 flex items-center gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-3">
        <ShieldCheck className="h-4 w-4 text-[#3F6B56] shrink-0" />
        <p className="text-sm text-[#3F6B56]">
          FIF hipotezleri yanlışlanabilir olmalıdır. Bir örüntünün yanlış olduğunu <strong>Reddedildi</strong> ile işaretleyip nedenini yazabilirsin.
          Zaman damgaları kaydediliyor; ileride gerçek eğilim görselleştirmesi bunun üzerine eklenecek.
        </p>
      </div>
    </div>
  );
};
