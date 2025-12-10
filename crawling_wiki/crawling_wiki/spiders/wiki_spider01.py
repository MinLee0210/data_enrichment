import scrapy
from tqdm import tqdm
from scrapy import signals


class WikiDataSpider_001(scrapy.Spider):
    name = "wiki_spider01"
    start_urls = [
                    # "https://en.wikipedia.org/wiki/List_of_Chinese_actors", 
                    # "https://en.wikipedia.org/wiki/List_of_Chinese_actresses", 
                    # "https://en.wikipedia.org/wiki/List_of_Armenian_actors", 
                    # "https://en.wikipedia.org/wiki/List_of_Armenian_actors", 
                    # "https://en.wikipedia.org/wiki/List_of_Bhutanese_actors", 
                    # "https://en.wikipedia.org/wiki/List_of_Burmese_actors", 
        #                     "https://en.wikipedia.org/wiki/List_of_Khmer_film_actors", 
        # "https://en.wikipedia.org/wiki/List_of_Egyptians#Actors", 
        # "https://en.wikipedia.org/wiki/Lists_of_Indian_actors", 
        # "https://en.wikipedia.org/wiki/List_of_Indian_film_actresses", 
        # "https://en.wikipedia.org/wiki/List_of_Indian_male_film_actors", 
        # "https://en.wikipedia.org/wiki/List_of_Iranian_actresses", 
        # "https://en.wikipedia.org/wiki/List_of_Iranian_male_actors", 
        # "https://en.wikipedia.org/wiki/List_of_Israeli_actors", 
        "https://en.wikipedia.org/wiki/List_of_Japanese_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Japanese_actors", 
        "https://en.wikipedia.org/wiki/List_of_Jordanian_actors", 
        "https://en.wikipedia.org/wiki/List_of_Malaysian_actors", 
        "https://en.wikipedia.org/wiki/List_of_Nepalese_actors", 
        "https://en.wikipedia.org/wiki/List_of_North_Korean_actors", 
        "https://en.wikipedia.org/wiki/List_of_Pakistani_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Pakistani_male_actors", 
        "https://en.wikipedia.org/wiki/List_of_Jordanian_actors", 
        "https://en.wikipedia.org/wiki/List_of_Malaysian_actors", 
        "https://en.wikipedia.org/wiki/List_of_Nepalese_actors", 
        "https://en.wikipedia.org/wiki/List_of_North_Korean_actors", 
        "https://en.wikipedia.org/wiki/List_of_Pakistani_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Pakistani_male_actors", 
        "https://en.wikipedia.org/wiki/Lists_of_Philippine_actors", 
        "https://en.wikipedia.org/wiki/List_of_Filipino_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Filipino_male_actors", 
        "https://en.wikipedia.org/wiki/List_of_South_Korean_actresses",
        "https://en.wikipedia.org/wiki/List_of_South_Korean_male_actors", 
        "https://en.wikipedia.org/wiki/List_of_Sri_Lankan_actors", 
        "https://en.wikipedia.org/wiki/List_of_Taiwanese_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Thai_actresses", 
        "https://en.wikipedia.org/wiki/List_of_Thai_male_actors", 
        "https://en.wikipedia.org/wiki/List_of_Turkish_actors", 
        "https://en.wikipedia.org/wiki/List_of_Uzbekistani_film_actors", 
        "https://en.wikipedia.org/wiki/List_of_Vietnamese_actors"
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
        crawler.signals.connect(
            spider.response_downloaded, signal=signals.response_downloaded
        )

        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Crawling data ... ", unit="pages")

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
