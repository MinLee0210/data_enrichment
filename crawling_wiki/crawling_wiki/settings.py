BOT_NAME = "crawling_wiki"

SPIDER_MODULES = ["crawling_wiki.spiders"]
NEWSPIDER_MODULE = "crawling_wiki.spiders"

ROBOTSTXT_OBEY = True
FEED_EXPORT_ENCODING = "utf-8"

DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS = 4

FLARESOLVERR_URL = "http://localhost:8191/"


# ============================
# Playwright Settings
# ============================

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}

# ============================
# Rate Limit
# ============================

CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4

DOWNLOAD_DELAY = 0.5  # Playwright ổn nên delay thấp hơn được
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 3

COOKIES_ENABLED = True
