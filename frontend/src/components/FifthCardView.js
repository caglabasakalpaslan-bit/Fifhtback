import React, { useState } from "react";
import { BaskaBirDilde } from "./BaskaBirDilde";
import { returnCard } from "../lib/api";

const Section = ({ label, children, testId }) => (
  <div data-testid={testId} className="space-y-1.5">
    <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#8A847C] font-semibold">{label}</p>
    <div>{children}</div>
  </div>
);

const RETURNS = [
  { key: "tuttu", label: "Tuttu" },
  { key: "degisti", label: "Değişti" },
  { key: "uymadi", label: "Uymadı" },
  { key: "baska", label: "Başka bir şey çıktı" },
];

// The Fifth Card: AYRIM · NEDEN ÖNEMLİ · HÂLÂ AÇIK (only if genuine) · YANINDA GÖTÜR · BAŞKA BİR DİLDE (optional).
// No scores, no myth required to understand it. `card.distinction` is the core's and is never edited here.
export const FifthCardView = ({ card, enrichment, isReturnVisit }) => {
  const [returned, setReturned] = useState(card?.returns?.length ? card.returns[card.returns.length - 1] : null);
  const [busy, setBusy] = useState(false);
  if (!card) return null;
  const mark = async (outcome) => {
    setBusy(true);
    try { const c = await returnCard(card.session_id, outcome); setReturned(c.returns[c.returns.length - 1]); } catch { /* keep quiet */ } finally { setBusy(false); }
  };
  return (
    <div data-testid="fifth-card" className="space-y-6">
      <h2 className="font-serif text-2xl sm:text-3xl leading-snug">{card.title}</h2>
      <Section label="Ayrım" testId="card-distinction">
        <p className="font-serif text-xl sm:text-2xl leading-snug text-[#1A1816]">{card.distinction}</p>
      </Section>
      <Section label="Neden önemli" testId="card-why">
        <p className="text-base leading-relaxed text-[#1A1816]">{card.why_it_matters}</p>
      </Section>
      {card.still_open && (
        <Section label="Hâlâ açık" testId="card-open">
          <p className="text-sm leading-relaxed text-[#57534E]">{card.still_open}</p>
        </Section>
      )}
      <Section label="Yanında götür" testId="card-take">
        <p className="text-base italic leading-relaxed text-[#1A1816]">{card.take_with_you}</p>
      </Section>
      {enrichment?.used && <BaskaBirDilde enrichment={enrichment} />}
      {isReturnVisit && (
        <div data-testid="card-return" className="border-t border-[#E7E0D8] pt-4 space-y-2">
          <p className="text-sm text-[#57534E]">{returned ? `Son dönüşün: ${RETURNS.find((r) => r.key === returned.outcome)?.label || returned.outcome}` : card.return_prompt}</p>
          <div className="flex flex-wrap gap-2">
            {RETURNS.map((r) => (
              <button key={r.key} data-testid={`card-return-${r.key}`} disabled={busy} onClick={() => mark(r.key)}
                className={`rounded-full border px-3.5 py-1.5 text-sm ${returned?.outcome === r.key ? "border-[#1A1816] bg-[#1A1816] text-[#FAF8F5]" : "border-[#E7E0D8] bg-white text-[#57534E] hover:border-[#1A1816]"}`}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
