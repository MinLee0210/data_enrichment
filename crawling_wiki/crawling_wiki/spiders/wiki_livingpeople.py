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
class LivingPeopleSpider(scrapy.Spider):
    name = "living_people"
    allowed_domains = ["wikipedia.org"]

    start_urls = [
        "https://en.wikipedia.org/wiki/Category:Date_of_birth_missing_(living_people)",
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_missing_(living_people)",
        "https://en.wikipedia.org/wiki/Category:Year_of_death_missing",
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_missing",
        "https://en.wikipedia.org/wiki/Category:2025_deaths",
        "https://en.wikipedia.org/wiki/Category:Place_of_birth_missing",
        "https://en.wikipedia.org/wiki/Category:Place_of_death_missing",
        "https://en.wikipedia.org/wiki/Category:Date_of_birth_unknown",
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_unknown",
        "https://en.wikipedia.org/wiki/Category:Place_of_death_unknown",
        "https://en.wikipedia.org/wiki/Category:Living_people",
        "https://en.wikipedia.org/wiki/Category:Possibly_living_people",
        "https://en.wikipedia.org/wiki/Category:Politicians_executed_during_the_Iranian_Revolution",
        "https://en.wikipedia.org/wiki/Category:Lists_of_Chinese_people",
    ]

    existing_urls = set()
    expected = 0
    processed = 0
    progress = None

    # ============================================================
    # REGISTER SIGNALS (to enable tqdm + JSON loading)
    # ============================================================
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)

        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.response_downloaded, signal=signals.response_downloaded)

        return spider

    # ============================================================
    # OPEN SPIDER: load JSON + initialize tqdm
    # ============================================================
    def spider_opened(self, spider):
        # ---- Load JSON files ----
        cwd = os.getcwd()
        json_pattern = os.path.join(cwd, "living_people_*.json")
        json_files = glob.glob(json_pattern)

        self.logger.info(f"📌 Loading previous files:\n{json_files}")

        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for entry in data:
                    url = entry.get("profile_url")
                    if url:
                        self.existing_urls.add(url)

            except Exception as e:
                self.logger.info(f"❌ Failed to load {jf}: {e}")

        self.logger.info(f"📌 Loaded {len(self.existing_urls)} existing profile URLs")

        # ---- Init tqdm ----
        self.progress = tqdm(total=0, desc="Crawling profiles", unit="page")

    def spider_closed(self, spider):
        if self.progress:
            self.progress.close()

    # ============================================================
    # NORMALIZE URL
    # ============================================================
    def normalize_url(self, base, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(base, url)
        return url

    # ============================================================
    # CATEGORY PAGE PARSER
    # ============================================================
    def parse(self, response):
        people = response.css("#mw-pages .mw-category-group ul li a")
        self.logger.info(f"📄 {response.url} → {len(people)} profiles found")

        for p in people:
            name = p.css("::text").get("").strip()
            href = self.normalize_url(response.url, p.attrib.get("href"))

            # Skip if already scraped
            if href in self.existing_urls:
                continue

            # Increase expected tasks
            self.expected += 1
            self.progress.total = self.expected
            self.progress.refresh()

            yield response.follow(
                href,
                callback=self.parse_profile,
                meta={"name": name, "profile_url": href},
            )

        # Pagination
        next_page = response.xpath("//a[contains(text(), 'next page')]/@href").get()
        if next_page:
            next_url = self.normalize_url(response.url, next_page)
            yield response.follow(next_url, callback=self.parse)

    # ============================================================
    # PROFILE PAGE PARSER
    # ============================================================
    def parse_profile(self, response):
        name = response.meta["name"]
        profile_url = response.meta["profile_url"]

        if profile_url in self.existing_urls:
            return

        infobox = response.css("table.infobox")
        metadata = {}

        for r in infobox.css("tr"):
            raw_label = r.css("th::text").get() or "".join(r.css("th *::text").getall())
            raw_value = r.css("td *::text").getall()

            label = clean_infobox_text([raw_label]) if raw_label else ""
            value = clean_infobox_text(raw_value)

            if label and value:
                metadata[label] = value

        img = infobox.css("img::attr(src)").get()
        image_url = self.normalize_url(response.url, img)

        description = " ".join(
            response.css("#mw-content-text .mw-parser-output > p::text").getall()
        ).strip()
        metadata["description"] = description

        born_raw = metadata.get("Born", "")
        date_of_birth = ""
        home_place = ""

        if born_raw:
            parts = born_raw.split(")")
            dob_str = parts[0].split("(")[0].strip()

            try:
                dt = datetime.strptime(dob_str, "%d %B %Y")
                date_of_birth = dt.strftime("%Y-%m-%dT00:00:00Z")
            except:
                date_of_birth = dob_str

            if len(parts) > 1:
                home_place = parts[1].strip()

        main_type = metadata.get("Occupation", "") or metadata.get("Occupations", "")
        gender = ""

        d = description.lower()
        if d.startswith("he ") or " he " in d:
            gender = "Male"
        elif d.startswith("she ") or " she " in d:
            gender = "Female"

        yield {
            "name": name,
            "mainType": main_type,
            "dateOfBirth": date_of_birth,
            "homePlace": home_place,
            "workPlace": main_type,
            "gender": gender,
            "image_url": image_url,
            "profile_url": profile_url,
            "metadata": metadata,
        }

    # ============================================================
    # UPDATE TQDM ON EACH RESPONSE
    # ============================================================
    def response_downloaded(self, response, request, spider):
        self.processed += 1
        if self.progress:
            self.progress.update(1)
