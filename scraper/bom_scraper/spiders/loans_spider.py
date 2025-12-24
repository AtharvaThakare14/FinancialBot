import re
from bom_scraper.items import LoanItem,scrapy


class LoansSpider(scrapy.Spider):
    name = "bom_loans"
    allowed_domains = ["bankofmaharashtra.in", "bankofmaharashtra.bank.in"]
    
    start_urls = [
        "https://bankofmaharashtra.bank.in/personal-banking/loans/home-loan",
        "https://bankofmaharashtra.bank.in/personal-banking/loans/personal-loan",
        "https://bankofmaharashtra.in/",
        "https://bankofmaharashtra.bank.in/personal-banking/loans/car-loan",
        "https://bankofmaharashtra.bank.in/personal-loan-for-businessclass-having-home-loan-with-us",
        "https://bankofmaharashtra.bank.in/educational-loans?utm_source=chatgpt.com"

    ]
    
    url_to_loan_type = {
        "home-loan": "home_loan",
        "personal-loan": "personal_loan",
        "education-loan": "education_loan",
        "vehicle-loan": "vehicle_loan",
    }
    
    def parse(self, response):
        loan_type = self._get_loan_type(response.url)
        self.logger.info(f"Parsing {loan_type} from {response.url}")
        
        item = LoanItem()
        item['loan_type'] = loan_type
        item['source_url'] = response.url
        
        main_content = self._find_main_content(response)
        
        if not main_content:
            self.logger.warning(f"No main content found for {loan_type}")
            # Try to grab body as last resort if nothing found
            main_content = response.css('body')
        
        self._extract_headings_and_paragraphs(main_content, item)
        self._extract_tables(main_content, item)
        
        yield item
    
    def _get_loan_type(self, url):
        for key, value in self.url_to_loan_type.items():
            if key in url:
                return value
        return "unknown_loan"
    
    def _find_main_content(self, response):
        selectors = [
            'div.field--name-body', 'div.node__content', 'div.region-content',
            'article.node', 'main', 'div.content', 'div#content', 'div.main-content',
        ]
        for selector in selectors:
            content = response.css(selector)
            if content:
                text = ' '.join(content.css('::text').getall())
                if len(text) > 100:
                    return content
        return None
    
    def _extract_headings_and_paragraphs(self, content, item):
        for element in content.css('h2, h3, h4, p, li'):
            text = element.css('::text').get()
            if not text:
                text = ' '.join(element.css('::text').getall())
            text = text.strip()
            if self._is_noise(text):
                continue
            section = self._classify_content(text)
            item[section].append(text)
    
    def _extract_tables(self, content, item):
        for table in content.css('table'):
            rows = []
            for tr in table.css('tr'):
                cells = [c.css('::text').get().strip() for c in tr.css('th, td') if c.css('::text').get()]
                if cells:
                    rows.append(' | '.join(cells))
            if rows:
                item['other_details'].extend(rows)
    
    def _is_noise(self, text):
        if not text or len(text) < 10: return True
        return False
    
    def _classify_content(self, text):
        t = text.lower()
        if any(x in t for x in ['interest', 'rate', '%']): return 'interest_rates'
        if any(x in t for x in ['eligib', 'criteria']): return 'eligibility'
        if any(x in t for x in ['tenure', 'period']): return 'tenure'
        if any(x in t for x in ['fee', 'charge']): return 'fees_and_charges'
        return 'overview'
