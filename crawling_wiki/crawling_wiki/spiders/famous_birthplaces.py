import scrapy
from urllib.parse import urljoin
import re


class FamousBirthplacesFullSpider(scrapy.Spider):
    name = "famous_birthplaces_full"
    allowed_domains = ["famousbirthdays.com"]
    start_urls = ["https://www.famousbirthdays.com/birthplace/"]

    custom_settings = {
        "FEEDS": {
            "famous_birthplaces_full.json": {"format": "json", "encoding": "utf8"}
        },
        "DOWNLOAD_DELAY": 0.5,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def normalize(self, base, url):
        """Ensure absolute URLs"""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(base, url)
        return url

    def parse(self, response):
        """Step 1: Get all country URLs"""
        for a in response.css("a.tile::attr(href)").getall():
            country_url = urljoin(response.url, a)
            yield scrapy.Request(
                url=country_url,
                callback=self.parse_country,
                meta={"birthplace": a.split("/")[-1].replace(".html", "").capitalize()},
            )

    def parse_country(self, response):
        """Step 2: Get all profile URLs within each country page"""
        birthplace = response.meta["birthplace"]

        for person in response.css("a.tile"):
            profile_url = person.css("::attr(href)").get()
            name_raw = person.css("p.type-16-18-small::text").get(default="").strip()
            main_type = person.css("p.tile__description::text").get(default="").strip()
            image_url = person.css("div.tile__picture img::attr(src)").get()

            # Clean name like "Josh Richards, 23" → "Josh Richards"
            name = re.sub(r",\s*\d+$", "", name_raw).strip()

            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

            # Pass partial info to next page
            yield scrapy.Request(
                url=self.normalize(response.url, profile_url),
                callback=self.parse_profile,
                meta={
                    "profile_url": self.normalize(response.url, profile_url),
                    "name": name,
                    "mainType": main_type,
                    "image_url": image_url or "",
                    "homePlace": birthplace,
                },
            )

        # pagination
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                callback=self.parse_country,
                meta={"birthplace": birthplace},
            )

    def parse_profile(self, response):
        """Step 3: Extract details from profile page"""
        name = response.meta["name"]
        main_type = response.meta["mainType"]
        image_url = response.meta["image_url"]
        birthplace = response.meta["homePlace"]
        profile_url = response.meta["profile_url"]

        # extract details
        date_of_birth = response.css(
            "span:contains('Birthday') + span a::text"
        ).getall()
        date_of_birth = " ".join(date_of_birth).strip() if date_of_birth else ""

        gender = ""
        # gender is not available directly on site; can infer later if you want

        # birthplace detail if exists on profile
        birth_city = response.css("span:contains('Birthplace') + span a::text").getall()
        if birth_city:
            birthplace = ", ".join(birth_city).strip()

        # extract About section
        about = (
            response.css("div.about h2:contains('About') + p::text")
            .get(default="")
            .strip()
        )
        before_fame = (
            response.css("div.about h2:contains('Before Fame') + p::text")
            .get(default="")
            .strip()
        )
        trivia = (
            response.css("div.about h2:contains('Trivia') + p::text")
            .get(default="")
            .strip()
        )

        yield {
            "profile_url": profile_url or "",
            "name": name,
            "mainType": main_type,
            "image_url": image_url or "",
            "homePlace": birthplace,
            "gender": gender,
            "dateOfBirth": date_of_birth,
            "about": about,
            "beforeFame": before_fame,
            "trivia": trivia,
        }
