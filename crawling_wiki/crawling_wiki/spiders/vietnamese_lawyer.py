import scrapy
from tqdm import tqdm
from scrapy import signals


class VietnameseLawyerSpider(scrapy.Spider):
    name = "vietnamese_lawyer"
    start_urls = ["https://www.danhbaluatsu.com/luat-su/p1"]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = None
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
        self.progress = tqdm(total=0, desc="Crawling Vietnamese lawyers", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        """Extract all lawyer profiles from the current page"""
        profiles = response.css("li")

        for p in profiles:
            name = p.css("div.right h2 a::text").get(default="").strip()
            profile_url = p.css("div.right h2 a::attr(href)").get(default="")
            image_url = p.css("div.left a img::attr(src)").get(default="")

            # Skip if the block has no valid lawyer info
            if not name and not profile_url:
                continue

            if profile_url:
                profile_url = response.urljoin(profile_url)
            if image_url and image_url.startswith("/"):
                image_url = response.urljoin(image_url)

            # Extract all labeled <p><span>...</span> Value</p>
            info = {}
            for line in p.css("div.right p"):
                label = line.css("span:first-child::text").get(default="").strip().rstrip(":")
                value = " ".join(line.css("::text").getall()).replace(label, "").strip()
                if label and value:
                    info[label] = value

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield {
                "name": name,
                "profile_url": profile_url,
                "image_url": image_url,
                **info,
            }

        # Pagination: follow /p2, /p3, etc.
        next_pages = response.css("#mainlink a::attr(href)").getall()
        for page in next_pages:
            if page and page not in response.url:
                yield response.follow(page, callback=self.parse)

    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.processed += 1
            self.progress.update(1)
