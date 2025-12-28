import scrapy
from urllib.parse import urljoin


class KOFICPeopleSpider(scrapy.Spider):
    name = "kofic_people"
    allowed_domains = ["www.koreanfilm.or.kr"]

    start_urls = [
        f"https://www.koreanfilm.or.kr/eng/films/index/peopleDList.jsp?pageIndex={i}"
        for i in range(1, 744)
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.3,
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEEDS": {"kofic_people.json": {"format": "json"}}
    }

    def parse(self, response):

        rows = response.css("table.Directory tbody tr")

        for row in rows:

            # Person ID
            js_call = row.css("td.left a::attr(href)").get()
            if not js_call or "peopleView" not in js_call:
                continue

            people_id = js_call.split("'")[1]
            profile_url = (
                f"https://www.koreanfilm.or.kr/eng/films/index/"
                f"peopleView.jsp?peopleCd={people_id}"
            )

            # Image
            img_url = row.css("td img::attr(src)").get()
            img_url = urljoin(response.url, img_url) if img_url else ""

            # =============================
            # FIXED NAME EXTRACTION
            # =============================
            name_a = row.css("td.left a")

            eng_name = name_a.xpath("text()[1]").get(default="").strip()
            kor_name = name_a.xpath("text()[2]").get(default="").strip()

            # Main type (Actor, Director, etc)
            main_type = row.css("td .bul_none li::text").get(default="").strip()

            # Company
            company = row.css("td:nth-child(3)::text").get(default="").strip()

            # Filmography
            films = [
                f.strip()
                for f in row.css("td:nth-child(4) li::text").getall()
            ]

            yield {
                "people_id": people_id,
                "profile_url": profile_url,
                "image_url": img_url,

                "name_en": eng_name,
                "name_kr": kor_name,

                "mainType": main_type,
                "company": company,
                "filmography": films,
            }
