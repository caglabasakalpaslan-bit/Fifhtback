// All primary Turkish UI copy lives here.
// Rule: human language first, system language second. If a normal employee
// would not say it out loud, it does not belong in a primary slot.

export const BRAND = {
  name: "Fifthback",
  line: "Sesin sadece duyulsun diye değil, anlaşılsın diye.",
};

export const NAV = {
  entry: "Söyle",
  home: "Benim Alanım",
  manager: "Yönetici Görünümü",
  patterns: "Örüntü Haritası",
};

// FIRST-TIME WELCOME — one short screen, then straight in.
// The two context questions were removed from this step: nothing in the product
// reads them, so they were blocking entry for no return. lib/entryContext.js is
// kept intact so they can come back later, asked at a moment that earns them.
export const WELCOME = {
  title: "Bugün buraya hoş geldin.",
  body: [
    "Adını koymakta zorlandığın bir şeyi anlat. Fifthback ne olabileceğini birlikte görmeye çalışır.",
  ],
  privacy: "Anlattıkların bu cihazda kalır. Paylaşmayı sen seçersin.",
  cta: "Başla",
};

export const ENTRY = {
  title: "Söyle.",
  sub: "Aklında ne varsa yazabilirsin, konuşarak anlatabilirsin ya da hikâyelerden sana en yakın olanla başlayabilirsin.",
  paths: {
    write: "Yaz",
    speak: "Konuş",
    find: "Bir hikâyede kendini bul",
  },
  writePlaceholder: "Aklında ne var?",
  writeHint: "Tek bir cümle bile yeter. Kendi kelimelerinle yaz.",
  submit: "Gönder",
  // Shown ONLY inside the "Bir hikâyede kendini bul" mode — never as a second,
  // always-visible strip under the writing area.
  dictionaryLabel: "İş Hayatı Sözlüğü",
  dictionaryHint: "Sana tanıdık gelen bir cümleden başlayabilirsin.",
  dictionaryMore: "Başka hikâyeler göster",
};

export const VOICE = {
  idle: "Hazır olduğunda başla. Konuşman yazıya çevrilecek.",
  recording: "Dinliyorum…",
  stop: "Bitir",
  start: "Konuşmaya başla",
  transcriptTitle: "Söylediklerin böyle yazıldı",
  transcriptHint: "Yanlış yazılan bir yer varsa düzelt. Onaylamadan hiçbir şey analiz edilmez.",
  confirm: "Bu hâliyle gönder",
  discard: "Sil, baştan başla",
  notStored: "Ses kaydı saklanmaz. Yalnızca onayladığın metin işlenir.",
  unavailable: "Bu tarayıcıda konuşmayı yazıya çevirme desteği yok.",
  unavailableHint: "Şimdilik yazarak anlatabilirsin. Sesli anlatım altyapısı bu önizlemede bağlı değil.",
};

export const REFLECT = {
  title: "Bunu birlikte görelim",
  // Similar is not the same. Never say other people have this exact problem.
  similarLead: "Buna benzeyen bir sıkışmayı başkaları da tarif etmiş.",
  similarCaveat: "Aynı durum değil — yalnızca benzer bir yerde takılmışlar.",
  noneLead: "Bunu şimdilik tek başına anlatmışsın.",
  noneBody: "Benzer bir şey anlatıldığında burada görünecek.",
  technical: "Bunu nasıl adlandırıyoruz?",
  back: "Geri dön",
  enough: "Bu kadarı yeterli. Anlatmak istediğin anlaşıldı.",
  skip: "Geç",
  similar: "Benzer hikâyeler",
  toHome: "Benim Alanım'a git",
};

export const HOME = {
  title: "Benim Alanım",
  sub: "Anlattıkların ve şu an nerede oldukları.",
  empty: "Henüz bir şey anlatmadın.",
  emptyCta: "İlk hikâyeni anlat",
  journeyLabel: "Nerede",
  visibility: {
    private: "Yalnızca bende",
    shared: "Anonim olarak paylaşıldı",
    privateHint: "Şimdilik sadece sende.",
    sharedHint: "Anonim paylaşıldı — kim olduğun görünmüyor.",
    share: "Paylaşıma aç",
    unshare: "Paylaşımdan çek",
  },
};

// Shown after sharing. Deliberately describes what the code does today: the flag
// is stored in this browser. No transfer happens in this preview, so no claim of
// one is made here.
export const SHARED_CONFIRM = {
  title: "Paylaşıma açıldı.",
  body: "Bu Fifthback artık paylaşılabilir olarak işaretli. Bu önizlemede kaydın bu cihazda tutulur; kuruma bir aktarım yapılmaz. Kimliğin hiçbir yerde istenmedi.",
  seeMine: "Paylaştığımı gör",
  back: "Benim Alanım'a dön",
};

export const STATES = {
  NEW: { label: "Yeni", tone: "blue" },
  MATCHED: { label: "Benzer hikâyeler bulundu", tone: "violet" },
  FOLLOWING: { label: "Takip ediyorum", tone: "amber" },
  SHARED: { label: "Paylaştım", tone: "teal" },
  MOVING: { label: "Değişim var", tone: "sage" },
  RESOLVED: { label: "Çözüldü", tone: "green" },
};

export const MANAGER = {
  title: "Sorumlu olduğun alanda ne oluyor?",
  sub: "Kişiler değil, işin nerede sıkıştığı görünür.",
  never: "Bu bir çalışan değerlendirmesi değildir. Kişi, kişilik, motivasyon veya performans ölçülmez.",
  axes: {
    spread: "Yayılım",
    repetition: "Tekrar",
    impact: "İşe etkisi",
    blocker: "Takılma noktası",
    voice: "Konuşma kolaylığı",
    change: "Değişim",
  },
  gated: "Anonimlik eşiği karşılanmadığı için bu kırılım gösterilmiyor.",
  gatedShort: "Eşik altında",
};

export const PATTERNS = {
  title: "Örüntü Haritası",
  sub: "Yakın duran hikâyeler aynı mekanizmaya bağlanıyor. Yoğun bölgeler sıkışıklık demek.",
  legend: "Nokta büyüklüğü: kaç sinyalden oluştuğu · Yakınlık: mekanizma benzerliği",
  openHint: "Bir noktaya tıkla",
  demoBadge: "24 örnek anonim sinyal (demo verisi)",
};

export const DETAIL = {
  angles: {
    why: "Neden bunlar birlikte?",
    impact: "Etkisi ne?",
    history: "Ne zamandır, ne kadar tekrar ediyor?",
    unknown: "Burada hâlâ net olmayan ne?",
    next: "Buradan sonra neyi deneyebilirsin?",
  },
  provenance: "Bunu oluşturan sinyaller",
  provenanceNote: "Örnekler gizliliği korumak için yeniden yazıldı. Kimsenin kendi cümlesi olduğu gibi gösterilmez.",
  provenanceGated: "Bu hikâye henüz yeterli sayıda sinyalden oluşmadığı için örnek gösterilmiyor.",
  mechanismLabel: "Bunu nasıl adlandırıyoruz?",
  tried: "Daha önce ne denenmiş?",
  worked: "Ne zaman işe yaramış?",
  failed: "Ne zaman yetmemiş?",
  more: "Devamını aç",
  less: "Kapat",
};

export const PRESSURE = {
  label: "Sıkışıklık",
  high: "Sıkışıklık yüksek",
  medium: "Sıkışıklık orta",
  low: "Sıkışıklık düşük",
  none: "Yeterli veri yok",
};

export const DEMO_NOTE = "Örnek veri — gerçek çalışan gönderimi değildir.";
