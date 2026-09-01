# Signal Mapping & Public-Signal Classification

**Status:** documentation only. Describes how a statement travels through Fifthback
today, what it is classified as at each step, and how far it is allowed to travel.
Nothing here is wired into the application.

Companion documents: `ontology.md` (what the terms mean), `ambiguities.md` (where the
current mapping is inconsistent).

---

## 1. The pipeline

```
Anlatı ──extract──▶ Sinyal ──(share)──▶ Havuz Satırı ──cluster──▶ Küme
                                                                    │
                                              ┌─────────────────────┼──────────────┐
                                              ▼                     ▼              ▼
                                          Mekanizma             Hikâye          Örüntü
                                                                                   │
                                                              ┌────────────────────┼─────────┐
                                                              ▼                    ▼         ▼
                                                         Sıkışıklık          Geçmiş Vaka   Eylem
```

Two properties are attached at entry and carried, unchanged, for the whole journey:

- **Provenance (P0–P3)** — where the statement came from. Set once, never upgraded.
- **Disclosure (D0–D3)** — how far it may be shown. Can only rise by an explicit act,
  and never above the ceiling its provenance permits.

Everything else — cluster, mechanism, pressure band — is derived and may change on
re-analysis. Provenance may not.

---

## 2. Provenance tiers

| Tier | Turkish | What it is | May add mass? | Notes |
| --- | --- | --- | --- | --- |
| **P0** | birinci ağızdan | The person's own words, typed or spoken into the product | ✅ | The only tier that can support a verbatim-evidence claim (INV-01) |
| **P1** | aktarılan | Anonymous lines entered on someone else's behalf: manager-pasted signals, retro exports, workshop notes | ✅ | The wording is the relayer's, so it cannot be quoted as evidence |
| **P2** | örnek / demo | The 24 seeded pool lines, the İş Hayatı Sözlüğü phrases, the seeded manager patterns | ❌ | Must be visibly labelled wherever it sits next to real content |
| **P3** | dış kamusal | Publicly posted statements about work life from outside the organisation | ❌ | Vocabulary and hypothesis generation only |

### Where each tier lives today

- **P0** — `InterpretRequest.text`, and the entries in `lib/mySignals.js`.
- **P1** — `POST /api/pattern-room/add-signals`, appended to `pattern_room_meta.pool`
  and landing in the `c_new` catch-all cluster until a live re-analysis places them.
- **P2** — `PATTERN_ROOM_SIGNALS` (24 lines), `DICTIONARY` (14 phrases), the five
  seeded `Pattern` rows, labelled by `PATTERNS.demoBadge` and `DEMO_NOTE`.
- **P3** — **does not exist in the product today.** It is defined here because
  research work will encounter such material, and it needs a class that keeps it out
  of the counting path. See §4.3.

### The relay caveat

P1 is the tier most likely to be misread. A manager pasting *"Onaylar günler sürüyor"*
has produced a real signal about the work system, but the sentence is **theirs**, not
an employee's. It therefore:

- may contribute to cluster mass and to pattern frequency;
- may **not** be presented as something an employee said;
- may **not** be used as `Signal.evidence` for anybody's interpretation.

The distinction matters because the product's core promise is that quotes are real.

---

## 3. Disclosure classes

| Class | Turkish | Where it is visible | Gate |
| --- | --- | --- | --- |
| **D0** | yalnızca bende | The author's own browser, `localStorage` only | none — it never leaves the device |
| **D1** | anonim havuz | Inside an aggregate cluster, never on its own | `MIN_AGGREGATE_N` = 5 |
| **D2** | yönetici görünümü | A manager's view of their own area | `MIN_MANAGER_N` = 8 |
| **D3** | dışa açık | Demos, research write-ups, anything leaving the organisation | P2/P3 only, or a paraphrased aggregate above every threshold |

D2 is stricter than D1 on purpose: a manager already knows who reports to them, so a
group size that is anonymous to the organisation is not anonymous to them. This is
stated once in `lib/privacy.js` and is the single most load-bearing asymmetry in the
privacy model.

### Movement between classes

```
D0 ──author shares──▶ D1 ──threshold met──▶ D2 ──paraphrase + all thresholds──▶ D3
 ▲                     │
 └──author unshares────┘
```

