import scrapy
from datetime import datetime


class LoanItem(scrapy.Item):
    """
    Structured item for loan product information.
    """
    
    # Metadata fields
    loan_type = scrapy.Field()         
    source_url = scrapy.Field()         
    scraped_at = scrapy.Field()         
    
    # Content sections (all are lists of strings)
    overview = scrapy.Field()           
    interest_rates = scrapy.Field()     
    eligibility = scrapy.Field()        # Eligibility criteria
    tenure = scrapy.Field()             # Loan tenure details
    fees_and_charges = scrapy.Field()   # Processing fees, etc.
    special_concessions = scrapy.Field() # Discounts for women, defence, etc.
    other_details = scrapy.Field()      # Tables, misc info
    
    def __init__(self, *args, **kwargs):
        """Initialize with empty lists for all content fields."""
        super().__init__(*args, **kwargs)
        
        # Set defaults
        self.setdefault('overview', [])
        self.setdefault('interest_rates', [])
        self.setdefault('eligibility', [])
        self.setdefault('tenure', [])
        self.setdefault('fees_and_charges', [])
        self.setdefault('special_concessions', [])
        self.setdefault('other_details', [])
        self.setdefault('scraped_at', datetime.utcnow().isoformat())
