from core.matcher import annotate
from core.textutil import parse_weight, name_tokens
from scraper.araz import ArazScraper
from tests.fixture import listing_html, ROWS


def test_weight():
    assert parse_weight("Tac Şirvan Təzə Toyuq Açıq 1kq")[:2] == (1.0, "kg")
    assert parse_weight("Süd 500 qr")[:2] == (0.5, "kg")
    assert parse_weight("Süd 0.5 L")[:2] == (0.5, "l")
    assert parse_weight("Pepsi 330ml")[:2] == (0.33, "l")
    assert parse_weight("SOBA HİCAZ CİYƏR TEZE AÇIQ KQ")[:2] == (1.0, "kg")
    assert parse_weight("Mercan Təzə Ciyər Açıqkq")[:2] == (1.0, "kg")
    assert parse_weight("Tac Gilezi Təzə Toyuq Açıq")[0] is None


def test_listing_parser():
    items = ArazScraper().parse_listing(listing_html(), "Təzə ağ ətlər")
    assert len(items) == len(ROWS) == 22
    first = items[0]
    assert first["name"] == "Mərcan Təzə Pətənək Açıq kq"
    assert (first["price"], first["old_price"], first["discount"]) == (6.39, 6.70, 5)
    assert first["category"] == "Təzə toyuq içalat"
    assert first["image"].endswith("/1000024346.png") and first["code"] == "1000024346"
    assert items[1]["own_brand"] is True and items[1]["discount"] == 24
    no_old = [i for i in items if i["name"].startswith("Bərdə Təzə File")][0]
    assert no_old["old_price"] is None and no_old["price"] == 9.85


def test_matching_across_markets():
    base = dict(category="x", price=5.0, weight_value=1.0, weight_unit="kg")
    a = {**base, "id": "a1", "market": "araz", "name": "Tac Şirvan Təzə Toyuq Açıq 1kq"}
    b = {**base, "id": "b1", "market": "bravo", "name": "Tac Sirvan Toyuq Teze 1 kq", "price": 5.5}
    c = {**base, "id": "c1", "market": "bravo", "name": "Mercan File 1kq"}
    groups = annotate([a, b, c])
    assert a["compare_count"] == 2 and a["is_cheapest"] and not b["is_cheapest"]
    assert c["compare_count"] == 1
    assert len(groups) == 2
