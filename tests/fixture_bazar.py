"""bazarstore.az (nopCommerce) kateqoriya səhifəsini təqlid edən HTML. Məhsullar real səhifədən."""
ROWS = [
 # id, slug, ad, qiymətlər (mətn kimi)
 (101, "hicaz-teze-bud-aciq-kq", "HİCAZ TƏZƏ BUD BÜTÖV AÇIQ KQ", "5,99 ₼"),
 (102, "hicaz-teze-qanad-aciq-kq", "HİCAZ TƏZƏ QANAD AÇIQ KQ", "7,29 ₼"),
 (103, "hicaz-teze-toyuq-paket-kg", "HİCAZ TƏZƏ TOYUQ PAKET KQ", "7,19 ₼"),
 (104, "kend-colpasi-eded", "KƏND ÇOLPASI ƏDƏD", "7,30 ₼"),
 (105, "mercan-toyuq-ayaqlari-aciq-kq", "MƏRCAN TƏZƏ TOYUQ BUD BÜTÖV AÇIQ KQ", "6,75 ₼"),
 (106, "m%C9%99rcan-t%C9%99z%C9%99-toyuq-bud-butulka-a%C3%A7iq-kq", "MƏRCAN TƏZƏ TOYUQ BUD BUTULKA AÇIQ KQ", "7,50 ₼"),
 (107, "mercan-teze-toyuq-paket-kq", "MƏRCAN TƏZƏ TOYUQ PAKET KQ", "7,75 ₼"),
 (108, "seba-teze-bud-butulka-aciq-kq", "SƏBA TƏZƏ BUD BUTULKA AÇIQ KQ", "5,99 ₼"),
 (109, "seba-teze-bud-dibi-aciq-kq", "SƏBA TƏZƏ BUD DİBİ AÇIQ KQ", "6,99 ₼"),
 (110, "seba-teze-ciyer-aciq-kg", "SƏBA TƏZƏ CİYƏR AÇIQ KQ", "3,65 ₼"),
 # endirim (köhnə qiymət əvvəl) + vahid qiyməti mətni + qram "Q"
 (111, "gulum-sirin-qargidali-425-q", "GULUM ŞİRİN QARĞIDALI 425 Q", "2,40 ₼ 1,89 ₼"),
 (112, "xiyar-kg", "XİYAR KG", "1,69 ₼ 1 kg(s) üçün 1,69 ₼ təşkil edir"),
]


def listing_html():
    items = []
    for pid, slug, name, prices in ROWS:
        spans = prices
        items.append(f"""
<div class="product-item" data-productid="{pid}">
  <div class="picture"><a href="/{slug}" title="{name}">
    <img alt="{name} şəkli" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==" data-lazyloadsrc="https://bazarstore.az/images/thumbs/00{pid}_415.jpeg"></a></div>
  <div class="details"><h2 class="product-title"><a href="/{slug}">{name}</a></h2>
    <div class="add-info"><div class="prices"><span class="price actual-price">{spans}</span></div>
    <button>Səbətə əlavə et</button></div></div>
</div>""")
    return "<html><body><div class='product-grid'>" + "".join(items) + "</div></body></html>"
