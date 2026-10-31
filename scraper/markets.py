"""Aktiv market botlarının siyahısı. Yeni market: scraper/<ad>.py yazıb bura əlavə edin."""
from .araz import ArazScraper

MARKETS = {
    "araz": ArazScraper,
    # "bravo": BravoScraper,
}
