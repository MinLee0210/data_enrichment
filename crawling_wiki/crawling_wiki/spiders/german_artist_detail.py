import json
from pathlib import Path
import scrapy


ROOT_DIR = Path(__file__).resolve().parents[2]


class GermanArtistDetailSpider(scrapy.Spider):
    name = "german_artist_detail"
    input_file = ROOT_DIR / "german_artist_wiki.json"

    def start_requests(self):
        with self.input_file.open("r", encoding="utf-8") as f:
            artists = json.load(f)

        for artist in artists:
            yield scrapy.Request(
                url=artist["href"],
                callback=self.parse_artist,
                cb_kwargs={"title": artist["title"]},
            )

    def parse_artist(self, response, title):
        image_url = self.extract_image_url(response)
        summary = self.extract_summary(response)

        yield {
            "title": title,
            "url": response.url,
            "summary": summary,
            "image_urls": [image_url]
            if image_url
            else [],  # required by ImagesPipeline
        }

    @staticmethod
    def extract_image_url(response) -> str | None:
        image_url = (
            response.css(".infobox img::attr(src)").get()
            or response.css("figure a img::attr(src)").get()
        )
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url
        return image_url

    @staticmethod
    def extract_summary(response) -> str | None:
        for p in response.css("div.mw-parser-output > p"):
            text = " ".join(p.css("::text").getall()).strip()
            if text:
                return text
        return None
