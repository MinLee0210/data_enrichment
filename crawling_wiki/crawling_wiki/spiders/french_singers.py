import scrapy
from tqdm import tqdm
from scrapy import signals


class FrenchArtistSpider(scrapy.Spider):
    name = "french_artist"
    start_urls = ["https://en.wikipedia.org/wiki/List_of_French_singers"]

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
        crawler.signals.connect(
            spider.response_downloaded, signal=signals.response_downloaded
        )

        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Crawling French singers", unit="pages")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        links = response.css("li a[href^='/wiki/']:not([href*=':'])")

        for link in links:
            href = link.attrib["href"]
            if any(
                href.startswith(path)
                for path in [
                    "/wiki/List_",
                    "/wiki/Category:",
                    "/wiki/File:",
                    "/wiki/Wikipedia:",
                ]
            ):
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield response.follow(
                href,
                callback=self.parse_singer,
                cb_kwargs={"title": link.css("::text").get()},
            )

    def parse_singer(self, response, title):
        image_url = (
            response.css(".infobox img::attr(src)").get()
            or response.css("figure a img::attr(src)").get()
        )
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        summary = None
        for p in response.css("div.mw-parser-output > p"):
            text = " ".join(p.css("::text").getall()).strip()
            if text:
                summary = text
                break

        yield {
            "title": title,
            "url": response.url,
            "image_url": image_url or "",
            "summary": summary or "",
        }

    def response_downloaded(self, response, request, spider):
        """Update progress for every successful response, not just items."""
        if self.progress:
            self.processed += 1
            self.progress.update(1)
