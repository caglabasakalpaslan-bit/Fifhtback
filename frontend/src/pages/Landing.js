import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Mic, Compass } from "lucide-react";

const Door = ({ to, eyebrow, title, line, icon: Icon, accent, testId }) => (
  <Link
    to={to}
    data-testid={testId}
    className="group block rounded-3xl border border-[#E7E0D8] bg-white p-7 sm:p-9 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[#1A1816]/20"
  >
    <Icon className="h-6 w-6" style={{ color: accent }} strokeWidth={1.75} />
    <div className="mt-6 text-[11px] font-mono uppercase tracking-[0.22em]" style={{ color: accent }}>{eyebrow}</div>
    <div className="mt-2 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.02]">{title}</div>
    <p className="mt-4 text-base text-[#57534E] leading-relaxed">{line}</p>
    <div className="mt-6 text-sm font-medium text-[#1A1816] opacity-70 group-hover:opacity-100 transition-opacity">Gir →</div>
  </Link>
);

export const Landing = () => (
  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="py-12 sm:py-20">
    <div className="max-w-3xl">
      <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#8A847C]">İki kapı</p>
      <h1 className="mt-3 font-serif text-4xl sm:text-6xl font-medium tracking-tight leading-[1.02]">
        Ya anlat, ya kendini bul.
      </h1>
    </div>
    <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-5">
      <Door to="/anlat" eyebrow="Anlat" title="Anlat" line="Burası sesinin duyulduğu yer." icon={Mic} accent="#C85A32" testId="door-anlat" />
      <Door to="/kesfet" eyebrow="Kendini bul" title="Kendini Bul" line="Burası yaşanmışlıkların sesi." icon={Compass} accent="#3F6B56" testId="door-kesfet" />
    </div>
  </motion.div>
);
