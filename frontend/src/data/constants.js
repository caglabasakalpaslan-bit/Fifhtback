// Shared style + content maps for Fifthback

export const TYPE_META = {
  REQUEST: { label: "Talep", badge: "bg-sky-50 text-sky-800 border-sky-200", dot: "#0284C7" },
  TENSION: { label: "Gerginlik", badge: "bg-amber-50 text-amber-800 border-amber-200", dot: "#D97706" },
  PROBLEM: { label: "Sorun", badge: "bg-rose-50 text-rose-800 border-rose-200", dot: "#E11D48" },
  SUGGESTION: { label: "Öneri", badge: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "#059669" },
  POSITIVE: { label: "Olumlu", badge: "bg-violet-50 text-violet-800 border-violet-200", dot: "#7C3AED" },
  OTHER: { label: "Diğer", badge: "bg-stone-100 text-stone-700 border-stone-200", dot: "#78716C" },
};

export const STATUS_META = {
  NEW: { label: "Yeni", badge: "bg-blue-50 text-blue-700 border-blue-200", dot: "#2563EB" },
  ACTIVE: { label: "Aktif", badge: "bg-amber-50 text-amber-700 border-amber-200", dot: "#D97706" },
  STUCK: { label: "Takıldı", badge: "bg-rose-50 text-rose-700 border-rose-200", dot: "#E11D48" },
  RESOLVED: { label: "Çözüldü", badge: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "#059669" },
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
    label: "Tasarım ↔ Yazılım devir gerginliği",
    text: "Her sprintte tasarımlar geç geliyor ve yazılım ekibi onları eline aldığında yarısı elimizdeki sürede gerçekten yapılamıyor. Bu sürekli tekrarlanıyor ve kimse bunu konuşmak istemiyor.",
    song: { title: "Under Pressure", artist: "Queen & David Bowie" },
  },
  {
    key: "onboarding",
    label: "Sessiz işe alışma talebi",
    text: "Üç hafta önce başladım ve hâlâ araçların yarısına erişimim yok. Rahatsız edici olmak istemiyorum, o yüzden kendi başıma çözmeye çalışıyorum ama bu beni yavaşlatıyor.",
    song: null,
  },
  {
    key: "meetings",
    label: "Toplantı yoğunluğu sorunu",
    text: "Takvimim tamamen toplantılarla dolu ve asıl işi yapmaya neredeyse hiç vaktim kalmıyor. Odaklanabildiğimde saat çoktan 18:00 oluyor.",
    song: { title: "Everything In Its Right Place", artist: "Radiohead" },
  },
  {
    key: "gratitude",
    label: "Teşekkür ve kazanımlar",
    text: "Sadece şunu söylemek istiyorum: destek ekibi geçen hafta büyük bir müşteri sorununu sessizce çözdü ve kimse fark etmedi. Harikalar ve gerçekten minnettarım.",
    song: { title: "Lovely Day", artist: "Bill Withers" },
  },
];
