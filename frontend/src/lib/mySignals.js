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

export function addSignal({ text, clusterId, storyTitle, matched }) {
  const list = loadSignals();
  const item = {
    id: `sig_${Date.now()}`,
    text,
    clusterId: clusterId || null,
    storyTitle: storyTitle || null,
    state: matched ? "MATCHED" : "NEW",
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
