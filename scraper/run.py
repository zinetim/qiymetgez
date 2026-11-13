"""İstifadə:
  python -m scraper.run                         # bütün marketlər
  python -m scraper.run --market bazarstore     # yalnız biri
  python -m scraper.run --max-minutes 120       # hər market üçün vaxt limiti (limit bitəndə nəticə yenə də yazılır)
  python -m scraper.run --regroup               # çəkmədən, yalnız mövcud datada qruplaşdırmanı yenidən hesabla
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from core import matcher, store
from .markets import MARKETS

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "products.json"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", action="append", help="yalnız bu market(lər)")
    ap.add_argument("--details", action="store_true", help="hər məhsulun öz səhifəsini də oxu (barkod/kod). Yavaşdır!")
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--max-minutes", type=float, default=None, help="hər market üçün maksimum dəqiqə")
    ap.add_argument("--no-discover", action="store_true", help="kateqoriya kəşfini söndür (yalnız defolt + config)")
    ap.add_argument("--regroup", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args(argv)

    data = store.load(a.out)
    products = data["products"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    if a.regroup:
        print("qrup sayı (çox marketli):", matcher.assign_groups(products))
        store.save(a.out, {"updated": data.get("updated"), "products": products})
        return

    ok = 0
    for key in (a.market or MARKETS):
        scraper = MARKETS[key](details=a.details, max_pages=a.max_pages)
        try:
            items, complete = scraper.run(max_minutes=a.max_minutes, discover=not a.no_discover)
        except Exception as e:  # bir market çöksə digərləri davam etsin
            print(f"[{key}] XƏTA: {e!r}", file=sys.stderr)
            continue
        if not items:
            print(f"[{key}] heç nə tapılmadı, köhnə data saxlanıldı", file=sys.stderr)
            continue
        before = sum(1 for p in products if p["market"] == key)
        products = store.merge(products, items, key, today)
        multi = matcher.assign_groups(products)
        store.save(a.out, {"updated": now.isoformat(timespec="seconds"), "products": products})
        ok += 1
        print(f"[{key}] {before} → {sum(1 for p in products if p['market'] == key)} məhsul yazıldı "
              f"({'tam' if complete else 'QİSMƏN'}); çox marketli qrup: {multi}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
