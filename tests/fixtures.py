"""Saxta saytlar: nopCommerce (Bazarstore) və Next.js (Araz) quruluşunu təqlid edir. Real səhifələrdən götürülmüş forma."""
from urllib.parse import parse_qs, quote, unquote, urlparse

BASE_B = "https://bazarstore.az"
BASE_A = "https://www.arazmarket.az"


# ------------------------------ Araz ------------------------------
def araz_listing(rows, count_header=True):
    """rows: (slug, kod, ad, kateqoriya, endirim, yeni, köhnə, araz_brendi)"""
    cards = []
    for slug, code, title, cat, disc, new, old, own in rows:
        href = f"{BASE_A}/az/products/{slug}"
        orig = f"https://b7x9kq.arazmarket.az/storage/products/{code}.png"
        src = f"{BASE_A}/_next/image?url={quote(orig, safe='')}&w=3840&q=75"
        badge = ("<span>Araz brendi</span>" if own else "") + (f"<span>{disc}%</span>" if disc else "")
        price = f"{new:.2f}" + (f" <del>{old:.2f}</del>" if old else "")
        cards.append(
            f'<div class="card"><img src="/_next/static/media/load.png" alt="loading">'
            f'<a href="{href}"><img src="{src}" alt="{slug}" title="{title}"></a>{badge}'
            f'<a href="{href}"><strong>{cat}</strong></a><a href="{href}">{title}</a>'
            f'<a href="{href}">{price}</a></div>')
    head = f"<h1>Kateqoriya</h1><p>{len(rows)} məhsul</p>" if count_header else ""
    return f"<html><body>{head}<div class='grid'>{''.join(cards)}</div></body></html>"


ARAZ_ROWS = [
    ("mercan-teze-petenek-aciq-kq-8897", "1000024346", "Mərcan Təzə Pətənək Açıq kq", "Təzə toyuq içalat", 0, 6.70, None, 0),
    ("soba-hicaz-toyuq-teze-aciq-kq-11584", "1000012614", "SOBA HICAZ TOYUQ TƏZƏ AÇIQ KQ", "Təzə toyuq bütöv", 30, 4.99, 7.10, 1),
    ("mercan-teze-toyuq-paket-soyudulmus-1kq-10097", "1000012429", "Mercan Təzə Toyuq Paket Soyudulmuş 1kq", "Təzə toyuq bütöv", 15, 6.59, 7.75, 0),
    ("hicaz-teze-toyuq-paket-1kq-9172", "1000012576", "Hicaz Təzə Toyuq Paket 1kq", "Təzə toyuq bütöv", 17, 5.99, 7.20, 0),
    ("sirvan-teze-ciyer-aciq-1kq-8649", "1000013173", "Şirvan Təzə Ciyər Açıq 1kq", "Təzə toyuq içalat", 26, 3.49, 4.70, 0),
    ("mercan-teze-file-aciq-1kq-8646", "1000013115", "Mercan Təzə File Açıq 1kq", "Təzə toyuq file", 0, 10.50, None, 0),
]


# ----------------------------- Bazarstore -----------------------------
def bazar_item(pid, slug, name, price_text, img=True):
    im = (f'data-lazyloadsrc="https://bazarstore.az/images/thumbs/00{pid}_415.jpeg"' if img else "")
    return (f'<div class="product-item" data-productid="{pid}"><div class="picture"><a href="/{slug}">'
            f'<img alt="x" src="data:image/gif;base64,R0lGOD" {im}></a></div>'
            f'<div class="details"><h2 class="product-title"><a href="/{slug}">{name}</a></h2>'
            f'<div class="prices"><span class="price">{price_text}</span></div></div></div>')


def bazar_page(items):
    return "<html><body><div class='product-grid'>" + "".join(items) + "</div></body></html>"


