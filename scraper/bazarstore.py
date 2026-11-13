"""Bazarstore (bazarstore.az), nopCommerce.

* qiymət vergüllüdür "5,99 ₼"; endirimdə köhnə qiymət ƏVVƏL gəlir ("2,40 ₼ 1,89 ₼") → kiçik olan yenidir
* şəkillər lazy-load: real ünvan data-lazyloadsrc / data-src atributlarındadır
* səhifələmə ?pagenumber=N, səhifə ölçüsü ?pagesize=20
* kateqoriya ağacı ana səhifənin menyusundadır (14 üst + ~330 alt kateqoriya)

Çəkmə sırası: ƏVVƏL alt kateqoriyalar (məhsul ən dəqiq kateqoriyasını alsın), SONRA 14 üst kateqoriya tam şəkildə
(alt kateqoriyada olmayıb birbaşa üstdə olan məhsulları da tutmaq üçün). Üst kateqoriya səhifəsi alt kateqoriyaların
məhsullarını da göstərir (et-toyuq-baliq: 59 səhifə ilə yoxlanılıb)."""
import json
import re
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper, clean_name, norm_path, prettify

PRICE = re.compile(r"(\d{1,3}(?:[ \u00a0]\d{3})*[.,]\d{2})(?!\d)")
TIER = re.compile(r"\d+(?:[.,]\d+)?\s*[A-Za-z]+\(s\)\s*üçün\s*[\d.,\s]+₼?\s*təşkil edir", re.I)
IMG_ATTRS = ("data-lazyloadsrc", "data-original", "data-src", "data-lazy-src", "src")
GTIN = re.compile(r"(?:Barkod|Barcode|GTIN|EAN)\D{0,12}(\d{8,14})", re.I)

# kateqoriya olmayan tək-seqmentli səhifələr və məhsulları təkrarlayan "sanal" bölmələr
NOT_CATEGORY = {
    "customer", "register", "login", "wishlist", "cart", "blog", "newproducts", "faq", "superkart",
    "haqqimizda", "karyera", "stores", "iso-sertifikatlar", "recentlyviewedproducts", "butun-mehsullar",
    "manufacturer", "endirimli-məhsullar", "endirimli-mehsullar", "super-maqazin", "search", "contactus",
}
TOP_LEVEL = [
    ("Meyvə, tərəvəz", "/meyve-terevez"), ("Ət, Toyuq, Balıq", "/et-toyuq-baliq"),
    ("Təməl qida", "/temel-qida"), ("Süd, Səhər yeməyi", "/sud-seher-yemeyi"),
    ("İçkilər", "/ickiler"), ("Atışdırmalıq", "/atisdirmaliq"),
    ("Tort, Bişmələr, Çörək", "/tort-bismeler-corek"), ("Baxım, kosmetik, sağlamlıq", "/baxim-kosmetik-sagliq"),
    ("Ev və bağ məhsulları", "/ev-ve-bag-mehsullari"), ("Petshop", "/petshop"),
    ("Elektronika", "/elektronika"), ("Dəftərxana ləvazimatları", "/defterxana-levazimatlari"),
    ("Uşaq dünyası", "/usaq-dunyasi"), ("Deterjan, təmizlik", "/deterjan-temizlik"),
]


def _price(txt):
    return float(txt.replace("\u00a0", "").replace(" ", "").replace(",", "."))


class BazarstoreScraper(BaseScraper):
    market = "bazarstore"
    market_name = "Bazarstore"
    base_url = "https://bazarstore.az"
    profile = "open"   # Cloudflare "bot" adlı UA-nı süzür (diaqnostika ilə təsdiqlənib)
    page_param = "pagenumber"
    extra_params = {"pagesize": "20"}
    categories = TOP_LEVEL
    discover_pages = ["/"]

    # ---- kateqoriya kəşfi ----
    def is_category_href(self, href):
        u = urlparse(urljoin(self.base_url, href))
        if u.netloc.replace("www.", "") != "bazarstore.az" or u.query or u.fragment:
            return False
        segs = [s for s in u.path.split("/") if s]
        return len(segs) == 1 and unquote(segs[0]).lower() not in NOT_CATEGORY

    def category_links(self, html):
        """Menyudakı bütün kateqoriya linkləri, DOM sırası ilə. 'Brendlər' başlayanda menyu bitir."""
        out, seen = [], set()
        for a in BeautifulSoup(html, "html.parser").select("a[href]"):
            if "/manufacturer/" in a["href"]:
                break
            text = clean_name(a.get_text(" ", strip=True))
            if not self.is_category_href(a["href"]) or not text or text.startswith("Hamısına bax"):
                continue
            path = urlparse(urljoin(self.base_url, a["href"])).path
            k = norm_path(path)
            if k not in seen:
                seen.add(k)
                out.append((text, path))
        return out

    def get_categories(self, discover=True):
        """[əl ilə] + [alt kateqoriyalar: dərindən üstə doğru (tərs DOM sırası)] + [14 üst kateqoriya, TAM rejimdə]."""
        seen, out = set(), []

        def add(n, p, full=False):
            k = norm_path(p)
            if k not in seen and k != "/":
                seen.add(k)
                out.append((n, p, full))

        for n, p in self.manual_categories():
            add(n, p)
        tops = {norm_path(p) for _, p in TOP_LEVEL}
        disc = self.discover() if discover else []
        for n, p in reversed(disc):          # DOM-da uşaqlar valideyndən sonra gəlir → tərsinə: uşaq əvvəl
            if norm_path(p) not in tops:
                add(n, p)
        for n, p in TOP_LEVEL:
            add(n, p, full=True)
        return out

    # ---- siyahı ----
    def _image(self, card):
        img = card.select_one(".picture img") or card.find("img")
        if not img:
            return None
        for attr in IMG_ATTRS:
            v = (img.get(attr) or "").strip()
            if v and not v.startswith("data:"):
                return urljoin(self.base_url, v)
        return None

    def parse_listing(self, html, category):
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.product-item[data-productid]") or soup.select("div.product-item")
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
