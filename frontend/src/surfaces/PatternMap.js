import React, { useEffect, useMemo, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { getPatternRoom } from "../lib/api";
import { PATTERNS, DEMO_NOTE } from "../data/copy";
import { humanTitle, secondaryLabel } from "../data/stories";
import { pressureFromPatternRoom } from "../lib/pressure";
import { StoryDetail } from "../components/StoryDetail";

const BAND_COLOR = { high: "#C85A32", medium: "#D97706", low: "#3F6B56", none: "#A8A29E" };
const W = 640;
const H = 440;

// Mechanism similarity, using the same 5-char stem trick the backend already
// uses in _match_prevalence — so "belirsiz" and "belirsizliği" count as related.
const stems = (text) =>
  new Set(
    (text || "")
      .toLocaleLowerCase("tr")
      .split(/[^\wçğıöşüİ]+/)
      .filter((w) => w.length >= 5)
      .map((w) => w.slice(0, 5))
  );

function similarity(a, b) {
  const sa = stems(a);
  const sb = stems(b);
  let shared = 0;
  sa.forEach((w) => { if (sb.has(w)) shared += 1; });
  return shared;
}

// Deterministic force layout: similar mechanisms pull together, everything
// repels, a weak centre pull keeps it on canvas. Stories that share a mechanism
// end up as a visible cluster instead of spokes on a wheel.
function layout(patterns) {
  const n = patterns.length;
  if (n === 0) return { nodes: [], edges: [], regions: 0 };

  const maxW = Math.max(...patterns.map((p) => p.evidence?.length || 1));
  const nodes = patterns.map((p, i) => {
    const angle = (i / n) * Math.PI * 2;
    return {
      ...p,
      // deterministic seed, not random, so the map is stable between renders
      x: W / 2 + Math.cos(angle) * 110,
      y: H / 2 + Math.sin(angle) * 90,
      vx: 0,
      vy: 0,
      r: 20 + ((p.evidence?.length || 1) / maxW) * 26,
      weight: p.evidence?.length || 1,
    };
  });

  const edges = [];
  for (let i = 0; i < n; i += 1) {
    for (let j = i + 1; j < n; j += 1) {
      const shared = similarity(nodes[i].mechanism, nodes[j].mechanism);
      if (shared > 0) edges.push({ i, j, shared });
    }
  }

  for (let step = 0; step < 400; step += 1) {
    // repulsion
    for (let i = 0; i < n; i += 1) {
      for (let j = i + 1; j < n; j += 1) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const d = Math.max(24, Math.hypot(dx, dy));
        const force = 9000 / (d * d);
        const fx = (dx / d) * force;
        const fy = (dy / d) * force;
        nodes[i].vx -= fx; nodes[i].vy -= fy;
        nodes[j].vx += fx; nodes[j].vy += fy;
      }
    }
    // attraction along shared-mechanism links
    edges.forEach(({ i, j, shared }) => {
      const dx = nodes[j].x - nodes[i].x;
      const dy = nodes[j].y - nodes[i].y;
      const d = Math.max(1, Math.hypot(dx, dy));
      const target = 132 - shared * 26; // more shared stems = sit closer
      const force = (d - target) * 0.012;
      const fx = (dx / d) * force;
      const fy = (dy / d) * force;
      nodes[i].vx += fx; nodes[i].vy += fy;
      nodes[j].vx -= fx; nodes[j].vy -= fy;
    });
    // weak centring
    nodes.forEach((nd) => {
      nd.vx += (W / 2 - nd.x) * 0.004;
      nd.vy += (H / 2 - nd.y) * 0.004;
      nd.x += nd.vx * 0.55;
      nd.y += nd.vy * 0.55;
      nd.vx *= 0.82;
      nd.vy *= 0.82;
      // keep clear of the edges so labels stay on canvas
      nd.x = Math.max(nd.r + 76, Math.min(W - nd.r - 76, nd.x));
      nd.y = Math.max(nd.r + 30, Math.min(H - nd.r - 34, nd.y));
    });
  }

  // A dense region = a connected group of stories sharing a mechanism.
  const parent = nodes.map((_, i) => i);
  const find = (a) => (parent[a] === a ? a : (parent[a] = find(parent[a])));
  edges.forEach(({ i, j }) => { parent[find(i)] = find(j); });
  const sizes = {};
  nodes.forEach((_, i) => { const root = find(i); sizes[root] = (sizes[root] || 0) + 1; });
  const regions = Object.values(sizes).filter((c) => c >= 2).length;

  return { nodes, edges, regions };
}

