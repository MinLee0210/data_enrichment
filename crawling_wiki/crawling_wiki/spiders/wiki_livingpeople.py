import scrapy
from urllib.parse import urljoin
from datetime import datetime
import re


# ============================================================
# TEXT CLEANER FOR INFOBOX VALUES
# ============================================================
def clean_infobox_text(nodes):
    """
    Clean infobox text by removing:
    - CSS selector junk from hlist (::before/::after)
    - style blocks injected into text
    - reference markers [1], [2]
    - whitespace fragmentation
    - bullets injected by CSS
    """
    if not nodes:
        return ""

    raw = " ".join(nodes).strip()

    # Remove style blocks like ".mw-parser-output .hlist ... { ... }"
    raw = re.sub(r"\.mw-parser-output[^{}]+{[^{}]+}", "", raw)

    # Remove CSS selector fragments
    raw = re.sub(r"[.#]mw[\w\-\s:;{}().,]*", "", raw)

    # Remove leftover { ... }
    raw = re.sub(r"{[^{}]*}", "", raw)

    # Remove reference markers: [1], [23], [a], etc.
    raw = re.sub(r"\[\d+\]", "", raw)
    raw = re.sub(r"\[[a-zA-Z]\]", "", raw)

    # Remove CSS bullet symbols
    raw = raw.replace("•", " ")

    # Clean commas, spaces
    raw = raw.replace(" ,", ",")
    raw = raw.replace(" ;", ";")

    # Collapse whitespace
    raw = re.sub(r"\s+", " ", raw).strip()

    return raw


# ============================================================
# SPIDER
# ============================================================
class LivingPeopleSpider(scrapy.Spider):
    name = "living_people"
    allowed_domains = ["wikipedia.org"]
    # start_urls = ["https://en.wikipedia.org/wiki/Category:Living_people"]
    # start_urls = ["https://en.wikipedia.org/wiki/Category:Possibly_living_people"]
    start_urls = [
        "https://en.wikipedia.org/wiki/Category:Date_of_birth_missing_(living_people)", 
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_missing_(living_people)", 
        "https://en.wikipedia.org/wiki/Category:Year_of_death_missing", 
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_missing"
        "https://en.wikipedia.org/wiki/Category:2025_deaths", 
        "https://en.wikipedia.org/wiki/Category:Place_of_birth_missing", 
        "https://en.wikipedia.org/wiki/Category:Place_of_death_missing", 
        "https://en.wikipedia.org/wiki/Category:Date_of_birth_unknown"
        "https://en.wikipedia.org/wiki/Category:Year_of_birth_unknown"
        "https://en.wikipedia.org/wiki/Category:Place_of_death_unknown"
    ]

    # --------------------------------------------------------
    # Normalize URL
    # --------------------------------------------------------
    def normalize_url(self, base, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(base, url)
        return url

    # --------------------------------------------------------
    # PARSE CATEGORY PAGE
    # --------------------------------------------------------
    def parse(self, response):
        people = response.css("#mw-pages .mw-category-group ul li a")
        self.logger.info(f"📄 {response.url} → {len(people)} profiles found")

        for p in people:
            name = p.css("::text").get("").strip()
            href = self.normalize_url(response.url, p.attrib.get("href"))

            yield response.follow(
                href,
                callback=self.parse_profile,
                meta={"name": name, "profile_url": href},
            )

        # -------- NEXT PAGE ONLY --------
        next_page = response.xpath("//a[contains(text(), 'next page')]/@href").get()
        if next_page:
            next_url = self.normalize_url(response.url, next_page)
            self.logger.info(f"➡️ Moving to next page → {next_url}")
            yield response.follow(next_url, callback=self.parse)

    # --------------------------------------------------------
    # PARSE PROFILE PAGE
    # --------------------------------------------------------
    def parse_profile(self, response):
        name = response.meta["name"]
        profile_url = response.meta["profile_url"]

        infobox = response.css("table.infobox")

        # ======================================================
        # 1) FULL METADATA EXTRACTION (ALL INFOBOX FIELDS)
        # ======================================================
        metadata = {}

        rows = infobox.css("tr")
        for r in rows:
            # Extract label
            raw_label = (
                r.css("th::text").get()
                or "".join(r.css("th *::text").getall())
            )
            # Extract value
            raw_value = r.css("td *::text").getall()

            label = clean_infobox_text([raw_label]) if raw_label else ""
            value = clean_infobox_text(raw_value)

            if label and value:
                metadata[label] = value

        # ======================================================
        # 2) IMAGE URL
        # ======================================================
        img = infobox.css("img::attr(src)").get()
        image_url = self.normalize_url(response.url, img)

        # ======================================================
        # 3) DESCRIPTION (first paragraph)
        # ======================================================
        description = " ".join(
            response.css("#mw-content-text .mw-parser-output > p::text").getall()
        ).strip()
        metadata["description"] = description

        # ======================================================
        # 4) Top-level Fields (Derived)
        # ======================================================
        born_raw = metadata.get("Born", "")

        date_of_birth = ""
        home_place = ""

        if born_raw:
            # Example: "14 October 1960 (age 65) Ørland Municipality, Norway"
            parts = born_raw.split(")")
            dob_str = parts[0].split("(")[0].strip()

            # Try parse to ISO
            try:
                dt = datetime.strptime(dob_str, "%d %B %Y")
                date_of_birth = dt.strftime("%Y-%m-%dT00:00:00Z")
            except:
                date_of_birth = dob_str

            # Extract birthplace
            if len(parts) > 1:
                home_place = parts[1].strip()

        # Main Type (Occupation)
        main_type = (
            metadata.get("Occupation", "")
            or metadata.get("Occupations", "")
        )

        # Gender heuristic
        gender = ""
        desc_lower = description.lower()
        if desc_lower.startswith("he ") or " he " in desc_lower:
            gender = "Male"
        elif desc_lower.startswith("she ") or " she " in desc_lower:
            gender = "Female"

        # ======================================================
        # FINAL OUTPUT
        # ======================================================
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
