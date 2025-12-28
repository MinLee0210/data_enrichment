import scrapy
from urllib.parse import urljoin
from datetime import datetime
import json
import glob
import re
from tqdm import tqdm
from scrapy import signals
import os 


# ============================================================
# CLEAN TEXT
# ============================================================
def clean_text(nodes):
    if not nodes:
        return ""
    raw = " ".join(nodes)
    raw = re.sub(r"\[\d+\]", "", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


# ============================================================
# SPIDER
# ============================================================
class AsianWikiJapaneseActorsSpider(scrapy.Spider):
    name = "asian_wiki"
    allowed_domains = ["asianwiki.com"]

    start_urls = [
        "https://asianwiki.com/index.php?title=Category:Japanese_actors"
    ]

    existing_urls = set()
    progress = None
    profile_urls = set()
    profile_url_file = "profile_url.json"
    custom_settings = {
        # ---------------- HEADERS (Cloudflare friendly)
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://asianwiki.com/",
        },

        # ---------------- SCRAPY
        "COOKIES_ENABLED": True,
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0.5,
        "AUTOTHROTTLE_ENABLED": True,
        "RETRY_ENABLED": False,
        "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504],

        # ---------------- PLAYWRIGHT
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30_000,
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
        # ---- load existing profile_url.json ----
        if os.path.exists(self.profile_url_file):
            try:
                with open(self.profile_url_file, "r", encoding="utf-8") as f:
                    urls = json.load(f)
                    self.profile_urls.update(urls)
            except Exception:
                pass

        # ---- load existing scraped profiles ----
        for jf in glob.glob("asianwiki_actors_*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    for row in json.load(f):
                        if row.get("profile_url"):
                            self.existing_urls.add(row["profile_url"])
            except Exception:
                pass

        self.logger.info(
            f"Loaded {len(self.existing_urls)} scraped profiles | "
            f"{len(self.profile_urls)} profile URLs"
        )

        self.progress = tqdm(total=0, desc="AsianWiki Actors", unit="profile")



    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

        # ---- persist profile URLs ----
        try:
            with open(self.profile_url_file, "w", encoding="utf-8") as f:
                json.dump(sorted(self.profile_urls), f, indent=2, ensure_ascii=False)
            self.logger.info(
                f"Saved {len(self.profile_urls)} profile URLs to {self.profile_url_file}"
            )
        except Exception as e:
            self.logger.error(f"Failed to save profile URLs: {e}")


    # ============================================================
    # URL NORMALIZER
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
    # CATEGORY PARSER  ✅ selector preserved
    # ============================================================
    def parse(self, response):
        links = response.css("table ul li a")
        self.logger.info(f"{response.url} → {len(links)} profiles")

        for a in links:
            name = a.css("::text").get("").strip()
            href = self.normalize_url(response.url, a.attrib.get("href"))

            if not href or href in self.existing_urls:
                continue

            if self.progress:
                self.progress.total += 1
                self.progress.refresh()

            yield response.follow(
    href,
    callback=self.parse_profile,
    headers={"Referer": response.url},
    meta={
        "name": name,
        "profile_url": href,
        "playwright": True,   # <<< FORCE Playwright
        "playwright_page_methods": [
    ("wait_for_load_state", "domcontentloaded"),
],
    },
)


        # pagination
        next_page = response.xpath(
            "//div[@id='mw-pages']//a[contains(text(),'next')]/@href"
        ).get()

        if next_page:
            yield response.follow(
                self.normalize_url(response.url, next_page),
                callback=self.parse
            )


    # ============================================================
    # PROFILE PARSER (Scrapy → Playwright fallback)
    # ============================================================
    def parse_profile(self, response):
        # ---- Cloudflare fallback ----
        if response.status == 403 and not response.meta.get("playwright"):
            yield scrapy.Request(
                response.url,
                callback=self.parse_profile,
                dont_filter=True,
                meta={
                    "name": response.meta["name"],
                    "profile_url": response.meta["profile_url"],
                    "playwright": True,
                    "playwright_page_methods": [
    ("wait_for_load_state", "domcontentloaded"),
],
                },
            )
            return

        profile_url = response.meta["profile_url"]
        name = response.meta["name"]

        if profile_url in self.existing_urls:
            return

        data = {
            "name": name,
            "profile_url": profile_url,
            "image_url": "",
            "metadata": {},
            "notes": [],
        }

        # image
        img = response.css(".thumb.tright img::attr(src)").get()
        data["image_url"] = self.normalize_url(response.url, img)

        # metadata
        for li in response.css("ul li"):
            label = clean_text(li.css("b::text").getall())
            value = clean_text(li.css("::text").getall())

            if not label:
                continue

            label = label.replace(":", "").strip()
            value = value.replace(label, "").strip()
            data["metadata"][label] = value

        # notes
        notes = response.xpath(
            "//h2[span[text()='Notes']]/following-sibling::ol[1]/li/text()"
        ).getall()
        data["notes"] = [clean_text([n]) for n in notes]

        # born normalization
        born = data["metadata"].get("Born", "")
        if born:
            try:
                dt = datetime.strptime(born, "%B %d, %Y")
                data["dateOfBirth"] = dt.strftime("%Y-%m-%d")
            except Exception:
                data["dateOfBirth"] = born

        yield data


    # ============================================================
    # TQDM UPDATE
    # ============================================================
    def response_downloaded(self, response, request, spider):
        if self.progress:
            self.progress.update(1)
