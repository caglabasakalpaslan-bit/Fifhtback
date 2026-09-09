import React from "react";
import { Link, Outlet } from "react-router-dom";
import { BackLink } from "../components/BackLink";

// Legacy / internal views. Not linked from public navigation; code kept intact.
export const INTERNAL_VIEWS = [
  { path: "fifth", label: "The Fifth (eski prototip)" },
  { path: "calisan-sesi", label: "Çalışan Sesi" },
  { path: "yonetici", label: "Yönetici Görünümü" },
  { path: "pattern-room", label: "Pattern Room" },
];

export const InternalLayout = () => (
  <div className="py-6 space-y-4">
    <div className="flex items-center justify-between">
      <BackLink to="/" label="Ana kapı" testId="internal-back" />
      <span className="text-[10px] font-mono uppercase tracking-[0.18em] rounded-full border border-[#E7E0D8] px-2.5 py-1 text-[#8A847C]">iç görünüm</span>
    </div>
    <Outlet />
  </div>
);

export const InternalIndex = () => (
  <div className="max-w-2xl space-y-4">
    <h1 className="font-serif text-3xl">İç görünümler</h1>
    <p className="text-sm text-[#8A847C]">Herkese açık gezinmede görünmez. Kod silinmedi.</p>
    <ul className="space-y-2">
      {INTERNAL_VIEWS.map((v) => (
        <li key={v.path}><Link className="text-[#1A1816] underline underline-offset-4" to={`/internal/${v.path}`}>{v.label}</Link></li>
      ))}
    </ul>
  </div>
);
