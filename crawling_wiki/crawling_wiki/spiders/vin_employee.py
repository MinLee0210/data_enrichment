import scrapy
from tqdm import tqdm
from scrapy import signals


class VinUniPeopleSpider(scrapy.Spider):
    name = "vinuni_people"
    start_urls = ["https://vinuni.edu.vn/vi/directory-vi/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = None
        self.visited = set()
        self.expected = 0

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self, spider):
        self.progress = tqdm(total=0, desc="Crawling VinUni Directory", unit="profiles")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    def parse(self, response):
        if response.url in self.visited:
            return
        self.visited.add(response.url)

        # Inspecting the HTML, we can try selectors like this:
        # The page put images, h3 and p in sequence (not wrapped in a unique container in the snippet shown)
        # But a safer way is to find the “directory person blocks” by inspecting parent elements.
        persons = response.css("div.directory .person, .staff-item, div[class*='directory'] img")  # fallback

        # A more precise guess: find all <img> under a parent that groups a person
        # Actually from the HTML, images are right under the page content, so we can do:
        for img in response.css("img"):
            alt = img.attrib.get("alt", "").strip()
            src = img.attrib.get("src", "").strip()
            if not alt or alt.lower().startswith("image"):
                # skip placeholder or generic images
                continue

            # The <h3> and <p> next to that image (in the HTML) likely belong to the same person
            # So we look for a sibling <h3> and <p> near it
            # We can try using xpath to go up to parent then find h3 / p
            parent = img.xpath("ancestor-or-self::*[position()=1]")  # just use current as fallback
            # But simpler: use following-sibling axis
            name = img.xpath("following::h3[1]/text()").get(default="").strip()
            position = img.xpath("following::p[1]/text()").get(default="").strip()

            # Build full image URL
            image_url = response.urljoin(src)

            if name:
                self.expected += 1
                if self.progress:
                    self.progress.total = self.expected
                    self.progress.refresh()

                yield {
                    "name": name,
                    "position": position,
                    "image_url": image_url,
                }

        # This directory-vi page seems static, so likely no pagination. If there were:
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
