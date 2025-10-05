import scrapy
from tqdm import tqdm
from scrapy import signals


class HCMUSSHLecturerSpider(scrapy.Spider):
    name = "hcmussh_lecturers"
    start_urls = ["https://daotaonhanluc.hcmussh.edu.vn/giang-vien/"]

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
        self.progress = tqdm(total=0, desc="Crawling lecturers", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        page_url = response.url
        if page_url in self.visited_pages:
            return
        self.visited_pages.add(page_url)

        lecturers = response.css("div.m-lectureCard")

        for lec in lecturers:
            profile_url = lec.css("div.m-lectureCard__avatar a::attr(href)").get(default="").strip()
            image_url = lec.css("div.m-lectureCard__avatar img::attr(src)").get(default="").strip()
            name = lec.css("div.m-lectureCard__info p:nth-of-type(1)::text").get(default="").strip()
            title = lec.css("div.m-lectureCard__info p:nth-of-type(2)::text").get(default="").strip()

            if profile_url.startswith("/"):
                profile_url = response.urljoin(profile_url)
            if image_url.startswith("/"):
                image_url = response.urljoin(image_url)

            if not name:
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield {
                "name": name,
                "profile_url": profile_url,
                "image_url": image_url,
                "title": title,
            }

        # Pagination (if exists)
        next_page = response.css("a.next.page-numbers::attr(href)").get()
        if next_page:
            next_page = response.urljoin(next_page)
            if next_page not in self.visited_pages:
                yield scrapy.Request(next_page, callback=self.parse)

    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.processed += 1
            self.progress.update(1)
