// ADAPTER LAYER — not an engine.
//
// The backend already decides what clusters exist, which signals belong to them,
// and what the five-angle analysis says. This file only puts a human face on
// that output:
//
//   existing cluster_id  ->  human STORY title (primary)
//   existing mechanism   ->  secondary label, kept small
//   existing evidence    ->  replaced for display by paraphrases (privacy)
//
// No clustering, no scoring of people, no new source of truth. If the backend
// returns a cluster this file does not know, the UI falls back to the backend's
// own name rather than inventing one.

// story title + paraphrased provenance, keyed by the EXISTING curated cluster ids
export const STORY_BY_CLUSTER = {
  c1: {
    title: "Kararlar bir yerde takılıyor.",
    mechanism: "karar gecikmesi · belirsiz sahiplik",
    why: "Farklı görünen şikâyetlerin hepsi aynı yere çıkıyor: kararın kimde olduğu belli değil.",
    provenance: [
      "Başlayabilmek için onay bekliyoruz.",
      "Son sözün kimde olduğu belli değil.",
      "Her onayda aynı kişiyi bekliyoruz.",
    ],
  },
  c2: {
    title: "Aynı işi ikinci kez yapıyoruz.",
    mechanism: "yeniden iş · geç geri bildirim",
    why: "Hepsi aynı sebepten: doğrulama iş bittikten sonra geliyor.",
    provenance: [
      "İş bittikten sonra “aslında şöyle olacaktı” deniyor.",
      "Gereksinimler yolun ortasında değişiyor.",
      "Bitmiş işi tekrar tekrar düzenliyoruz.",
    ],
  },
  c3: {
    title: "İşin sahibi kim, belli değil.",
    mechanism: "belirsiz sahiplik · devir sürtüşmesi",
    why: "Ortak nokta şu: işin sahibi baştan belli değil.",
    provenance: [
      "Herkes bir başkasının yaptığını sanıyor.",
      "Devirlerde bağlam kayboluyor.",
      "İş, sahibi çıkana kadar ekipler arasında dolaştı.",
    ],
  },
  c4: {
    title: "Herkes meşgul ama işler ilerlemiyor.",
    mechanism: "öncelik belirsizliği · akış tıkanması",
    why: "Hepsi aynı şeyi gösteriyor: sorun kapasite değil, neyin önce geldiğinin belirsizliği.",
    provenance: [
      "Bu hafta hangi işin öncelikli olduğunu bilmiyoruz.",
      "Herkes meşgul ama bazı işler el değmeden bekliyor.",
      "Daha kalabalığız ama teslimat hızlanmadı.",
    ],
  },
  c5: {
    title: "Bilgi dağınık, aynı şeyi elle taşıyoruz.",
    mechanism: "bilgi boşluğu · araç kopukluğu",
    why: "Ortak nokta şu: güvenilir tek bir kaynak yok, bilgi elle taşınıyor.",
    provenance: [
      "Aradığım bilgiyi ilk bakışta hiçbir zaman bulamıyorum.",
      "Araçların yarısı birbiriyle konuşmuyor.",
      "Aynı veriyi iki yere ayrı ayrı giriyoruz.",
    ],
  },
  c_new: {
    title: "Yeni anlatılanlar henüz yerine oturmadı.",
    mechanism: "kümelenmeyi bekliyor",
    why: "Bu anlatılanlar henüz ortak bir mekanizmaya bağlanmadı.",
    provenance: [],
  },
};

// Human-language titles for the EXISTING seeded manager patterns, matched by title.
export const STORY_BY_PATTERN_TITLE = {
  "Tasarım ↔ Yazılım devir sürtüşmesi": "Devirde iş yarım kalıyor.",
  "Toplantı yoğunluğu odaklanmayı aşındırıyor": "Toplantılar işin yerini alıyor.",
  "Yeni çalışanlar için sessiz işe alışma boşlukları": "Yeni gelen sessizce bekliyor.",
  "Perde arkası çalışmanın takdir edilmesi": "Görünmeyen emek fark ediliyor.",
  "Önce-yazılı (async) dokümantasyon alışkanlığı": "Yazıya dökmek işi kolaylaştırdı.",
};

// İŞ HAYATI SÖZLÜĞÜ — natural human sentences, not consulting categories.
// `featured` marks the few the mode opens with; the rest stay here and are
// revealed on request. Routing is the same for every phrase.
//
// `cluster: null` is deliberate, not missing data. It means one of two things:
//   - the phrase is positive, and no cluster describes positives; or
//   - the phrase is about the cost of speaking up — voice safety, fear of
//     being misunderstood, self-doubt — which no current cluster describes.
// Both land on the honest "henüz eşleşmedi" state rather than being filed
// under a mechanism that does not match. No new cluster is invented here.
// `cluster` points at the existing curated cluster the phrase belongs to, so
// selecting a phrase reuses the backend's clustering instead of bypassing it.
export const DICTIONARY = [
  { phrase: "Söylesem olmuyor, sussam gönlüm razı değil.", cluster: null, featured: true },
  { phrase: "İşimden değil, işin yapılış şeklinden yoruldum.", cluster: "c4", featured: true },
  { phrase: "Herkes biliyor ama kimse söylemiyor.", cluster: null },
  { phrase: "Toplantılardan iş yapmaya zaman kalmıyor.", cluster: "c1", featured: true },
  { phrase: "Bir şey yanlış ama adını koyamıyorum.", cluster: null },
  { phrase: "Ne yaparsak yapalım karar yine başa dönüyor.", cluster: "c1", featured: true },
  { phrase: "Öncelikler sürekli değişiyor.", cluster: "c4" },
  { phrase: "Kimse son kararın kimde olduğunu bilmiyor.", cluster: "c1" },
  { phrase: "Bunu yöneticime söylesem yanlış anlaşılır.", cluster: null },
  { phrase: "Ben mi abartıyorum, yoksa gerçekten böyle mi?", cluster: null, featured: true },
  { phrase: "Bitirdiğimiz iş geri dönüyor.", cluster: "c2" },
  { phrase: "Aradığım bilgiyi hiçbir zaman bulamıyorum.", cluster: "c5" },
  // the dictionary is not only complaints
  { phrase: "Zor bir işi birlikte çıkardık.", cluster: null, positive: true, featured: true },
  { phrase: "Takıldığımda gerçekten yardım geldi.", cluster: null, positive: true },
];

export const whyTogether = (clusterId, backendWhyFormed) =>
  STORY_BY_CLUSTER[clusterId]?.why || backendWhyFormed;

export const storyFor = (cluster) => STORY_BY_CLUSTER[cluster?.id] || null;

// Human title first, backend name only as fallback. Never invents a title.
export const humanTitle = (clusterId, backendName) =>
  STORY_BY_CLUSTER[clusterId]?.title || backendName;

export const secondaryLabel = (clusterId, backendMechanism) =>
  STORY_BY_CLUSTER[clusterId]?.mechanism || backendMechanism;
