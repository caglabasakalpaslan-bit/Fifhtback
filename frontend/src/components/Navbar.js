import React from "react";
import { Link, NavLink } from "react-router-dom";
import { Disc3, BookMarked } from "lucide-react";

// Public navigation: exactly two doors — ANLAT and KENDİNİ BUL.
// The user's saved cards (MY FIFTHBACK) are a small archive action, not a third tab.
// Legacy internal views are not linked from anywhere.
export const Navbar = () => {
  const tabs = [
    { to: "/anlat", label: "Anlat", testId: "nav-anlat" },
    { to: "/kesfet", label: "Kendini Bul", testId: "nav-kesfet" },
  ];
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF8F5]/85 border-b border-[#E7E0D8]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2">
        <Link to="/" className="flex items-center gap-2.5 min-w-0" data-testid="brand-logo">
          <div className="relative h-9 w-9 shrink-0 rounded-full bg-[#1A1816] flex items-center justify-center">
            <Disc3 className="h-5 w-5 text-[#C85A32] vinyl-spin" strokeWidth={1.75} />
          </div>
          <div className="leading-none truncate hidden sm:block">
            <span className="font-serif text-xl font-medium tracking-tight">Fifthback</span>
          </div>
        </Link>

        <div className="flex items-center gap-2 min-w-0">
          <nav className="flex items-center gap-1 rounded-full border border-[#E7E0D8] bg-white p-1 shadow-sm" aria-label="Ana gezinme">
            {tabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                data-testid={t.testId}
                className={({ isActive }) =>
                  `px-3 sm:px-4 py-1.5 text-sm font-medium rounded-full transition-colors whitespace-nowrap ${isActive ? "bg-[#1A1816] text-[#FAF8F5]" : "text-[#57534E] hover:text-[#1A1816]"}`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <NavLink
            to="/kartlarim"
            data-testid="nav-kartlarim"
            aria-label="Kartlarım"
            title="Kartlarım"
            className={({ isActive }) =>
              `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-colors ${isActive ? "border-[#1A1816] bg-[#1A1816] text-[#FAF8F5]" : "border-[#E7E0D8] bg-white text-[#57534E] hover:text-[#1A1816]"}`
            }
          >
            <BookMarked className="h-4 w-4" strokeWidth={1.75} />
          </NavLink>
        </div>
      </div>
    </header>
  );
};
