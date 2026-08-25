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

export const CLUSTER_COLORS = [
  { bg: "bg-[#FDF2EC]", border: "border-[#E9BCA6]", text: "text-[#B04D27]", dot: "#C85A32", solid: "#C85A32" },
  { bg: "bg-[#EDF5F0]", border: "border-[#B7D4C4]", text: "text-[#2F5344]", dot: "#3F6B56", solid: "#3F6B56" },
  { bg: "bg-[#FEF3C7]", border: "border-[#E7C766]", text: "text-[#92400E]", dot: "#D97706", solid: "#D97706" },
  { bg: "bg-[#EEF1F5]", border: "border-[#B9C4D2]", text: "text-[#334155]", dot: "#475569", solid: "#475569" },
  { bg: "bg-[#F3ECF7]", border: "border-[#CDB6DE]", text: "text-[#6B21A8]", dot: "#7C3AED", solid: "#7C3AED" },
  { bg: "bg-[#E7F4F5]", border: "border-[#A9D3D6]", text: "text-[#0E5A63]", dot: "#0E7490", solid: "#0E7490" },
  { bg: "bg-[#FDECEF]", border: "border-[#EBB4C0]", text: "text-[#9F1239]", dot: "#E11D48", solid: "#E11D48" },
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
