# Steam Oyun Benzerlik Ağı

Sosyal Ağ Analizi dönem ödevi · Büyük Veri Analistliği · Hazırlayan: Beril Özdizdar (2516016020)

**Etkileşimli ağ:** https://beril-ozdr.github.io/steam-network/

## Tek cümlelik bulgu

Steam'in en popüler 2.000 oyununda etiketler rastlantıyla değil gruplar halinde birlikte geçiyor; bağlantı tahmini, "Female Protagonist + Sandbox" gibi olası ama verimizde hiç ya da çok az oyunda denenmiş kombinasyonları işaret ediyor.

## CV cümlesi

SteamSpy verisinden 2.000 oyunluk bir benzerlik ağı kurup Louvain/Leiden topluluk tespiti, null model karşılaştırması ve Adamic-Adar bağlantı tahmini ile bağımsız stüdyolar için az denenmiş etiket kombinasyonlarını belirledim (Python, NetworkX, igraph; tahminler eski %70 / yeni %30 oyun ayrımıyla doğrulandı).

## Araştırma sorusu

Bağımsız bir oyun stüdyosu için **doymamış** (az rekabetli ama ilgi gören) etiket kombinasyonları hangileridir?

## Veri

- Kaynak: [SteamSpy API](https://steamspy.com/api.php), toplama tarihi 25 Ekim 2026. API hız sınırlarına uyuldu, kazıma yapılmadı.
- `all` listesinin ilk 3 sayfası (3.000 oyun) alındı; olumlu + olumsuz değerlendirme sayısına göre en popüler **2.000 oyun** seçildi.
- Her oyunda oy sayısına göre ilk 15 etiket tutuldu, 5'ten az oyunda geçen etiketler atıldı (346 etiket kaldı).
- Kişisel kullanıcı verisi yok; yalnızca oyunlara ait herkese açık bilgiler var.
- **Sınırlama:** İlk 3 sayfa en popüler oyunların tamamını kapsamıyor (ör. Dota 2 yok). Sonuçlar bu örneklem için geçerlidir.

### Ağlar

| Ağ | Düğüm | Kenar | Yoğunluk | Bileşen | En büyük bileşen |
|---|---|---|---|---|---|
| Oyun–etiket (iki parçalı) | 2346 | 29650 | 0.04285 | 1 | 2346 |
| Etiket–etiket | 346 | 22500 | 0.37698 | 1 | 346 |
| Oyun–oyun (benzerlik ≥ 0.5) | 2000 | 53315 | 0.02667 | 39 | 1958 |

Kenar tanımları: oyun–etiket kenarı etiketin aldığı oy sayısıyla ağırlıklıdır; etiket–etiket kenarı iki etiketin birlikte geçtiği oyun sayısıdır; oyun–oyun kenarı etiket oy vektörlerinin kosinüs benzerliğidir (eşik 0.5, düşük eşik her şeyi birbirine bağlayan yoğun bir ağ üretir).

### Veri sözlüğü (`data/processed/`)

| Dosya | Sütun | Anlamı |
|---|---|---|
| `edges_game_tag.csv` | appid, oyun, etiket, oy | Oyunun taşıdığı etiket ve o etiketin aldığı kullanıcı oyu |
| `edges_tag_tag.csv` | etiket_a, etiket_b, ortak_oyun, jaccard | İki etiketin birlikte geçtiği oyun sayısı ve Jaccard benzerliği |
| `edges_game_game.csv` | appid_a, appid_b, oyun_a, oyun_b, benzerlik | İki oyunun etiket profilinin kosinüs benzerliği |
| `*.graphml` | – | Aynı ağlar GraphML biçiminde (Gephi için) |
| `stats.csv` | ag, dugum, kenar, yogunluk, ... | Yukarıdaki temel ağ istatistikleri |

`data/raw/` SteamSpy'dan alınan ham JSON/JSONL dosyalarını ve `meta.json` (toplama tarihi, seçim ölçütü) dosyasını içerir.

## Yöntem ve sonuçlar (özet)

| Adım | Defter | Ne yapıldı |
|---|---|---|
| Temel ölçüler, derece dağılımı, merkeziyet, topluluklar, null model | `notebooks/01_analiz.ipynb` | Louvain ve Leiden (10 farklı tohum, NMI/ARI), 100 rastgele ağla karşılaştırma |
| Bağlantı tahmini | `notebooks/02_baglanti_tahmini.ipynb` | Adamic-Adar ve Jaccard; eski %70 oyunla tahmin, yeni %30 oyunla doğrulama |
| Poster | `notebooks/03_poster.ipynb` | A3 PDF poster |
| Etkileşimli ağ | `notebooks/04_etkilesimli_ag.ipynb` | `index.html` üretir (arama, detay paneli, topluluk filtresi, TR/EN) |

Sunumdaki ana sonuçlar: ağ kümelenme ve modülerlikte rastgele ağlardan belirgin biçimde yüksek; oyunlar 5 büyük grupta toplanıyor ve gruplar 10 farklı denemede kararlı; en olası 100 tahminin yaklaşık %43'ü yeni oyunlarda gerçekleşti.

Bu bulgular nedensellik iddiası taşımaz: ağ verisi bir kombinasyonun neden az denendiğini ya da başarılı olup olmayacağını söylemez.

## Çalıştırma

```
pip install -r requirements.txt
python fetch_data.py          # ham veriyi toplar (uzun sürer, hız sınırı nedeniyle)
python build_network_v2.py    # ağları kurar, data/processed/ içine yazar
```

Defterler Google Colab için hazırlanmıştır; `steam-network.zip` dosyasını yükleyerek çalıştırın. Rastgelelik için sabit tohumlar kullanılır.

## Dosyalar

- `fetch_data.py`, `build_network_v2.py`: veri toplama ve ağ kurma
- `notebooks/`: analiz defterleri
- `data/`: ham ve işlenmiş veri
- `index.html`: etkileşimli ağ
- `steam-network.zip`: defterlerin Colab'da kullandığı paket

## Yapay zekâ kullanımı

Bu projede **Claude (Anthropic)** kullanıldı: veri toplama ve ağ kurma script'lerinin, analiz defterlerinin ve etkileşimli ağ sayfasının ilk taslakları için. Araştırma sorusu ve kapsamı benim; script'leri ve defterleri çalıştırdım, çıktıları kontrol ettim, yorumları kendi cümlelerimle yazdım.
