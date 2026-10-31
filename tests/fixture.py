"""arazmarket.az kateqoriya səhifəsinin quruluşunu təqlid edən test HTML-i (real məhsul məlumatları)."""
from urllib.parse import quote

ROWS = [
 # slug, şəkil kodu, ad, kateqoriya, endirim, yeni, köhnə, Araz brendi
 ("mercan-teze-petenek-aciq-kq-8897","1000024346","Mərcan Təzə Pətənək Açıq kq","Təzə toyuq içalat",5,6.39,6.70,0),
 ("soba-hicaz-toyuq-teze-aciq-kq-11584","1000012614","SOBA HICAZ TOYUQ TƏZƏ AÇIQ KQ","Təzə toyuq bütöv",24,5.39,7.10,1),
 ("mercan-teze-toyuq-paket-soyudulmus-1kq-10097","1000012429","Mercan Təzə Toyuq Paket Soyudulmuş 1kq","Təzə toyuq bütöv",15,6.59,7.75,0),
 ("islami-kesim-toyuq-1kq-10091","1000010654","İslami Kəsim Toyuq 1kq","Təzə toyuq bütöv",7,6.49,7.00,0),
 ("tac-gilezi-teze-toyuq-aciq-9787","1000107951","Tac Gilezi Təzə Toyuq Açıq","Təzə toyuq bütöv",9,5.29,5.80,0),
 ("sirvan-teze-bud-ustu-aciq-1kq-9531","1000012685","Şirvan Təzə Bud Ustu Açıq 1kq","Təzə toyuq bud",29,5.59,7.90,0),
 ("tac-sirvan-teze-toyuq-aciq-1kq-9530","1000012609","Tac Şirvan Təzə Toyuq Açıq 1kq","Təzə toyuq bütöv",19,5.99,7.40,0),
 ("hicaz-teze-toyuq-paket-1kq-9172","1000012576","Hicaz Təzə Toyuq Paket 1kq","Təzə toyuq bütöv",17,5.99,7.20,0),
 ("berde-teze-bud-dibi-aciq-1kq-9039","1000113283","Bərdə Təzə Bud Dibi Açıq 1kq","Təzə toyuq bud dibi",0,7.30,None,0),
 ("berde-teze-file-aciq-9037","1000113280","Bərdə Təzə File Açıq","Təzə toyuq file",0,9.85,None,0),
 ("shirvan-teze-bud-butov-kq-8931","1000028350","Shirvan Təzə Bud Butov kq","Təzə toyuq bud bütöv",34,4.59,6.95,0),
 ("tac-sirvan-teze-file-aciq-1kq-8580","1000012529","Tac Şirvan Təzə File Açıq 1kq","Təzə toyuq file",15,8.99,10.60,0),
 ("mercan-teze-ciyer-aciqkq-8810","1000018799","Mercan Təzə Ciyər Açıqkq","Təzə toyuq içalat",10,3.89,4.30,0),
 ("soba-hicaz-ciyer-teze-aciq-kq-8797","1000018109","SOBA HİCAZ CİYƏR TEZE AÇIQ KQ","Təzə toyuq içalat",35,2.99,4.60,1),
 ("soba-hicaz-qanad-teze-aciq-kq-8666","1000013385","SOBA HİCAZ QANAD TƏZƏ AÇIQ KQ","Təzə toyuq qanad",18,5.99,7.30,1),
 ("soba-hicaz-butulka-teze-aciq-kq-8656","1000013240","SOBA HİCAZ BUTULKA TƏZƏ AÇIQ KQ","Təzə toyuq bud",14,5.99,7.00,1),
 ("sirvan-teze-ciyer-aciq-1kq-8649","1000013173","Şirvan Təzə Ciyər Açıq 1kq","Təzə toyuq içalat",36,2.99,4.70,0),
 ("mercan-teze-file-aciq-1kq-8646","1000013115","Mercan Təzə File Açıq 1kq","Təzə toyuq file",14,8.99,10.50,0),
 ("soba-hicaz-bud-ustu-teze-aciq-kq-8637","1000013006","SOBA HİCAZ BUD ÜSTÜ TƏZƏ AÇIQ KQ","Təzə toyuq bud",10,6.59,7.30,1),
 ("shirvan-teze-qanad-aciq-kq-8630","1000012949","Shirvan Təzə Qanad Açıq kq","Təzə toyuq qanad",29,5.59,7.90,0),
 ("shirvan-teze-butulka-aciq-kq-8612","1000012754","Shirvan Təzə Butulka Açıq kq","Təzə toyuq bud",29,5.59,7.90,0),
 ("soba-hicaz-file-aciq-teze-kq-8596","1000012635","SOBA HICAZ FILE ACIQ TƏZƏ KQ","Təzə toyuq file",9,8.99,9.90,1),
]
BASE = "https://www.arazmarket.az"


def listing_html():
    cards = []
    for slug, code, title, cat, disc, new, old, own in ROWS:
        href = f"{BASE}/az/products/{slug}"
        orig = f"https://b7x9kq.arazmarket.az/storage/products/{code}.png"
        src = f"{BASE}/_next/image?url={quote(orig, safe='')}&w=3840&q=75"
        badge = (f"<span>Araz brendi</span>" if own else "") + (f"<span>{disc}%</span>" if disc else "")
        price = f"{new:.2f}" + (f" {old:.2f}" if old else "")
        cards.append(
            f'<div class="card"><img src="/_next/static/media/load.png" alt="loading">'
            f'<a href="{href}"><img src="{src}" alt="{slug}" title="{title}"></a>{badge}'
            f'<a href="{href}"><strong>{cat}</strong></a><a href="{href}">{title}</a>'
            f'<a href="{href}">{price}</a></div>'
        )
    return "<html><body><h1>Təzə ağ ətlər</h1><div class='grid'>" + "".join(cards) + "</div></body></html>"
