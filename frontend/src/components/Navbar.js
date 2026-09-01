import React from "react";
import { motion } from "framer-motion";
import { Disc3 } from "lucide-react";
import { BRAND, NAV } from "../data/copy";

export const Navbar = ({ view, setView }) => {
  const tabs = [
    { key: "entry", label: NAV.entry },
    { key: "home", label: NAV.home },
    { key: "manager", label: NAV.manager },
    { key: "patterns", label: NAV.patterns },
  ];
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF8F5]/85 border-b border-[#E7E0D8]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2.5" data-testid="brand-logo">
          <div className="relative h-9 w-9 rounded-full bg-[#1A1816] flex items-center justify-center">
            <Disc3 className="h-5 w-5 text-[#C85A32] vinyl-spin" strokeWidth={1.75} />
          </div>
          <div className="leading-none">
            <span className="font-serif text-xl font-medium tracking-tight">{BRAND.name}</span>
            <span className="hidden lg:inline ml-2 text-[11px] text-[#8A847C]">
              {BRAND.line}
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-1 mx-auto rounded-full border border-[#E7E0D8] bg-white p-1 shadow-sm">
          {tabs.map((t) => (
            <button
              key={t.key}
              data-testid={`nav-${t.key}-tab`}
              onClick={() => setView(t.key)}
              className="relative px-4 py-1.5 text-sm font-medium rounded-full transition-colors"
            >
              {view === t.key && (
                <motion.span
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-full bg-[#1A1816]"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <span className={`relative z-10 ${view === t.key ? "text-[#FAF8F5]" : "text-[#57534E]"}`}>
                {t.label}
              </span>
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
};
