"""Aktiv market botları. Yeni market: scraper/<ad>.py yazıb bura əlavə edin."""
from .araz import ArazScraper
from .bazarstore import BazarstoreScraper

MARKETS = {
    "araz": ArazScraper,
    "bazarstore": BazarstoreScraper,
}
