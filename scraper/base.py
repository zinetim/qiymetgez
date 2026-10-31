"""Bütün market botları üçün ümumi baza: sorğu, təkrar cəhd, səhifələmə, məhsul formatı."""
import hashlib
import random
import re
import time
from urllib.parse import urlencode
from datetime import datetime, timezone

import requests

from core.textutil import parse_weight, unit_price

UA = ("Mozilla/5.0 (compatible; QiymetgezBot/1.0; +https://github.com/YOUR_USER/qiymetgez) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")


class BaseScraper:
    market = ""            # qısa açar: "araz"
    market_name = ""       # görünən ad
    base_url = ""
    categories = []        # [(kateqoriya adı, yol)]
    delay = (0.8, 1.6)     # sorğular arası fasilə (saniyə), saytı yormamaq üçün
    page_param = "page"    # səhifələmə parametri (nopCommerce: "pagenumber")
    extra_params = {}      # hər sorğuya əlavə parametrlər (məs. {"pagesize": "20"})

    def __init__(self, details=False, max_pages=10, log=print):
        self.details, self.max_pages, self.log = details, max_pages, log
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "az,en;q=0.8"})

    # ---- şəbəkə ----
    def get(self, url, retries=3):
        last = None
        for i in range(retries):
            try:
                r = self.s.get(url, timeout=25)
                if r.status_code == 404:
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

    def page_url(self, path, page):
        params = dict(self.extra_params)
        if page > 1:
            params[self.page_param] = page
        return self.base_url + path + (("?" + urlencode(params)) if params else "")

    # ---- hər market özü yazır ----
    def parse_listing(self, html, category):
        raise NotImplementedError

    def parse_detail(self, html):
        return {}

    # ---- ümumi axın ----
    def run(self):
        raw, seen = [], set()
        for cat_name, path in self.categories:
            self.log(f"[{self.market}] {cat_name}")
            for page in range(1, self.max_pages + 1):
                html = self.get(self.page_url(path, page))
                if not html:
                    break
                items = self.parse_listing(html, cat_name)
                fresh = [i for i in items if i["url"] not in seen]
                self.log(f"  səhifə {page}: {len(items)} məhsul, {len(fresh)} yeni")
                if not fresh:
                    break
                seen.update(i["url"] for i in fresh)
                raw.extend(fresh)
        if self.details:
            for n, item in enumerate(raw, 1):
                html = self.get(item["url"])
                if html:
                    item.update({k: v for k, v in self.parse_detail(html).items() if v})
                if n % 10 == 0:
                    self.log(f"  detallar: {n}/{len(raw)}")
        return [self.finish(r) for r in raw if r.get("price")]

    def finish(self, r):
        value, unit, label = parse_weight(r["name"])
        up, up_label = unit_price(r["price"], value, unit)
        old = r.get("old_price")
        if old and old <= r["price"]:
            old = None
        discount = r.get("discount") or (round((1 - r["price"] / old) * 100) if old else None)
        code = str(r.get("code") or r["url"].rstrip("/").split("/")[-1].split("-")[-1])
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", code):  # URL-də təhlükəsiz id
            code = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        return {
            "id": f"{self.market}-{code}",
            "market": self.market,
            "market_name": self.market_name,
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
            "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
