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


def test_weight_gram_q():
    assert parse_weight("GULUM ŞİRİN QARĞIDALI 425 Q")[:2] == (0.425, "kg")
    assert parse_weight("Çips Lays Сыр, 140 q")[:2] == (0.14, "kg")
    assert parse_weight("Yumurta 10 lu")[0] is None


def test_bazarstore_parser():
    from scraper.bazarstore import BazarstoreScraper
    from tests.fixture_bazar import listing_html as bz, ROWS as BR
    s = BazarstoreScraper()
    items = s.parse_listing(bz(), "Təzə toyuq")
    assert len(items) == len(BR) == 12
    by = {i["code"]: i for i in items}
    assert by["101"]["price"] == 5.99 and by["101"]["old_price"] is None
    assert by["101"]["image"].endswith("00101_415.jpeg")          # lazy-load atributundan
    assert (by["111"]["price"], by["111"]["old_price"]) == (1.89, 2.40)  # köhnə qiymət əvvəl
    assert by["112"]["price"] == 1.69 and by["112"]["old_price"] is None  # vahid qiyməti mətni atıldı
    assert s.page_url("/teze-toyuq", 1).endswith("/teze-toyuq?pagesize=20")
    assert s.page_url("/teze-toyuq", 3).endswith("?pagesize=20&pagenumber=3")
    f = s.finish(by["106"])
    assert f["id"] == "bazarstore-106" and f["weight_value"] == 1.0


def test_cross_market_real_names():
    """Real Araz və Bazarstore adları avtomatik eyni qrupa düşməlidir."""
    from scraper.araz import ArazScraper
    from scraper.bazarstore import BazarstoreScraper
    from tests.fixture import listing_html as az
    from tests.fixture_bazar import listing_html as bz
    a, b = ArazScraper(), BazarstoreScraper()
    prods = [a.finish(r) for r in a.parse_listing(az(), "x")] + [b.finish(r) for r in b.parse_listing(bz(), "x")]
    groups = annotate(prods)
    by = {p["name"]: p for p in prods}
    hicaz_a, hicaz_b = by["Hicaz Təzə Toyuq Paket 1kq"], by["HİCAZ TƏZƏ TOYUQ PAKET KQ"]
    assert hicaz_a["group"] == hicaz_b["group"] and hicaz_a["compare_count"] == 2
    mer_a, mer_b = by["Mercan Təzə Toyuq Paket Soyudulmuş 1kq"], by["MƏRCAN TƏZƏ TOYUQ PAKET KQ"]
    assert mer_a["group"] == mer_b["group"]
    assert mer_a["is_cheapest"] and not mer_b["is_cheapest"]   # 6.59 < 7.75


def test_bazarstore_fallback_without_product_item_class():
    from scraper.bazarstore import BazarstoreScraper
    from tests.fixture_bazar import listing_html as bz
    html = bz().replace("product-item", "box")
    items = BazarstoreScraper().parse_listing(html, "x")
    assert len(items) == 12 and items[0]["price"] == 5.99


def test_markets_listed_even_without_data(tmp_path, monkeypatch):  # pytest tələb edir
    """Data boş olsa da index-də hər iki market görünməlidir."""
    import json, importlib, app as appmod
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"updated": None, "products": []}))
    monkeypatch.setattr(appmod, "DATA_FILE", f)
    appmod._cache.update({"mtime": None, "payload": None})
    html = appmod.app.test_client().get("/").get_data(as_text=True)
    assert "Bazarstore" in html and "Araz Supermarket" in html
    appmod._cache.update({"mtime": None, "payload": None})


def test_cards_show_other_market_prices():
    import app as appmod
    appmod._cache.update({"mtime": None, "payload": None})
    c = appmod.app.test_client()
    html = c.get("/?q=hicaz+paket").get_data(as_text=True)
    assert "Bazarstore" in html and "Araz Supermarket" in html and 'class="others"' in html


def test_block_is_not_retried(monkeypatch):
    """403 alınanda bot təkrar-təkrar sorğu göndərməməli, dayanmalıdır."""
    from scraper.bazarstore import BazarstoreScraper
    calls = []

    class R:
        status_code = 403
        text = "Forbidden"
        headers = {"server": "cloudflare", "cf-ray": "x"}

    s = BazarstoreScraper(log=lambda *_: None)
    monkeypatch.setattr(s.s, "get", lambda *a, **k: (calls.append(1), R())[1])
    assert s.get("https://bazarstore.az/x") is None
    assert len(calls) == 1


def test_profile_env(monkeypatch):
    from scraper.bazarstore import BazarstoreScraper
    monkeypatch.setenv("SCRAPER_PROFILE", "browser")
    assert "QiymetgezBot" not in BazarstoreScraper().s.headers["User-Agent"]
    monkeypatch.setenv("SCRAPER_PROFILE", "")
    assert "QiymetgezBot" in BazarstoreScraper().s.headers["User-Agent"]
    assert BazarstoreScraper().max_pages == 80 and BazarstoreScraper(max_pages=5).max_pages == 5
