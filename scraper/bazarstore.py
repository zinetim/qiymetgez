"""Bazarstore (bazarstore.az) botu. Sayt nopCommerce üzərindədir, siyahı server tərəfdə HTML-də gəlir.

Xüsusiyyətlər:
  * qiymət vergüllüdür: "5,99 ₼"
  * endirimdə köhnə qiymət ƏVVƏL, yeni qiymət SONRA gəlir ("2,40 ₼ 1,89 ₼"); kiçik olanı yeni sayırıq
  * şəkillər lazy-load: real ünvan data-lazyloadsrc / data-src kimi atributlarda olur
  * səhifələmə: ?pagenumber=2, səhifə ölçüsü: ?pagesize=20
"""
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper

PRICE = re.compile(r"(\d{1,3}(?:[ \u00a0]\d{3})*[.,]\d{2})(?!\d)")
# "2 lb(s) üçün 2,45 ₼ təşkil edir" (1 kq/vahid qiyməti) - əsas qiymət deyil, atırıq
TIER = re.compile(r"\d+(?:[.,]\d+)?\s*[A-Za-z]+\(s\)\s*üçün\s*[\d.,\s]+₼?\s*təşkil edir", re.I)
IMG_ATTRS = ("data-lazyloadsrc", "data-original", "data-src", "data-lazy-src", "src")
GTIN = re.compile(r"(?:Barkod|Barcode|GTIN|EAN)\D{0,12}(\d{8,14})", re.I)


def _price(txt):
    return float(txt.replace("\u00a0", "").replace(" ", "").replace(",", "."))


class BazarstoreScraper(BaseScraper):
    market = "bazarstore"
    market_name = "Bazarstore"
    base_url = "https://bazarstore.az"
    page_param = "pagenumber"
    extra_params = {"pagesize": "20"}
    # Üst kateqoriya səhifələri alt kateqoriyaların məhsullarını da göstərir (et-toyuq-baliq: 59 səhifə).
    # Yeni kateqoriya: (ad, yol) əlavə edin. Yol saytdakı kateqoriya linkinin sonudur.
    # Diqqət: hər kateqoriya yüzlərlə məhsul = yüzlərlə sorğu. Əvvəl bir neçəsi ilə başlayın.
    categories = [
        ("Ət, Toyuq, Balıq", "/et-toyuq-baliq"),
        ("Süd, Səhər yeməyi", "/sud-seher-yemeyi"),
        ("Təməl qida", "/temel-qida"),
        ("İçkilər", "/ickiler"),
    ]
    max_pages = 80

    def _image(self, card):
        img = (card.select_one(".picture img") or card.find("img"))
        if not img:
            return None
        for attr in IMG_ATTRS:
            v = (img.get(attr) or "").strip()
            if v and not v.startswith("data:"):
                return urljoin(self.base_url, v)
        return None

    def parse_listing(self, html, category):
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-productid].product-item") or soup.select(".product-item")
        if not cards:  # tema fərqli sinif işlədirsə: başlığı olan və qiyməti içində olan ən yaxın blok
            for t in soup.select(".product-title"):
                node = t
                for _ in range(5):
                    node = node.parent
                    if node is None:
                        break
                    if PRICE.search(node.get_text(" ", strip=True)):
                        cards.append(node)
                        break
        out = []
        for c in cards:
            a = c.select_one(".product-title a, h2 a, h3 a")
            if not a or not a.get("href"):
                continue
            box = c.select_one(".prices") or c
            text = TIER.sub(" ", box.get_text(" ", strip=True))
            nums = [_price(x) for x in PRICE.findall(text)][:2]
            if not nums:
                continue
            img = self._image(c)
            out.append({
                "name": a.get_text(" ", strip=True),
                "url": urljoin(self.base_url, a["href"]),
                "image": img,
                "image_thumb": img,
                "price": min(nums),
                "old_price": max(nums) if len(nums) > 1 and max(nums) > min(nums) else None,
                "category": category,
                "code": c.get("data-productid"),
            })
        return out

    def parse_detail(self, html):
        """Məhsul səhifəsindən barkod: əvvəl JSON-LD (gtin), sonra mətn."""
        soup = BeautifulSoup(html, "html.parser")
        gtin = None
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or "")
            except (ValueError, TypeError):
                continue
            for node in (data if isinstance(data, list) else [data]):
                if isinstance(node, dict):
                    for k in ("gtin13", "gtin12", "gtin8", "gtin14", "gtin"):
                        v = str(node.get(k) or "")
                        if v.isdigit() and 8 <= len(v) <= 14:
                            gtin = v
                            break
            if gtin:
                break
        if not gtin:
            m = GTIN.search(soup.get_text(" ", strip=True))
            gtin = m.group(1) if m else None
        return {"barcode": gtin}
