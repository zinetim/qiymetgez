import json
import os
import sys
import tempfile
import time
from pathlib import Path

from core import matcher, robots, store
from core.textutil import parse_weight
from tests.fixtures import (ARAZ_ROWS, BAZAR_HOME, FakeBazar, Resp, araz_listing, bazar_item, bazar_page)


def quiet(*_a, **_k):
    pass


# ---------------------------------------------------------------- textutil
def test_weight():
    assert parse_weight("Tac Şirvan Təzə Toyuq Açıq 1kq")[:2] == (1.0, "kg")
    assert parse_weight("Süd 500 qr")[:2] == (0.5, "kg")
    assert parse_weight("Süd 0.5 L")[:2] == (0.5, "l")
    assert parse_weight("Pepsi 330ml")[:2] == (0.33, "l")
    assert parse_weight("SOBA HİCAZ CİYƏR TEZE AÇIQ KQ")[:2] == (1.0, "kg")
    assert parse_weight("Mercan Təzə Ciyər Açıqkq")[:2] == (1.0, "kg")
    assert parse_weight("Tac Gilezi Təzə Toyuq Açıq")[0] is None
    assert parse_weight("GULUM ŞİRİN QARĞIDALI 425 Q")[:2] == (0.425, "kg")
    assert parse_weight("Çips Lays Сыр, 140 q")[:2] == (0.14, "kg")
    assert parse_weight("Yumurta 10 lu")[0] is None


# ---------------------------------------------------------------- Araz parser
def test_araz_parser():
    from scraper.araz import ArazScraper
    s = ArazScraper(log=quiet)
    items = s.parse_listing(araz_listing(ARAZ_ROWS), "Təzə ağ ətlər")
    assert len(items) == 6 and s.expected_count(araz_listing(ARAZ_ROWS)) == 6
    a = items[0]
    assert (a["price"], a["old_price"]) == (6.70, None)       # indi endirimsiz: yalnız bir qiymət
    b = items[1]
    assert (b["price"], b["old_price"], b["discount"], b["own_brand"]) == (4.99, 7.10, 30, True)
    assert b["category"] == "Təzə toyuq bütöv" and b["code"] == "1000012614"
    assert b["image"].endswith("/1000012614.png") and "_next/image" in b["image_thumb"]


def test_araz_category_href():
    from scraper.araz import ArazScraper
    s = ArazScraper(log=quiet)
    assert s.is_category_href("/az/categories/teze-ag-etler-66")
    assert s.is_category_href("https://www.arazmarket.az/az/categories/sud-12/")
    assert not s.is_category_href("/az/products/xxx-1") and not s.is_category_href("/az/categories/abc")
    html = '<a href="/az/categories/a-1">A</a><a href="/az/categories/a-1">A2</a><a href="/az/categories/b-2">B</a><a href="/az/basket">x</a>'
    assert [p for _, p in s.category_links(html)] == ["/az/categories/a-1", "/az/categories/b-2"]


# ---------------------------------------------------------------- Bazarstore parser
def test_bazarstore_parser():
    from scraper.bazarstore import BazarstoreScraper
    s = BazarstoreScraper(log=quiet)
    html = bazar_page([
        bazar_item(101, "hicaz-bud", "HİCAZ TƏZƏ BUD BÜTÖV AÇIQ KQ", "5,99 ₼"),
        bazar_item(111, "gulum", "GULUM ŞİRİN QARĞIDALI 425 Q", "2,40 ₼ 1,89 ₼"),          # köhnə qiymət əvvəl
        bazar_item(112, "xiyar", "XİYAR KG", "1,69 ₼ 1 kg(s) üçün 1,69 ₼ təşkil edir"),   # vahid qiyməti mətni atılır
        bazar_item(113, "yox", "BAHA", "1 234,50 ₼"),
    ])
    by = {i["code"]: i for i in s.parse_listing(html, "x")}
    assert by["101"]["price"] == 5.99 and by["101"]["old_price"] is None and by["101"]["image"].endswith("00101_415.jpeg")
    assert (by["111"]["price"], by["111"]["old_price"]) == (1.89, 2.40)
    assert by["112"]["price"] == 1.69 and by["112"]["old_price"] is None
    assert by["113"]["price"] == 1234.50
    assert s.page_url("/x", 1).endswith("/x?pagesize=20") and s.page_url("/x", 3).endswith("?pagesize=20&pagenumber=3")
    assert s.finish(by["101"])["id"] == "bazarstore-101"


