"""Ad təmizləmə, qramaj çıxarma və müqayisə üçün normallaşdırma."""
import re

_MAP = str.maketrans({
    "ə": "e", "Ə": "e", "ı": "i", "İ": "i", "I": "i", "ö": "o", "Ö": "o",
    "ü": "u", "Ü": "u", "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g",
})

WEIGHT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(kq|kg|qr|gr|g|ml|lt|l|litr|eded|ed|ad)\b", re.I
)
STOP = {"kq", "kg", "qr", "gr", "g", "ml", "l", "aciq", "teze", "paket",
        "soyudulmus", "ed", "eded", "ad", "butov"}


def fold(s: str) -> str:
    """Azərbaycan hərflərini latın əsaslı sadə formaya salır, kiçildir."""
    return re.sub(r"\s+", " ", (s or "").translate(_MAP).lower()).strip()


def _n(x: float) -> str:
    return f"{round(x, 3):g}"


def parse_weight(name: str):
    """(dəyər, vahid, etiket) qaytarır. Vahid: kg | l | ad. Rəqəm yoxdursa 'kq' = çəkili mal."""
    f = fold(name)
    m = WEIGHT_RE.search(f)
    if m:
        n = float(m.group(1).replace(",", "."))
        u = m.group(2)
        if u in ("kq", "kg"):
            return round(n, 4), "kg", (f"{_n(n)} kq" if n >= 1 else f"{_n(n * 1000)} qr")
        if u in ("qr", "gr", "g"):
            kg = n / 1000
            return round(kg, 4), "kg", (f"{_n(kg)} kq" if kg >= 1 else f"{_n(n)} qr")
        if u == "ml":
            l = n / 1000
            return round(l, 4), "l", (f"{_n(l)} L" if l >= 1 else f"{_n(n)} ml")
        if u in ("l", "lt", "litr"):
            return round(n, 4), "l", (f"{_n(n)} L" if n >= 1 else f"{_n(n * 1000)} ml")
        return round(n, 4), "ad", f"{_n(n)} ədəd"
    if re.search(r"kq\b", f):
        return 1.0, "kg", "1 kq (çəkili)"
    return None, None, ""


def unit_price(price, value, unit):
    """1 kq / 1 L / 1 ədəd üçün qiymət."""
    if not price or not value or not unit:
        return None, ""
    label = {"kg": "kq", "l": "L", "ad": "ədəd"}[unit]
    return round(price / value, 2), label


def name_tokens(name: str) -> frozenset:
    f = WEIGHT_RE.sub(" ", fold(name))
    out = set()
    for t in re.findall(r"[a-z0-9]+", f):
        if len(t) > 3:
            t = re.sub(r"(kq|kg)$", "", t)
        if t and t not in STOP and not t.isdigit():
            out.add(t)
    return frozenset(out)
