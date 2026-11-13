"""Bütün market botları üçün baza: sorğu, kateqoriya kəşfi, səhifələmə, robots.txt, məhsul formatı."""
import hashlib
import os
import random
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core import robots
from core.textutil import parse_weight, unit_price

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

UA = ("Mozilla/5.0 (compatible; QiymetgezBot/1.0; +https://github.com/zinetim/qiymetgez) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")
PROFILES = {
    "bot": {"User-Agent": UA, "Accept-Language": "az,en;q=0.8"},
    # "open": brauzer formatında, "bot" sözü yoxdur, amma əlaqə ünvanı var: sayt sahibi kim olduğumuzu görə bilir
    "open": {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36 Qiymetgez/1.0 (+https://github.com/zinetim/qiymetgez; qiymet muqayisesi)"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "az,en;q=0.8",
    },
    "browser": {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "az,en;q=0.8",
    },
}
BLOCK_CODES = (401, 403, 429)


def norm_path(p):
    """Kateqoriya yolunu müqayisə üçün normallaşdırır (kiçik hərf, %-kodlaşdırma açılır, son '/' atılır)."""
    return unquote(urlparse(p).path).rstrip("/").lower() or "/"


def prettify(path):
    seg = unquote(urlparse(path).path).rstrip("/").split("/")[-1]
    seg = re.sub(r"-\d+$", "", seg).replace("-", " ").strip()
    return seg[:1].upper() + seg[1:]


def clean_name(s):
    """Başlanğıcdakı emoji/simvolları atır: '🥩Ət, Toyuq' → 'Ət, Toyuq'."""
    return re.sub(r"^[^\w]+", "", (s or "").strip())


class BaseScraper:
    market = ""            # qısa açar: "araz"
    market_name = ""
    base_url = ""
    categories = []        # defolt kateqoriyalar [(ad, yol)]
    discover_pages = []    # kateqoriya linkləri axtarılacaq səhifələr (yol)
    use_sitemap = False
    delay = (0.8, 1.6)     # sorğular arası fasilə (saniyə)
    page_param = "page"
    extra_params = {}
    max_pages = 400        # bir kateqoriyada maksimum səhifə
    profile = "bot"        # SCRAPER_PROFILE mühit dəyişəni üstün gəlir

    def __init__(self, details=False, max_pages=None, log=print):
        self.details, self.log = details, log
        if max_pages:
            self.max_pages = max_pages
        self.s = requests.Session()
        name = os.environ.get("SCRAPER_PROFILE") or self.profile
        self.s.headers.update(PROFILES.get(name, PROFILES["bot"]))
        self._rules = None
        self.blocked = False
        self.requests_made = 0

    # ---------------- şəbəkə ----------------
    def get(self, url, retries=3):
        if self.blocked:
            return None
        last = None
        for i in range(retries):
            try:
                r = self.s.get(url, timeout=25)
                self.requests_made += 1
                if r.status_code == 404:
                    return None
                if r.status_code in BLOCK_CODES:
                    h = r.headers
                    self.blocked = True   # blok olunmuşuq: təkrar-təkrar sınamırıq, run dayanır
                    self.log(f"  ! {r.status_code} BLOK: {url}\n    server={h.get('server')} cf-ray={h.get('cf-ray')} "
                             f"retry-after={h.get('retry-after')}\n    cavab: {r.text[:120]!r}\n"
                             f"    → python -m scraper.diagnose ilə səbəbi yoxlayın")
                    return None
                r.raise_for_status()
                r.encoding = "utf-8"
                time.sleep(random.uniform(*self.delay))
                return r.text
            except requests.RequestException as e:
                last = e
                time.sleep(2 ** i)
        self.log(f"  ! alınmadı: {url} ({last})")
        return None

    def robots_ok(self, path_and_query):
        if self._rules is None:
            try:
                r = self.s.get(self.base_url + "/robots.txt", timeout=20)
                if r.status_code == 200:
                    self._rules = robots.parse(r.text)
                    self.log(f"  robots.txt oxundu: {len(self._rules)} qayda")
                else:
                    self._rules = []
                    self.log(f"  ! robots.txt alınmadı (HTTP {r.status_code}), qaydalar yoxlanılmadı")
            except requests.RequestException as e:
                self._rules = []
                self.log(f"  ! robots.txt xətası: {e}")
        return robots.allowed(self._rules, path_and_query)

    def page_url(self, path, page):
        params = dict(self.extra_params)
        if page > 1:
            params[self.page_param] = page
        return self.base_url + path + (("?" + urlencode(params)) if params else "")

    # ---------------- market özü yazır ----------------
    def parse_listing(self, html, category):
        raise NotImplementedError

    def parse_detail(self, html):
        return {}

    def is_category_href(self, href):
        return False

    def expected_count(self, html):
        """Səhifədə yazılmış ümumi məhsul sayı (varsa). Tamlıq yoxlaması üçün."""
        return None

    def item_key(self, item):
        return item.get("code") or item["url"]

    # ---------------- kateqoriya kəşfi ----------------
    def manual_categories(self):
        """config/categories_<market>.txt: hər sətir `yol`, tam link və ya `Ad | yol`."""
        f = CONFIG_DIR / f"categories_{self.market}.txt"
        out = []
        if not f.exists():
            return out
        host = urlparse(self.base_url).netloc.replace("www.", "")
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.split(" #")[0].strip()
            if not line or line.startswith("#"):
                continue
            name, path = (x.strip() for x in line.split("|", 1)) if "|" in line else ("", line)
            if path.startswith("http"):
                u = urlparse(path)
                if u.netloc.replace("www.", "") != host:
                    continue
                path = u.path
            if not path.startswith("/"):
                continue
            out.append((name or prettify(path), path))
        return out

    def category_links(self, html):
        out, seen = [], set()
        for a in BeautifulSoup(html, "html.parser").select("a[href]"):
            if not self.is_category_href(a["href"]):
                continue
            path = urlparse(urljoin(self.base_url, a["href"])).path
            k = norm_path(path)
            if k in seen:
                continue
            seen.add(k)
            out.append((clean_name(a.get_text(" ", strip=True)) or prettify(path), path))
        return out

    def sitemap_categories(self):
        out, todo, done = [], ["/sitemap.xml"], set()
        while todo and len(done) < 12:
            path = todo.pop(0)
            if path in done or not self.robots_ok(path):
                continue
            done.add(path)
            xml = self.get(self.base_url + path)
            if not xml:
                continue
            for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
                if loc.endswith(".xml"):
                    todo.append(urlparse(loc).path)
                elif self.is_category_href(loc):
                    p = urlparse(loc).path
                    out.append((prettify(p), p))
        self.log(f"  sitemap: {len(out)} kateqoriya")
        return out

    def discover(self):
        found = []
        for path in self.discover_pages:
            if self.blocked or not self.robots_ok(path):
                continue
            html = self.get(self.base_url + path)
            if not html:
                self.log(f"  kəşf: {path} alınmadı")
                continue
            links = self.category_links(html)
            self.log(f"  kəşf: {path} → {len(links)} kateqoriya linki")
            found += links
        if self.use_sitemap and not self.blocked:
            found += self.sitemap_categories()
        return found

    def get_categories(self, discover=True):
        """[(ad, yol, tam_rejim)]: əl ilə yazılanlar, defoltlar, kəşf olunanlar (təkrarsız)."""
        seen, out = set(), []

        def add(n, p, full=False):
            k = norm_path(p)
            if k not in seen and k != "/":
                seen.add(k)
                out.append((n, p, full))

        for n, p in self.manual_categories():
            add(n, p)
        for n, p in self.categories:
            add(n, p)
        if discover:
            for n, p in self.discover():
                add(n, p)
        return out

    # ---------------- əsas axın ----------------
    def crawl_category(self, name, path, full, seen, raw, deadline):
        """Bir kateqoriyanı səhifə-səhifə oxuyur. Qaytarır: dict(listed, new, pages, expected, ok)."""
        st = {"listed": 0, "new": 0, "pages": 0, "expected": None, "ok": True}
        for page in range(1, self.max_pages + 1):
            if deadline and time.time() > deadline:
                st["ok"] = False
                return st
            url = self.page_url(path, page)
            if not self.robots_ok(url[len(self.base_url):]):
                self.log(f"  ✗ robots.txt qadağan edir, keçildi: {url}")
                return st
            html = self.get(url)
            if html is None:
                st["ok"] = page == 1 and not self.blocked   # 1-ci səhifə 404 = köhnə kateqoriya, normaldır
                return st
            if page == 1:
                st["expected"] = self.expected_count(html)
            items = self.parse_listing(html, name)
            if not items:
                break
            st["pages"] += 1
            st["listed"] += len(items)
            fresh = [i for i in items if self.item_key(i) not in seen]
            for i in fresh:
                seen.add(self.item_key(i))
            raw.extend(fresh)
            st["new"] += len(fresh)
            if not fresh and not full:
                break   # bu səhifədə yeni heç nə yoxdur: kateqoriya artıq çəkilib
        return st

    def run(self, max_minutes=None, discover=True):
        """(məhsullar, tam_tamamlandı) qaytarır."""
        t0 = time.time()
        deadline = t0 + max_minutes * 60 if max_minutes else None
        cats = self.get_categories(discover)
        self.log(f"[{self.market}] {len(cats)} kateqoriya çəkiləcək")
        raw, seen, complete, problems = [], set(), True, []
        for n, (name, path, full) in enumerate(cats, 1):
            if self.blocked or (deadline and time.time() > deadline):
                complete = False
                self.log("  ! dayandırıldı (" + ("blok" if self.blocked else "vaxt limiti") + ")")
                break
            st = self.crawl_category(name, path, full, seen, raw, deadline)
            if not st["ok"]:
                complete = False
            warn = ""
            if st["expected"] and st["listed"] < st["expected"] * 0.9:
                warn = f"  ⚠ sayt {st['expected']} məhsul yazır, bot {st['listed']} gördü (səhifələmə?)"
                problems.append(name)
            self.log(f"  [{n}/{len(cats)}] {name}: {st['listed']} siyahıda, +{st['new']} yeni, {st['pages']} səhifə"
                     f"{' (tam)' if full else ''}{warn}")
        if self.details:
            for k, item in enumerate(raw, 1):
                html = self.get(item["url"])
                if html:
                    item.update({a: b for a, b in self.parse_detail(html).items() if b})
                if k % 50 == 0:
                    self.log(f"  detallar: {k}/{len(raw)}")
        items = [self.finish(r) for r in raw if r.get("price")]
        self.log(f"[{self.market}] bitdi: {len(items)} məhsul, {self.requests_made} sorğu, "
                 f"{(time.time() - t0) / 60:.1f} dəq, tam={complete}")
        if problems:
            self.log(f"  ⚠ tamlıq xəbərdarlığı olan kateqoriyalar: {', '.join(problems[:10])}")
        return items, complete

    def finish(self, r):
        value, unit, label = parse_weight(r["name"])
        up, up_label = unit_price(r["price"], value, unit)
        old = r.get("old_price")
        if old and old <= r["price"]:
            old = None
        discount = r.get("discount") or (round((1 - r["price"] / old) * 100) if old else None)
        code = str(r.get("code") or r["url"].rstrip("/").split("/")[-1].split("-")[-1])
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", code):
            code = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        return {
            "id": f"{self.market}-{code}",
            "market": self.market,
            "name": r["name"].strip(),
            "category": r.get("category"),
            "price": round(r["price"], 2),
            "old_price": round(old, 2) if old else None,
            "discount": discount,
            "weight_value": value,
            "weight_unit": unit,
            "weight_label": label,
            "unit_price": up,
            "unit_label": up_label,
            "barcode": r.get("barcode"),
            "code": r.get("code"),
            "own_brand": bool(r.get("own_brand")),
            "image": r.get("image"),
            "image_thumb": r.get("image_thumb") or r.get("image"),
            "url": r["url"],
        }
