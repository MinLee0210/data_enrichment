"Ref: https://en.wikipedia.org/wiki/Lists_of_German_politicians"

import scrapy
from tqdm import tqdm
from scrapy import signals

class GermanPoliticiansSpider(scrapy.Spider):
    name = "german_politicians"

    start_urls = [
        # "https://en.wikipedia.org/wiki/List_of_Alternative_for_Germany_politicians",
        # "https://en.wikipedia.org/wiki/List_of_Christian_Social_Union_of_Bavaria_politicians",
        # "https://en.wikipedia.org/wiki/List_of_Bavarian_People%27s_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Centre_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Christian_Democratic_Union_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Communist_Party_members",
        # "https://en.wikipedia.org/wiki/List_of_German_Democratic_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Free_Democratic_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Green_Party_politicians",
        "https://en.wikipedia.org/wiki/List_of_German_People%27s_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_National_People%27s_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_Independent_Social_Democratic_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_German_Left_Party_politicians",
        # "https://en.wikipedia.org/wiki/List_of_Liberal_Democratic_Party_of_Germany_politicians",
        # "https://en.wikipedia.org/wiki/List_of_National_Democratic_Party_of_Germany_politicians",
        # "https://en.wikipedia.org/wiki/List_of_Social_Democratic_Party_of_Germany_members",
    ]

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
        self.progress = tqdm(total=0, desc="Crawling politicians", unit="pages")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        links = response.css("li a[href^='/wiki/']:not([href*=':'])")

        for link in links:
            href = link.attrib["href"]
            if any(
                href.startswith(path)
                for path in ["/wiki/List_", "/wiki/Category:", "/wiki/File:", "/wiki/Wikipedia:"]
            ):
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield response.follow(
                href,
                callback=self.parse_politician,
                cb_kwargs={"title": link.css("::text").get()},
            )

    def parse_politician(self, response, title):
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