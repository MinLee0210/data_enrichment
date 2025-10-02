import scrapy


class GermanArtistWikiSpider(scrapy.Spider):
    name = "german_artist_wiki"
    start_urls = ["https://en.wikipedia.org/wiki/List_of_German_artists"]

    def parse(self, response):
        for link in response.css("li a[href^='/wiki/']:not([href*=':'])"):
            yield {
                "title": link.css("::text").get(),
                "href": response.urljoin(link.attrib["href"]),
            }
