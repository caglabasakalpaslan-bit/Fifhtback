// Shared style + content maps for Fifthback

export const TYPE_META = {
  REQUEST: { label: "Request", badge: "bg-sky-50 text-sky-800 border-sky-200", dot: "#0284C7" },
  TENSION: { label: "Tension", badge: "bg-amber-50 text-amber-800 border-amber-200", dot: "#D97706" },
  PROBLEM: { label: "Problem", badge: "bg-rose-50 text-rose-800 border-rose-200", dot: "#E11D48" },
  SUGGESTION: { label: "Suggestion", badge: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "#059669" },
  POSITIVE: { label: "Positive", badge: "bg-violet-50 text-violet-800 border-violet-200", dot: "#7C3AED" },
  OTHER: { label: "Other", badge: "bg-stone-100 text-stone-700 border-stone-200", dot: "#78716C" },
};

export const STATUS_META = {
  NEW: { label: "New", badge: "bg-blue-50 text-blue-700 border-blue-200", dot: "#2563EB" },
  ACTIVE: { label: "Active", badge: "bg-amber-50 text-amber-700 border-amber-200", dot: "#D97706" },
  STUCK: { label: "Stuck", badge: "bg-rose-50 text-rose-700 border-rose-200", dot: "#E11D48" },
  RESOLVED: { label: "Resolved", badge: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "#059669" },
};

export const SONG_SUGGESTIONS = [
  { title: "Under Pressure", artist: "Queen & David Bowie" },
  { title: "Helplessness Blues", artist: "Fleet Foxes" },
  { title: "Everything In Its Right Place", artist: "Radiohead" },
  { title: "Lovely Day", artist: "Bill Withers" },
  { title: "Dog Days Are Over", artist: "Florence + The Machine" },
];

export const DEMO_PRESETS = [
  {
    key: "handoff",
    label: "Design ↔ Eng handoff tension",
    text: "Every sprint the designs come in late and by the time engineering picks them up half of them can't actually be built in the time we have. It keeps happening and nobody wants to talk about it.",
    song: { title: "Under Pressure", artist: "Queen & David Bowie" },
  },
  {
    key: "onboarding",
    label: "Silent onboarding request",
    text: "I joined three weeks ago and I still don't have access to half the tools. I don't want to be annoying so I keep figuring it out on my own, but it's slowing me down.",
    song: null,
  },
  {
    key: "meetings",
    label: "Meeting overload problem",
    text: "My calendar is completely full of meetings and I have almost no time to do the actual work. By the time I can focus it's already 6pm.",
    song: { title: "Everything In Its Right Place", artist: "Radiohead" },
  },
  {
    key: "gratitude",
    label: "Gratitude & wins",
    text: "I just want to say the support team quietly saved a huge customer escalation last week and nobody noticed. They're amazing and I'm really grateful.",
    song: { title: "Lovely Day", artist: "Bill Withers" },
  },
];
