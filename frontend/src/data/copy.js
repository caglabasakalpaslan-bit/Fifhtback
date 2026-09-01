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

// FIRST-TIME WELCOME — shown once, before the Söyle surface.
// The opening story is expected to be rewritten: keep `body` a plain list of
// paragraphs and `questions` a plain list, so copy can change without touching
// the component. Order of paragraphs = order on screen, first one leads.
export const WELCOME = {
  title: "Bugün buraya hoş geldin.",
  body: [
    "Kimsenin hayatı aynı değil. Kimi dün yaşadığı bir şeyi anlatır, kimi yıllardır taşıdığı bir meseleyi.",
    "Fifthback insanları kalıplara ayırmak yerine, anlattıkları hikâyelerden yola çıkar.",
    "Söylediklerini benzer deneyimlerle birlikte anlamlandırır; tekrar eden örüntüleri ve çözümü görebilmek için önce ayırt edilmesi gereken soruları karşımıza çıkarır.",
    "Burada amaç yalnızca sorunu tarif etmek değildir. Bir şey denediğinde, istersen daha sonra geri gelip ne yaptığını ve neyin değiştiğini paylaşabilirsin. Bu deneyim, kimliğin açığa çıkmadan, benzer bir durumda olan başka insanların önünü görmesine yardımcı olabilir.",
  ],
  // Only two, and only context — never identity.
  questions: [
    {
      key: "experience",
      label: "Çalışma deneyimin hangi aralıkta?",
      options: ["0–1 yıl", "1–3 yıl", "3–7 yıl", "7+ yıl"],
    },
    {
      key: "leads",
      label: "Şu anda ekip yönetiyor musun?",
      options: ["Evet", "Hayır"],
    },
  ],
  support:
    "Fifthback yaş, cinsiyet ya da departman üzerinden insanları sınıflandırmaz. Bu iki bilgi yalnızca anlattığını daha doğru bağlama yerleştirebilmek için kullanılır.",
  privacy:
    "Kimliğini istemeyiz. Paylaşımın üzerinde kontrol sende kalır. Kişisel hikâyeler başkalarına birebir aktarılmaz; sistem gerekli olduğunda anonimleştirilmiş ve birleştirilmiş örüntüler üzerinden çalışır.",
  cta: "Devam et",
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
  title: "Bunu nereye koyduğunu birlikte görelim",
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
    share: "Anonim olarak paylaş",
    unshare: "Paylaşımdan çek",
  },
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
    unknown: "Hâlâ neyi bilmiyoruz?",
    next: "Ne denenebilir?",
  },
  provenance: "Bunu oluşturan sinyaller",
  provenanceNote: "Örnekler gizliliği korumak için yeniden yazıldı. Kimsenin kendi cümlesi olduğu gibi gösterilmez.",
  provenanceGated: "Bu hikâye henüz yeterli sayıda sinyalden oluşmadığı için örnek gösterilmiyor.",
  mechanismLabel: "Mekanizma",
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