- The only edge out of D0 is an explicit act by the author
  (`HOME.visibility.share`). Nothing else can promote it.
- The D0 ← D1 edge exists (`unshare`) but does **not** retract mass already counted
  into a cluster — the aggregate has no per-item retraction path. This is a real
  limitation and is recorded in `ambiguities.md` §7.
- Reaching D3 requires paraphrase, never the original sentence (INV-06).

---

## 4. Public-signal classification

"Public signal" is used here for any statement that has left the author's private
space. It splits into two cases that are frequently conflated, and the whole point of
this section is that they must not be.

### 4.1 Internally public (D1/D2, provenance P0/P1)

A statement the author chose to share into their own organisation's pool. It is
*public* in the sense that others may encounter its effect — but only ever as part of
an aggregate, paraphrased, above threshold.

Rules:

1. It contributes to mass exactly once, at the index it occupies in the pool.
2. It is never rendered alone; the smallest renderable unit is a cluster.
3. Its displayed provenance is a paraphrase drawn from `STORY_BY_CLUSTER[*].provenance`,
   which requires at least `MIN_PROVENANCE_N` = 4 contributing signals.
4. If any non-empty bucket of a breakdown falls below `MIN_BUCKET_N` = 2, the whole
   breakdown is suppressed — so "17 of 18" can never expose the one.

### 4.2 Externally public (D3, provenance P3)

A statement about work life posted publicly outside the organisation: a forum thread,
a public review, a social post, a published survey verbatim.

**Eligibility** — a P3 item may be used for research only if all of the following hold:

| Check | Requirement |
| --- | --- |
| Genuinely public | Posted in a space with no expectation of privacy; no scraping behind a login or paywall |
| About the work system | Describes how work happens, not a named person's conduct or character |
| No identification retained | Author handle, employer name and any identifying detail are dropped at intake, not at publication |
| Paraphrasable | The mechanism survives being restated in the researcher's own words |
| Not sensitive | Fails the sensitivity screen below → excluded |

**Sensitivity screen** — exclude outright if the item involves any of:

- an identifiable individual's conduct, performance or health;
- a protected characteristic used as the subject of the complaint;
- an active legal dispute, harassment allegation or safety incident;
- anything where the author is identifiable from the content itself even after the
  handle is removed.

These are excluded rather than redacted. Redaction of a small, identifiable community
does not produce anonymity.

**What a P3 item may do**

- ✅ Suggest that a mechanism exists, or that the vocabulary is missing a term.
- ✅ Provide a phrasing candidate for the İş Hayatı Sözlüğü, once rewritten.
- ✅ Corroborate that a mechanism observed internally is not unique to this
  organisation (evidence grade E3).

**What a P3 item may never do**

- ❌ Contribute to `frequency`, `evidence[]`, `signal_indices`, prevalence, or any
  count a user sees.
- ❌ Appear as a quotation anywhere in the product.
- ❌ Be mixed into the pool passed to `POST /api/pattern-room/add-signals`.

### 4.3 Why the barrier is absolute

`_match_prevalence` deliberately returns `found=False` rather than an estimate, and
`estimated_cost` stays qualitative rather than inventing a currency figure. Both exist
to keep every number a user sees traceable to something that actually happened inside
their organisation.

A single external line entering the pool would silently break that: the cluster's
`signal_indices` would grow, the pattern's evidence count would rise, `repetition`
would climb, and the sıkışıklık band could shift — all without one additional person
in the organisation having said anything. There is no way to display that honestly,
so the barrier is structural rather than a matter of care.

This rule is recorded as **G-03** in `schema.json`.

---

## 5. Current mappings

### 5.1 Pool line → cluster (the 24 seeded lines)

Membership is by **index**, from `_curated_pattern_room`. Note that this makes the
pool effectively append-only: reordering or deleting a line silently re-points every
cluster.

