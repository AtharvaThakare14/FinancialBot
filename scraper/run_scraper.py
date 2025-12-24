import sys
import os
from pathlib import Path

scraper_dir = Path(__file__).parent
sys.path.insert(0, str(scraper_dir))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def main():
    """
    Run the Bank of Maharashtra loan scraper.
    """
    settings = get_project_settings()
    
    process = CrawlerProcess(settings)
    
    from bom_scraper.spiders.loans_spider import LoansSpider
    
    process.crawl(LoansSpider)
    
    process.start()


if __name__ == "__main__":
    main()
