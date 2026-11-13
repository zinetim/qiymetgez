import os
from collections import Counter, defaultdict
from datetime import datetime
from math import ceil
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

from core import matcher, store
from core.textutil import fold
from scraper.markets import MARKETS

BASE = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("DATA_FILE", BASE / "data" / "products.json"))
PER_PAGE = 20

app = Flask(__name__)
_cache = {"mtime": None, "payload": None}

SORTS = {
    "default": ("Tövsiyə: müqayisəli və endirimli", lambda p: (p["compare_count"] < 2, -p["spread"], -(p.get("discount") or 0))),
    "cheap": ("Əvvəl ucuz", lambda p: p["price"]),
    "expensive": ("Əvvəl bahalı", lambda p: -p["price"]),
    "unit": ("1 kq/L qiyməti", lambda p: (p.get("unit_price") is None, p.get("unit_price") or 0)),
    "discount": ("Ən çox endirim", lambda p: -(p.get("discount") or 0)),
    "spread": ("Marketlər arası ən böyük fərq", lambda p: -p["spread"]),
    "az": ("Əlifba (A-Z)", lambda p: fold(p["name"])),
}


def get_data():
    """data/products.json dəyişəndə avtomatik yenidən oxuyur."""
    try:
        mtime = DATA_FILE.stat().st_mtime
    except FileNotFoundError:
        mtime = None
    if _cache["payload"] is None or _cache["mtime"] != mtime:
        raw = store.load(DATA_FILE)
        products = raw["products"]
        names = {k: c.market_name for k, c in MARKETS.items()}
        for p in products:
            p["market_name"] = names.get(p["market"]) or p.get("market_name") or p["market"]
        groups = matcher.build(products)
        counts = Counter(p["market"] for p in products)
        markets = [{"key": k, "name": c.market_name, "count": counts.get(k, 0)} for k, c in MARKETS.items()]
        markets += [{"key": k, "name": next(p["market_name"] for p in products if p["market"] == k), "count": n}
                    for k, n in counts.items() if k not in MARKETS]
        cats = defaultdict(Counter)
        for p in products:
            if p.get("category"):
                cats[p["market"]][p["category"]] += 1
        _cache["payload"] = {
            "updated": raw.get("updated"),
            "products": products,
            "by_id": {p["id"]: p for p in products},
            "groups": groups,
            "markets": markets,
            "cat_groups": [(m["name"], sorted(cats[m["key"]].items())) for m in markets if cats[m["key"]]],
            "multi": sum(1 for g in groups.values() if g[0]["compare_count"] > 1),
        }
        _cache["mtime"] = mtime
    return _cache["payload"]


@app.template_filter("money")
def money(v):
    return f"{v:.2f}" if v is not None else "-"


@app.template_filter("dt")
def dt(v):
    try:
        return datetime.fromisoformat(v).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return "-"


def page_window(page, pages, w=2):
    """[1, None, 7, 8, 9, 10, 11, None, 850]: None = '…'."""
    nums = sorted({1, pages, *range(max(1, page - w), min(pages, page + w) + 1)})
    out, prev = [], 0
    for n in nums:
        if n - prev > 1:
            out.append(None)
        out.append(n)
        prev = n
    return out


def spark(history, w=260, h=56, pad=6):
    if len(history) < 2:
        return None
    vals = [x[1] for x in history]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = [f"{pad + i * (w - 2 * pad) / (len(vals) - 1):.1f},{h - pad - (v - lo) * (h - 2 * pad) / span:.1f}"
           for i, v in enumerate(vals)]
    return {"points": " ".join(pts), "w": w, "h": h, "lo": lo, "hi": hi}


def filter_products(args):
    d = get_data()
    q, cat, market = fold(args.get("q", "")), args.get("cat", ""), args.get("market", "")
    only_cmp = args.get("cmp") == "1"
    toks = q.split()
    items = [p for p in d["products"]
             if (not toks or all(t in p["search"] for t in toks))
             and (not cat or p.get("category") == cat)
             and (not market or p["market"] == market)
             and (not only_cmp or p["compare_count"] > 1)]
    sort = args.get("sort", "default")
    items.sort(key=SORTS.get(sort, SORTS["default"])[1])
    return items


@app.route("/")
def index():
    d = get_data()
    args = request.args.to_dict()
    items = filter_products(args)
    pages = max(1, ceil(len(items) / PER_PAGE))
    try:
        page = min(max(1, int(args.get("page", 1))), pages)
    except ValueError:
        page = 1
    return render_template(
        "index.html", products=items[(page - 1) * PER_PAGE: page * PER_PAGE], total=len(items),
        page=page, pages=pages, window=page_window(page, pages), args=args, sorts=SORTS, d=d,
        deals=sum(1 for p in d["products"] if p.get("discount")),
    )


@app.route("/m/<pid>")
def product(pid):
    d = get_data()
    p = d["by_id"].get(pid)
    if not p:
        abort(404)
    same = d["groups"][p["g"]]
    related = [x for x in d["products"] if x.get("category") == p.get("category") and x["id"] != pid and x["market"] == p["market"]][:4]
    return render_template("product.html", p=p, same=same, related=related, spark=spark(p.get("history", [])), d=d)


@app.route("/api/products")
def api_products():
    items = filter_products(request.args)
    try:
        limit = min(int(request.args.get("limit", 100)), 500)
    except ValueError:
        limit = 100
    slim = [{k: v for k, v in p.items() if k not in ("search", "history", "others")} for p in items[:limit]]
    return jsonify({"updated": get_data()["updated"], "count": len(items), "products": slim})


@app.route("/healthz")
def healthz():
    return "ok"


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", d=get_data()), 404


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