| # | Line | Cluster | Mechanism ids |
| --- | --- | --- | --- |
| 0 | Onaylar günler sürüyor. | c1 | karar-gecikmesi |
| 1 | Aynı kararı tekrar tekrar konuşuyoruz. | c1 | karar-gecikmesi |
| 2 | Geliştirme başladıktan sonra spesifikasyonlar değişiyor. | c2 | yeniden-is |
| 3 | Çoğu zaman tek bir kıdemli kişiyi bekliyorum. | c1 | karar-gecikmesi, belirsiz-sahiplik |
| 4 | Daha fazla kişi işe aldık ama teslimat hızlanmadı. | c4 | kapasite-kisiti, onceliklendirme-catismasi |
| 5 | İki ekip de işin sahibinin diğeri olduğunu sanmış. | c3 | belirsiz-sahiplik |
| 6 | Kimse sonuçlandıramadığı için toplantıları tekrarlıyoruz. | c1 | karar-gecikmesi |
| 7 | İş, geç gelen geri bildirimden sonra geri gönderiliyor. | c2 | yeniden-is |
| 8 | Herkes meşgul ama bazı işler el değmeden bekliyor. | c4 | onceliklendirme-catismasi |
| 9 | Önemli bilgiler üç farklı araca dağılmış durumda. | c5 | bilgi-boslugu |
| 10 | Çok fazla toplantı var ama yeterince karar çıkmıyor. | c1 | karar-gecikmesi |
| 11 | Başlayabilmek için onay bekliyoruz. | c1 | karar-gecikmesi |
| 12 | Son sözün kimde olduğundan kimse emin değil. | c1 | belirsiz-sahiplik |
| 13 | Gereksinimler yolun ortasında değişiyor, baştan yapıyoruz. | c2 | yeniden-is |
| 14 | Aynı rapor iki farklı ekip tarafından hazırlanıyor. | c5 | surec-tekrari |
| 15 | Geri bildirim ancak iş bittikten sonra geliyor. | c2 | yeniden-is |
| 16 | Her onay için tek bir kişi darboğaz oluyor. | c1 | karar-gecikmesi, belirsiz-sahiplik |
| 17 | Bu hafta hangi işin öncelikli olduğunu bilemiyoruz. | c4 | onceliklendirme-catismasi |
| 18 | Tasarım ile geliştirme arasındaki devirlerde bağlam kayboluyor. | c3 | devir-surtusmesi |
| 19 | Yeni bir araç aldık ama hâlâ veriyi elle kopyalıyoruz. | c5 | arac-sistem-surtusmesi |
| 20 | Kararlar bir hafta sonra yeniden açılıyor. | c1 | karar-gecikmesi |
| 21 | Bir talep, sahibi çıkana kadar üç ekip arasında gidip geldi. | c3 | belirsiz-sahiplik, devir-surtusmesi |
| 22 | Son dakika değişikliklerden sonra sunumları tekrar tekrar düzenliyoruz. | c2 | yeniden-is |
| 23 | Araçlarımızın yarısı birbiriyle konuşmuyor. | c5 | arac-sistem-surtusmesi |

Distribution: c1 = 9, c2 = 5, c5 = 4, c3 = 3, c4 = 3. The c1 mass is what puts it at
rank 1, and it is worth noting that c1 carries **two** mechanisms — part of its size
may be a vocabulary artefact rather than a real concentration (`ambiguities.md` §2).

### 5.2 Cluster → story

| Cluster | Engine name (secondary) | Story title (primary) |
| --- | --- | --- |
| c1 | Karar Akışı / Sahiplik Darboğazı | Kararlar bir yerde takılıyor. |
| c2 | Yeniden İş Döngüsü | Aynı işi ikinci kez yapıyoruz. |
| c3 | Sahiplik & Devir Karışıklığı | İşin sahibi kim, belli değil. |
| c4 | Kapasite vs. Öncelik | Herkes meşgul ama işler ilerlemiyor. |
| c5 | Bilgi & Araç Kopukluğu | Bilgi dağınık, aynı şeyi elle taşıyoruz. |
| c_new | Yeni Sinyaller (kümelenmeyi bekliyor) | Yeni anlatılanlar henüz yerine oturmadı. |

### 5.3 Dictionary phrase → cluster

`DICTIONARY` in `frontend/src/data/stories.js`. Selecting a phrase routes it into an
existing cluster rather than bypassing clustering.

