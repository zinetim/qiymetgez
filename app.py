import os
from collections import Counter
from datetime import datetime
from math import ceil
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, url_for

from core import matcher, store
from core.textutil import fold

BASE = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("DATA_FILE", BASE / "data" / "products.json"))
PER_PAGE = 20

app = Flask(__name__)
_cache = {"mtime": None, "payload": None}

SORTS = {
    "default": ("Tövsiyə olunan", None),
    "cheap": ("Əvvəl ucuz", lambda p: p["price"]),
    "expensive": ("Əvvəl bahalı", lambda p: -p["price"]),
    "unit": ("1 kq/L qiyməti", lambda p: (p.get("unit_price") is None, p.get("unit_price") or 0)),
    "discount": ("Ən çox endirim", lambda p: -(p.get("discount") or 0)),
    "az": ("Əlifba (A-Z)", lambda p: fold(p["name"])),
}


def get_data():
    """data/products.json dəyişəndə avtomatik yenidən oxuyur (redeploy olmadan da işləyir)."""
    try:
        mtime = DATA_FILE.stat().st_mtime
    except FileNotFoundError:
        mtime = None
    if _cache["payload"] is None or _cache["mtime"] != mtime:
        raw = store.load(DATA_FILE)
        products = raw["products"]
        groups = matcher.annotate(products)
        _cache["payload"] = {
            "updated": raw.get("updated"),
            "products": products,
            "by_id": {p["id"]: p for p in products},
            "groups": groups,
            "markets": sorted({(p["market"], p["market_name"]) for p in products}),
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


def spark(history, w=260, h=56, pad=6):
    """Qiymət tarixçəsi üçün SVG xətti (nöqtələr sətri)."""
    if len(history) < 2:
        return None
    vals = [x[1] for x in history]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = pad + i * (w - 2 * pad) / (len(vals) - 1)
        y = h - pad - (v - lo) * (h - 2 * pad) / span
        pts.append(f"{x:.1f},{y:.1f}")
    return {"points": " ".join(pts), "w": w, "h": h, "lo": lo, "hi": hi}


def filter_products(args):
    d = get_data()
    q, cat, market = fold(args.get("q", "")), args.get("cat", ""), args.get("market", "")
    items = [p for p in d["products"]
             if (not q or all(t in p["search"] for t in q.split()))
             and (not cat or p.get("category") == cat)
             and (not market or p["market"] == market)]
    sort = args.get("sort", "default")
    if sort in SORTS and SORTS[sort][1]:
        items.sort(key=SORTS[sort][1])
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
    cats = Counter(p["category"] for p in d["products"] if p.get("category"))
    return render_template(
        "index.html", products=items[(page - 1) * PER_PAGE: page * PER_PAGE], total=len(items),
        page=page, pages=pages, args=args, cats=sorted(cats.items()), sorts=SORTS,
        d=d, deals=sum(1 for p in d["products"] if p.get("discount")),
    )


@app.route("/m/<pid>")
def product(pid):
    d = get_data()
    p = d["by_id"].get(pid)
    if not p:
        abort(404)
    same = d["groups"][p["group"]]
    related = [x for x in d["products"] if x.get("category") == p.get("category") and x["id"] != pid][:4]
    return render_template("product.html", p=p, same=same, related=related, spark=spark(p.get("history", [])), d=d)


@app.route("/api/products")
def api_products():
    items = filter_products(request.args)
    limit = min(int(request.args.get("limit", 100)), 500)
    slim = [{k: v for k, v in p.items() if k not in ("search", "history")} for p in items[:limit]]
    return jsonify({"updated": get_data()["updated"], "count": len(items), "products": slim})


@app.route("/healthz")
def healthz():
    return "ok"


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html", d=get_data()), 404


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
