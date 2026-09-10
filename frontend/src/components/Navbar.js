import React from "react";
import { Link, NavLink } from "react-router-dom";
import { Disc3, ShieldCheck } from "lucide-react";

// Public navigation: Anlat and the user's saved cards. Nothing else is listed.
export const Navbar = () => {
  const tabs = [
    { to: "/anlat", label: "Anlat", testId: "nav-anlat" },
    { to: "/kartlarim", label: "Kartlarım", testId: "nav-kartlarim" },
  ];
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF8F5]/85 border-b border-[#E7E0D8]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-2.5 min-w-0" data-testid="brand-logo">
          <div className="relative h-9 w-9 shrink-0 rounded-full bg-[#1A1816] flex items-center justify-center">
            <Disc3 className="h-5 w-5 text-[#C85A32] vinyl-spin" strokeWidth={1.75} />
          </div>
          <div className="leading-none truncate">
            <span className="font-serif text-xl font-medium tracking-tight">Fifthback</span>
            <span className="hidden sm:inline ml-2 text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A847C]">sesin duyuldu</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 rounded-full border border-[#E7E0D8] bg-white p-1 shadow-sm" aria-label="Ana gezinme">
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              data-testid={t.testId}
              className={({ isActive }) =>
                `px-3.5 sm:px-4 py-1.5 text-sm font-medium rounded-full transition-colors whitespace-nowrap ${isActive ? "bg-[#1A1816] text-[#FAF8F5]" : "text-[#57534E] hover:text-[#1A1816]"}`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-1.5 text-[#3F6B56]" data-testid="privacy-chip">
          <ShieldCheck className="h-4 w-4" strokeWidth={2} />
          <span className="text-xs font-medium">Kimlik bilgisi saklanmaz</span>
        </div>
      </div>
    </header>
  );
};
