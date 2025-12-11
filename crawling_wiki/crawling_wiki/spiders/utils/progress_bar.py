from tqdm import tqdm

class ProgressBarExtension:
    def __init__(self):
        self.pbar = tqdm(desc="Profiles crawled", unit="profile")

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()

        crawler.signals.connect(ext.item_scraped, signal=crawler.signals.item_scraped)
        crawler.signals.connect(ext.spider_closed, signal=crawler.signals.spider_closed)

        return ext

    def item_scraped(self, item, spider):
        # Update tqdm bar for each scraped item
        self.pbar.update(1)

    def spider_closed(self, spider):
        self.pbar.close()