def test_bazarstore_category_discovery_order():
    from scraper.bazarstore import BazarstoreScraper
    s = BazarstoreScraper(log=quiet)
    links = s.category_links(BAZAR_HOME)
    paths = [p for _, p in links]
    assert "/hinduska-eti" in paths and "/meyve-terevez" in paths
    assert "/manufacturer/all" not in paths and "/abad" not in paths          # brendlər menyudan çıxarılır
    assert "/super-maqazin" not in paths and "/butun-mehsullar" not in paths and "/customer/info" not in paths
    assert "/blog" not in paths and "/nestle-dondurma-160-ml" not in paths    # menyudan sonrakılar
    assert paths.count("/et-qastronom") == 1                                  # "Hamısına bax" təkrarı yoxdur
    assert {pp: nn for nn, pp in links}["/et-toyuq-baliq"] == "Ət, Toyuq, Balıq"              # emoji təmizlənib
    s.discover = lambda: links
    cats = s.get_categories()
    keys = [p for _, p, _ in cats]
    # alt kateqoriya həmişə öz üst kateqoriyasından ƏVVƏL gəlir
    assert keys.index("/teze-toyuq") < keys.index("/ag-et") < keys.index("/et-toyuq-baliq")
    assert keys.index("/berk-meyveler") < keys.index("/meyve") < keys.index("/meyve-terevez")
    full = [p for _, p, f in cats if f]
    assert len(full) == 14 and all(not f for _, p, f in cats if p == "/teze-toyuq")


# ---------------------------------------------------------------- tam çəkmə simulyasiyası
def make_scraper(fake, **kw):
    from scraper.bazarstore import BazarstoreScraper
    s = BazarstoreScraper(log=kw.pop("log", quiet), **kw)
    s.delay = (0, 0)
    s.s.get = fake.get
    return s


def test_full_crawl_leaf_first_and_complete():
    fake = FakeBazar()
    s = make_scraper(fake)
    items, complete = s.run()
    ids = {i["code"] for i in items}
    expected = set()
    for top in FakeBazar.TREE.values():
        for v in top.values():
            expected |= {str(x) for x in v}
    assert complete and ids == expected and len(items) == len(expected), (len(items), len(expected))
    cat = {i["code"]: i["category"] for i in items}
    assert cat["2000"] == "Təzə toyuq"                 # ən dəqiq (alt) kateqoriya
    assert cat["1099"] == "Meyvə, tərəvəz"             # yalnız üst kateqoriyada olan məhsul da tutuldu
    assert cat["3000"] == "Limonadlar"
    # robots.txt qadağası (/cart) heç vaxt çağırılmayıb, təkrar sorğu da yoxdur
    assert not any("/cart" in c for c in fake.calls) and len(fake.calls) == len(set(fake.calls))
    # alt kateqoriyalar çəkildikdən sonra üstlər tam taranır: bir üst kateqoriyanın bütün səhifələri
    assert any("/et-toyuq-baliq?pagesize=20&pagenumber=2" in c for c in fake.calls)


def test_pagination_stops_and_large_category():
    """47 məhsullu kateqoriya: 3 səhifə (20+20+7), 4-cü səhifə boşdur → dayanır."""
    fake = FakeBazar()
    s = make_scraper(fake)
    raw, seen = [], set()
    st = s.crawl_category("Təzə toyuq", "/teze-toyuq", False, seen, raw, None)
    assert st["pages"] == 3 and st["new"] == 47 == len(raw)
    pages_requested = [c for c in fake.calls if "teze-toyuq" in c]
    assert len(pages_requested) == 4                    # 3 dolu + 1 boş səhifə
    # eyni kateqoriyanı yenidən çəkəndə (hamısı artıq görülüb): 1 sorğu ilə dayanır
    n0 = len(fake.calls)
    st2 = s.crawl_category("Təzə toyuq", "/teze-toyuq", False, seen, raw, None)
    assert st2["new"] == 0 and len(fake.calls) - n0 == 1


def test_block_stops_whole_run():
    fake = FakeBazar(block_after=5)
    s = make_scraper(fake)
    items, complete = s.run()
    assert s.blocked and not complete
    assert len(fake.calls) <= 8                        # blokdan sonra sorğu göndərilmir


def test_time_budget_returns_partial():
    fake = FakeBazar()
    s = make_scraper(fake)
    items, complete = s.run(max_minutes=1e-9)
    assert not complete


def test_robots_blocks_category():
    fake = FakeBazar(robots="User-agent: *\nDisallow: /et-toyuq-baliq\nDisallow: /teze-toyuq\n")
    s = make_scraper(fake)
    items, complete = s.run()
    assert not any("/teze-toyuq" in c and "robots" not in c for c in fake.calls)
    assert all(i["category"] != "Təzə toyuq" for i in items)