// Wrap a title onto at most two lines on word boundaries — never a mid-word cut.
function wrap(title, max = 22) {
  const words = title.split(" ");
  const lines = [];
  let line = "";
  words.forEach((w) => {
    if ((line + " " + w).trim().length <= max) line = (line + " " + w).trim();
    else { if (line) lines.push(line); line = w; }
  });
  if (line) lines.push(line);
  if (lines.length <= 2) return lines;
  return [lines[0], `${lines.slice(1).join(" ").slice(0, max - 1)}…`];
}

export const PatternMap = () => {
  const [data, setData] = useState(null);
  const [openRank, setOpenRank] = useState(null);

  useEffect(() => {
    getPatternRoom().then(setData).catch(() => setData({ patterns: [], signals: [] }));
  }, []);

  const { nodes, edges, regions } = useMemo(
    () => (data ? layout(data.patterns || []) : { nodes: [], edges: [], regions: 0 }),
    [data]
  );
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
          {/* halo: heavier + higher pressure reads as a denser area */}
          {nodes.map((nd) => {
            const pr = pressureFromPatternRoom(nd, maxEvidence);
            return (
              <circle key={`glow-${nd.rank}`} cx={nd.x} cy={nd.y} r={nd.r * 2.3}
                fill={BAND_COLOR[pr.band]} opacity={0.07} />
            );
          })}

          {edges.map((e, i) => (
            <line key={i} x1={nodes[e.i].x} y1={nodes[e.i].y} x2={nodes[e.j].x} y2={nodes[e.j].y}
              stroke="#C9C0B6" strokeWidth={Math.min(3, e.shared)} opacity={0.55} />
          ))}

          {nodes.map((nd) => {
            const pr = pressureFromPatternRoom(nd, maxEvidence);
            const lines = wrap(humanTitle(nd.cluster_id, nd.name));
            return (
              <g
                key={nd.rank}
                onClick={() => setOpenRank(nd.rank)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setOpenRank(nd.rank); }}
                tabIndex={0}
                role="button"
                aria-label={humanTitle(nd.cluster_id, nd.name)}
                style={{ cursor: "pointer" }}
                data-testid={`map-node-${nd.rank}`}
              >
                <circle cx={nd.x} cy={nd.y} r={nd.r} fill={BAND_COLOR[pr.band]} opacity={0.92} />
                <text x={nd.x} y={nd.y + 4} textAnchor="middle" fill="#FAF8F5"
                      style={{ fontSize: 13, fontWeight: 600 }}>{nd.weight}</text>
                {lines.map((ln, li) => (
                  <text key={li} x={nd.x} y={nd.y + nd.r + 15 + li * 13} textAnchor="middle"
                        fill="#3A3632" style={{ fontSize: 11 }}>{ln}</text>
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      {/* compact summary replaces the duplicated list */}
      <div className="mt-3 flex items-center justify-between text-[12px] text-[#8A847C]">
        <span data-testid="map-summary">
          {nodes.length} hikâye · {data.signals?.length || 0} sinyal · {regions} yoğun bölge
        </span>
        <span>{PATTERNS.openHint}</span>
      </div>

      <div className="mt-6 flex items-start gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-3">
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
