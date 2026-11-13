"""403/blok səbəbini tapır. İstifadə:
    python -m scraper.diagnose [url]
A) bot  B) bot + ?pagesize=20  C) adi brauzer  D) 'open' (brauzer formatı + açıq kimlik); sonra robots.txt."""
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
    has = "product-item" in r.text
    print(f"{label}: HTTP {r.status_code} | server={h.get('server')} | cf-ray={h.get('cf-ray')} | "
          f"{len(r.text)} simvol | məhsul-bloku={'VAR' if has else 'yox'}")
    if r.status_code != 200:
        print(f"    cavab başlanğıcı: {r.text[:140]!r}")
    return r.status_code, has


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
    for prof in ("open", "browser", "bot"):
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
        from .bazarstore import TOP_LEVEL
        print("\n   Üst kateqoriyalar robots.txt-ə görə:")
        for name, path in TOP_LEVEL:
            for target in (path, path + "?pagesize=20&pagenumber=2"):
                print(f"     {'İCAZƏ VAR ' if robots.allowed(rules, target) else 'QADAĞANDIR'}  {target}")

    print("\n--- NƏTİCƏ ---")
    ok = lambda k: res.get(k) and res[k][0] == 200
    if ok("A"):
        print("A işləyir: sayt bota icazə verir.")
    elif ok("D"):
        print("D ('open') işləyir: sayt yalnız 'bot' sözü olan UA-nı süzür. Bazarstore botu 'open' profili ilə işləyir.")
    elif ok("C"):
        print("Yalnız 'browser' profili keçir. İstifadə şərtlərinə və robots.txt-ə baxın, mümkünsə sayt ilə əlaqə saxlayın.\n"
              "Qərar verirsinizsə: GitHub → Settings → Secrets and variables → Actions → Variables → SCRAPER_PROFILE = browser.")
    else:
        print("Hər variant bloklanıb. Proxy/captcha keçməyin: sayt ilə əlaqə saxlayıb feed və ya icazə istəyin.")


if __name__ == "__main__":
    main()
