import scrapy
from urllib.parse import urljoin
from datetime import datetime
import json
import glob
import re
import os
from tqdm import tqdm
from scrapy import signals


# ============================================================
# CLEAN TEXT FUNCTION
# ============================================================
def clean_infobox_text(nodes):
    if not nodes:
        return ""

    raw = " ".join(nodes).strip()
    raw = re.sub(r"\.mw-parser-output[^{}]+{[^{}]+}", "", raw)
    raw = re.sub(r"[.#]mw[\w\-\s:;{}().,]*", "", raw)
    raw = re.sub(r"{[^{}]*}", "", raw)
    raw = re.sub(r"\[\d+\]", "", raw)
    raw = re.sub(r"\[[a-zA-Z]\]", "", raw)
    raw = raw.replace("•", " ")
    raw = raw.replace(" ,", ",")
    raw = raw.replace(" ;", ";")
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


# ============================================================
# SPIDER
# ============================================================
class CpopHomeChineseActorsSpider(scrapy.Spider):
    name = "cpophome"
    allowed_domains = ["cpophome.com"]
    start_urls = [
        "https://www.cpophome.com/chinese-actors/",
        "https://www.cpophome.com/chinese-actress/",
        "https://www.cpophome.com/chinese-singer/",
    ]

    existing_urls = set()
    expected = 0
    processed = 0
    progress = None
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,          # seconds
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }
    # ============================================================
    # SIGNALS
    # ============================================================
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.response_downloaded, signal=signals.response_downloaded)
        return spider

    # ============================================================
    # OPEN
    # ============================================================
    def spider_opened(self, spider):
        json_files = glob.glob("cpophome_actors_*.json")
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        if item.get("profile_url"):
                            self.existing_urls.add(item["profile_url"])
            except Exception:
                pass

        self.logger.info(f"Loaded {len(self.existing_urls)} existing profiles")

        # ✅ FIX: initialize tqdm safely
        self.progress = tqdm(
            total=0,
            desc="Crawling profiles",
            unit="page"
        )

    def spider_closed(self, spider):
        # ✅ FIX: never use truthiness on tqdm
        if self.progress is not None:
            self.progress.close()

    # ============================================================
    # NORMALIZE URL
    # ============================================================
    def normalize_url(self, base, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(base, url)
        return url

    # ============================================================
    # LIST PAGE
    # ============================================================
    def parse(self, response):
        actors = response.css("a.celebrity_list_group")

        for a in actors:
            href = self.normalize_url(response.url, a.attrib.get("href"))
            name = a.css("span.celebrity_rank_name strong::text").get(default="").strip()

            if not href or href in self.existing_urls:
                continue

            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield response.follow(
                href,
                callback=self.parse_profile,
                meta={
                    "name": name,
                    "profile_url": href
                }
            )

        # pagination
        # next_pages = response.css(
        #     "div.celebrity_list_pagination a::attr(href)"
        # ).getall()

        # for np in next_pages:
        #     yield response.follow(
        #         self.normalize_url(response.url, np),
        #         callback=self.parse
        #     )
        next_page = response.css(
            "div.celebrity_list_pagination "
            "li.celebrity_list_pagination_li_current_page + li a::attr(href)"
        ).get()

        if next_page:
            yield response.follow(
                self.normalize_url(response.url, next_page),
                callback=self.parse
            )
    # ============================================================
    # PROFILE PAGE
    # ============================================================
    def parse_profile(self, response):
        profile_url = response.meta["profile_url"]
        if profile_url in self.existing_urls:
            return

        name = response.css("h1.entry-title::text").get(
            response.meta.get("name", "")
        ).strip()

        image_url = self.normalize_url(
            response.url,
            response.css("img.wp-post-image::attr(src)").get()
        )

        intro = clean_infobox_text(
            response.css(".entry-content > p:nth-of-type(1)::text").getall()
        )

        job = ""
        if "actor" in intro.lower():
            job = "Actor"
        elif "singer" in intro.lower():
            job = "Singer"

        gender = ""
        d = intro.lower()
        if d.startswith("he ") or " he " in d:
            gender = "Male"
        elif d.startswith("she ") or " she " in d:
            gender = "Female"

        metadata = {
            "intro": intro,
            "paragraphs": [
                clean_infobox_text(p)
                for p in response.css(".entry-content p::text").getall()
                if p.strip()
            ],
            "dramas": response.css("ul.drama_profile li::text").getall(),
            "movies": response.css("ul.drama_profile li::text").getall(),
        }

        yield {
            "name": name,
            "job": job,
            "gender": gender,
            "image_url": image_url,
            "profile_url": profile_url,
            "metadata": metadata,
            # "source": "cpophome",
            # "scraped_at": datetime.utcnow().isoformat() + "Z"
        }

    # ============================================================
    # TQDM UPDATE
    # ============================================================
    def response_downloaded(self, response, request, spider):
        self.processed += 1
        if self.progress is not None:
            self.progress.update(1)
