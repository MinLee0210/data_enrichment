import scrapy
from urllib.parse import urljoin


class WikiThaiPeopleSpider(scrapy.Spider):
    name = "wiki_thai_people"
    allowed_domains = ["en.wikipedia.org"]
    start_urls = [
        # "https://en.wikipedia.org/wiki/List_of_Thai_actresses",
        # "https://en.wikipedia.org/wiki/List_of_Thai_male_actors",
        "https://en.wikipedia.org/wiki/List_of_Thai_film_directors"
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEEDS": {"thai_wiki_people.json": {"format": "json", "encoding": "utf8"}},
    }

    def parse(self, response):
        """Collect profile links from list pages."""
        self.logger.info(f"Collecting links from: {response.url}")

        # collect all <li><a href="/wiki/Person"> links inside content
        links = response.css("div.mw-parser-output ul li a::attr(href)").getall()
        for link in links:
            if link.startswith("/wiki/") and not any(x in link for x in [":", "#"]):
                yield response.follow(link, callback=self.parse_profile)

    def parse_profile(self, response):
        """Extract profile info and infobox metadata."""
        def clean_join(elements):
            texts = [
                t.strip()
                for t in elements
                if t.strip() and not t.lower().startswith(".mw-parser-output")
            ]
            return " ".join(texts)

        # --- Try to extract name ---
        name = (
            response.css("table.infobox .fn::text").get()
            or response.css("#firstHeading::text").get()
            or ""
        ).strip()

        # --- Try to extract image ---
        image_url = (
            response.css("table.infobox img::attr(src)").get()
            or response.css("img.mw-file-element::attr(src)").get()
            or ""
        )
        if image_url:
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            elif image_url.startswith("/"):
                image_url = urljoin(response.url, image_url)

        # --- Extract metadata (key-value pairs) ---
        metadata = {}
        rows = response.xpath("//table[contains(@class,'infobox')]//tr[th and td]")
        for row in rows:
            key = row.xpath("normalize-space(th//text())").get()
            values = row.xpath(
                "td//text()[not(ancestor::style) and not(ancestor::script)]"
            ).getall()
            value = clean_join(values)
            if key and value:
                metadata[key] = value

        # --- Short description ---
        desc = " ".join(response.css("p::text").getall()[:3]).strip()

        yield {
            "profile_url": response.url,
            "name": name,
            "gender": response.meta.get("gender", ""),
            "image_url": image_url,
            "metadata": metadata,
            "description": desc,
        }
