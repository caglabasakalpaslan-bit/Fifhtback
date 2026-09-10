import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Trash2 } from "lucide-react";
import { BackLink } from "../components/BackLink";
import { getSavedCards, removeSavedCard } from "../lib/storage";

const fmt = (iso) => {
  try { return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" }); } catch { return ""; }
};

// The user's saved cards. Stored in this browser only; opening one reloads the full record from the server.
export const Kartlarim = () => {
  const navigate = useNavigate();
  const [cards, setCards] = useState(getSavedCards());
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto py-10 sm:py-14 space-y-8">
      <BackLink to="/" label="Kapılara dön" testId="cards-back" />
      <div>
        <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#8A847C] font-semibold">Kartlarım</p>
        <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">Yanında götürdüklerin.</h1>
        <p className="mt-3 text-[#57534E]">Bu tarayıcıda saklanır. Kimlik yok, hesap yok.</p>
      </div>
      {cards.length === 0 ? (
        <div data-testid="cards-empty" className="rounded-2xl border border-dashed border-[#E7E0D8] p-6 text-[#8A847C] space-y-3">
          <p>Henüz bir kartın yok.</p>
          <Link to="/anlat" className="inline-flex text-sm font-medium text-[#1A1816]">Anlat →</Link>
        </div>
      ) : (
        <ul className="space-y-3" data-testid="cards-list">
          {cards.map((c) => (
            <li key={c.session_id} data-testid="cards-item" className="rounded-2xl border border-[#E7E0D8] bg-white shadow-sm">
              <button onClick={() => navigate(`/anlat/${c.session_id}`)} className="w-full text-left p-5 space-y-1.5">
                <div className="flex items-center justify-between gap-3 text-xs text-[#8A847C]">
                  <span>{c.avatar} {c.nickname}</span>
                  <span>{fmt(c.saved_at)}</span>
                </div>
                <div className="font-serif text-xl leading-snug">{c.title}</div>
                {c.mode === "CLOSE" ? (
                  <p className="text-sm text-[#57534E]">{c.close}</p>
                ) : (
                  <>
                    {c.distinction && <p className="text-sm text-[#3F6B56]">{c.distinction}</p>}
                    {c.take_with_you && <p className="text-sm italic text-[#57534E]">{c.take_with_you}</p>}
                  </>
                )}
              </button>
              <div className="flex justify-end border-t border-[#F0EAE2] px-4 py-2">
                <button data-testid="cards-remove" onClick={() => setCards(removeSavedCard(c.session_id))}
                  className="inline-flex items-center gap-1.5 text-xs text-[#8A847C] hover:text-[#B04D27]">
                  <Trash2 className="h-3.5 w-3.5" /> Listeden çıkar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
};
