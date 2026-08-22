import React from "react";
import { motion } from "framer-motion";
import { Disc3, ShieldCheck } from "lucide-react";

export const Navbar = ({ view, setView }) => {
  const tabs = [
    { key: "employee", label: "Employee Voice" },
    { key: "manager", label: "Manager Lens" },
  ];
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF8F5]/85 border-b border-[#E7E0D8]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2.5" data-testid="brand-logo">
          <div className="relative h-9 w-9 rounded-full bg-[#1A1816] flex items-center justify-center">
            <Disc3 className="h-5 w-5 text-[#C85A32] vinyl-spin" strokeWidth={1.75} />
          </div>
          <div className="leading-none">
            <span className="font-serif text-xl font-medium tracking-tight">Fifthback</span>
            <span className="hidden sm:inline ml-2 text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A847C]">
              feedback, heard
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-1 rounded-full border border-[#E7E0D8] bg-white p-1 shadow-sm">
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

        <div className="hidden md:flex items-center gap-1.5 text-[#3F6B56]" data-testid="privacy-chip">
          <ShieldCheck className="h-4 w-4" strokeWidth={2} />
          <span className="text-xs font-medium">No identities stored</span>
        </div>
      </div>
    </header>
  );
};