def test_manual_categories_file():
    from scraper import base
    from scraper.araz import ArazScraper
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "categories_araz.txt").write_text(
            "# şərh\nSüd | /az/categories/sud-12\nhttps://www.arazmarket.az/az/categories/cay-7\nhttps://evil.com/x\nyanlis\n", encoding="utf-8")
        old = base.CONFIG_DIR
        base.CONFIG_DIR = Path(d)
        try:
            s = ArazScraper(log=quiet)
            got = s.manual_categories()
        finally:
            base.CONFIG_DIR = old
    assert got == [("Süd", "/az/categories/sud-12"), ("Cay", "/az/categories/cay-7")], got


def test_completeness_warning_for_araz():
    """Sayt '300 məhsul' yazır, amma yalnız 6 göstərir → xəbərdarlıq."""
    from scraper.araz import ArazScraper
    s = ArazScraper(log=quiet)
    html = araz_listing(ARAZ_ROWS).replace("6 məhsul", "300 məhsul")
    assert s.expected_count(html) == 300
    logs = []
    s2 = ArazScraper(log=logs.append)
    s2.delay = (0, 0)
    s2.s.get = lambda url, timeout=0, **k: Resp(html) if "/categories/x-1" in url and "page=" not in url else Resp("", 404)
    s2.get_categories = lambda discover=True: [("X", "/az/categories/x-1", False)]
    s2.robots_ok = lambda p: True
    items, complete = s2.run()
    assert len(items) == 6 and any("300" in str(l) and "⚠" in str(l) for l in logs)


# ---------------------------------------------------------------- saxlama
def test_store_merge_history_and_pruning():
    def P(i, price, market="araz"):
        return {"id": i, "market": market, "name": i, "price": price}
    old = [dict(P("a", 5.0), history=[["2026-10-01", 5.0]], first_seen="2026-10-01", last_seen="2026-10-10"),
           dict(P("gone", 1.0), history=[], first_seen="2026-09-01", last_seen="2026-10-01"),     # 12 gün görünməyib → silinir
           dict(P("recent", 2.0), history=[], first_seen="2026-09-01", last_seen="2026-10-09"),   # 2 gün → qalır
           P("other", 9.0, "bazarstore")]
    out = store.merge(old, [P("a", 6.0), P("new", 3.0)], "araz", "2026-10-11")
    by = {p["id"]: p for p in out}
    assert set(by) == {"a", "recent", "new", "other"}
    assert by["a"]["history"] == [["2026-10-01", 5.0], ["2026-10-11", 6.0]] and by["a"]["first_seen"] == "2026-10-01"
    assert by["new"]["first_seen"] == "2026-10-11" and by["other"]["price"] == 9.0
    out2 = store.merge(out, [P("a", 6.0), P("new", 3.0)], "araz", "2026-10-11")      # eyni gün təkrar: tarixçə şişmir
    assert [p for p in out2 if p["id"] == "a"][0]["history"] == by["a"]["history"]


def test_store_save_one_product_per_line():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.json"
        store.save(f, {"updated": "x", "products": [{"id": "b", "n": "Ə"}, {"id": "a", "n": "1"}]})
        lines = f.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 4 and lines[1].startswith('{"id":"a"') and "Ə" in lines[2]
        assert [p["id"] for p in store.load(f)["products"]] == ["a", "b"]


# ---------------------------------------------------------------- qruplaşdırma
def test_matching_real_names_across_markets():
    from scraper.araz import ArazScraper
    from scraper.bazarstore import BazarstoreScraper
    a, b = ArazScraper(log=quiet), BazarstoreScraper(log=quiet)
    prods = [a.finish(r) for r in a.parse_listing(araz_listing(ARAZ_ROWS), "x")]
    bz = bazar_page([bazar_item(1, "h", "HİCAZ TƏZƏ TOYUQ PAKET KQ", "7,19 ₼"),
                     bazar_item(2, "m", "MƏRCAN TƏZƏ TOYUQ PAKET KQ", "7,75 ₼"),
                     bazar_item(3, "f", "MƏRCAN TƏZƏ FİLE AÇIQ KQ", "10,90 ₼"),
                     bazar_item(4, "x", "TAMAMİLƏ BAŞQA MƏHSUL KQ", "1,00 ₼")])
    prods += [b.finish(r) for r in b.parse_listing(bz, "x")]
    multi = matcher.assign_groups(prods)
    groups = matcher.build(prods)
    by = {p["name"]: p for p in prods}
    assert by["Hicaz Təzə Toyuq Paket 1kq"]["g"] == by["HİCAZ TƏZƏ TOYUQ PAKET KQ"]["g"]
    assert by["Mercan Təzə Toyuq Paket Soyudulmuş 1kq"]["g"] == by["MƏRCAN TƏZƏ TOYUQ PAKET KQ"]["g"]
    assert by["Mercan Təzə File Açıq 1kq"]["g"] == by["MƏRCAN TƏZƏ FİLE AÇIQ KQ"]["g"]
    assert by["TAMAMİLƏ BAŞQA MƏHSUL KQ"]["compare_count"] == 1
    h = by["Hicaz Təzə Toyuq Paket 1kq"]
    assert h["is_cheapest"] and h["spread"] == 1.20 and h["others"][0]["price"] == 7.19
    assert multi == 3


