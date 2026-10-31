"""İstifadə:  python -m scraper.run [--market araz] [--details] [--max-pages 6]"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from core import store
from .markets import MARKETS

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "products.json"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", action="append", help="yalnız bu market(lər)")
    ap.add_argument("--details", action="store_true", help="hər məhsulun öz səhifəsini də oxu (kod/barkod)")
    ap.add_argument("--max-pages", type=int, default=None, help="bir kateqoriyada maks. səhifə (defolt: marketin öz limiti)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args(argv)

    data = store.load(a.out)
    products = data["products"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    ok = 0

    for key in (a.market or MARKETS):
        scraper = MARKETS[key](details=a.details, max_pages=a.max_pages)
        try:
            items = scraper.run()
        except Exception as e:  # bir market çöksə digərləri davam etsin
            print(f"[{key}] XƏTA: {e}", file=sys.stderr)
            continue
        if not items:
            print(f"[{key}] heç nə tapılmadı, köhnə data saxlanıldı", file=sys.stderr)
            continue
        products = store.merge(products, items, key, today)
        ok += 1
        print(f"[{key}] {len(items)} məhsul yazıldı")

    if not ok:
        sys.exit(1)  # heç nə yazılmayıb, GitHub Actions qırmızı olsun
    store.save(a.out, {"updated": now.isoformat(timespec="seconds"), "products": products})


if __name__ == "__main__":
    main()
