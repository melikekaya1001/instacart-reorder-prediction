
## 1. Problem

Instacart kullanıcılarının bir sonraki siparişlerinde hangi ürünleri yine alacağını önceden tahmin etmek. Bu tahmin, "tekrar al" önerileri ve kampanya hedeflemesi için kullanılabilir.

Veri: [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (Kaggle).

## 2. CRISP-DM Proje Kartı

| Alan | Tanım |
|---|---|
| **İş hedefi** | Kullanıcıya bir sonraki sepetinde alması muhtemel ürünleri önermek, sepet tamamlamayı kolaylaştırmak |
| **Analiz birimi** | Sınıflandırma: (kullanıcı, ürün) çifti. Kümeleme: kullanıcı |
| **Zaman ufku** | Gözlem: kullanıcının tüm `prior` siparişleri. Tahmin: bir sonraki sipariş (`train`) |
| **Başarı metriği** | F1 ve PR-AUC (sınıflandırma), silhouette (kümeleme). Pozitif sınıf az olduğu için accuracy kullanılmadı |
| **Baseline** | "Geçmişte ürünü en az 2 kez aldıysa tekrar alır" kuralı |

**CRISP-DM aşamaları**

1. **İş anlayışı:** Tekrar alım tahmini ile kişiselleştirilmiş öneri hedeflendi.
2. **Veri anlayışı:** 6 tablo (`orders`, `order_products__prior/train`, `products`, `aisles`, `departments`); `eval_set` sütunu geçmiş/gelecek ayrımını verir.
3. **Veri hazırlama:** 10.000 kullanıcı örneklendi, SQL ile özellik ve etiket tabloları üretildi (`query.sql`).
4. **Modelleme:** Baseline kural, Lojistik Regresyon, HistGradientBoosting (sınıflandırma); K-Means (kümeleme).
5. **Değerlendirme:** Kullanıcı bazlı train/validation/test ayrımı; eşik validation setinden seçildi, sonuçlar test setinde raporlandı.
6. **Dağıtım:** Uygulanmadı; model çıktısı bir "tekrar al" öneri listesi olarak kullanılabilir.

## 3. Aynı Problemin İki Veri Madenciliği Görevi Olarak Formülasyonu

| | Görev A: Sınıflandırma | Görev B: Kümeleme |
|---|---|---|
| **Soru** | Kullanıcı bu ürünü bir sonraki siparişinde alacak mı? | Kullanıcılar alışveriş davranışına göre hangi gruplara ayrılır? |
| **Hedef** | `label` (0/1), ürün `train` siparişinde var mı | Yok (gözetimsiz) |
| **Girdi** | `times_bought`, `n_prior_orders`, `orders_since_last`, `purchase_rate`, `avg_gap_days`, `product_n_users`, `product_reorder_rate` | `n_orders`, `avg_basket_size`, `avg_gap_days`, `reorder_ratio`, `avg_hour`, `weekend_ratio` |
| **Metrik** | F1, PR-AUC | Silhouette |

## 4. Varsayımlar

- Analiz, `train` siparişi bulunan kullanıcılar arasından **sabit seed (42) ile rastgele seçilen 10.000 kullanıcı** üzerinde yapıldı (tam veri ~32 milyon satır).
- Özellikler yalnızca `prior` siparişlerinden hesaplandı; etiket yalnızca `train` siparişinden geldi (sızıntı önlemi).
- Aday ürünler, kullanıcının geçmişte en az bir kez aldığı ürünlerdir. Kullanıcının ilk kez alacağı ürünler kapsam dışıdır.
- Ürün düzeyindeki istatistikler (`product_n_users`, `product_reorder_rate`) 10.000 kullanıcılık örneklemden hesaplandı.
- `order_dow` değerleri 0 ve 1 hafta sonu kabul edildi (veri setinde gün isimleri verilmemiştir, bu yaygın bir varsayımdır).
- Eksik `days_since_prior_order` değerleri (ilk sipariş) medyan ile dolduruldu.

## 5. Sonuçlar

Tüm değerler test setindedir (`results.csv`).

### Görev A: Sınıflandırma

| Model | F1 | PR-AUC |
|---|---:|---:|
| Baseline (≥2 kez alındı) | 0.282 | 0.225 |
| Lojistik Regresyon | 0.400 | 0.366 |
| HistGradientBoosting | **0.421** | **0.394** |

- HistGradientBoosting, baseline'a göre F1'i yaklaşık **0.14 puan** (%49 göreli), PR-AUC'yi yaklaşık **0.17 puan** artırdı.
- Lojistik regresyon basit olmasına rağmen baseline'ı belirgin biçimde geçti; boosting modeli doğrusal olmayan ilişkiler sayesinde bir miktar daha iyi.
- Eşikler validation setinden seçildi (logreg 0.637, hist_gb 0.205). Logreg `class_weight="balanced"` kullandığı için olasılıkları yukarı kaymış, bu yüzden eşiği yüksek çıktı.

### Görev B: Kümeleme

| k | Silhouette |
|---|---:|
| 3 | 0.176 |
| 4 | 0.162 |
| **5** | **0.177** |
| 6 | 0.175 |

- En yüksek silhouette k=5'te, ancak k=3, 5 ve 6 arasındaki fark çok küçük. Değerler düşük (~0.18), yani kümeler birbirinden **net ayrılmıyor**; kullanıcı davranışı kesin gruplardan çok sürekli bir yelpaze gibi.
- Bu nedenle segmentler "kesin sınıflar" olarak değil, **pazarlama için yaklaşık profiller** olarak yorumlandı.

**Segment özeti (fig2'ye bakarak doldur):**

- Küme 0: ...
- Küme 1: ...
- Küme 2: ...
- Küme 3: ...
- Küme 4: ...

## 6. Görseller ve Yorumlar

**`figures/fig1_reorder_by_times_bought.png`** – Bir ürün geçmişte ne kadar çok alındıysa bir sonraki siparişte tekrar alınma olasılığı o kadar artıyor. Bu, `times_bought` özelliğinin güçlü bir sinyal olduğunu ve baseline kuralının neden mantıklı bir başlangıç olduğunu gösteriyor.

**`figures/fig2_cluster_profiles.png`** – Her kümenin, özelliklerin genel ortalamasından kaç standart sapma saptığını gösterir. Sipariş sıklığı, sepet büyüklüğü ve tekrar alım oranı bakımından birbirinden ayrışan kullanıcı tipleri görülür (yukarıdaki segment özetine bakınız).

**`figures/fig3_f1_comparison.png`** – Test setinde baseline ve iki modelin F1 karşılaştırması. Her iki model de baseline'ı geçiyor, en iyisi HistGradientBoosting.

## 7. Nasıl Çalıştırılır


Veri bu depoya dahil değildir (dosyalar çok büyük ve veri Instacart'a aittir).
Kaggle'dan indirin: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis

Gerekli dosyaları `data/` klasörüne koyun:

- `orders.csv`
- `order_products__prior.csv`
- `order_products__train.csv`
- `products.csv`
- `aisles.csv`
- `departments.csv`

Beklenen yapı:

    data/
    ├── orders.csv
    ├── order_products__prior.csv
    ├── order_products__train.csv
    ├── products.csv
    ├── aisles.csv
    └── departments.csv

```
pip install -r requirements.txt
python prepare_db.py     # veriyi örnekleyip data/db.sqlite oluşturur
python solution.py       # results.csv ve figures/ üretir
```

Tüm rastgelelik `seed=42` ile sabitlenmiştir; aynı veriyle aynı sonuçlar elde edilir.

## 8. Dosyalar

| Dosya | İçerik |
|---|---|
| `prepare_db.py` | Veriyi örnekleyip SQLite'a yükler |
| `query.sql` | Özellik/etiket ve kullanıcı özet sorguları |
| `solution.py` | Modelleme, değerlendirme, görseller |
| `results.csv` | Deney ve metrik özeti |
| `figures/` | Açıklamalı görseller |
| `reflection.md` | Riskler ve alınan önlemler |
