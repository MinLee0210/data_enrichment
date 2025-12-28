import scrapy
from urllib.parse import urljoin
import re


class KProfilesActressesSpider(scrapy.Spider):
    name = "kprofiles"
    allowed_domains = ["kprofiles.com"]
    start_urls = [
        "https://kprofiles.com/korean-actresses-profiles/",
        "https://kprofiles.com/thai-actors-actresses-list/",
        "https://kprofiles.com/korean-actors-list/",
        "https://kprofiles.com/chinese-actresses/",
        "https://kprofiles.com/chinese-actors-profile/",
    ]

    # ============================================================
    # STEP 1: GET ALL PROFILE LINKS
    # ============================================================
    def parse(self, response):
        profile_links = set()
        for a in response.css("a[href]"):
            href = a.attrib.get("href", "").strip()
            text = a.css("::text").get(default="").strip()
            if (
                href.startswith("https://kprofiles.com/")
                and "profile" in href
                and text
            ):
                profile_links.add(href)

        self.logger.info(f"{response.url} → {len(profile_links)} profiles")

        for url in sorted(profile_links):
            yield scrapy.Request(url, callback=self.parse_profile)

    # ============================================================
    # STEP 2: PARSE PROFILE PAGE
    # ============================================================
    def parse_profile(self, response):
        name = response.css("h1::text").get(default="").strip()
        image_url = response.css("img.wp-post-image::attr(src)").get()

        # ============================================================
        # NOTE (caption below image) — nice to have
        # ============================================================
        note = " ".join(
            response.css(
                "div.entry-content > p::text, "
                "div.entry-content > p em::text"
            ).getall()
        ).strip()

        # ============================================================
        # STRICT FIELDS (background-color spans ONLY)
        # ============================================================
        strict = {}
        center_p = response.css("div.entry-content p[style*='text-align']")
        if center_p:
            p = center_p[0]
            bg_spans = p.xpath(".//span[contains(@style, 'background-color')]")
            for span in bg_spans:
                label = span.xpath("normalize-space(text())").get()
                if not label or not label.endswith(":"):
                    continue
                label = label.replace(":", "").strip()

                # collect nodes until <br>
                value_nodes = span.xpath(
                    "following-sibling::node()["
                    "not(self::br)]["
                    "preceding-sibling::span[1] = current()"
                    "]"
                )
                parts = []
                for node in value_nodes:
                    if node.root.tag == "a":
                        txt = node.xpath("normalize-space(text())").get()
                        if txt:
                            parts.append(txt)
                    else:
                        txt = node.xpath("normalize-space(.)").get()
                        if txt:
                            parts.append(txt)

                value = " ".join(parts).replace("\xa0", " ").strip()
                if value:
                    strict[label] = value

        # ============================================================
        # MAP STRICT → CORE FIELDS (MUST HAVE)
        # ============================================================
        date_of_birth = strict.get("Birthday", "")
        height = strict.get("Height", "")
        weight = strict.get("Weight", "")
        nationality = strict.get("Nationality", "")

        # job inference (fallback only)
        job = ""
        note_l = note.lower()
        if "actress" in note_l:
            job = "Actress"
        elif "actor" in note_l:
            job = "Actor"
        elif "model" in note_l:
            job = "Model"

        # ============================================================
        # OPTIONAL FACTS (nice to have)
        # ============================================================
        facts_list = []
        full_text = p.xpath("string(.)").get() if center_p else ""
        for line in full_text.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("–"):
                facts_list.append(line.lstrip("-– ").strip())

        yield {
            "profile_url": response.url,
            "name": name,
            # ===== STRICT (guaranteed correct) =====
            "dateOfBirth": date_of_birth,
            "height": height,
            "weight": weight,
            "nationality": nationality,
            "job": job,
            # ===== NICE TO HAVE =====
            "note": note,
            "image_url": image_url,
            "facts": strict,
            "facts_list": facts_list,
        }