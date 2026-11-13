"""Bir kateqoriya səhifəsini yoxlayır. İstifadə:  python -m scraper.debug bazarstore /teze-toyuq"""
import sys

from .markets import MARKETS


def main():
    if len(sys.argv) < 3:
        sys.exit("istifadə: python -m scraper.debug <market> <kateqoriya-yolu>")
    key, path = sys.argv[1], sys.argv[2]
    sc = MARKETS[key]()
    url = sc.page_url(path, 1)
    print("URL:", url)
    html = sc.get(url)
    if not html:
        sys.exit("SƏHİFƏ ALINMADI (blok? python -m scraper.diagnose)")
    open(f"/tmp/debug_{key}.html", "w", encoding="utf-8").write(html)
    items = sc.parse_listing(html, path)
    print(f"HTML {len(html)} simvol → /tmp/debug_{key}.html | tapılan məhsul: {len(items)} | saytın yazdığı say: {sc.expected_count(html)}")
    for i in items[:5]:
        print(" -", i["name"], "|", i["price"], "| köhnə:", i.get("old_price"), "| şəkil:", "var" if i.get("image") else "YOX", "| kod:", i.get("code"))
    if len(items) > 1:
        p2 = sc.get(sc.page_url(path, 2))
        n2 = sc.parse_listing(p2, path) if p2 else []
        fresh = {i["url"] for i in n2} - {i["url"] for i in items}
        print(f"2-ci səhifə: {len(n2)} məhsul, 1-ci səhifədən fərqli: {len(fresh)} (0 olarsa səhifələmə parametri işləmir)")


if __name__ == "__main__":
    main()