def test_matching_scale_20k_is_fast():
    """20 000 məhsul: tərs indeks sayəsində saniyələr içində qruplaşır, O(n²) deyil."""
    import random
    random.seed(7)
    brands = [f"Marka{i}" for i in range(120)]
    kinds = ["Süd", "Çay", "Yağ", "Makaron", "Düyü", "Şokolad", "Peçenye", "Kolbasa", "Pendir", "Yoqurt", "Şampun", "Sabun"]
    sizes = ["200 qr", "500 qr", "1 kq", "0.5 L", "1 L", "250 ml", "2 kq"]
    base = [(random.choice(brands), random.choice(kinds), random.choice(sizes), random.choice(["Klassik", "Premium", "Sadə", "Xüsusi", "Mini"]))
            for _ in range(7000)]
    prods = []
    n = 0
    for market in ("araz", "bazarstore"):
        for k in range(10000):
            b, kind, size, v = base[random.randrange(len(base))] if random.random() < 0.5 else base[k % len(base)]
            name = f"{b} {kind} {v} {size}" + (f" {random.randrange(50)}" if random.random() < 0.3 else "")
            prods.append({"id": f"{market}-{n}", "market": market, "name": name, "price": round(random.uniform(1, 20), 2),
                          "weight_unit": None, "weight_value": None})
            n += 1
    from core.textutil import parse_weight
    for p in prods:
        p["weight_value"], p["weight_unit"], _ = parse_weight(p["name"])
    t = time.time()
    multi = matcher.assign_groups(prods)
    dt = time.time() - t
    assert dt < 20, f"çox yavaş: {dt:.1f}s"
    assert multi > 500 and all("g" in p for p in prods)
    # düzgünlük: brute-force ilə eyni nəticə (nümunə üzərində). Prefix-filter heç bir uyğunluğu qaçırmamalıdır.
    from core.textutil import name_tokens
    sample = [p for p in prods if p["market"] == "araz"][:300]
    others = [p for p in prods if p["market"] == "bazarstore"]
    missed = 0
    for a in sample:
        ta = name_tokens(a["name"])
        for b in others:
            if (a["weight_unit"], a["weight_value"]) != (b["weight_unit"], b["weight_value"]):
                continue
            tb = name_tokens(b["name"])
            if ta and tb and len(ta & tb) / len(ta | tb) >= 0.75 and a["g"] != b["g"]:
                missed += 1
    assert missed == 0, f"prefix-filter {missed} uyğunluğu qaçırdı"
    t = time.time()
    matcher.build(prods)
    assert time.time() - t < 5
    print(f"   20k məhsul: assign_groups {dt:.1f}s, çox marketli qrup {multi}")


# ---------------------------------------------------------------- robots + profillər + blok
def test_robots_wildcards():
    txt = "User-agent: *\nDisallow: /cart\nDisallow: /*?*returnUrl=\nDisallow: /search\nAllow: /search/autocomplete$\nUser-agent: badbot\nDisallow: /\n"
    r = robots.parse(txt)
    assert robots.allowed(r, "/teze-toyuq?pagesize=20&pagenumber=2") and not robots.allowed(r, "/cart")
    assert not robots.allowed(r, "/login?returnUrl=%2Fx") and not robots.allowed(r, "/search?q=1")
    assert robots.allowed(r, "/search/autocomplete")
    assert robots.allowed(robots.parse("User-agent: *\nDisallow:\n"), "/x")
    assert not robots.allowed(robots.parse("User-agent: *\nDisallow: /\n"), "/x")


