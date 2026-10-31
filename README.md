# Qiymətgəz: supermarket qiymət müqayisəsi

Bot marketlərin saytından **ad, qiymət, köhnə qiymət, endirim, qramaj, kod/barkod, şəkil** toplayır,
sayt isə onları kartlarda göstərir, qiymət tarixçəsi və marketlər arası müqayisə verir.

```
GitHub Actions (hər gün)  →  python -m scraper.run  →  data/products.json  →  git push
                                                                                   ↓
                                                      Render avtomatik yenidən yayımlayır (Flask + gunicorn)
```

Botu Render-də yox, GitHub Actions-da işlədirik, çünki Render-in pulsuz planında fayl sistemi müvəqqətidir
və bəzi saytlar server IP-lərini bloklayır. Data repoda saxlanır, hər yeniləmə git tarixçəsində görünür.

## 1. Lokal işə salmaq

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scraper.run --details      # botu işə sal (detallı rejim: hər məhsulun öz səhifəsi də oxunur)
python app.py                        # http://localhost:5000
```

`data/products.json` içində artıq arazmarket.az-dan 22 və bazarstore.az-dan 12 məhsul var, ona görə sayt bot işləmədən də açılır.

## 2. GitHub

1. Yeni repo yaradın (məs. `qiymetgez`), bu qovluğu push edin.
2. **Settings → Actions → General → Workflow permissions → Read and write permissions** seçin.
3. **Actions → scrape → Run workflow** ilə ilk dəfə əl ilə işə salın. Yaşıl olsa, data yenilənib.
4. `scraper/base.py`-dakı `YOUR_USER` yerinə GitHub adınızı yazın (bot saytlara özünü düzgün təqdim etsin).

## 3. Render

1. render.com → **New → Blueprint** → repo seçin. `render.yaml` hər şeyi özü qurur.
2. Və ya əl ilə: **Web Service**, Build `pip install -r requirements.txt`, Start `gunicorn app:app`.
3. Bot hər dəfə `data/products.json`-u commit edəndə Render saytı avtomatik yeniləyir.

Pulsuz planda sayt 15 dəqiqə istifadəsiz qalanda yatır, ilk açılış 30-50 saniyə çəkə bilər.

## 4. Yeni kateqoriya və ya market

- **Kateqoriya:** `scraper/araz.py` içində `categories` siyahısına sətir əlavə edin.
- **Market:** `scraper/_template.py`-ı kopyalayın, selektorları yazın, `scraper/markets.py`-a əlavə edin.
  Eyni məhsul avtomatik qruplaşır (barkod eynidirsə, yaxud ad + qramaj ≥ 75% uyğundursa) və məhsul səhifəsində müqayisə cədvəli görünür.

## Bilmək lazım olanlar

- **Barkod:** arazmarket.az saytında real barkod (EAN) göstərilmir, yalnız daxili "Məhsul kodu" var.
  Bot onu `code` kimi saxlayır. Bot səhifədə `Barkod/EAN` yazısı görsə, `barcode`-a yazır və müqayisə dəqiqləşir.
- **Qramaj:** ayrıca sahə yoxdur, addan çıxarılır (`1kq`, `500 qr`, `0.5 L`). Adında rəqəm olmayan "kq" malları çəkili sayılır (1 kq).
- **Şəkillər** marketin serverindən göstərilir (kopyalanmır). Açıq yayıma keçəndə marketlərdən icazə almaq və ya şəkilləri
  öz yaddaşınıza yükləmək daha təhlükəsizdir. Eyni şey qiymət məlumatlarının istifadəsinə də aiddir: saytın istifadə şərtlərinə və `robots.txt`-ə baxın.
- **Sayt dəyişsə** (Araz dizaynı yeniləyəndə) yalnız `scraper/araz.py` düzəlir. Testlər: `python -m pytest`.
- **JS ilə yüklənən saytlar** üçün `requests` kifayət etməyə bilər, onda Playwright-a keçmək lazım olur.

## Marketlər

| Market | Fayl | Platforma | Səhifələmə | Qeyd |
|---|---|---|---|---|
| Araz Supermarket | `scraper/araz.py` | Next.js | `?page=N` | qiymət `5.99`, köhnə qiymət ikinci gəlir |
| Bazarstore | `scraper/bazarstore.py` | nopCommerce | `?pagenumber=N&pagesize=20` | qiymət `5,99 ₼`, endirimdə **köhnə qiymət əvvəl** gəlir, şəkillər lazy-load |

- Bazarstore kateqoriyaları `scraper/bazarstore.py` içindəki `categories` siyahısındadır (hazırda 20 ədəd). Əlavə etmək üçün saytdakı kateqoriya linkinin sonunu yazın (məs. `("Pendir", "/pendir")`).
- Yalnız bir marketi işlətmək: `python -m scraper.run --market bazarstore`
- Hər marketdə eyni kateqoriyaları izləyin, yoxsa müqayisə üçün ortaq məhsul tapılmaz (məs. Araz-a da süd, çay, yağ kateqoriyaları əlavə edin).
- Marketlər arası eyni məhsul avtomatik tapılır: ad (hərf/ə-ö fərqi nəzərə alınmadan) + qramaj ≥ 75% uyğundursa, yaxud barkod eynidirsə.
- Bot gündə bir dəfə işləyir (03:00 UTC). Saytları yormamaq üçün sorğular arasında 0.8-1.6 san fasilə var.

## Problem olsa: botu yoxlamaq

Sayt market zolağında marketin adı həmişə görünür. Yanında `0` və ya "soon" işarəsi varsa, bot hələ o marketin datasını yazmayıb. Səbəbi tapmaq üçün (Codespaces və ya lokal):

```bash
python -m scraper.debug bazarstore /teze-toyuq
```

Bu əmr bir səhifəni çəkir və neçə məhsul tapıldığını, qiymət, köhnə qiymət və şəkli göstərir. `Tapılan məhsul: 0` çıxarsa:
1. `SƏHİFƏ ALINMADI` yazılıbsa, sayt sorğunu bloklayıb (403/429). Fasiləni artırın (`delay` in `scraper/base.py`).
2. HTML alınıb, amma 0 məhsuldursa, `/tmp/debug_bazarstore.html` faylına baxın: `grep -c product-item /tmp/debug_bazarstore.html`. Selektorlar dəyişibsə, `scraper/bazarstore.py` içindəki `parse_listing` düzəldilir.

GitHub Actions-da: **Actions → scrape → son işləmə → "Run scraper" addımı** log-unda hər marketin neçə məhsul yazdığı görünür.

## Data faylı haqqında

`data/products.json` botun yazdığı faylıdır. Zip-dəki versiya yalnız başlanğıc datadır (Araz 22 + Bazarstore 12 məhsul). Bot işlədikcə onu real data ilə əvəz edir. Bot yalnız öz marketinin məhsullarını yeniləyir, digər marketə toxunmur.
