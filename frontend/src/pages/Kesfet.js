import React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { BackLink } from "../components/BackLink";
import { setExplorationContext, getExplorationContext } from "../lib/storage";

// KENDİNİ BUL — structural shell only. World visuals (Olympos etc.) are NOT designed here;
// a hand-drawn UX direction will define them. This screen only records which world was chosen.
export const WORLDS = [
  { group: "Mitler", items: [{ id: "yunan-mitleri", title: "Yunan Mitleri", line: "Olympos'un kapıları.", active: true }] },
  { group: null, items: [{ id: "yasanmis-hikayeler", title: "Yaşanmış Hikâyeler", line: "Gerçek insanların anlattıkları.", active: true }] },
  { group: "Yakında", items: [
    { id: "atasozleri", title: "Atasözleri & Deyimler", active: false },
    { id: "internetin-sesi", title: "İnternetin Sesi", active: false },
    { id: "sinema-edebiyat", title: "Sinema / Edebiyat", active: false },
  ] },
];

const WorldRow = ({ w }) => {
  const navigate = useNavigate();
  if (!w.active) {
    return (
      <div data-testid={`world-${w.id}`} aria-disabled="true" className="flex items-center justify-between rounded-2xl border border-dashed border-[#E7E0D8] px-5 py-4 text-[#B8B0A6]">
        <span className="font-serif text-xl">{w.title}</span>
        <span className="text-[10px] font-mono uppercase tracking-[0.16em]">yakında</span>
      </div>
    );
  }
  return (
    <button
      data-testid={`world-${w.id}`}
      onClick={() => { setExplorationContext({ world: w.id, title: w.title }); navigate(`/kesfet/${w.id}`); }}
      className="w-full text-left flex items-center justify-between rounded-2xl border border-[#E7E0D8] bg-white px-5 py-4 shadow-sm hover:border-[#3F6B56] transition-colors"
    >
      <div>
        <div className="font-serif text-xl">{w.title}</div>
        {w.line && <div className="text-sm text-[#8A847C]">{w.line}</div>}
      </div>
      <span className="text-sm text-[#3F6B56]">Gir →</span>
    </button>
  );
};

export const Kesfet = () => (
  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto py-10 sm:py-14 space-y-8">
    <BackLink to="/" label="Kapılara dön" testId="kesfet-back" />
    <div>
      <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#3F6B56] font-semibold">Kendini bul</p>
      <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">Burası yaşanmışlıkların sesi.</h1>
      <p className="mt-3 text-[#57534E]">Bir dünya seç. İçinde kendine tanıdık gelen bir şey ara.</p>
    </div>
    <div className="space-y-6">
      {WORLDS.map((g, i) => (
        <div key={i} className="space-y-2">
          {g.group && <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#8A847C]">{g.group}</p>}
          {g.items.map((w) => <WorldRow key={w.id} w={w} />)}
        </div>
      ))}
    </div>
  </motion.div>
);

// Placeholder for a chosen world. Deliberately no layout for figures/rooms/gates here.
export const KesfetWorld = () => {
  const { worldId } = useParams();
  const world = WORLDS.flatMap((g) => g.items).find((w) => w.id === worldId);
  const ctx = getExplorationContext();
  if (!world || !world.active) {
    return (
      <div className="max-w-2xl mx-auto py-14 space-y-6">
        <BackLink to="/kesfet" label="Dünyalara dön" />
        <p className="font-serif text-2xl">Bu dünya henüz açık değil.</p>
      </div>
    );
  }
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto py-10 sm:py-14 space-y-8">
      <BackLink to="/kesfet" label="Dünyalara dön" testId="world-back" />
      <div>
        <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#3F6B56] font-semibold">Kendini bul · {world.title}</p>
        <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">Kapı hazırlanıyor.</h1>
        <p className="mt-3 text-[#57534E]">Bu dünyanın içi henüz çizilmedi. Seçimin kaydedildi{ctx?.world === world.id ? "" : ""}; geri dönüp başka bir yere bakabilirsin.</p>
      </div>
      <Link to="/anlat" data-testid="world-to-anlat" className="inline-flex text-sm font-medium text-[#57534E] hover:text-[#1A1816]">
        Şimdilik kendi hikâyeni anlatmak istersen → Anlat
      </Link>
    </motion.div>
  );
};
