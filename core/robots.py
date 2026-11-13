"""Sadə robots.txt oxuyucusu (Python-un robotparser-i `*` və `$` wildcard-larını tanımır, nopCommerce isə onları işlədir)."""
import re


def parse(text, agent="qiymetgez"):
    """Bizə aid qaydalar siyahısı: [("allow"|"disallow", yol-nümunəsi), ...]."""
    groups, cur = [], None
    for line in (text or "").splitlines():
        line = line.split("#")[0].strip()
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if cur is None or cur["rules"]:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(v.lower())
        elif k in ("allow", "disallow") and cur is not None:
            cur["rules"].append((k, v))
    specific = [g for g in groups if any(a != "*" and a in agent.lower() for a in g["agents"])]
    star = [g for g in groups if "*" in g["agents"]]
    return [r for g in (specific or star) for r in g["rules"]]


def allowed(rules, target):
    """target = yol + sorğu. Ən uzun uyğun qayda qalib gəlir, bərabərlikdə allow."""
    best = None
    for kind, pat in rules:
        if not pat:
            continue
        end = pat.endswith("$")
        rx = re.escape(pat[:-1] if end else pat).replace(r"\*", ".*") + ("$" if end else "")
        if re.match(rx, target):
            if best is None or len(pat) > best[0] or (len(pat) == best[0] and kind == "allow"):
                best = (len(pat), kind)
    return best is None or best[1] == "allow"
