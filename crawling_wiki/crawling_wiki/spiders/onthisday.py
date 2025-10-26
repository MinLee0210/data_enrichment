import scrapy, random
from urllib.parse import urljoin

# user_agents = [
#     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#     'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#     'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/121.0',
#     'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
# ]


class OnThisDaySpider(scrapy.Spider):
    name = "onthisday"
    allowed_domains = ["onthisday.com"]
    start_urls = [
        # "https://www.onthisday.com/people/generation/generation-z",
        # "https://www.onthisday.com/people/generation/generation-alpha",
        # "https://www.onthisday.com/people/generation/millennial",
        # "https://www.onthisday.com/people/generation/generation-x",
        # "https://www.onthisday.com/people/generation/baby-boomer",
        # "https://www.onthisday.com/people/generation/silent-generation",
        # "https://www.onthisday.com/people/generation/lost-generation"
        "https://www.onthisday.com/people/admirals",
        "https://www.onthisday.com/people/profession/anthropologists",
        "https://www.onthisday.com/people/artists",
        "https://www.onthisday.com/people/assassins",
        "https://www.onthisday.com/people/astronauts",
        "https://www.onthisday.com/people/profession/us-attorneys-general",
        "https://www.onthisday.com/people/australian-prime-ministers",
        "https://www.onthisday.com/people/profession/automobile-pioneers",
        "https://www.onthisday.com/people/aviators",
        "https://www.onthisday.com/people/british-prime-ministers",
        "https://www.onthisday.com/people/canadian-prime-ministers",
        "https://www.onthisday.com/people/chess-grandmasters",
        "https://www.onthisday.com/people/chinese-leaders",
        "https://www.onthisday.com/people/nationality/ukrainian",
    ]
    # ua = random.choice(user_agents)

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0.5,
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEEDS": {"onthisday_people.json": {"format": "json", "encoding": "utf8"}},
        # "USER_AGENT": (
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
        #     "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        # ),
    }

    def normalize(self, base, url):
        """Ensure URLs are absolute and valid."""
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        return urljoin(base, url)

    def parse(self, response):
        """Extract all people on the page, then go to the next page."""
        for li in response.css("ul.photo-list--full-width li"):
            profile_url = self.normalize(response.url, li.css("a::attr(href)").get())
            image_url = self.normalize(response.url, li.css("img::attr(src)").get())

            # Clean up name (remove ranking numbers, commas, etc.)
            raw_texts = li.css("a::text").getall()
            name = " ".join(
                [t.strip() for t in raw_texts if t.strip() and not t.strip().isdigit()]
            )
            name = name.split(",")[0] if "," in name else name

            if not name:
                continue

            yield response.follow(
                profile_url,
                callback=self.parse_profile,
                meta={
                    "profile_url": profile_url,
                    "name": name,
                    "image_url": image_url,
                },
                # headers={"User-Agent": self.custom_settings["USER_AGENT"]},
            )

        # --- Pagination handler ---
        next_page = (
            response.css("ul.pag a.pag_next::attr(href)").get()
            or response.css("ul.pag li a[rel='next']::attr(href)").get()
        )

        if next_page:
            next_page_url = self.normalize(response.url, next_page)
            print(f"\n🌀 Moving to next page: {next_page_url}\n")
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                # headers={"User-Agent": self.custom_settings["USER_AGENT"]},
            )
        else:
            print("\n✅ Finished scraping all pages for this generation.\n")

    def parse_profile(self, response):
        """Extract full profile information."""
        profile_url = response.meta["profile_url"]
        name = response.meta["name"]
        image_url = response.meta["image_url"]

        def extract_after_label(label):
            return response.xpath(
                f"//b[text()='{label}']/following-sibling::a/text()"
            ).get()

        def extract_text_after_label(label):
            return response.xpath(
                f"//b[text()='{label}']/following-sibling::text()"
            ).get()

        main_type = extract_after_label("Profession:") or ""
        nationality = extract_after_label("Nationality:") or ""
        date_part = extract_after_label("Born:") or ""
        year_part = response.xpath(
            "//b[text()='Born:']/following-sibling::a[2]/text()"
        ).get()
        birthplace = extract_text_after_label("Birthplace:") or ""
        about = " ".join(
            response.xpath(
                "//b[text()='Biography:']/following-sibling::text()"
            ).getall()
        ).strip()

        if date_part and year_part:
            date_of_birth = f"{date_part} {year_part}"
        else:
            date_of_birth = date_part or year_part or ""

        yield {
            "profile_url": profile_url,
            "name": name,
            "mainType": main_type,
            "image_url": image_url,
            "homePlace": birthplace.strip(),
            "gender": "",
            "dateOfBirth": date_of_birth,
            "nationality": nationality,
            "about": about,
        }