def test_profiles():
    from scraper.araz import ArazScraper
    from scraper.bazarstore import BazarstoreScraper
    os.environ.pop("SCRAPER_PROFILE", None)
    ua = BazarstoreScraper().s.headers["User-Agent"]
    assert "bot" not in ua.lower() and "Qiymetgez/1.0" in ua and "zinetim" in ua
    assert "QiymetgezBot" in ArazScraper().s.headers["User-Agent"]
    os.environ["SCRAPER_PROFILE"] = "browser"
    try:
        assert "Qiymetgez" not in BazarstoreScraper().s.headers["User-Agent"]
    finally:
        os.environ.pop("SCRAPER_PROFILE")


# ---------------------------------------------------------------- sayt (Flask)
def _write_data(path, n_per_market=3000):
    import random
    random.seed(3)
    prods = []
    for i in range(n_per_market):
        base = f"Marka{i % 400} Məhsul{i % 700} {['1 kq', '500 qr', '1 L'][i % 3]}"
        for mk in ("araz", "bazarstore"):
            if mk == "bazarstore" and i % 3:
                continue
            w, u, lab = parse_weight(base)
            prods.append({"id": f"{mk}-{i}", "market": mk, "name": base if mk == "araz" else base.upper(),
                          "category": f"Kat{i % 40}", "price": round(1 + (i % 50) * 0.37 + (0.8 if mk == "bazarstore" else 0), 2),
                          "old_price": None, "discount": (i % 5) * 5 or None, "weight_value": w, "weight_unit": u,
                          "weight_label": lab, "unit_price": 1.0, "unit_label": "kq", "image": None, "image_thumb": None,
                          "url": f"https://x/{mk}/{i}", "history": [["2026-10-01", 1.0]], "first_seen": "2026-10-01", "last_seen": "2026-10-11"})
    matcher.assign_groups(prods)
    store.save(path, {"updated": "2026-10-11T03:00:00+00:00", "products": prods})
    return len(prods)


def test_app_with_thousands_of_products():
    import app as appmod
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "p.json"
        n = _write_data(f)
        old = appmod.DATA_FILE
        appmod.DATA_FILE = f
        appmod._cache.update({"mtime": None, "payload": None})
        try:
            t = time.time()
            d_ = appmod.get_data()
            load_s = time.time() - t
            assert len(d_["products"]) == n and n > 2000 and load_s < 5, (n, load_s)
            c = appmod.app.test_client()
            r = c.get("/")
            html = r.get_data(as_text=True)
            assert r.status_code == 200 and html.count('class="card"') == 20
            assert "Marka" in html and 'class="gap"' in html                       # windowed səhifələmə: …
            assert html.count('class="pager"') == 1 and html.count("<a href=\"/?page=") < 12   # yüzlərlə səhifə linki YOXDUR
            # ən yüksək səhifə, səhifədən kənar, etibarsız
            last = appmod.page_window(1, 200)
            assert last == [1, 2, 3, None, 200]
            assert c.get("/?page=99999").status_code == 200 and c.get("/?page=abc").status_code == 200
            r = c.get("/?market=bazarstore&sort=cheap")
            assert r.status_code == 200 and r.get_data(as_text=True).count('class="card"') == 20
            r = c.get("/?q=marka5+məhsul5&cmp=1")
            assert r.status_code == 200
            api = c.get("/api/products?q=marka7&limit=5").get_json()
            assert api["count"] > 0 and len(api["products"]) <= 5 and "search" not in api["products"][0]
            multi = [p for p in d_["products"] if p["compare_count"] > 1][0]
            r = c.get("/m/" + multi["id"])
            h = r.get_data(as_text=True)
            assert r.status_code == 200 and 'class="savebox"' in h and "cmp-table" in h
            assert c.get("/m/yox").status_code == 404 and c.get("/healthz").get_data(as_text=True) == "ok"
            top = c.get("/").get_data(as_text=True)
            assert "marketdə müqayisə" in top       # ana səhifə əvvəl müqayisəli məhsulları göstərir
            print(f"   {n} məhsul yükləndi: {load_s:.2f}s")
        finally:
            appmod.DATA_FILE = old
            appmod._cache.update({"mtime": None, "payload": None})


def test_app_empty_data_shows_both_markets():
    import app as appmod
    with tempfile.TemporaryDirectory() as d:
        old = appmod.DATA_FILE
        appmod.DATA_FILE = Path(d) / "yox.json"
        appmod._cache.update({"mtime": None, "payload": None})
        try:
            html = appmod.app.test_client().get("/").get_data(as_text=True)
            assert "Bazarstore" in html and "Araz Supermarket" in html and "Hələ data yoxdur" in html
        finally:
            appmod.DATA_FILE = old
            appmod._cache.update({"mtime": None, "payload": None})
