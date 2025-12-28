import scrapy
from urllib.parse import urljoin
import re
import json
import glob
import os
from tqdm import tqdm
from scrapy import signals


# ============================================================
# TEXT CLEANER
# ============================================================
def clean_text(nodes):
    if not nodes:
        return ""
    raw = " ".join(nodes)
    raw = raw.replace("\xa0", " ")
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


# ============================================================
# SPIDER
# ============================================================
class KProfilesActressSpider(scrapy.Spider):
    name = "kprofiles"
    allowed_domains = ["kprofiles.com"]
    start_urls = [
        "https://kprofiles.com/korean-actresses-profiles/",
        "https://kprofiles.com/thai-actors-actresses-list/",
        "https://kprofiles.com/korean-actors-list/",
        "https://kprofiles.com/chinese-actresses/",
        "https://kprofiles.com/chinese-actors-profile/",
        "https://kprofiles.com/kpop-solo-singers/", 
        "https://kprofiles.com/kpop-male-solo-singers/", 
        "https://kprofiles.com/c-pop-singers-profile/"
        
    ]

    existing_urls = set()
    expected = 0
    processed = 0
    progress = None

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

    def spider_opened(self, spider):
        cwd = os.getcwd()
        json_files = glob.glob(os.path.join(cwd, "kprofiles_actresses_*.json"))

        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for x in data:
                    if x.get("profile_url"):
                        self.existing_urls.add(x["profile_url"])
            except Exception:
                pass

        self.logger.info(f"Loaded {len(self.existing_urls)} existing URLs")
        self.progress = tqdm(total=0, desc="KProfiles profiles", unit="profile")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

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
    # INDEX PAGE
    # ============================================================
    def parse(self, response):
        links = response.css("p strong a")

        self.logger.info(f"Found {len(links)} profile links")

        for a in links:
            name = a.css("::text").get("").strip()
            href = self.normalize_url(response.url, a.attrib.get("href"))

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
                    "profile_url": href,
                }
            )

    # ============================================================
    # PROFILE PAGE
    # ============================================================
    def parse_profile(self, response):
        profile_url = response.meta["profile_url"]
        name = response.meta["name"]

        if profile_url in self.existing_urls:
            return

        content = response.css("div.entry-content")

        # ------------------------
        # IMAGE
        # ------------------------
        img = content.css("img::attr(src)").get()
        image_url = self.normalize_url(response.url, img)

        # ------------------------
        # METADATA (highlighted spans)
        # ------------------------
        metadata = {}

        for p in content.css("p"):
            spans = p.css("span[style*='background']")
            if not spans:
                continue

            texts = p.xpath(".//text()").getall()
            texts = [t.strip() for t in texts if t.strip()]

            key = None
            value_parts = []

            for t in texts:
                if t.endswith(":"):
                    key = t.replace(":", "").strip()
                elif key:
                    value_parts.append(t)

            if key and value_parts:
                metadata[key] = clean_text(value_parts)

        # ------------------------
        # EXTRA TEXT BLOCKS
        # ------------------------
        facts = []
        for li in content.css("ul li"):
            txt = clean_text(li.xpath(".//text()").getall())
            if txt:
                facts.append(txt)

        if facts:
            metadata["facts"] = facts

        # ------------------------
        # JOB / GENDER
        # ------------------------
        job = "Actress"
        gender = "Female"

        # Infer job if present
        desc = clean_text(
            content.css("p::text").getall()
        ).lower()

        if "model" in desc:
            job += ", Model"

        # ------------------------
        yield {
            "name": name,
            "profile_url": profile_url,
            "image_url": image_url,
            "job": job,
            "gender": gender,
            "metadata": metadata,
        }

    # ============================================================
    # TQDM UPDATE
    # ============================================================
    def response_downloaded(self, response, request, spider):
        self.processed += 1
        if self.progress:
            self.progress.update(1)
