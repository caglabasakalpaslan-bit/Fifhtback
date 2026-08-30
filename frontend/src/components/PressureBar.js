import React from "react";
import { PRESSURE } from "../data/copy";

const BAND = {
  high: { color: "#C85A32", label: PRESSURE.high },
  medium: { color: "#D97706", label: PRESSURE.medium },
  low: { color: "#3F6B56", label: PRESSURE.low },
  none: { color: "#A8A29E", label: PRESSURE.none },
};

// Shows the reading AND how complete it is. A confident-looking bar built from
// one of four components would misrepresent the engine.
export const PressureBar = ({ pressure, compact = false }) => {
  if (!pressure) return null;
  const band = BAND[pressure.band] || BAND.none;
  const pct = pressure.score === null ? 0 : Math.round(pressure.score * 100);
  return (
    <div data-testid="pressure-bar">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-mono uppercase tracking-[0.14em] text-[#8A847C]">{PRESSURE.label}</span>
        <span style={{ color: band.color }} className="font-medium">{band.label}</span>
      </div>
      <div className="mt-1.5 h-1.5 rounded-full bg-[#EFE9E1] overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: band.color }} />
      </div>
      {!compact && pressure.coverage !== undefined && pressure.coverage < 1 && (
        <p className="mt-1.5 text-[11px] text-[#A8A29E]">
          Bu okuma {Math.round(pressure.coverage * 4)}/4 boyuta dayanıyor — geri kalanı henüz ölçülmüyor.
        </p>
      )}
    </div>
  );
};
