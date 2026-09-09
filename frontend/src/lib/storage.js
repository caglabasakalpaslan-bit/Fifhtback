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
