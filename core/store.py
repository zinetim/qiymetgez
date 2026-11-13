"""Saxlama: data/products.json. Hər məhsul ayrı sətirdə (git fərqləri kiçik olsun), id üzrə sıralı."""
import json
import os
import tempfile
from datetime import date
from pathlib import Path

HISTORY_LIMIT = 60
KEEP_DAYS = 7   # bu qədər gün görünməyən məhsul silinir (müvəqqəti xəta bütün datanı silməsin)


def load(path):
    p = Path(path)
    if not p.exists():
        return {"updated": None, "products": []}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    products = sorted(data["products"], key=lambda x: x["id"])
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write('{"updated":' + json.dumps(data.get("updated")) + ',"products":[\n')
        f.write(",\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in products))
        f.write("\n]}\n")
    os.replace(tmp, p)


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def merge(old_products, new_products, market, today, keep_days=KEEP_DAYS):
    """Bu marketin yeni məhsullarını yazır (tarixçə saxlanır). Görünməyənlər keep_days gün saxlanır, sonra silinir.
    Digər marketlərə toxunmur."""
    old_by_id = {p["id"]: p for p in old_products}
    new_ids = {p["id"] for p in new_products}
    out = [p for p in old_products if p["market"] != market]
    for p in old_products:
        if p["market"] == market and p["id"] not in new_ids:
            seen = p.get("last_seen") or p.get("first_seen") or today
            if _days(seen, today) <= keep_days:
                p["last_seen"] = seen
                out.append(p)
    for p in new_products:
        prev = old_by_id.get(p["id"])
        hist = [list(h) for h in prev.get("history", [])] if prev else []
        if not hist or hist[-1][1] != p["price"]:
            if hist and hist[-1][0] == today:
                hist[-1][1] = p["price"]
            else:
                hist.append([today, p["price"]])
        p["history"] = hist[-HISTORY_LIMIT:]
        p["first_seen"] = (prev or {}).get("first_seen", today)
        p["last_seen"] = today
        out.append(p)
    return out
