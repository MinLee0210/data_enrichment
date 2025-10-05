import scrapy
from tqdm import tqdm
from scrapy import signals


class FPTHanoiTeacherSpider(scrapy.Spider):
    name = "fpt_teachers"
    start_urls = ["https://hanoi-school.fpt.edu.vn/danh-sach-giao-vien"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = None
        self.visited_pages = set()
        self.expected = 0
        self.processed = 0

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.response_downloaded, signal=signals.response_downloaded)
        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Crawling teachers", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        page_url = response.url
        if page_url in self.visited_pages:
            return
        self.visited_pages.add(page_url)

        # Each teacher card
        teachers = response.css("ul.bricks-layout-wrapper.isotope > li.bricks-layout-item")

        for teacher in teachers:
            # ✅ image + profile
            profile_url = teacher.css("figure.image-wrapper a::attr(href)").get(default="").strip()
            image_url = teacher.css("figure.image-wrapper img::attr(src)").get(default="").strip()

            if profile_url.startswith("/"):
                profile_url = response.urljoin(profile_url)
            if image_url.startswith("/"):
                image_url = response.urljoin(image_url)

            # ✅ name
            name = teacher.css("h3.dynamic a::text").get(default="").strip()

            # ✅ role — more reliable extraction
            role_texts = teacher.css("p.dynamic[data-field-id='qookvo'] *::text").getall()
            role = " ".join(t.strip() for t in role_texts if t.strip())

            if not name and not image_url:
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield {
                "name": name,
                "profile_url": profile_url,
                "image_url": image_url,
                "role": role,
            }

    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.processed += 1
            self.progress.update(1)
