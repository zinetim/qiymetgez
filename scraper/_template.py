"""İkinci market üçün şablon. Kopyalayın: scraper/bravo.py, sonra scraper/markets.py-a əlavə edin.

1) Brauzerdə kateqoriya səhifəsini açın, F12 → Elements, bir məhsul kartına baxın.
2) parse_listing-də hər kart üçün aşağıdakı açarlarla dict qaytarın:
   name, url, image, price, old_price (varsa), discount (varsa), category, own_brand, barcode (varsa)
3) Qalanını (qramaj, 1 kq qiyməti, tarixçə, müqayisə qruplaşdırması) sistem özü edir.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper


class TemplateScraper(BaseScraper):
    market = "bravo"
    market_name = "Bravo Supermarket"
    base_url = "https://bravo.az"
    categories = [("Süd məhsulları", "/kateqoriya-yolu")]

    def parse_listing(self, html, category):
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for card in soup.select(".product-card"):           # <- real selektor ilə əvəz edin
            out.append({
                "name": card.select_one(".title").get_text(strip=True),
                "url": self.base_url + card.select_one("a")["href"],
                "image": card.select_one("img")["src"],
                "price": float(card.select_one(".price").get_text(strip=True).replace("₼", "").replace(",", ".")),
                "category": category,
            })
        return out
