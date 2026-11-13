"""Araz Supermarket (arazmarket.az). Next.js saytıdır, məhsul siyahısı HTML-də hazır gəlir.
Kateqoriya menyusu isə JS ilə yüklənir, buna görə kateqoriyalar config/categories_araz.txt faylından
(və ya sitemap-dan) gəlir. README-də brauzer konsolu ilə siyahını necə toplamaq göstərilib."""
import re
from urllib.parse import parse_qs, quote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper

PRICE_LINK = re.compile(r"^\d+[.,]\d{2}(\s+\d+[.,]\d{2})?$")
NUM = re.compile(r"\d+[.,]\d{2}")
EAN = re.compile(r"(?:Barkod|Barcode|EAN)\D{0,12}(\d{8,14})", re.I)
CODE = re.compile(r"Məhsul kodu\s*:?\s*(\d+)", re.I)
CAT_PATH = re.compile(r"^/az/categories/[^/?#]+-\d+/?$")
COUNT = re.compile(r"(\d[\d.,]*)\s*məhsul", re.I)


def _f(x):
    return float(x.replace(",", "."))


class ArazScraper(BaseScraper):
    market = "araz"
    market_name = "Araz Supermarket"
    base_url = "https://www.arazmarket.az"
    categories = [("Təzə ağ ətlər", "/az/categories/teze-ag-etler-66")]
    discover_pages = ["/az", "/az/categories"]
    use_sitemap = True

    def is_category_href(self, href):
        u = urlparse(urljoin(self.base_url, href))
        return u.netloc.replace("www.", "") == "arazmarket.az" and bool(CAT_PATH.match(u.path)) and not u.query

    def expected_count(self, html):
        m = COUNT.search(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        return int(re.sub(r"\D", "", m.group(1))) if m else None

    def _card(self, a, href):
        """Məhsulun öz kartı: yalnız bu məhsula aid linkləri saxlayan ən böyük valideyn."""
        best, node = None, a
        for _ in range(7):
            node = node.parent
            if node is None:
                break
            hrefs = {urljoin(self.base_url, x["href"]) for x in node.select('a[href*="/products/"]')}
            if len(hrefs) > 1:
                break
            if href in hrefs:
                best = node
        return best

    @staticmethod
    def _orig_image(src):
        q = parse_qs(urlparse(src).query)
        return q["url"][0] if "url" in q else src

    def parse_listing(self, html, category):
        soup = BeautifulSoup(html, "html.parser")
        out, done = [], set()
        for a in soup.select('a[href*="/products/"]'):
            href = urljoin(self.base_url, a["href"])
            if href in done:
                continue
            card = self._card(a, href)
            if card is None:
                continue
            done.add(href)
            links = [x for x in card.select("a[href]") if urljoin(self.base_url, x["href"]) == href]
            price_txt = next((x.get_text(" ", strip=True) for x in links
                              if PRICE_LINK.match(x.get_text(" ", strip=True))), "")
            nums = [_f(n) for n in NUM.findall(price_txt)]
            if not nums:
                continue
            img = next((i for i in card.find_all("img") if "products" in (i.get("src") or "")), None)
            orig = self._orig_image(img["src"]) if img else None
            name = (img.get("title") or img.get("alt")) if img else None
            if not name:
                name = next((x.get_text(" ", strip=True) for x in links
                             if x.get_text(strip=True) and not x.find("strong") and not x.find("img")
                             and not PRICE_LINK.match(x.get_text(" ", strip=True))), None)
            if not name:
                continue
            cat_el = next((x for x in links if x.find(["strong", "b"])), None)
            text = card.get_text(" ", strip=True)
            m = re.search(r"(\d{1,2})\s*%", text)
            out.append({
                "name": name,
                "url": href,
                "image": orig,
                "image_thumb": f"{self.base_url}/_next/image?url={quote(orig, safe='')}&w=384&q=75" if orig else None,
                # iki qiymət varsa: kiçiyi yeni, böyüyü köhnə (Araz-da yeni əvvəl gəlir)
                "price": min(nums[:2]),
                "old_price": max(nums[:2]) if len(nums) > 1 and max(nums[:2]) > min(nums[:2]) else None,
                "discount": int(m.group(1)) if m else None,
                "category": cat_el.get_text(" ", strip=True) if cat_el else category,
                "own_brand": "Araz brendi" in text,
                "code": (re.search(r"/(\d{6,})\.\w+$", orig or "") or [None, None])[1],
            })
        return out

    def parse_detail(self, html):
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        code, ean = CODE.search(text), EAN.search(text)
        return {"code": code.group(1) if code else None, "barcode": ean.group(1) if ean else None}
