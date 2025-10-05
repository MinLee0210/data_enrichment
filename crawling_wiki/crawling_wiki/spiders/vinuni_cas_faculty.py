import scrapy
from scrapy import signals
from tqdm import tqdm

import scrapy
from scrapy import signals
from tqdm import tqdm


import scrapy
from scrapy import signals
from tqdm import tqdm


class VinUniCasFacultySpider(scrapy.Spider):
    name = "vinuni_cas_faculty_sections"
    allowed_domains = ["cas.vinuni.edu.vn", "vinuni.edu.vn"]
    start_urls = ["https://cas.vinuni.edu.vn/vi/doi-ngu-lanh-dao-giang-day/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = None
        self.expected = 0

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Scraping CAS Faculty", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        # Loop through each <section> block (each category)
        sections = response.css("section.sectionGovernanceOfficersNew")

        for section in sections:
            # Extract the section title
            section_title = section.xpath("normalize-space(.//h2/text())").get(default="")
            if not section_title:
                section_title = section.css("div.secHeading::text").get(default="").strip()

            # Extract each faculty member card
            faculty_cards = section.css("div.governanceOfficers__item")

            for card in faculty_cards:
                name = card.css("h3.governanceOfficers__title a::text").get(default="").strip()
                position = card.css("p.governanceOfficers__position::text").get(default="").strip()

                # Extract image and profile links
                image_url = card.css("div.governanceOfficers__img img::attr(src)").get(default="")
                if image_url:
                    image_url = response.urljoin(image_url)

                profile_url = card.css("h3.governanceOfficers__title a::attr(href)").get(default="")
                if profile_url:
                    profile_url = response.urljoin(profile_url)

                if not name:
                    continue

                self.expected += 1
                self.progress.total = self.expected
                self.progress.refresh()

                yield {
                    "section": section_title or "Unknown",
                    "name": name,
                    "position": position,
                    "workplace": "Viện Khoa học và Giáo dục Khai phóng (College of Arts and Sciences – CAS)",
                    "image_url": image_url,
                    "profile_url": profile_url,
                }


# class VinUniCasFacultySpider(scrapy.Spider):
#     name = "vinuni_cas_faculty"
#     allowed_domains = ["cas.vinuni.edu.vn", "vinuni.edu.vn"]
#     start_urls = ["https://cas.vinuni.edu.vn/vi/doi-ngu-lanh-dao-giang-day/"]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.progress = None
#         self.expected = 0

#     @classmethod
#     def from_crawler(cls, crawler, *args, **kwargs):
#         spider = super().from_crawler(crawler, *args, **kwargs)
#         crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
#         crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
#         return spider

#     def spider_opened(self, spider):
#         self.progress = tqdm(total=0, desc="Scraping CAS Faculty", unit="profiles")

#     def spider_closed(self, spider):
#         if self.progress:
#             self.progress.close()

#     def parse(self, response):
#         cards = response.css("div.testimonialItem__wrap")

#         for card in cards:
#             name = card.css("h3.testimonialItem__title::text").get(default="").strip()

#             # Handle <br> in position text
#             position_raw = card.css("p.testimonialItem__position").get(default="")
#             position = (
#                 scrapy.Selector(text=position_raw)
#                 .xpath("string()")
#                 .get(default="")
#                 .replace("\n", " ")
#                 .strip()
#             )

#             image_url = response.urljoin(card.css("img::attr(src)").get(default=""))
#             profile_url = response.urljoin(
#                 card.css("a.imgGroup::attr(href)").get(default="")
#                 or card.css("a.testimonialItem__linkContent::attr(href)").get(default="")
#             )

#             if not name:
#                 continue

#             self.expected += 1
#             self.progress.total = self.expected
#             self.progress.refresh()

#             yield {
#                 "name": name,
#                 "position": position,
#                 "workplace": "Viện Khoa học và Giáo dục Khai phóng (College of Arts and Sciences – CAS)",
#                 "image_url": image_url,
#                 "profile_url": profile_url,
#             }
