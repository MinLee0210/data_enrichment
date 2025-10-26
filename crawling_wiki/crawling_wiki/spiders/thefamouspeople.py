import scrapy
from urllib.parse import urljoin
from datetime import datetime


class FamousProfilesSpider(scrapy.Spider):
    name = "thefamouspeople"
    allowed_domains = ["thefamouspeople.com"]
    start_urls = [
        # "https://www.thefamouspeople.com/thailand.php",
        # "https://www.thefamouspeople.com/thailand-men.php",
        # "https://www.thefamouspeople.com/thailand-women.php",
        # "https://www.thefamouspeople.com/thai-singers.php"
        # "https://www.thefamouspeople.com/ukraine.php",
        # "https://www.thefamouspeople.com/ukrainian-musicians.php",
        # "https://www.thefamouspeople.com/ukrainian-writers.php",
        # "https://www.thefamouspeople.com/ukrainian-leaders.php"
        # "https://www.thefamouspeople.com/vietnam.php",
        # "https://www.thefamouspeople.com/vietnam-men.php",
        # "https://www.thefamouspeople.com/vietnam-women.php",
        # "https://www.thefamouspeople.com/vietnamese-sportspersons.php",
        # "https://www.thefamouspeople.com/vietnamese-film-theater-personalities.php"
        # "https://www.thefamouspeople.com/south_korea.php",
        # "https://www.thefamouspeople.com/south-korean-musicians.php",
        # "https://www.thefamouspeople.com/south-korean-singers.php",
        # "https://www.thefamouspeople.com/south-korean-film-theater-personalities.php",
        # "https://www.thefamouspeople.com/south-korean-leaders.php",
        # "https://www.thefamouspeople.com/south-korean-list-of-youtubers.php",
        # "https://www.thefamouspeople.com/south-korean-business-people.php",
        # "https://www.thefamouspeople.com/south-korean-sportspersons.php",
        # "https://www.thefamouspeople.com/taiwan.php",
        # "https://www.thefamouspeople.com/taiwan-women.php",
        # "https://www.thefamouspeople.com/taiwanese-singers.php",
        # "https://www.thefamouspeople.com/taiwanese-film-theater-personalities.php",
        # "https://www.thefamouspeople.com/taiwanese-leaders.php",
        # "https://www.thefamouspeople.com/taiwanese-sportspersons.php",
        # "https://www.thefamouspeople.com/russia.php",
        # "https://www.thefamouspeople.com/russian-federation-men.php",
        # "https://www.thefamouspeople.com/russian-leaders.php",
        # "https://www.thefamouspeople.com/russian-writers.php",
        # "https://www.thefamouspeople.com/russian-intellectuals-academics.php",
        # "https://www.thefamouspeople.com/russian-musicians.php",
        # "https://www.thefamouspeople.com/russian-sportspersons.php",
        # "https://www.thefamouspeople.com/russian-activists.php",
        # "https://www.thefamouspeople.com/russian-dancers.php",
        # "https://www.thefamouspeople.com/russian-scientists.php",
        # "https://www.thefamouspeople.com/russian-physicians.php",
        # "https://www.thefamouspeople.com/russian-painters.php",
        # "https://www.thefamouspeople.com/russian-inventors-discoverers.php",
        # "https://www.thefamouspeople.com/russian-film-theater-personalities.php",
        # "https://www.thefamouspeople.com/russian-list-of-social-media-stars.php",
        # "https://www.thefamouspeople.com/russian-list-of-instagram-stars.php",
        # "https://www.thefamouspeople.com/russian-list-of-youtubers.php",
        # "https://www.thefamouspeople.com/russian-fashion.php",
        # "https://www.thefamouspeople.com/russian-lawyers-judges.php",
        # "https://www.thefamouspeople.com/russian-business-people.php",
        # "https://www.thefamouspeople.com/russian-singers.php",
        # "https://www.thefamouspeople.com/russian-media-personalities.php",
        # "https://www.thefamouspeople.com/russian-criminals.php",
        # "https://www.thefamouspeople.com/russian-lyricists-songwriters.php",
        # "https://www.thefamouspeople.com/russian-spiritual-religious-leaders.php",
        # "https://www.thefamouspeople.com/russian-engineers.php",
        "https://www.thefamouspeople.com/list-of-musical-ly.php",
        "https://www.thefamouspeople.com/list-of-twitch-stars.php",
        "https://www.thefamouspeople.com/list-of-younow-stars.php",
        "https://www.thefamouspeople.com/list-of-viners.php",
    ]

    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8",
        "DOWNLOAD_DELAY": 0.5,
        "FEEDS": {"thefamouspeople.json": {"format": "json", "encoding": "utf8"}},
    }

    def normalize_url(self, base, url):
        """Normalize relative and protocol-relative URLs."""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(base, url)
        return url

    def parse(self, response):
        articles = response.css("article.feature")
        self.logger.info(f"✅ Found {len(articles)} profiles on: {response.url}")

        for article in articles:
            # --- Name and mainType ---
            name = article.css(".ptitle-internal::text").get(default="").strip()
            main_type = (
                article.css(".ptitle-internal div::text")
                .get(default="")
                .strip("() ")
                .strip()
            )

            # --- Profile URL ---
            profile_url = (
                article.css("a.titleLink::attr(href)").get()
                or article.xpath(".//a[contains(@href, '/profiles/')]/@href").get()
            )
            profile_url = self.normalize_url(response.url, profile_url)

            # --- Image URL (MUST exist) ---
            image_node = article.css("img.combi-profile-img")
            image_url = (
                image_node.attrib.get("src")
                or image_node.attrib.get("data-src")
                or image_node.attrib.get("data-original")
            )
            image_url = self.normalize_url(response.url, image_url)

            if not image_url:
                # Fallback: try any image in the 'image' div
                image_url = article.xpath(
                    ".//div[contains(@class, 'image')]//img[contains(@src, '/thumbs/')]/@src"
                ).get()
                image_url = self.normalize_url(response.url, image_url)

            # --- Enforce existence ---
            if not image_url:
                raw_image_block = article.css("div.image").get()
                self.logger.warning(
                    f"⚠️ Missing image for {name or 'UNKNOWN'} ({response.url})\n{raw_image_block}"
                )

            # --- Extract facts ---
            def extract(label):
                val = article.xpath(
                    f".//div[@class='desc-q'][b[contains(., '{label}')]]/text()"
                ).get()
                return val.strip() if val else ""

            def to_iso(date_str):
                try:
                    dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
                    return dt.strftime("%Y-%m-%dT00:00:00Z")
                except Exception:
                    return date_str.strip()

            birth_raw = extract("Birthdate")
            if "(" in birth_raw:
                birth_raw = birth_raw.split("(")[0].strip()
            date_of_birth = to_iso(birth_raw)
            sun_sign = extract("Sun Sign")
            birthplace = extract("Birthplace")
            died = to_iso(extract("Died"))

            # --- Description ---
            description = " ".join(article.css(".descEvent::text").getall()).strip()

            # --- Gender heuristic ---
            gender = ""
            desc_lower = description
            if any(p in desc_lower for p in ["He "]):
                gender = "Male"
            elif any(p in desc_lower for p in ["She "]):
                gender = "Female"

            yield {
                "profile_url": profile_url or "",
                "name": name,
                "mainType": main_type,
                "image_url": image_url or "",
                "homePlace": birthplace,
                "gender": gender,
                "dateOfBirth": date_of_birth,
                "sunSign": sun_sign,
                "died": died,
                "description": description,
            }

        # --- Pagination ---
        next_page = response.css("ul.pagination a.next::attr(href)").get()
        if next_page:
            yield response.follow(urljoin(response.url, next_page), callback=self.parse)
