import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Loader2, ShieldCheck } from "lucide-react";
import { getPatternRoom } from "../lib/api";
import { PATTERNS, DEMO_NOTE } from "../data/copy";
import { humanTitle, secondaryLabel } from "../data/stories";
import { pressureFromPatternRoom } from "../lib/pressure";
import { StoryDetail } from "../components/StoryDetail";

const BAND_COLOR = { high: "#C85A32", medium: "#D97706", low: "#3F6B56", none: "#A8A29E" };

// Deterministic radial layout. Related mechanisms sit near each other because
// clusters that share a mechanism word are placed on neighbouring angles.
function layout(patterns, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  // heaviest pattern nearest the centre — dense middle reads as sıkışıklık
  const sorted = [...patterns].sort((a, b) => (b.evidence?.length || 0) - (a.evidence?.length || 0));
  const maxW = Math.max(...patterns.map((q) => q.evidence?.length || 1));
  // The heaviest story sits at the centre; the rest ring it. The densest area of
  // the picture is therefore where the pressure actually is.
  return sorted.map((p, i) => {
    const weight = p.evidence?.length || 1;
    const r = 20 + (weight / maxW) * 26;
    if (i === 0) return { ...p, x: cx, y: cy, r, weight, labelAbove: false };
    const ring = i - 1;
    const count = sorted.length - 1;
    const angle = (ring / count) * Math.PI * 2 - Math.PI / 2;
    return {
      ...p,
      x: cx + Math.cos(angle) * 150,
      y: cy + Math.sin(angle) * 118,
      r,
      weight,
      labelAbove: Math.sin(angle) < -0.1,
    };
  });
}

// A link exists when two clusters share a mechanism word — that is the engine's
// own vocabulary, not a new similarity model.
function links(nodes) {
  const out = [];
  const words = (s) => new Set((s || "").toLowerCase().split(/[^\wçğıöşü]+/).filter((w) => w.length > 4));
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = words(nodes[i].mechanism);
      const b = words(nodes[j].mechanism);
      const shared = [...a].filter((w) => b.has(w)).length;
      if (shared > 0) out.push({ a: nodes[i], b: nodes[j], strength: shared });
    }
  }
  return out;
}

const W = 640;
const H = 420;

export const PatternMap = () => {
  const [data, setData] = useState(null);
  const [openRank, setOpenRank] = useState(null);

  useEffect(() => {
    getPatternRoom().then(setData).catch(() => setData({ patterns: [], signals: [] }));
  }, []);

  const nodes = useMemo(() => (data ? layout(data.patterns || [], W, H) : []), [data]);
  const edges = useMemo(() => links(nodes), [nodes]);
  const maxEvidence = useMemo(
    () => Math.max(1, ...(data?.patterns || []).map((p) => p.evidence?.length || 0)),
    [data]
  );

  if (!data) {
    return <div className="py-24 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-[#8A847C]" /></div>;
  }

  const openPattern = (data.patterns || []).find((p) => p.rank === openRank);

  return (
    <div className="py-12 max-w-3xl mx-auto" data-testid="pattern-map">
      <h1 className="font-serif text-4xl text-[#1A1816]">{PATTERNS.title}</h1>
      <p className="mt-2 text-[15px] text-[#57534E]">{PATTERNS.sub}</p>
      <span className="mt-3 inline-block rounded-full bg-[#F4EFEA] px-2.5 py-0.5 text-[10px] text-[#8A847C]" data-testid="demo-badge">
        {PATTERNS.demoBadge}
      </span>

      <div className="mt-6 rounded-2xl border border-[#E7E0D8] bg-white overflow-hidden">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={PATTERNS.title}>
          {/* dense-area wash: heavier nodes glow, so clusters of pressure are visible at a glance */}
          {nodes.map((n) => {
            const pr = pressureFromPatternRoom(n, maxEvidence);
            return (
              <circle key={`glow-${n.rank}`} cx={n.x} cy={n.y} r={n.r * 2.1}
                fill={BAND_COLOR[pr.band]} opacity={0.06} />
            );
          })}

          {edges.map((e, i) => (
            <line key={i} x1={e.a.x} y1={e.a.y} x2={e.b.x} y2={e.b.y}
              stroke="#C9C0B6" strokeWidth={e.strength} opacity={0.5} />
          ))}

          {nodes.map((n) => {
            const pr = pressureFromPatternRoom(n, maxEvidence);
            const title = humanTitle(n.cluster_id, n.name);
            return (
              <g key={n.rank} onClick={() => setOpenRank(n.rank)} style={{ cursor: "pointer" }}
                 data-testid={`map-node-${n.rank}`}>
                <circle cx={n.x} cy={n.y} r={n.r} fill={BAND_COLOR[pr.band]} opacity={0.9} />
                <text x={n.x} y={n.y + 4} textAnchor="middle" fill="#FAF8F5"
                      style={{ fontSize: 13, fontWeight: 600 }}>{n.weight}</text>
                <text
                  x={n.x}
                  y={n.labelAbove ? n.y - n.r - 9 : n.y + n.r + 16}
                  textAnchor="middle"
                  fill="#3A3632"
                  style={{ fontSize: 11 }}
                >
                  {title.length > 24 ? `${title.slice(0, 23)}…` : title}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mt-3 text-[12px] text-[#8A847C]">{PATTERNS.legend} · {PATTERNS.openHint}</p>

      {/* compact list as the accessible path to the same detail */}
      <div className="mt-6 space-y-2">
        {nodes.map((n) => {
          const pr = pressureFromPatternRoom(n, maxEvidence);
          return (
            <button
              key={n.rank}
              onClick={() => setOpenRank(n.rank)}
              data-testid={`map-row-${n.rank}`}
              className="w-full flex items-center gap-3 rounded-xl border border-[#E7E0D8] bg-white px-4 py-3 text-left hover:border-[#C85A32] transition-colors"
            >
              <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: BAND_COLOR[pr.band] }} />
              <span className="flex-1 min-w-0">
                <span className="block font-serif text-[16px] text-[#1A1816] truncate">
                  {humanTitle(n.cluster_id, n.name)}
                </span>
                <span className="block text-[11px] font-mono uppercase tracking-[0.12em] text-[#8A847C] truncate">
                  {secondaryLabel(n.cluster_id, n.mechanism)}
                </span>
              </span>
              <span className="text-[12px] text-[#8A847C] shrink-0">{n.weight} sinyal</span>
            </button>
          );
        })}
      </div>

      <div className="mt-8 flex items-start gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-3">
        <ShieldCheck className="h-4 w-4 text-[#3F6B56] shrink-0 mt-0.5" />
        <p className="text-[13px] text-[#3F6B56]">
          Bu bir çalışan değerlendirmesi değildir. Yalnızca iş sisteminin sürtünmesi incelenir.
        </p>
      </div>

      <StoryDetail
        pattern={openPattern}
        pressure={openPattern ? pressureFromPatternRoom(openPattern, maxEvidence) : null}
        open={openRank !== null}
        onClose={() => setOpenRank(null)}
        isDemo
      />
    </div>
  );
};
