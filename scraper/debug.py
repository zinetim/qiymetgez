"""Bir kateqoriya səhifəsini yoxlayır: nə tapıldı, nə tapılmadı.
İstifadə:  python -m scraper.debug bazarstore /teze-toyuq
HTML /tmp/debug_<market>.html faylına yazılır (selektorlar uyğun gəlmirsə baxmaq üçün)."""
import sys

from .markets import MARKETS


def main():
    if len(sys.argv) < 3:
        sys.exit("istifadə: python -m scraper.debug <market> <kateqoriya-yolu>")
    key, path = sys.argv[1], sys.argv[2]
    sc = MARKETS[key](log=print)
    url = sc.page_url(path, 1)
    print("URL:", url)
    html = sc.get(url)
    if not html:
        sys.exit("SƏHİFƏ ALINMADI (bloklanıb ola bilər: şəbəkə/IP, 403/429 yoxlayın)")
    out = f"/tmp/debug_{key}.html"
    open(out, "w", encoding="utf-8").write(html)
    print(f"HTML: {len(html)} simvol → {out}")
    items = sc.parse_listing(html, path)
    print(f"Tapılan məhsul: {len(items)}")
    for i in items[:5]:
        print(" -", i["name"], "|", i["price"], "| köhnə:", i.get("old_price"), "| şəkil:", "var" if i.get("image") else "YOX", "| kod:", i.get("code"))
    if not items:
        print("Heç nə tapılmadı. Yoxlayın: grep -c 'product-item' " + out)


if __name__ == "__main__":
    main()