# nopCommerce menyusunun real quruluşu: iç-içə siyahılar, "Hamısına bax", sonra Brendlər, sonra footer
BAZAR_HOME = """<html><body>
<a href="/">logo</a><a href="/customer/info">Hesabım</a><a href="/register?returnUrl=%2F">Qeydiyyat</a>
<a href="/wishlist">Seçilmişlər</a><a href="/cart">səbət</a>
<ul>
 <li><a href="/meyve-terevez">🍉Meyvə, tərəvəz</a>
   <ul><li><a href="/meyve" title="Meyvə">Meyvə</a>
         <ul><li><a href="/berk-meyveler">Bərk meyvələr</a></li><li><a href="/sitrus-meyveler">Sitrus</a></li></ul></li>
       <li><a href="/terevez">Tərəvəz</a></li></ul></li>
 <li><a href="/et-toyuq-baliq">🥩Ət, Toyuq, Balıq</a>
   <ul><li><a href="/ag-et">Ağ ət</a>
         <ul><li><a href="/teze-toyuq">Təzə toyuq</a></li><li><a href="/hinduska-eti">Hinduşka əti</a></li></ul></li>
       <li><a href="/et-qastronom">Ət qastronom</a><a href="/et-qastronom">Hamısına bax</a></li></ul></li>
 <li><a href="/ickiler">🍹İçkilər</a><ul><li><a href="/limonadlar">Limonadlar</a></li></ul></li>
 <li><a href="/super-maqazin">Super Maqazin</a></li>
 <li><a href="/endirimli-məhsullar">Endirimli Məhsullar</a></li>
 <li><a href="/butun-mehsullar#/manFilters=69">Öz Məhsullarımız</a></li>
 <li><a href="/manufacturer/all">Bütün Brendlər</a><ul><li><a href="/abad">ABAD</a></li><li><a href="/adidas">ADIDAS</a></li></ul></li>
</ul>
<a href="/blog">Bloq</a><a href="/faq">FAQ</a><a href="/haqqimizda">Haqqımızda</a><a href="/nestle-dondurma-160-ml">Tövsiyə edilən məhsul</a>
</body></html>"""


class Resp:
    def __init__(self, text="", status=200, headers=None):
        self.text, self.status_code, self.headers = text, status, headers or {"server": "test"}
        self.encoding = "utf-8"

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")


class FakeBazar:
    """Bazarstore kimi cavab verir: kateqoriya ağacı, səhifələmə (?pagesize=&pagenumber=), üst kateqoriyada alt məhsullar."""
    TREE = {  # üst → {alt: [məhsul id-ləri]}; "_direct" = birbaşa üst kateqoriyada olanlar
        "meyve-terevez": {"meyve": range(1000, 1030), "terevez": range(1030, 1045), "_direct": [1099]},
        "et-toyuq-baliq": {"teze-toyuq": range(2000, 2047), "hinduska-eti": range(2047, 2052), "et-qastronom": range(2052, 2060), "_direct": []},
        "ickiler": {"limonadlar": range(3000, 3012), "_direct": []},
    }

    def __init__(self, robots="User-agent: *\nDisallow: /cart\nDisallow: /search\n", block_after=None):
        self.calls, self.robots, self.block_after = [], robots, block_after

    def products_of(self, slug):
        if slug in self.TREE:
            ids = []
            for k, v in self.TREE[slug].items():
                ids += list(v)
            return sorted(set(ids))
        for top in self.TREE.values():
            if slug in top:
                return list(top[slug])
        return None

    def get(self, url, timeout=0, **kw):
        u = urlparse(url)
        self.calls.append(url)
        if self.block_after is not None and len(self.calls) > self.block_after:
            return Resp("Forbidden", 403, {"server": "cloudflare", "cf-ray": "x"})
        path = unquote(u.path).strip("/")
        if path == "robots.txt":
            return Resp(self.robots) if self.robots is not None else Resp("", 404)
        if path == "":
            return Resp(BAZAR_HOME)
        ids = self.products_of(path)
        if ids is None:
            return Resp("", 404)
        q = parse_qs(u.query)
        size, page = int(q.get("pagesize", ["10"])[0]), int(q.get("pagenumber", ["1"])[0])
        chunk = ids[(page - 1) * size: page * size]
        items = [bazar_item(i, f"urun-{i}", f"MƏHSUL {i} KQ", f"{1 + (i % 17) * 0.5:.2f} ₼".replace(".", ",")) for i in chunk]
        return Resp(bazar_page(items))
