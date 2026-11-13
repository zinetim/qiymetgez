"""Müqayisə bölməsini təkmilləşdirir (qənaət qutusu, qiymət zolağı, fərq %, bərabərlik).
Repo kökündə işlədin:  python apply_compare.py     (təkrar işlətmək təhlükəsizdir)"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SECTION = (HERE / "compare_section.html").read_text(encoding="utf-8").strip()
CSS = (HERE / "compare.css").read_text(encoding="utf-8")

tpl = pathlib.Path("templates/product.html")
css = pathlib.Path("static/style.css")
for f in (tpl, css):
    if not f.exists():
        sys.exit(f"XƏTA: {f} tapılmadı. Skripti repo kökündə (app.py olan qovluqda) işlədin.")

s = tpl.read_text(encoding="utf-8")
if 'class="savebox"' in s:
    print("keçildi (artıq tətbiq olunub): templates/product.html")
else:
    new, n = re.subn(r'<section class="compare">.*?</section>', lambda m: SECTION, s, count=1, flags=re.S)
    if n != 1:
        sys.exit('XƏTA: templates/product.html içində <section class="compare"> tapılmadı. Heç nə yazılmadı.')
    tpl.write_text(new, encoding="utf-8")
    print("yeniləndi: templates/product.html")

c = css.read_text(encoding="utf-8")
if ".savebox" in c:
    print("keçildi (artıq tətbiq olunub): static/style.css")
else:
    css.write_text(c.rstrip() + "\n" + CSS, encoding="utf-8")
    print("yeniləndi: static/style.css")

t = pathlib.Path("tests/test_core.py")
if t.exists() and "test_compare_box" not in t.read_text(encoding="utf-8"):
    with t.open("a", encoding="utf-8") as f:
        f.write('''

def test_compare_box():
    """Məhsul bir neçə marketdə varsa, məhsul səhifəsində qənaət qutusu və fərq göstərilməlidir."""
    import app as appmod
    appmod._cache.update({"mtime": None, "payload": None})
    d = appmod.get_data()
    multi = [p for p in d["products"] if p["compare_count"] > 1]
    if not multi:
        return  # data hələ tək marketdədir
    html = appmod.app.test_client().get("/m/" + multi[0]["id"]).get_data(as_text=True)
    assert 'class="savebox"' in html or "qiymət eynidir" in html
    assert "cmp-table" in html
''')
    print("yeniləndi: tests/test_core.py")
print("\nHazırdır. Yoxlayın:  python -m pytest -q  və  python app.py")
