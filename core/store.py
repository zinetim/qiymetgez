"""JSON saxlama + qiymət tarixçəsi."""
import json
import os
import tempfile
from pathlib import Path

HISTORY_LIMIT = 90


def load(path):
    p = Path(path)
    if not p.exists():
        return {"updated": None, "products": []}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def merge(old_products, new_products, market, today):
    """Bu marketin köhnə məhsullarını yenisi ilə əvəz edir, tarixçəni saxlayır, digər marketlərə toxunmur."""
    old_by_id = {p["id"]: p for p in old_products}
    merged = [p for p in old_products if p["market"] != market]
    for p in new_products:
        prev = old_by_id.get(p["id"])
        hist = [list(h) for h in prev.get("history", [])] if prev else []
        if not hist or hist[-1][1] != p["price"] or hist[-1][0] != today:
            if hist and hist[-1][0] == today:
                hist[-1][1] = p["price"]
            else:
                hist.append([today, p["price"]])
        p["history"] = hist[-HISTORY_LIMIT:]
        p["first_seen"] = prev.get("first_seen", today) if prev else today
        merged.append(p)
    return merged
