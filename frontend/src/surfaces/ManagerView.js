import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Loader2, Users, Repeat, Activity, MessageSquareOff, TrendingUp } from "lucide-react";
import { getPatterns } from "../lib/api";
import { MANAGER, DEMO_NOTE } from "../data/copy";
import { STORY_BY_PATTERN_TITLE } from "../data/stories";
import { pressureFromManagerPattern } from "../lib/pressure";
import { canShowAggregate, MIN_MANAGER_N } from "../lib/privacy";
import { PressureBar } from "../components/PressureBar";

const Axis = ({ icon: Icon, label, value, gated }) => (
  <div className="flex-1 min-w-[92px]">
    <div className="flex items-center gap-1 text-[#8A847C]">
      <Icon className="h-3 w-3" />
      <span className="text-[10px] font-mono uppercase tracking-[0.12em]">{label}</span>
    </div>
    <p className={`mt-0.5 text-[13px] ${gated ? "text-[#A8A29E] italic" : "text-[#1A1816]"}`}>{value}</p>
  </div>
);

export const ManagerView = () => {
  const [patterns, setPatterns] = useState(null);

  useEffect(() => {
    getPatterns().then(setPatterns).catch(() => setPatterns([]));
  }, []);

  const maxFreq = useMemo(
    () => Math.max(1, ...(patterns || []).map((p) => p.frequency || 0)),
    [patterns]
  );

  if (!patterns) {
    return <div className="py-24 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-[#8A847C]" /></div>;
  }

  return (
    <div className="py-12 max-w-3xl mx-auto" data-testid="manager-view">
      <h1 className="font-serif text-4xl text-[#1A1816]">{MANAGER.title}</h1>
      <p className="mt-2 text-[15px] text-[#57534E]">{MANAGER.sub}</p>
      <span className="mt-3 inline-block rounded-full bg-[#F4EFEA] px-2.5 py-0.5 text-[10px] text-[#8A847C]">
        {DEMO_NOTE}
      </span>

      <div className="mt-8 space-y-4">
        {patterns.map((p, i) => {
          const pressure = pressureFromManagerPattern(p, maxFreq);
          const n = p.frequency || 0;
          const visible = canShowAggregate(n, "manager");
          return (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-2xl border border-[#E7E0D8] bg-white p-5"
              data-testid="manager-story"
            >
              {/* PRIMARY: human language. Backend title becomes the small line. */}
              <h2 className="font-serif text-xl leading-snug text-[#1A1816]">
                {STORY_BY_PATTERN_TITLE[p.title] || p.title}
              </h2>
              <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C]">
                {p.title}
              </p>

              <div className="mt-4">
                {pressure.isFriction ? (
                  <PressureBar pressure={pressure} compact />
                ) : (
                  <p className="text-[13px] text-[#3F6B56]" data-testid="working-well">
                    {p.status === "RESOLVED" ? "Bu artık bir sürtüşme değil." : "Bu, işleyen bir şeyin işareti."}
                  </p>
                )}
              </div>

              {visible ? (
                <div className="mt-4 flex flex-wrap gap-4 border-t border-[#F0EAE2] pt-3" data-testid="manager-axes">
                  <Axis icon={Repeat} label={MANAGER.axes.repetition} value={`${n} anonim sinyal`} />
                  <Axis icon={Users} label={MANAGER.axes.spread} value={`${p.affected_teams?.length || 0} ekip`} />
                  <Axis icon={Activity} label={MANAGER.axes.impact} value={p.blocker ? "İşi yavaşlatıyor" : "Sınırlı"} />
                  {/* The engine does not measure this. We say so instead of guessing. */}
                  <Axis icon={MessageSquareOff} label={MANAGER.axes.voice} value="Henüz ölçülmüyor" gated />
                  <Axis icon={TrendingUp} label={MANAGER.axes.change} value={pressure.change?.label || "—"} />
                </div>
              ) : (
                <p className="mt-4 border-t border-[#F0EAE2] pt-3 text-[13px] text-[#A8A29E]" data-testid="manager-gated">
                  {MANAGER.gated} (en az {MIN_MANAGER_N} sinyal gerekir, şu an {n})
                </p>
              )}
            </motion.div>
          );
        })}
      </div>

      <div className="mt-8 flex items-start gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-3">
        <ShieldCheck className="h-4 w-4 text-[#3F6B56] shrink-0 mt-0.5" />
        <p className="text-[13px] text-[#3F6B56]">{MANAGER.never}</p>
      </div>
    </div>
  );
};
