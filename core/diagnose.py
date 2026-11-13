"""403/blok səbəbini tapır. İstifadə:
    python -m scraper.diagnose                       # Bazarstore, /et-toyuq-baliq
    python -m scraper.diagnose https://bazarstore.az/teze-toyuq

Eyni səhifəni 4 variantla yoxlayır:
  A) bot, parametrsiz   B) bot + ?pagesize=20   C) adi brauzer başlıqları   D) 'open' (brauzer formatı + açıq kimlik)
Sonra robots.txt-i oxuyur və botun kateqoriyalarının icazəli olub-olmadığını göstərir."""
import sys
import time

import requests

from core import robots

from .base import PROFILES

URL = "https://bazarstore.az/et-toyuq-baliq"


def probe(label, url, profile):
    try:
        r = requests.get(url, headers=PROFILES[profile], timeout=25)
    except requests.RequestException as e:
        print(f"{label}: ŞƏBƏKƏ XƏTASI {e}")
        return None
    h = r.headers
    has_products = "product-item" in r.text
    print(f"{label}: HTTP {r.status_code} | server={h.get('server')} | cf-ray={h.get('cf-ray')} | "
          f"cf-mitigated={h.get('cf-mitigated')} | {len(r.text)} simvol | məhsul-bloku={'VAR' if has_products else 'yox'}")
    if r.status_code != 200:
        print(f"    cavab başlanğıcı: {r.text[:140]!r}")
    return r.status_code, has_products


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    sep = "&" if "?" in url else "?"
    res = {}
    res["A"] = probe("A  bot, parametrsiz    ", url, "bot"); time.sleep(2)
    res["B"] = probe("B  bot, ?pagesize=20   ", f"{url}{sep}pagesize=20", "bot"); time.sleep(2)
    res["C"] = probe("C  brauzer başlıqları  ", url, "browser"); time.sleep(2)
    res["D"] = probe("D  'open' (açıq kimlik)", url, "open"); time.sleep(2)

    print("\n--- robots.txt ---")
    base = "/".join(url.split("/")[:3])
    rules = None
    for prof in ("open", "browser", "bot"):          # hansı profil keçirsə, onunla oxu
        try:
            r = requests.get(base + "/robots.txt", headers=PROFILES[prof], timeout=15)
        except requests.RequestException as e:
            print(f"   [{prof}] xəta: {e}")
            continue
        print(f"   [{prof}] HTTP {r.status_code}")
        if r.status_code == 200:
            for line in r.text.splitlines()[:60]:
                print("     ", line)
            rules = robots.parse(r.text)
            break
        time.sleep(1)
    if rules is not None:
        from .bazarstore import BazarstoreScraper
        print("\n   Botun kateqoriyaları robots.txt-ə görə:")
        for name, path in BazarstoreScraper.categories:
            for target in (path, path + "?pagesize=20&pagenumber=2"):
                print(f"     {'İCAZƏ VAR ' if robots.allowed(rules, target) else 'QADAĞANDIR'}  {target}")

    print("\n--- NƏTİCƏ ---")
    ok = lambda k: res.get(k) and res[k][0] == 200
    if ok("A"):
        print("A işləyir: sayt bota icazə verir. Bazarstore botu normal işləməlidir.")
    elif ok("D"):
        print("D ('open' profil) işləyir: sayt yalnız 'bot' sözü olan UA-nı süzür. 'open' profil brauzer formatındadır,\n"
              "amma 'Qiymetgez/1.0 (+repo ünvanı)' ilə kim olduğunuzu açıq göstərir. Bazarstore botu bunu defolt işlədir.")
    elif ok("C"):
        print("Yalnız 'browser' profili keçir. Bu, saytın avtomatik girişi istəməməsi siqnalı ola bilər:\n"
              "əvvəl istifadə şərtlərinə və robots.txt-ə baxın, mümkünsə Bazarstore ilə əlaqə saxlayın.\n"
              "Qərar verirsinizsə: GitHub → Settings → Secrets and variables → Actions → Variables → SCRAPER_PROFILE = browser.")
    else:
        print("Hər variant bloklanıb: sayt (WAF/Cloudflare) bu IP-ni və ya avtomatik girişi qəbul etmir.\n"
              "Proxy/captcha keçməyə çalışmayın. Daha düzgün yollar:\n"
              "  1) Bazarstore ilə əlaqə: məlumat feed-i və ya yazılı icazə istəyin.\n"
              "  2) Kodu başqa şəbəkədən (ev interneti) yoxlayın.\n"
              "  3) Hələlik Bazarstore-u dayandırın (scraper/markets.py-da sətri şərhə alın).")


if __name__ == "__main__":
    main()
