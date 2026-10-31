"""403/blok səbəbini tapır. İstifadə:
    python -m scraper.diagnose                       # Bazarstore, /et-toyuq-baliq
    python -m scraper.diagnose https://bazarstore.az/teze-toyuq

Eyni səhifəni 3 variantla yoxlayır və nəticəni müqayisə edir:
  A) bot kimi, əlavə parametrsiz     B) bot kimi, ?pagesize=20 ilə     C) adi brauzer başlıqları ilə
Sonda robots.txt-ni oxuyur (qaydalara uyğunluğu yoxlamaq üçün)."""
import sys
import time

import requests

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
    res["A"] = probe("A  bot, parametrsiz   ", url, "bot"); time.sleep(2)
    res["B"] = probe("B  bot, ?pagesize=20  ", f"{url}{sep}pagesize=20", "bot"); time.sleep(2)
    res["C"] = probe("C  brauzer başlıqları ", url, "browser"); time.sleep(2)

    print("\n--- robots.txt ---")
    base = "/".join(url.split("/")[:3])
    try:
        r = requests.get(base + "/robots.txt", headers=PROFILES["bot"], timeout=15)
        print(f"HTTP {r.status_code}")
        if r.status_code == 200:
            for line in r.text.splitlines()[:40]:
                print("  ", line)
        else:
            print("   robots.txt alınmadı (bu da bloklanma əlaməti ola bilər)")
    except requests.RequestException as e:
        print("   xəta:", e)

    print("\n--- NƏTİCƏ ---")
    ok = lambda k: res.get(k) and res[k][0] == 200
    if ok("A"):
        print("A işləyir: sayt bota icazə verir. Bazarstore botu normal işləməlidir.")
    elif ok("B") and not ok("A"):
        print("Yalnız ?pagesize ilə işləyir (qeyri-adi). extra_params-ı yoxlayın.")
    elif ok("C") and not ok("A"):
        print("Yalnız 'brauzer' başlıqları ilə keçir: sayt 'bot' adlı sorğuları süzür (UA əsaslı filtr).\n"
              "Bu, saytın bot istəməməsi siqnalı ola bilər. Əvvəl istifadə şərtlərinə və robots.txt-ə baxın.\n"
              "Qərar verirsinizsə: GitHub repo → Settings → Variables → SCRAPER_PROFILE = browser.")
    else:
        print("Hər üç variant bloklanıb: sayt (WAF/Cloudflare) bu IP-ni və ya avtomatik girişi qəbul etmir.\n"
              "Bu halda proxy/captcha keçmək tövsiyə olunmur. Daha düzgün yollar:\n"
              "  1) Bazarstore ilə əlaqə: məlumat/qiymət feed-i və ya yazılı icazə istəyin.\n"
              "  2) Kodu başqa şəbəkədən (ev interneti) yoxlayın: Codespaces/GitHub IP-ləri tez-tez bloklanır.\n"
              "  3) Hələlik Bazarstore-u dayandırın (scraper/markets.py-da sətri şərhə alın).")


if __name__ == "__main__":
    main()
