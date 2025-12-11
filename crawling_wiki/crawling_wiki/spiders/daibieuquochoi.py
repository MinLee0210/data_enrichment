import scrapy
from urllib.parse import urljoin
import re
import sys
from tqdm import tqdm

from scrapy_playwright.page import PageMethod


class DBQHSpider(scrapy.Spider):
    name = "dbqh_spider"
    allowed_domains = ["dbqh.quochoi.vn"]

    # include XV for completeness
    ROMAN = [
        "I","II","III","IV","V","VI","VII",
        "VIII","IX","X","XI","XII","XIII","XIV","XV"
    ]
    start_urls = [f"https://dbqh.quochoi.vn/{r}/Daibieu.aspx" for r in ROMAN]

    visited_profiles = set()
    visited_pages = set()

    pbar = None

    custom_settings = {
    "PLAYWRIGHT_BROWSER_TYPE": "chromium",
    "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,

    # super important for stability:
    "CONCURRENT_REQUESTS": 4,
    "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 1,
    "PLAYWRIGHT_DEFAULT_CONTEXT": "default",
    "PLAYWRIGHT_CONTEXTS": {
        "default": {"viewport": None}
    },

    "DOWNLOAD_HANDLERS": {
        "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    },

    # ensure async reactor is loaded correctly
    "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",

    "LOG_LEVEL": "INFO",
}


    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                # meta={
                #     "playwright": True,
                #     "playwright_include_page": True,
                #     "playwright_page_methods": [
                #         PageMethod("wait_for_selector", "table")
                #     ],
                # },
            meta={
                "playwright": True,
                "playwright_context": "default",
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "table")
                ],
            },
                            callback=self.parse_playwright,
            )

    def open_spider(self, spider):
        self.pbar = tqdm(desc="Profiles", unit="profile", file=sys.stderr)

    def close_spider(self, spider):
        if self.pbar:
            self.pbar.close()

    def clean(self, x):
        return re.sub(r"\s+", " ", x).strip() if x else ""

    async def parse_playwright(self, response):
        page = response.meta["playwright_page"]
        html = await page.content()
        await page.close()

        # IMPORTANT: yield items from parse_list
        for item in self.parse_list(response.url, html):
            yield item

    # ----------------------------------------------------------
    # Parse LIST PAGE (JS-rendered HTML)
    # ----------------------------------------------------------
    def parse_list(self, url, html):
        sel = scrapy.Selector(text=html)

        if url in self.visited_pages:
            return
        self.visited_pages.add(url)

        # flexible selectors for old + new layouts
        rows = sel.css("div.ds-list table tbody tr")
        if not rows:
            rows = sel.css("div#list table tbody tr")
        if not rows:
            rows = sel.css("table tbody tr")

        self.logger.info(f"[LIST] {url} -> {len(rows)} <tr>")

        for row in rows:
            if not row.css("td.bg a"):
                continue

            link = row.css("td.bg a::attr(href)").get()
            if not link:
                continue

            profile_url = urljoin(url, link)
            if profile_url in self.visited_profiles:
                continue
            self.visited_profiles.add(profile_url)

            name = self.clean(row.css("td.bg a::text").get())
            gender = self.clean(row.css("td.gioitinh::text").get())
            main_type = self.clean(row.css("td.doandbieu::text").get())

            yield scrapy.Request(
                profile_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div.detail-desc")
                    ],
                    "name": name,
                    "gender": gender,
                    "mainType": main_type,
                    "profile_url": profile_url,
                },
                callback=self.parse_detail_playwright,
            )

        # pagination links (flexible)
        page_links = sel.css(
            "div.congress-bottom ul.paging li a::attr(href), "
            "ul.paging li a::attr(href)"
        ).getall()

        for link in page_links:
            next_page = urljoin(url, link)
            if next_page not in self.visited_pages:
                self.logger.info(f"[PAGING] {url} -> {next_page}")
                yield scrapy.Request(
                    next_page,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "table")
                        ],
                    },
                    callback=self.parse_playwright,
                )

    # ----------------------------------------------------------
    # Parse DETAIL PAGE (JS-rendered HTML)
    # ----------------------------------------------------------
    async def parse_detail_playwright(self, response):
        page = response.meta["playwright_page"]
        html = await page.content()
        await page.close()

        for item in self.parse_detail_html(response.meta, html):
            yield item

    # ----------------------------------------------------------
    # Extract fields from detail page
    # ----------------------------------------------------------
    def parse_detail_html(self, meta, html):
        sel = scrapy.Selector(text=html)

        if self.pbar:
            self.pbar.update(1)

        # image
        image_url = sel.css("img.img-detail::attr(src)").get()
        image_url = urljoin(meta["profile_url"], image_url) if image_url else ""

        # find detail container (varies by khóa)
        container = sel.css("div.detail-desc, div.detail, div.content-view")
        if not container:
            container = sel

        details = {}

        # for every <p><strong>Field: </strong> value</p>
        for p in container.css("p"):
            strong = p.css("strong::text").get()
            if not strong:
                continue

            title = self.clean(strong.replace(":", ""))
            key = (
                title.lower()
                .replace(" ", "_")
                .replace("đ", "d").replace("ê", "e").replace("ơ", "o")
                .replace("ư", "u").replace("ị", "i")
            )

            full_text = self.clean(" ".join(p.css("*::text").getall()))
            value = full_text[len(strong):].strip()
            details[key] = value

        yield {
            "profile_url": meta["profile_url"],
            "name": meta["name"],
            "mainType": meta["mainType"],
            "image_url": image_url,
            "gender": meta["gender"],

            # normalized standard fields
            "dateOfBirth": details.get("ngay_sinh"),
            "homePlace": details.get("que_quan"),

            # full dictionary of fields
            "details": details,
        }
