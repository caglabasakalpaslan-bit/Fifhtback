import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Users, Clock, Ban, Layers, ShieldCheck, TrendingUp, Loader2, Disc3 } from "lucide-react";
import { getPatterns } from "../lib/api";
import { TYPE_META, STATUS_META } from "../data/constants";

const STATUS_FILTERS = ["ALL", "NEW", "ACTIVE", "STUCK", "RESOLVED"];

const Metric = ({ icon: Icon, label, value, tint }) => (
  <div className="rounded-2xl border border-[#E7E0D8] bg-white p-4 shadow-sm">
    <div className="flex items-center gap-2 text-[#8A847C]">
      <Icon className="h-4 w-4" style={{ color: tint }} />
      <span className="text-[11px] font-mono uppercase tracking-[0.16em]">{label}</span>
    </div>
    <p className="mt-2 font-serif text-3xl font-medium text-[#1A1816]">{value}</p>
  </div>
);

const PatternCard = ({ p, index }) => {
  const type = TYPE_META[p.feedback_type] || TYPE_META.OTHER;
  const status = STATUS_META[p.status] || STATUS_META.NEW;
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-2xl border border-[#E7E0D8] bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
      data-testid={`pattern-card-${p.id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${type.badge}`}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: type.dot }} />
              {type.label}
            </span>
            <span
              data-testid={`pattern-status-${p.id}`}
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${status.badge}`}
            >
              {status.label}
            </span>
          </div>
          <h3 className="font-serif text-xl font-semibold text-[#1A1816] leading-snug">{p.title}</h3>
          {p.summary && <p className="mt-1.5 text-sm text-[#57534E] leading-relaxed">{p.summary}</p>}
        </div>
        <div className="text-right shrink-0">
          <div className="flex items-center gap-1 justify-end text-[#C85A32]">
            <TrendingUp className="h-4 w-4" />
            <span className="font-serif text-2xl font-medium">{p.frequency}</span>
          </div>
          <span className="text-[10px] font-mono uppercase tracking-wide text-[#8A847C]">mentions</span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div>
          <div className="flex items-center gap-1.5 text-[#8A847C] mb-1">
            <Users className="h-3.5 w-3.5" />
            <span className="text-[10px] font-mono uppercase tracking-wide">Affected teams</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {p.affected_teams.map((t) => (
              <span key={t} className="rounded-md bg-[#F4EFEA] px-2 py-0.5 text-xs text-[#57534E]">{t}</span>
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5 text-[#8A847C] mb-1">
            <Clock className="h-3.5 w-3.5" />
            <span className="text-[10px] font-mono uppercase tracking-wide">Unresolved for</span>
          </div>
          <p className="text-[#1A1816] font-medium">{p.unresolved_for}</p>
        </div>
        <div>
          <div className="flex items-center gap-1.5 text-[#8A847C] mb-1">
            <Ban className="h-3.5 w-3.5" />
            <span className="text-[10px] font-mono uppercase tracking-wide">Blocker</span>
          </div>
          <p className="text-[#1A1816]">{p.blocker}</p>
        </div>
      </div>

      {p.song_sentiment && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#FBF7F2] px-3 py-2">
          <Disc3 className="h-3.5 w-3.5 text-[#C85A32]" />
          <span className="text-xs text-[#57534E] italic">{p.song_sentiment}</span>
        </div>
      )}
    </motion.div>
  );
};

export const ManagerDashboard = ({ refreshKey }) => {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    let active = true;
    setLoading(true);
    getPatterns()
      .then((d) => active && setPatterns(d))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [refreshKey]);

  const filtered = useMemo(
    () => (filter === "ALL" ? patterns : patterns.filter((p) => p.status === filter)),
    [patterns, filter]
  );

  const stats = useMemo(() => {
    const total = patterns.reduce((a, p) => a + p.frequency, 0);
    const stuck = patterns.filter((p) => p.status === "STUCK").length;
    const teams = new Set(patterns.flatMap((p) => p.affected_teams.filter((t) => t !== "Aggregating…")));
    return { patterns: patterns.length, total, stuck, teams: teams.size };
  }, [patterns]);

  return (
    <div className="space-y-8 py-8 sm:py-12">
      <div>
        <span className="text-xs font-mono uppercase tracking-[0.22em] text-[#3F6B56] font-semibold">
          Manager Lens · patterns only
        </span>
        <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">
          What keeps coming up.
        </h1>
        <p className="mt-3 text-lg text-[#57534E] max-w-2xl">
          Recurring, anonymized patterns across teams — never a single person, never an identity.
          Just the tensions worth resolving.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Metric icon={Layers} label="Live patterns" value={stats.patterns} tint="#C85A32" />
        <Metric icon={TrendingUp} label="Total mentions" value={stats.total} tint="#D97706" />
        <Metric icon={Ban} label="Stuck & waiting" value={stats.stuck} tint="#E11D48" />
        <Metric icon={Users} label="Teams touched" value={stats.teams} tint="#3F6B56" />
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            data-testid={`status-filter-${f.toLowerCase()}`}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
              filter === f
                ? "bg-[#1A1816] text-[#FAF8F5] border-[#1A1816]"
                : "bg-white text-[#57534E] border-[#E7E0D8] hover:border-[#C85A32]"
            }`}
          >
            {f === "ALL" ? "All" : STATUS_META[f].label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[#8A847C]">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#E7E0D8] bg-white/60 py-16 text-center text-[#8A847C]">
          No patterns in this status yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4" data-testid="patterns-grid">
          {filtered.map((p, i) => <PatternCard key={p.id} p={p} index={i} />)}
        </div>
      )}

      <div className="flex items-center gap-2 rounded-2xl border border-[#CDE3D6] bg-[#EDF5F0] px-5 py-4">
        <ShieldCheck className="h-5 w-5 text-[#3F6B56] shrink-0" />
        <p className="text-sm text-[#3F6B56]">
          <span className="font-semibold">Privacy guarantee:</span> Fifthback never stores who said what.
          Managers see aggregated patterns only — zero names, zero individual timestamps.
        </p>
      </div>
    </div>
  );
};
