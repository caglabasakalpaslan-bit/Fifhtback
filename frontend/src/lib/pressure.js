// SIKIŞIKLIK — a presentation-layer reading of data the backend already produces.
//
// This does NOT score people and does NOT introduce new measurement. Every
// component below is read off an existing field:
//
//   repetition -> PRTopPattern.evidence.length | Pattern.frequency
//   spread     -> Pattern.affected_teams.length
//   impact     -> qualitative word the engine already wrote into estimated_cost
//   duration   -> Pattern.unresolved_for
//   change     -> Pattern.status
//
// Anything the engine does not measure stays null and renders as
// "Yeterli veri yok". We never fill a gap with a guess.

const clamp01 = (n) => Math.max(0, Math.min(1, n));

// The engine writes its own qualitative verdict into estimated_cost / confidence.
// We read that word rather than inventing a number.
const readQualitative = (text) => {
  if (!text) return null;
  const t = text.toLocaleLowerCase("tr");
  if (t.includes("orta-yüksek") || t.includes("orta-yuksek")) return 0.7;
  if (t.includes("yüksek") || t.includes("yuksek")) return 0.9;
  if (t.includes("orta")) return 0.55;
  if (t.includes("düşük") || t.includes("dusuk")) return 0.25;
  return null;
};

// Duration is written as free text ("3 aydır", "2 sprint"). Read months where
// the engine stated them; otherwise null.
const readDuration = (text) => {
  if (!text) return null;
  const t = text.toLocaleLowerCase("tr");
  const num = parseInt((t.match(/\d+/) || [])[0], 10);
  if (Number.isNaN(num)) return t.includes("uzun") ? 0.9 : null;
  if (t.includes("yıl") || t.includes("yil")) return 1;
  if (t.includes("ay")) return clamp01(num / 12);
  if (t.includes("hafta")) return clamp01(num / 52);
  if (t.includes("sprint")) return clamp01((num * 2) / 52);
  return null;
};

const CHANGE_BY_STATUS = {
  RESOLVED: { value: 0.0, label: "Çözüldü" },
  STUCK: { value: 1.0, label: "Takıldı" },
  ACTIVE: { value: 0.6, label: "Hareket var" },
  NEW: { value: 0.5, label: "Yeni" },
};

// Weights only combine the components that are actually present, so a pattern
// with less data is not penalised into looking calm.
const WEIGHTS = { repetition: 0.3, impact: 0.3, spread: 0.2, duration: 0.2 };

export function computePressure(components) {
  const present = Object.entries(components).filter(
    ([key, v]) => v !== null && v !== undefined && WEIGHTS[key] !== undefined
  );
  if (present.length === 0) return { score: null, band: "none", coverage: 0 };
  const totalW = present.reduce((s, [k]) => s + WEIGHTS[k], 0);
  const acc = present.reduce((s, [k, v]) => s + WEIGHTS[k] * v, 0);
  const score = acc / totalW;
  return {
    score,
    band: score >= 0.7 ? "high" : score >= 0.4 ? "medium" : "low",
    // how much of the picture we actually have — shown to the user, not hidden
    coverage: present.length / Object.keys(WEIGHTS).length,
  };
}

// ---- adapters over the two existing backend shapes -------------------------

// PRTopPattern (curated Pattern Room). Has mass + qualitative impact, but no
// team data and no speaking-cost measurement.
export function pressureFromPatternRoom(p, maxEvidence) {
  const components = {
    repetition: maxEvidence ? clamp01((p.evidence?.length || 0) / maxEvidence) : null,
    impact: readQualitative(p.estimated_cost),
    spread: null,     // engine has no team breakdown for these clusters
    duration: null,   // engine has no age for these clusters
  };
  return {
    ...computePressure(components),
    components,
    signalCount: p.evidence?.length || 0,
    // never measured by the engine — must not be invented
    speakingCost: null,
  };
}

// Pattern (seeded manager patterns). Richer: has frequency, teams, age, status.
export function pressureFromManagerPattern(p, maxFrequency) {
  // Positive feedback and resolved items are not friction. Reporting them as
  // "sıkışıklık" would misread the engine's own feedback_type/status.
  const isFriction = p.feedback_type !== "POSITIVE" && p.status !== "RESOLVED";
  const components = {
    repetition: maxFrequency ? clamp01((p.frequency || 0) / maxFrequency) : null,
    impact: p.blocker ? 0.7 : null,
    spread: clamp01((p.affected_teams?.length || 0) / 4),
    duration: readDuration(p.unresolved_for),
  };
  return {
    ...(isFriction ? computePressure(components) : { score: null, band: "none", coverage: 0 }),
    isFriction,
    components,
    signalCount: p.frequency || 0,
    teams: p.affected_teams?.length || 0,
    change: CHANGE_BY_STATUS[p.status] || null,
    speakingCost: null,
  };
}
