# Qiymətgəz: supermarket qiymət müqayisəsi

Bot marketlərin **bütün kateqoriyalarını** çəkir (ad, qiymət, köhnə qiymət, endirim, qramaj, şəkil, kod/barkod),
sayt isə onları kartlarda göstərir, marketlər arası müqayisə və qiymət tarixçəsi verir.

```
GitHub Actions (hər gün 07:00)  →  python -m scraper.run  →  data/products.json  →  git push  →  Render yenilənir
```

## Nə çəkilir

| Market | Kateqoriyalar | Necə tapılır |
|---|---|---|
| **Bazarstore** | 14 üst + ~330 alt kateqoriya (təxminən 12 000 məhsul) | Ana səhifənin menyusundan **avtomatik** kəşf olunur |
| **Araz** | siz yazdığınız siyahı | Araz menyusu JS ilə yüklənir, siyahını bir dəfə brauzerdən toplayırsınız (aşağıda) |

**Bazarstore üçün çəkmə sırası:** əvvəl alt kateqoriyalar (məhsul ən dəqiq kateqoriyasını alsın), sonra 14 üst kateqoriya tam şəkildə
(birbaşa üst kateqoriyada olan məhsulları tutmaq üçün). Təxminən 1 000-1 500 sorğu, 30-60 dəqiqə.

### Araz kateqoriyalarını necə toplamaq (1 dəqiqə)
1. arazmarket.az/az saytını brauzerdə açın, **"Məhsullar"** menyusunu açın ki, kateqoriyalar görünsün.
2. F12 → **Console**, bunu yapışdırıb Enter basın (siyahı buferə kopyalanır):
   ```js
   copy([...new Set([...document.querySelectorAll('a[href*="/categories/"]')].map(a => a.href))].join('\n'))
   ```
3. `config/categories_araz.txt` faylına yapışdırın (hər sətirdə bir link). Commit + push.

Menyu bütün alt kateqoriyaları göstərmirsə, əsas kateqoriyalara da girib 2-ci addımı təkrarlayın.
Yoxlamaq üçün: `python -m scraper.discover araz`.

**Araz üçün tamlıq yoxlaması:** bot hər kateqoriyada saytın yazdığı "N məhsul" ilə gördüyünü müqayisə edir.
`⚠ sayt 300 məhsul yazır, bot 24 gördü` çıxarsa, səhifələmə parametri işləmir: `python -m scraper.debug araz /az/categories/<slug>-<id>` çalışdırıb çıxışı göndərin.

## Lokal işə salmaq
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scraper.run --market bazarstore --max-minutes 10    # qısa sınaq
python -m scraper.run                                         # hamısı
python app.py                                                 # http://localhost:5000
python -m pytest -q                                           # testlər
```

## GitHub + Render
1. Repo-ya push edin. **Settings → Actions → General → Workflow permissions → Read and write.**
2. **Actions → scrape → Run workflow** ilə ilk dəfə əl ilə işə salın (`max_minutes` = 120 qalsın).
   Araz və Bazarstore ayrı addımlardır və hər biri bitən kimi commit olunur: biri bloklansa, digərinin datası itmir.
3. render.com → **New → Blueprint** → repo. Bot data commit edəndə Render saytı avtomatik yeniləyir.

## Böyük data üçün dizayn qərarları
- **Müvəqqəti xətaya davamlılıq:** məhsul 7 gün görünməsə silinir. Bir günlük blok/xəta bütün datanı silmir. Boş nəticə heç vaxt mövcud datanı əzmir.
- **Blok olanda dayanır:** 403/429 alanda bot təkrar-təkrar sorğu göndərmir, dərhal dayanır və o ana qədərki nəticəni yazır.
- **Vaxt limiti:** `--max-minutes` bitəndə də çəkilənlər yazılır (qismən).
- **Sürətli qruplaşdırma:** bot hər məhsula qrup açarı (`g`) yazır, sayt başlayanda hesablamır. 20 000 məhsul 0.5 saniyədə qruplaşır
  (prefix-filter: heç bir uyğunluğu qaçırmır, brute-force ilə testlə təsdiqlənib).
- **Saxlama:** `data/products.json`-da hər məhsul ayrı sətirdə, id üzrə sıralı (git fərqləri kiçik olsun). 12 000-17 000 məhsul təxminən 8-10 MB.
  GitHub-un 100 MB limiti çox uzaqdır, amma illər ərzində repo tarixçəsi böyüyəcək. Lazım olsa köhnə tarixçəni təmizləmək olar.
- **Nəzakətli çəkmə:** sorğular arasında 0.8-1.6 san fasilə, `robots.txt` qaydalarına riayət, gündə bir dəfə.

## Marketlər, profillər, blok
- `scraper/araz.py`, `scraper/bazarstore.py`. Yeni market: `scraper/_template.py`-ı kopyalayın, `scraper/markets.py`-a əlavə edin.
- **Bazarstore Cloudflare "bot" filtri:** adında "bot" olan User-Agent 403 alır (diaqnostika ilə təsdiqlənib). Botun profilləri:
  `bot` (Araz), `open` (Bazarstore: brauzer formatı + `Qiymetgez/1.0 (+repo)`, "bot" sözü yoxdur), `browser` (adi Chrome, yalnız əl ilə).
  Dəyişmək: GitHub → Settings → Secrets and variables → Actions → **Variables** → `SCRAPER_PROFILE`.
- 403 alırsınızsa: `python -m scraper.diagnose`. Hamısı bloklanıbsa proxy/captcha keçməyin, sayt ilə əlaqə saxlayın.
- Saytların istifadə şərtlərini oxuyun, mümkünsə marketlərlə razılaşın. Şəkillər marketin serverindən göstərilir (kopyalanmır).

## Bilməli olduğunuz məhdudiyyətlər
- Real barkod (EAN) yalnız marketin saytı göstərirsə toplanır. Araz və Bazarstore siyahı səhifələrində göstərmir, ona görə müqayisə **ad + qramaj** üzrədir.
  Fərqli yazılış (məs. "Azərçay" / "Azercay Buket") yaxşı tutulur, amma tamamilə fərqli adlar tutulmaz.
- Qramaj addan çıxarılır. Adında qramaj olmayan məhsullar yalnız çox sərt ad uyğunluğu ilə qruplaşır (səhv birləşmənin qarşısı üçün).
- Marketlərin kateqoriya adları fərqlidir, filtrdə hər marketin öz kateqoriyaları ayrıca qrupda göstərilir.
