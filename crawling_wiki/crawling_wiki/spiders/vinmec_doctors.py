import scrapy
from tqdm import tqdm
from scrapy import signals


class VinmecDoctorSpider(scrapy.Spider):
    name = "vinmec_doctors"
    start_urls = ["https://www.vinmec.com/vie/chuyen-gia-y-te/page_1"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = None
        self.expected = 0
        self.processed = 0
        self.visited_pages = set()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.response_downloaded, signal=signals.response_downloaded)
        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Crawling Vinmec doctors", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        """Parse all doctor cards on the current page"""
        page_url = response.url
        if page_url in self.visited_pages:
            return
        self.visited_pages.add(page_url)

        doctors = response.css("li.flex")

        for doc in doctors:
            name = doc.css("a.list_name_doctor::text").get(default="").strip()
            profile_url = doc.css("a.list_name_doctor::attr(href)").get(default="")
            if profile_url.startswith("/"):
                profile_url = response.urljoin(profile_url)

            # 🩺 Fixed image extraction — this now works
            image_url = doc.css("img::attr(src)").get(default="")
            if image_url and image_url.startswith("/"):
                image_url = response.urljoin(image_url)

            degree = doc.css("div.icon_list_doctor.degree::text").get(default="").strip()
            specialty = doc.css("div.icon_list_doctor.special::text").get(default="").strip()
            hospital = doc.css("div.icon_list_doctor.hospital a::text").get(default="").strip()
            hospital_url = doc.css("div.icon_list_doctor.hospital a::attr(href)").get(default="")
            if hospital_url.startswith("/"):
                hospital_url = response.urljoin(hospital_url)

            if not name:
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield {
                "name": name,
                "profile_url": profile_url,
                "image_url": image_url,
                "degree": degree,
                "specialty": specialty,
                "hospital": hospital,
                "hospital_url": hospital_url,
            }

        # Pagination
        next_pages = response.css("a.item_paging.page_button::attr(href)").getall()
        for next_page in next_pages:
            next_page = response.urljoin(next_page)
            if next_page not in self.visited_pages:
                yield scrapy.Request(next_page, callback=self.parse)

    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.processed += 1
            self.progress.update(1)
