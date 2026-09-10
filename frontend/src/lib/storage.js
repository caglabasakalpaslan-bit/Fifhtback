// Minimal client-side persistence. Nothing here is a profile or a score.
// localStorage : identity (pseudonymous user_ref + nickname + avatar) — survives sessions.
// sessionStorage: drafts and the current journey — survives refresh/back, dies with the tab.

const LS_IDENTITY = "fifth.identity";
const SS_ANLAT_DRAFT = "fifth.anlat.draft";
const SS_ANLAT_SESSION = "fifth.anlat.session";
const SS_KESFET_CONTEXT = "fifth.kesfet.context";

const safe = (fn, fallback) => { try { return fn(); } catch { return fallback; } };

const uuid = () =>
  (window.crypto?.randomUUID?.() ||
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    }));

export const getIdentity = () => safe(() => JSON.parse(localStorage.getItem(LS_IDENTITY)), null);

export const ensureUserRef = () => {
  const id = getIdentity() || {};
  if (!id.user_ref) {
    id.user_ref = uuid();
    safe(() => localStorage.setItem(LS_IDENTITY, JSON.stringify(id)));
  }
  return id.user_ref;
};

export const saveIdentity = ({ nickname, avatar }) => {
  const id = { ...(getIdentity() || {}), nickname, avatar };
  if (!id.user_ref) id.user_ref = uuid();
  safe(() => localStorage.setItem(LS_IDENTITY, JSON.stringify(id)));
  return id;
};

export const getDraft = () => safe(() => sessionStorage.getItem(SS_ANLAT_DRAFT) || "", "");
export const setDraft = (text) => safe(() => sessionStorage.setItem(SS_ANLAT_DRAFT, text));
export const clearDraft = () => safe(() => sessionStorage.removeItem(SS_ANLAT_DRAFT));

export const getCurrentSession = () => safe(() => JSON.parse(sessionStorage.getItem(SS_ANLAT_SESSION)), null);
export const setCurrentSession = (turn) => safe(() => sessionStorage.setItem(SS_ANLAT_SESSION, JSON.stringify(turn)));
export const clearCurrentSession = () => safe(() => sessionStorage.removeItem(SS_ANLAT_SESSION));

export const getExplorationContext = () => safe(() => JSON.parse(sessionStorage.getItem(SS_KESFET_CONTEXT)), null);
export const setExplorationContext = (ctx) =>
  safe(() => sessionStorage.setItem(SS_KESFET_CONTEXT, JSON.stringify({ ...ctx, at: new Date().toISOString() })));

// Saved cards — the user's own list of finished stories (localStorage, this browser only).
// Each entry is a pointer plus the readable card text; the full record stays on the server by session_id.
const LS_CARDS = "fifth.cards";

export const getSavedCards = () => safe(() => JSON.parse(localStorage.getItem(LS_CARDS)) || [], []);

export const saveCardRecord = (turn) => {
  if (!turn || turn.status !== "done") return getSavedCards();
  const entry = {
    session_id: turn.session_id,
    card_id: turn.card?.card_id || null,
    mode: turn.mode,
    title: turn.card?.title || (turn.mode === "CLOSE" ? "Duyuldu" : turn.distinction || "Açıklama"),
    distinction: turn.card?.distinction || turn.distinction || null,
    take_with_you: turn.card?.take_with_you || null,
    close: turn.close || null,
    nickname: turn.nickname,
    avatar: turn.avatar,
    saved_at: new Date().toISOString(),
  };
  const rest = getSavedCards().filter((c) => c.session_id !== entry.session_id);
  const next = [entry, ...rest].slice(0, 200);
  safe(() => localStorage.setItem(LS_CARDS, JSON.stringify(next)));
  return next;
};

export const removeSavedCard = (session_id) => {
  const next = getSavedCards().filter((c) => c.session_id !== session_id);
  safe(() => localStorage.setItem(LS_CARDS, JSON.stringify(next)));
  return next;
};

// Plain-text rendering of a finished turn, for copying or sharing by hand.
export const cardToText = (turn) => {
  if (!turn) return "";
  if (turn.mode === "CLOSE") return `${turn.close || ""}\n\n— Fifthback`;
  const c = turn.card;
  if (!c) return `${turn.distinction || ""}\n\n${turn.reveal || ""}\n\n— Fifthback`;
  const lines = [c.title, "", `AYRIM: ${c.distinction}`, "", `NEDEN ÖNEMLİ: ${c.why_it_matters}`];
  if (c.still_open) lines.push("", `HÂLÂ AÇIK: ${c.still_open}`);
  lines.push("", `YANINDA GÖTÜR: ${c.take_with_you}`, "", "— Fifthback");
  return lines.join("\n");
};
