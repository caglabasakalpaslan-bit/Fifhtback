// The employee's own signals, kept in the browser only.
// Nothing here is sent anywhere unless the person explicitly shares it.
const KEY = "fifthback.my-signals.v1";

export const STATE_ORDER = ["NEW", "MATCHED", "FOLLOWING", "SHARED", "MOVING", "RESOLVED"];

export function loadSignals() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function persist(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    /* private mode — the session still works, it just will not be remembered */
  }
  return list;
}

// One submission = one card. Saying the same sentence again (or a burst of
// clicks landing at once) advances the existing card instead of adding another.
// toLocaleLowerCase("tr"): plain toLowerCase turns "TOPLANTILARDAN" into a
// dotted i and stops matching the dotless "toplantılardan".
const norm = (t) => (t || "").trim().toLocaleLowerCase("tr").replace(/\s+/g, " ");
const RANK = { NEW: 0, MATCHED: 1, FOLLOWING: 2, SHARED: 3, MOVING: 4, RESOLVED: 5 };
const furthest = (a, b) => ((RANK[b] ?? 0) > (RANK[a] ?? 0) ? b : a);

export function addSignal({ text, clusterId, storyTitle, matched }) {
  const list = loadSignals();
  const nextState = matched ? "MATCHED" : "NEW";

  const existing = list.find((s) => norm(s.text) === norm(text));
  if (existing) {
    return persist(list.map((s) => (s.id === existing.id
      ? { ...s,
          clusterId: clusterId || s.clusterId,
          storyTitle: storyTitle || s.storyTitle,
          state: s.shared ? s.state : furthest(s.state, nextState) }
      : s)));
  }

  const item = {
    id: `sig_${Date.now()}`,
    text,
    clusterId: clusterId || null,
    storyTitle: storyTitle || null,
    state: nextState,
    shared: false,
    createdAt: new Date().toISOString(),
  };
  return persist([item, ...list]);
}

export function updateSignal(id, patch) {
  return persist(loadSignals().map((s) => (s.id === id ? { ...s, ...patch } : s)));
}

export function removeSignal(id) {
  return persist(loadSignals().filter((s) => s.id !== id));
}

// Collapses duplicates already sitting in storage from before the guard existed.
// Keeps the earliest card, its furthest state, and any sharing the person chose;
// nothing is thrown away silently beyond the repeated copies themselves.
export function dedupeSignals() {
  const list = loadSignals();
  const byText = new Map();
  for (const s of [...list].reverse()) {          // oldest first
    const k = norm(s.text);
    const prev = byText.get(k);
    if (!prev) { byText.set(k, { ...s }); continue; }
    byText.set(k, {
      ...prev,
      clusterId: prev.clusterId || s.clusterId,
      storyTitle: prev.storyTitle || s.storyTitle,
      shared: prev.shared || s.shared,
      state: (prev.shared || s.shared) ? "SHARED" : furthest(prev.state, s.state),
    });
  }
  const merged = [...byText.values()].reverse();  // newest first again
  return merged.length === list.length ? list : persist(merged);
}
