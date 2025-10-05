import re

import scrapy
from tqdm import tqdm
from scrapy import signals


def clean_text(values):
    """Join and clean extracted texts, remove style/script noise."""
    text = " ".join(v.strip() for v in values if v.strip())
    # remove CSS or JavaScript fragments
    if text.startswith(".mw-parser-output") or "{" in text or "}" in text:
        return ""
    return text


def clean_summary(text):
    return re.sub(r"\[\d+\]", "", text).strip()


class OtherCountrySingerSpider(scrapy.Spider):
    name = "other_country_singer"

    start_urls = [
        "https://en.wikipedia.org/wiki/List_of_Afghan_singers",
        "https://en.wikipedia.org/wiki/Category:Barbadian_singers",
        "https://en.wikipedia.org/wiki/Category:Bahamian_singers",
        "https://en.wikipedia.org/wiki/List_of_Bosniak_musicians",
        "https://en.wikipedia.org/wiki/List_of_Bulgarian_musicians_and_singers",
        "https://en.wikipedia.org/wiki/List_of_Cambodian_singers",
        "https://en.wikipedia.org/wiki/Category:Canadian_singers",
        "https://en.wikipedia.org/wiki/List_of_Democratic_Republic_of_the_Congo_singers",
        "https://en.wikipedia.org/wiki/List_of_Croatian_singers", 
        "https://en.wikipedia.org/wiki/List_of_Cuban_singers", 
        "https://en.wikipedia.org/wiki/List_of_Dutch_singers", 
        "https://en.wikipedia.org/wiki/List_of_Filipino_singers", 
        "https://en.wikipedia.org/wiki/List_of_Finnish_singers", 
        "https://en.wikipedia.org/wiki/List_of_Indonesian_singers", 
        "https://en.wikipedia.org/wiki/List_of_Iranian_singers",
        "https://en.wikipedia.org/wiki/List_of_Japanese_singers",
        "https://en.wikipedia.org/wiki/List_of_Icelandic_singers",
        "https://en.wikipedia.org/wiki/List_of_Lithuanian_singers",
        "https://en.wikipedia.org/wiki/List_of_Malaysian_singers",
        "https://en.wikipedia.org/wiki/List_of_Mexican_singers", 
        "https://en.wikipedia.org/wiki/List_of_Nepalese_singers", 
        "https://en.wikipedia.org/wiki/List_of_Portuguese_singers", 
        "https://en.wikipedia.org/wiki/List_of_Romanian_singers", 
        "https://en.wikipedia.org/wiki/List_of_Slovenian_singers"
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,  # be polite
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 6,  # ~5–6 workers
        "CONCURRENT_REQUESTS_PER_DOMAIN": 6,
        "DOWNLOAD_TIMEOUT": 15,  # avoid hanging forever
        "ROBOTSTXT_OBEY": True,
    }

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
        self.progress = tqdm(total=0, desc="Crawling singers", unit="pages")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        """Handle both List pages and Category pages"""
        links = response.css("li a[href^='/wiki/']:not([href*=':'])")

        # If it's a Category page, use .mw-category links
        if "Category:" in response.url or not links:
            links = response.css(".mw-category a[href^='/wiki/']:not([href*=':'])")

        for link in links:
            href = link.attrib["href"]

            # skip meta pages
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
                dont_filter=True,
            )

        # handle category pagination ("next page")
        next_page = response.css("a:contains('next page')::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_singer(self, response, title):
        """Extract info from individual singer page"""

        # image
        image_url = (
            response.css(".infobox img::attr(src)").get()
            or response.css("figure a img::attr(src)").get()
        )
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        # summary (first non-empty paragraph)
        summary = None
        for p in response.css("div.mw-parser-output > p"):
            text = " ".join(p.css("::text").getall()).strip()
            if text:
                summary = text
                break

        # infobox extraction
        infobox = {}
        for row in response.css("table.infobox tr"):
            label = row.css("th.infobox-label::text").get()
            value_raw = row.css("td.infobox-data ::text").getall()  # no *
            value = clean_text(value_raw)
            if label and value:
                infobox[label.strip()] = value


        yield {
            "title": title,
            "url": response.url,
            "image_url": image_url or "",
            "summary": summary or "",
            "infobox": infobox,
        }

    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.processed += 1
            self.progress.update(1)
