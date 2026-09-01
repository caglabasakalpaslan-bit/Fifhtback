// First-time entry context, kept in the browser only.
//
// Two answers, both optional, both about work context — never identity.
// Nothing here is sent to the backend by this module; it exists so the welcome
// step is shown once and so the answers are available to whatever wants to put
// a story in context later.
const KEY = "fifthback.entry-context.v1";

const EMPTY = { seen: false, experience: null, leads: null, answeredAt: null };

export function loadEntryContext() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...EMPTY, ...JSON.parse(raw) } : { ...EMPTY };
  } catch {
    return { ...EMPTY };
  }
}

// True once the person has been through the welcome step, whether or not they
// answered the two questions. Private-mode browsers simply see it again.
export function hasSeenWelcome() {
  return loadEntryContext().seen === true;
}

export function saveEntryContext({ experience = null, leads = null } = {}) {
  const next = { seen: true, experience, leads, answeredAt: new Date().toISOString() };
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* private mode — the flow still works, it just will not be remembered */
  }
  return next;
}
