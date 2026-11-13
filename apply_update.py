"""Yeniləmə: robots.txt dəstəyi + 'open' profil (Bazarstore üçün) + diaqnostika D variantı.
Repo kökündə işlədin:  python apply_update.py
Təkrar işlətmək təhlükəsizdir (artıq tətbiq olunubsa keçir)."""
import pathlib
import sys


def patch(path, edits, marker):
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"XƏTA: {path} tapılmadı. Skripti repo kökündə (app.py olan qovluqda) işlədin.")
    s = p.read_text(encoding="utf-8")
    if marker in s:
        print(f"keçildi (artıq tətbiq olunub): {path}")
        return
    for old, new in edits:
        if old not in s:
            sys.exit(f"XƏTA: {path} içində gözlənilən mətn tapılmadı:\n---\n{old[:200]}\n---\nFayl dəyişib. Heç nə yazılmadı bu fayla.")
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"yeniləndi: {path}")


# ---------------- scraper/base.py ----------------
patch("scraper/base.py", [
    ("import requests\n\nfrom core.textutil", "import requests\n\nfrom core import robots\nfrom core.textutil"),
    ("github.com/YOUR_USER/qiymetgez", "github.com/zinetim/qiymetgez"),
    ('''PROFILES = {
    "bot": {"User-Agent": UA, "Accept-Language": "az,en;q=0.8"},''', '''PROFILES = {
    "bot": {"User-Agent": UA, "Accept-Language": "az,en;q=0.8"},
    # "open": brauzer formatında, amma "bot" sözü olmadan və əlaqə ünvanı ilə: sayt sahibi kim olduğumuzu görə bilir
    "open": {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36 Qiymetgez/1.0 (+https://github.com/zinetim/qiymetgez; qiymet muqayisesi)"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "az,en;q=0.8",
    },'''),
    ('''    max_pages = 10         # bir kateqoriyada maksimum səhifə (market özü artıra bilər)
''', '''    max_pages = 10         # bir kateqoriyada maksimum səhifə (market özü artıra bilər)
    profile = "bot"        # sorğu başlıqları profili (PROFILES); SCRAPER_PROFILE mühit dəyişəni üstün gəlir
'''),
    ('''self.s.headers.update(PROFILES.get(os.environ.get("SCRAPER_PROFILE", "bot"), PROFILES["bot"]))''',
     '''name = os.environ.get("SCRAPER_PROFILE") or self.profile
        self.s.headers.update(PROFILES.get(name, PROFILES["bot"]))
        self._rules = None'''),
    ('''    def page_url(self, path, page):''', '''    def robots_ok(self, path_and_query):
        """Saytın robots.txt qaydalarına uyğunluq. robots.txt alınmasa xəbərdarlıq edib davam edir."""
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

    def page_url(self, path, page):'''),
    ('''                html = self.get(self.page_url(path, page))
                if not html:
                    break''', '''                url = self.page_url(path, page)
                if not self.robots_ok(url[len(self.base_url):]):
                    self.log(f"  ✗ robots.txt qadağan edir, keçildi: {url}")
                    break
                html = self.get(url)
                if not html:
                    break'''),
], marker="def robots_ok")

# ---------------- scraper/bazarstore.py ----------------
patch("scraper/bazarstore.py", [
    ('    page_param = "pagenumber"',
     '    profile = "open"   # Cloudflare "bot" adlı UA-nı süzür (diaqnostika ilə təsdiqlənib)\n    page_param = "pagenumber"'),
], marker='profile = "open"')

# ---------------- tests/test_core.py ----------------
patch("tests/test_core.py", [
    ('''    monkeypatch.setenv("SCRAPER_PROFILE", "")
    assert "QiymetgezBot" in BazarstoreScraper().s.headers["User-Agent"]''', '''    monkeypatch.setenv("SCRAPER_PROFILE", "")
    ua = BazarstoreScraper().s.headers["User-Agent"]          # Bazarstore defolt = "open"
    assert "bot" not in ua.lower() and "Qiymetgez/1.0" in ua and "zinetim" in ua
    from scraper.araz import ArazScraper
    assert "QiymetgezBot" in ArazScraper().s.headers["User-Agent"]   # Araz defolt = "bot"'''),
], marker="ua = BazarstoreScraper().s.headers")
p = pathlib.Path("tests/test_core.py")
if "test_robots_wildcards" not in p.read_text(encoding="utf-8"):
    with p.open("a", encoding="utf-8") as f:
        f.write('''

def test_robots_wildcards():
    from core import robots
    txt = """User-agent: *
Disallow: /cart
Disallow: /*?*returnUrl=
Disallow: /search
Allow: /search/autocomplete$
User-agent: badbot
Disallow: /
"""
    r = robots.parse(txt)
    assert robots.allowed(r, "/teze-toyuq?pagesize=20&pagenumber=2")
    assert not robots.allowed(r, "/cart")
    assert not robots.allowed(r, "/login?returnUrl=%2Fteze-toyuq")
    assert not robots.allowed(r, "/search?q=sud")
    assert robots.allowed(r, "/search/autocomplete")        # Allow daha uzundur
    assert robots.allowed(robots.parse("User-agent: *\\nDisallow:\\n"), "/hər-şey")
    assert not robots.allowed(robots.parse("User-agent: *\\nDisallow: /\\n"), "/x")


def test_scraper_skips_disallowed_category(monkeypatch):
    from scraper.bazarstore import BazarstoreScraper

    class R:
        status_code = 200
        text = "User-agent: *\\nDisallow: /et-toyuq-baliq\\n"

    s = BazarstoreScraper(log=lambda *_: None)
    monkeypatch.setattr(s.s, "get", lambda *a, **k: R())
    assert s.robots_ok("/teze-toyuq") and not s.robots_ok("/et-toyuq-baliq?pagesize=20")
''')
    print("yeniləndi: tests/test_core.py (yeni testlər əlavə olundu)")

# ---------------- README ----------------
p = pathlib.Path("README.md")
if p.exists() and "Cloudflare \"bot\" filtri" not in p.read_text(encoding="utf-8"):
    with p.open("a", encoding="utf-8") as f:
        f.write('''
## Bazarstore: Cloudflare "bot" filtri (diaqnostika nəticəsi)

`python -m scraper.diagnose` nəticəsi (Codespaces-dən): bot kimi sorğu **403** (Cloudflare), eyni IP-dən brauzer başlıqları ilə **200**.
Deməli IP bloklanmayıb, sayt yalnız adında "bot" olan User-Agent-i süzür.

| Profil | User-Agent | Haraya |
|---|---|---|
| `bot` | `...QiymetgezBot/1.0 (+repo)` | Araz (defolt) |
| `open` | brauzer formatı + `Qiymetgez/1.0 (+repo)`, "bot" sözü yoxdur | Bazarstore (defolt) |
| `browser` | adi Chrome, kimlik yoxdur | yalnız əl ilə seçilir |

`open` işləməsə, `SCRAPER_PROFILE=browser` təyin edin (GitHub: Settings → Secrets and variables → Actions → Variables).
Bot hər marketin `robots.txt` faylını oxuyur və qadağan olunmuş yolları keçir (`*` və `$` dəstəklənir).
''')
    print("yeniləndi: README.md")
print("\nHazırdır. Yoxlayın:  python -m pytest -q  və  python -m scraper.diagnose")