| Phrase | Routed to | Assessment |
| --- | --- | --- |
| Söylesem olmuyor, sussam gönlüm razı değil. | c3 | ⚠️ voice safety, not ownership |
| İşimden değil, işin yapılış şeklinden yoruldum. | c4 | ⚠️ system-level fatigue, weakly about priority |
| Herkes biliyor ama kimse söylemiyor. | c3 | ⚠️ voice safety, not ownership |
| Toplantılardan iş yapmaya zaman kalmıyor. | c1 | ⚠️ attention fragmentation, only indirectly decision latency |
| Bir şey yanlış ama adını koyamıyorum. | c3 | ⚠️ unnamed; c3 is acting as a catch-all |
| Ne yaparsak yapalım karar yine başa dönüyor. | c1 | ✅ karar-gecikmesi |
| Öncelikler sürekli değişiyor. | c4 | ✅ onceliklendirme-catismasi |
| Kimse son kararın kimde olduğunu bilmiyor. | c1 | ✅ belirsiz-sahiplik |
| Bunu yöneticime söylesem yanlış anlaşılır. | c3 | ⚠️ voice safety, not ownership |
| Ben mi abartıyorum, yoksa gerçekten böyle mi? | c3 | ⚠️ self-doubt / validation, not a mechanism at all |
| Bitirdiğimiz iş geri dönüyor. | c2 | ✅ yeniden-is |
| Aradığım bilgiyi hiçbir zaman bulamıyorum. | c5 | ✅ bilgi-boslugu |
| Zor bir işi birlikte çıkardık. | `null` (positive) | no cluster exists for it |
| Takıldığımda gerçekten yardım geldi. | `null` (positive) | no cluster exists for it |

Six of the twelve non-positive phrases are routed to a cluster whose mechanism does
not describe them. Five of those six are about the **cost of speaking up** — a
dimension the manager view declares as an axis and never measures. This is the
single largest semantic gap in the current model; it is written up in
`ambiguities.md` §4 and is the first research question in
`research-agent-brief.md`.

### 5.4 Seeded pattern title → story

`STORY_BY_PATTERN_TITLE`, keyed by exact title string.

| Seeded pattern title | Story title |
| --- | --- |
| Tasarım ↔ Yazılım devir sürtüşmesi | Devirde iş yarım kalıyor. |
| Toplantı yoğunluğu odaklanmayı aşındırıyor | Toplantılar işin yerini alıyor. |
| Yeni çalışanlar için sessiz işe alışma boşlukları | Yeni gelen sessizce bekliyor. |
| Perde arkası çalışmanın takdir edilmesi | Görünmeyen emek fark ediliyor. |
| Önce-yazılı (async) dokümantasyon alışkanlığı | Yazıya dökmek işi kolaylaştırdı. |

Three of these five name mechanisms that are **not in the vocabulary at all**:
attention fragmentation (meeting load), onboarding gaps, and recognition of invisible
work. The last two entries are positive and have no mechanism by construction.

### 5.5 Anlatı → pattern (prevalence)

`_match_prevalence` matches an interpretation against seeded patterns using 5-character
Turkish stem prefixes, requiring an overlap of at least 2 stems. Below that it returns
`found=False` and the UI shows an honest empty state.

The same stem technique drives `similar_to` distance on the Örüntü Haritası, which is
why *belirsiz* and *belirsizliği* pull toward each other on the map.

---

## 6. Classification procedure

For any new statement entering the system:

1. **Assign provenance.** Who typed this sentence, and was it about their own
   experience? P0 if the author is describing their own work; P1 if relayed; P2 if
   authored as an example; P3 if collected from outside the organisation.
2. **Set the disclosure ceiling.** P0/P1 → D2 maximum. P2/P3 → D3, but barred from
   mass (G-03, G-04).
3. **Run the sensitivity screen** (§4.2) for anything P3, and for any P0/P1 statement
   that names an individual. Naming an individual is a reason to exclude the naming,
   not the statement.
4. **Assign a mechanism** using the distinguishing tests in `ontology.md` §4. If two
   tests both pass, record both and flag it — a statement matching two mechanisms is
   usually a sign that a third, unnamed mechanism is at work.
5. **Assign an evidence grade** (E0–E4, `schema.json`). A single statement is E0 and
   supports no pattern claim on its own.
6. **Record what would change the assignment.** Every classification carries a
   falsifier, exactly as every hypothesis does. A classification nobody can argue with
   is one nobody checked.
