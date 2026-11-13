"""Yeni market şablonu. Kopyalayın: scraper/oba.py, sonra scraper/markets.py-a əlavə edin.
1) Kateqoriya səhifəsini açın, F12 → Elements, məhsul kartına baxın.
2) parse_listing hər kart üçün dict qaytarsın: name, url, image, price, old_price, discount, category, code, barcode.
3) Kateqoriya menyusu HTML-dədirsə is_category_href + discover_pages yazın; deyilsə config/categories_<market>.txt istifadə edin.
Qalanını (qramaj, 1 kq qiyməti, tarixçə, səhifələmə, robots.txt, müqayisə) sistem özü edir."""
from bs4 import BeautifulSoup

from .base import BaseScraper


class TemplateScraper(BaseScraper):
    market = "oba"
    market_name = "Oba Market"
    base_url = "https://oba.az"
    categories = [("Süd məhsulları", "/kateqoriya-yolu")]

    def parse_listing(self, html, category):
        out = []
        for card in BeautifulSoup(html, "html.parser").select(".product-card"):   # <- real selektor
            out.append({
                "name": card.select_one(".title").get_text(strip=True),
                "url": self.base_url + card.select_one("a")["href"],
                "image": card.select_one("img")["src"],
                "price": float(card.select_one(".price").get_text(strip=True).replace("₼", "").replace(",", ".")),
                "category": category,
            })
        return out
