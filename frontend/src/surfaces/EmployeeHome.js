import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Eye, EyeOff, Trash2 } from "lucide-react";
import { HOME, STATES } from "../data/copy";
import { loadSignals, updateSignal, removeSignal } from "../lib/mySignals";

const TONE = {
  blue: "bg-blue-50 text-blue-700 border-blue-200",
  violet: "bg-violet-50 text-violet-700 border-violet-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  teal: "bg-teal-50 text-teal-700 border-teal-200",
  sage: "bg-emerald-50 text-emerald-700 border-emerald-200",
  green: "bg-emerald-50 text-emerald-800 border-emerald-300",
};

// Compact journey: what already happened, then the step that comes next.
const JOURNEY = ["NEW", "MATCHED", "SHARED", "MOVING", "RESOLVED"];
const JOURNEY_STEP = {
  NEW: "Söyledin",
  MATCHED: "Benzer hikâyeler bulundu",
  SHARED: "Paylaştın",
  MOVING: "Değişim var",
  RESOLVED: "Çözüldü",
};

const Journey = ({ state }) => {
  const idx = Math.max(0, JOURNEY.indexOf(state));
  const next = JOURNEY[idx + 1];
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[12px]" data-testid="journey-line">
      {JOURNEY.slice(0, idx + 1).map((s, i) => (
        <React.Fragment key={s}>
          {i > 0 && <span className="text-[#C9C0B6]">→</span>}
          <span className="text-[#3A3632]">{JOURNEY_STEP[s]}</span>
        </React.Fragment>
      ))}
      {next && (
        <>
          <span className="text-[#C9C0B6]">→</span>
          <span className="text-[#A8A29E]">{JOURNEY_STEP[next]}</span>
        </>
      )}
    </div>
  );
};

const StateChip = ({ state }) => {
  const meta = STATES[state] || STATES.NEW;
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-[11px] ${TONE[meta.tone]}`} data-testid="state-chip">
      {meta.label}
    </span>
  );
};

export const EmployeeHome = ({ onStart }) => {
  const [signals, setSignals] = useState([]);
  useEffect(() => setSignals(loadSignals()), []);

  const toggleShare = (s) => {
    const shared = !s.shared;
    setSignals(updateSignal(s.id, { shared, state: shared ? "SHARED" : s.clusterId ? "MATCHED" : "NEW" }));
  };

  return (
    <div className="py-12 max-w-2xl mx-auto" data-testid="employee-home">
      <h1 className="font-serif text-4xl text-[#1A1816]">{HOME.title}</h1>
      <p className="mt-2 text-[15px] text-[#57534E]">{HOME.sub}</p>

      {signals.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-[#E7E0D8] p-10 text-center" data-testid="home-empty">
          <p className="text-[15px] text-[#8A847C]">{HOME.empty}</p>
          <button onClick={onStart} className="mt-4 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5]">
            {HOME.emptyCta}
          </button>
        </div>
      ) : (
        <div className="mt-8 space-y-3">
          {signals.map((s, i) => (
            <motion.div
              key={s.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-2xl border border-[#E7E0D8] bg-white p-5"
              data-testid="my-signal"
            >
              <div className="flex items-start justify-between gap-3">
                <StateChip state={s.state} />
                <button onClick={() => setSignals(removeSignal(s.id))} className="text-[#C9C0B6] hover:text-[#9F1239]" title="Sil">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* the person's own words stay primary */}
              <p className="mt-3 font-serif text-[17px] leading-relaxed text-[#1A1816]">“{s.text}”</p>

              {s.storyTitle && (
                <p className="mt-3 text-[13px] text-[#57534E]">
                  Benzer hikâye: <span className="text-[#1A1816]">{s.storyTitle}</span>
                </p>
              )}

              <div className="mt-3.5 rounded-xl bg-[#F7F3EE] px-3.5 py-2.5">
                <Journey state={s.state} />
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-[#F0EAE2] pt-3">
                <span className="flex items-center gap-1.5 text-[12px] text-[#8A847C]">
                  {s.shared ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                  {s.shared ? HOME.visibility.sharedHint : HOME.visibility.privateHint}
                </span>
                <button
                  data-testid="toggle-share"
                  onClick={() => toggleShare(s)}
                  className="rounded-full border border-[#E7E0D8] px-3 py-1.5 text-[13px] text-[#3A3632] hover:border-[#C85A32]"
                >
                  {s.shared ? HOME.visibility.unshare : HOME.visibility.share}
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <p className="mt-8 flex items-center gap-1.5 text-[12px] text-[#8A847C]">
        <ShieldCheck className="h-3.5 w-3.5 text-[#3F6B56]" />
        Anlattıkların bu cihazda tutuluyor. Paylaşmadığın sürece kuruma hiçbir şey gitmez.
      </p>
    </div>
  );
};
