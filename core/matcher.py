"""Fərqli marketlərdəki eyni məhsulu qruplaşdırır (barkod və ya ad + qramaj).

assign_groups(): ağır iş, botun içində bir dəfə işləyir və hər məhsula `g` (qrup açarı) yazır.
build():         yüngül, sayt başlayanda `g` əsasında müqayisə sahələrini doldurur.
Minlərlə məhsul üçün tərs indeks (token → məhsullar) istifadə olunur, O(n²) müqayisə yoxdur."""
import math
from collections import Counter, defaultdict

from .textutil import fold, name_tokens

THRESH = 0.75            # qramajı məlum olanlar üçün Jaccard həddi
THRESH_NOWEIGHT = 0.9    # qramajsız məhsullar üçün daha sərt
MAX_POSTING = 6000       # təhlükəsizlik: bir (qramaj, söz) siyahısı bundan böyükdürsə atılır


def assign_groups(products):
    """Prefix-filter: hər məhsul yalnız ən NADİR sözləri ilə (df artan sıra) indeksləşir. Jaccard >= THRESH olan
    iki məhsul mütləq ortaq prefix sözünə malikdir, yəni heç bir düzgün uyğunluq qaçırılmır, amma müqayisələr
    minlərlə yox, onlarla olur. Namizədlər həm də eyni qramaj bucket-i ilə məhdudlaşır."""
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
    wk = [(p.get("weight_unit"), p.get("weight_value")) for p in products]
    mk = [p["market"] for p in products]

    bar = defaultdict(list)
    for i, p in enumerate(products):
        if p.get("barcode"):
            bar[p["barcode"]].append(i)
    for ids in bar.values():
        for i in ids[1:]:
            union(ids[0], i)

    df = Counter(t for ts in toks for t in ts)
    ordered = [sorted(ts, key=lambda t: (df[t], t)) for ts in toks]

    def prefix_len(size):
        return size - math.ceil(THRESH * size - 1e-9) + 1

    index = defaultdict(list)
    for i, od in enumerate(ordered):
        for t in od[:prefix_len(len(od))]:
            index[(wk[i], t)].append(i)

    for i, od in enumerate(ordered):
        if not od:
            continue
        has_w = wk[i][0] is not None
        th = THRESH if has_w else THRESH_NOWEIGHT
        cand = set()
        for t in od[:prefix_len(len(od))]:
            lst = index[(wk[i], t)]
            if len(lst) <= MAX_POSTING:
                cand.update(j for j in lst if j > i)
        ti = toks[i]
        for j in cand:
            if mk[j] == mk[i] or find(i) == find(j):
                continue
            tj = toks[j]
            if not has_w and min(len(ti), len(tj)) < 2:
                continue
            if len(ti & tj) / len(ti | tj) >= th:
                union(i, j)

    roots = defaultdict(list)
    for i in range(n):
        roots[find(i)].append(i)
    multi = 0
    for idxs in roots.values():
        key = min(products[i]["id"] for i in idxs)
        for i in idxs:
            products[i]["g"] = key
        if len({mk[i] for i in idxs}) > 1:
            multi += 1
    return multi


def build(products):
    """{qrup: [məhsullar (ucuzdan bahaya)]} qaytarır və hər məhsula müqayisə sahələri yazır."""
    if any("g" not in p for p in products):
        assign_groups(products)
    groups = defaultdict(list)
    for p in products:
        groups[p["g"]].append(p)
    for members in groups.values():
        members.sort(key=lambda x: x["price"])
        lo, hi = members[0]["price"], members[-1]["price"]
        mkts = {m["market"] for m in members}
        for m in members:
            m["compare_count"] = len(mkts)
            m["spread"] = round(hi - lo, 2) if len(mkts) > 1 else 0
            m["is_cheapest"] = len(mkts) > 1 and m["price"] == lo
            m["others"] = [{"id": o["id"], "market": o["market"], "market_name": o.get("market_name") or o["market"],
                            "price": o["price"]} for o in members if o["market"] != m["market"]]
    for p in products:
        p["search"] = fold(f'{p["name"]} {p.get("category") or ""} {p.get("barcode") or ""} {p.get("code") or ""}')
    return groups
