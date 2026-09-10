import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Mic, Compass } from "lucide-react";
import { getSavedCards } from "../lib/storage";

// Two doors: ANLAT (the product) and KENDİNİ BUL (stable world-selection shell; interiors come later).
export const Landing = () => {
  const saved = getSavedCards();
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="py-12 sm:py-20">
      <div className="max-w-3xl">
        <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#8A847C]">Fifthback</p>
        <h1 className="mt-3 font-serif text-4xl sm:text-6xl font-medium tracking-tight leading-[1.02]">
          Sesin duyuldu.
        </h1>
        <p className="mt-4 text-base sm:text-lg text-[#57534E] leading-relaxed">
          Aklında nasıl duruyorsa öyle. Yaz ya da söyle; düzeltmene gerek yok.
        </p>
      </div>
      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-5">
        <Link
          to="/anlat"
          data-testid="door-anlat"
          className="group block rounded-3xl border border-[#E7E0D8] bg-white p-7 sm:p-9 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[#1A1816]/20"
        >
          <Mic className="h-6 w-6 text-[#C85A32]" strokeWidth={1.75} />
          <div className="mt-6 text-[11px] font-mono uppercase tracking-[0.22em] text-[#C85A32]">Anlat</div>
          <div className="mt-2 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.02]">Anlat</div>
          <p className="mt-4 text-base text-[#57534E] leading-relaxed">Burası sesinin duyulduğu yer.</p>
          <div className="mt-6 text-sm font-medium text-[#1A1816] opacity-70 group-hover:opacity-100 transition-opacity">Gir →</div>
        </Link>
        <Link
          to="/kesfet"
          data-testid="door-kesfet"
          className="group block rounded-3xl border border-[#E7E0D8] bg-white p-7 sm:p-9 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[#1A1816]/20"
        >
          <Compass className="h-6 w-6 text-[#3F6B56]" strokeWidth={1.75} />
          <div className="mt-6 text-[11px] font-mono uppercase tracking-[0.22em] text-[#3F6B56]">Kendini bul</div>
          <div className="mt-2 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.02]">Kendini Bul</div>
          <p className="mt-4 text-base text-[#57534E] leading-relaxed">Burası yaşanmışlıkların sesi. Bir dünya seç.</p>
          <div className="mt-6 text-sm font-medium text-[#1A1816] opacity-70 group-hover:opacity-100 transition-opacity">Gir →</div>
        </Link>
      </div>
      {saved.length > 0 && (
        <Link to="/kartlarim" data-testid="landing-cards-link" className="mt-8 inline-flex text-sm font-medium text-[#57534E] hover:text-[#1A1816]">
          Kartlarım ({saved.length}) →
        </Link>
      )}
    </motion.div>
  );
};
