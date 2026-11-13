"""Kateqoriya kəşfini göstərir (heç nə yazmır):
    python -m scraper.discover bazarstore
    python -m scraper.discover araz --write      # tapılanları config/categories_araz.txt-ə əlavə edir"""
import sys

from .base import CONFIG_DIR, norm_path
from .markets import MARKETS


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MARKETS:
        sys.exit(f"istifadə: python -m scraper.discover <{'|'.join(MARKETS)}> [--write]")
    sc = MARKETS[sys.argv[1]]()
    cats = sc.get_categories(discover=True)
    print(f"\nCƏMİ {len(cats)} kateqoriya ({sc.requests_made} sorğu):")
    for n, p, full in cats:
        print(f"  {'[TAM] ' if full else '       '}{n}  →  {p}")
    if "--write" in sys.argv:
        f = CONFIG_DIR / f"categories_{sc.market}.txt"
        have = {norm_path(p) for _, p in sc.manual_categories()}
        new = [(n, p) for n, p, _ in cats if norm_path(p) not in have]
        with f.open("a", encoding="utf-8") as fh:
            for n, p in new:
                fh.write(f"{n} | {p}\n")
        print(f"\n{len(new)} yeni kateqoriya {f} faylına yazıldı")
    if len(cats) <= 1 and sc.market == "araz":
        print("\nAraz menyusu JS ilə yüklənir. README-dəki brauzer konsolu üsulu ilə siyahını config/categories_araz.txt-ə yapışdırın.")


if __name__ == "__main__":
    main()
