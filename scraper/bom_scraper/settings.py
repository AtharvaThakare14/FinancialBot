"""
Scrapy settings for Bank of Maharashtra loan scraper.
"""

BOT_NAME = "bom_scraper"

SPIDER_MODULES = ["bom_scraper.spiders"]
NEWSPIDER_MODULE = "bom_scraper.spiders"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 1
DOWNLOAD_TIMEOUT = 30

ITEM_PIPELINES = {
    "bom_scraper.pipelines.ContentValidationPipeline": 100,
    "bom_scraper.pipelines.LoanJsonPipeline": 300,
}

AUTOTHROTTLE_ENABLED = True
LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
