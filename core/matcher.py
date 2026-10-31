"""Fərqli marketlərdəki eyni məhsulu qruplaşdırır (barkod və ya ad+qramaj üzrə)."""
from collections import defaultdict
from .textutil import name_tokens, fold

THRESHOLD = 0.75


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def annotate(products):
    """Hər məhsula group, compare_count, is_cheapest, search əlavə edir. {group: [məhsullar]} qaytarır."""
    n = len(products)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    toks = [name_tokens(p["name"]) for p in products]
    buckets, by_barcode = defaultdict(list), defaultdict(list)
    for i, p in enumerate(products):
        buckets[(p.get("weight_unit"), p.get("weight_value"))].append(i)
        if p.get("barcode"):
            by_barcode[p["barcode"]].append(i)

    for idxs in by_barcode.values():
        for i in idxs[1:]:
            union(idxs[0], i)
    for idxs in buckets.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if products[i]["market"] != products[j]["market"] and _jaccard(toks[i], toks[j]) >= THRESHOLD:
                    union(i, j)

    groups = defaultdict(list)
    for i, p in enumerate(products):
        groups[find(i)].append(p)
    out = {}
    for members in groups.values():
        members.sort(key=lambda x: x["price"])
        key = members[0]["id"]
        low = members[0]["price"]
        multi = len({m["market"] for m in members}) > 1
        for m in members:
            m["group"] = key
            m["compare_count"] = len({x["market"] for x in members})
            m["is_cheapest"] = multi and m["price"] == low
            m["search"] = fold(f'{m["name"]} {m.get("category", "")} {m.get("barcode") or ""} {m.get("code") or ""}')
        out[key] = members
    return out
