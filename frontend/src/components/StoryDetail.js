import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ShieldCheck, Quote, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "./ui/dialog";
import { DETAIL, PRESSURE, DEMO_NOTE } from "../data/copy";
import { STORY_BY_CLUSTER, humanTitle, secondaryLabel, whyTogether } from "../data/stories";
import { canShowProvenance } from "../lib/privacy";
import { PressureBar } from "./PressureBar";

// One collapsible angle. Progressive disclosure: the first angle is open,
// everything else costs one click. No walls of text.
const Angle = ({ label, children, defaultOpen = false, testId }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-[#EFE9E1] last:border-0">
      <button
        data-testid={testId}
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 py-3 text-left group"
      >
        <span className="font-serif text-[15px] text-[#1A1816] leading-snug">{label}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-[#8A847C] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="pb-4 text-sm leading-relaxed text-[#57534E]">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// The five-angle card. Reads EXISTING PRTopPattern fields — no new backend data.
export const StoryDetail = ({ pattern, pressure, open, onClose, isDemo }) => {
  if (!pattern) return null;
  const title = humanTitle(pattern.cluster_id, pattern.name);
  const mechanism = secondaryLabel(pattern.cluster_id, pattern.mechanism);
  const story = STORY_BY_CLUSTER[pattern.cluster_id];
  const n = pattern.evidence?.length || 0;
  const showProvenance = canShowProvenance(n) && story?.provenance?.length > 0;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl bg-[#FAF8F5] border-[#E7E0D8] p-0 overflow-hidden" data-testid="story-detail">
        <div className="px-6 pt-6 pb-4">
          {isDemo && (
            <span className="inline-block mb-2 rounded-full bg-[#F4EFEA] px-2.5 py-0.5 text-[10px] text-[#8A847C]">
              {DEMO_NOTE}
            </span>
          )}
          {/* PRIMARY: human language. */}
          <DialogTitle className="font-serif text-2xl leading-tight text-[#1A1816] text-left" data-testid="story-detail-title">
            {title}
          </DialogTitle>
          {/* SECONDARY: mechanism, deliberately small. */}
          <DialogDescription className="mt-1 text-[13px] text-[#8A847C] text-left">
            {DETAIL.mechanismLabel}: {mechanism}
          </DialogDescription>
          <div className="mt-4">
            <PressureBar pressure={pressure} />
          </div>
        </div>

        <div className="max-h-[46vh] overflow-y-auto px-6">
          <Angle label={DETAIL.angles.why} defaultOpen testId="angle-why">
            {whyTogether(pattern.cluster_id, pattern.why_formed)}
          </Angle>
          <Angle label={DETAIL.angles.impact} testId="angle-impact">
            <p>{pattern.affected_work}</p>
            <p className="mt-2 text-[#8A847C]">{pattern.estimated_cost}</p>
          </Angle>
          <Angle label={DETAIL.angles.history} testId="angle-history">
            <p>
              Bu hikâye {n} anonim sinyalden oluşuyor.{" "}
              {pattern.past_patterns?.length > 0
                ? "Benzer durumlarda daha önce şunlar denenmiş:"
                : "Benzer bir geçmiş kayıt bulunmuyor."}
            </p>
            {pattern.past_patterns?.map((pp, i) => (
              <div key={i} className="mt-2 rounded-lg border border-[#F0EAE2] bg-white p-3">
                <p className="text-[13px]"><span className="text-[#1A1816] font-medium">{DETAIL.tried}</span>{" "} {pp.tried}</p>
                <p className="text-[13px] mt-1"><span className="text-[#3F6B56] font-medium">{DETAIL.worked}</span>{" "} {pp.changed}</p>
                <p className="text-[13px] mt-1"><span className="text-[#9F1239] font-medium">{DETAIL.failed}</span>{" "} {pp.when_failed}</p>
              </div>
            ))}
          </Angle>
          <Angle label={DETAIL.angles.unknown} testId="angle-unknown">
            {pattern.uncertain}
          </Angle>
          <Angle label={DETAIL.angles.next} testId="angle-next">
            {pattern.next_moves?.map((m, i) => (
              <div key={i} className="flex items-start gap-2 mt-2 first:mt-0">
                <Sparkles className="h-3.5 w-3.5 text-[#C85A32] mt-1 shrink-0" />
                <span>{m}</span>
              </div>
            ))}
          </Angle>
        </div>

        {/* PROVENANCE — the causal bridge, paraphrased. */}
        <div className="mt-1 border-t border-[#EFE9E1] bg-[#F7F3EE] px-6 py-4">
          <div className="flex items-center gap-1.5 text-[#8A847C]">
            <Quote className="h-3.5 w-3.5" />
            <span className="text-[13px]">{DETAIL.provenance}</span>
          </div>
          {showProvenance ? (
            <>
              <div className="mt-2.5 space-y-1.5" data-testid="provenance-list">
                {story.provenance.map((ex, i) => (
                  <p key={i} className="rounded-md border border-[#E7E0D8] bg-white px-3 py-2 text-[13px] text-[#3A3632]">
                    “{ex}”
                  </p>
                ))}
              </div>
              <p className="mt-2.5 flex items-start gap-1.5 text-[11px] text-[#8A847C]">
                <ShieldCheck className="h-3 w-3 mt-0.5 shrink-0 text-[#3F6B56]" />
                {DETAIL.provenanceNote}
              </p>
            </>
          ) : (
            <p className="mt-2 text-[13px] text-[#8A847C]">{DETAIL.provenanceGated}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
