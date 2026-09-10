import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Trash2, Loader2 } from "lucide-react";
import { BackLink } from "../components/BackLink";
import { getSavedCards, removeSavedCard, replaceSavedCards, ensureUserRef } from "../lib/storage";
import { listSavedCards, deleteSavedCard } from "../lib/api";

const fmt = (iso) => {
  try { return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" }); } catch { return ""; }
};

// MY FIFTHBACK v0: the user's saved Fifth Cards, newest first. Source of truth is the server (by the
// browser's pseudonymous user_ref); the local mirror is shown while loading or if the server is unreachable.
export const Kartlarim = () => {
  const navigate = useNavigate();
  const [cards, setCards] = useState(getSavedCards());
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let alive = true;
    listSavedCards(ensureUserRef())
      .then((list) => {
        if (!alive) return;
        const merged = list.map((r) => ({
          session_id: r.session_id, card_id: r.card_id, title: r.title, distinction: r.distinction,
          why_it_matters: r.why_it_matters, still_open: r.still_open, take_with_you: r.take_with_you,
          route_path: r.route_path, nickname: r.nickname, avatar: r.avatar, created_at: r.created_at, saved_at: r.saved_at,
        }));
        setCards(replaceSavedCards(merged));
      })
      .catch(() => { if (alive) setOffline(true); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const remove = async (c) => {
    setCards(removeSavedCard(c.session_id));
    if (c.card_id) { try { await deleteSavedCard(c.card_id, ensureUserRef()); } catch { /* local removal already applied */ } }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto py-10 sm:py-14 space-y-8">
      <BackLink to="/" label="Kapılara dön" testId="cards-back" />
      <div>
        <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#8A847C] font-semibold">Kartlarım</p>
        <h1 className="mt-3 font-serif text-4xl sm:text-5xl font-medium tracking-tight leading-[1.05]">Yanında götürdüklerin.</h1>
        <p className="mt-3 text-[#57534E]">Kaydettiğin Fifth Kartları, en yeniden eskiye. Kimlik yok, hesap yok.</p>
        {loading && <p className="mt-2 inline-flex items-center gap-2 text-xs text-[#8A847C]" data-testid="cards-loading"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Yükleniyor…</p>}
        {offline && <p className="mt-2 text-xs text-[#B04D27]" data-testid="cards-offline">Sunucuya ulaşılamadı; bu tarayıcıda saklananlar gösteriliyor.</p>}
      </div>
      {cards.length === 0 ? (
        <div data-testid="cards-empty" className="rounded-2xl border border-dashed border-[#E7E0D8] p-6 text-[#8A847C] space-y-3">
          <p>Henüz kaydedilmiş bir kartın yok.</p>
          <Link to="/anlat" className="inline-flex text-sm font-medium text-[#1A1816]">Anlat →</Link>
        </div>
      ) : (
        <ul className="space-y-3" data-testid="cards-list">
          {cards.map((c) => (
            <li key={c.session_id} data-testid="cards-item" className="rounded-2xl border border-[#E7E0D8] bg-white shadow-sm">
              <button onClick={() => navigate(`/anlat/${c.session_id}`)} className="w-full text-left p-5 space-y-2">
                <div className="flex items-center justify-between gap-3 text-xs text-[#8A847C]">
                  <span>{c.avatar} {c.nickname}</span>
                  <span>{fmt(c.saved_at)}</span>
                </div>
                <div className="font-serif text-xl leading-snug">{c.title}</div>
                {c.distinction && (
                  <p className="text-sm text-[#3F6B56]"><span className="font-mono text-[10px] uppercase tracking-[0.18em] mr-2">Ayrım</span>{c.distinction}</p>
                )}
                {c.take_with_you && (
                  <p className="text-sm italic text-[#57534E]"><span className="not-italic font-mono text-[10px] uppercase tracking-[0.18em] mr-2 text-[#8A847C]">Yanında götür</span>{c.take_with_you}</p>
                )}
              </button>
              <div className="flex justify-end border-t border-[#F0EAE2] px-4 py-2">
                <button data-testid="cards-remove" onClick={() => remove(c)}
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
