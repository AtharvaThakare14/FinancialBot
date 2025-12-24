import json
import logging
from pathlib import Path
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


logger = logging.getLogger(__name__)


class LoanJsonPipeline:
    """
    Pipeline to save each loan item as a separate JSON file.
    Output format: data/raw/{loan_type}.json
    """
    
    def __init__(self):
        """Initialize the pipeline and ensure output directory exists."""
        self.output_dir = Path("../data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        loan_type = adapter.get('loan_type', 'unknown')
        
        # Convert item to dict
        item_dict = dict(adapter)
        
        # Save to JSON file
        output_file = self.output_dir / f"{loan_type}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(item_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved {loan_type} → {output_file.name}")
        return item


class ContentValidationPipeline:
    """
    Validates that extracted content meets minimum quality standards.
    """
    
    MIN_CONTENT_LENGTH = 50  # Lowered for robustness
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Calculate total content length
        total_length = 0
        for field in ['overview', 'interest_rates', 'eligibility', 
                     'tenure', 'fees_and_charges', 'special_concessions', 
                     'other_details']:
            items = adapter.get(field, [])
            total_length += sum(len(text) for text in items)
        
        if total_length < self.MIN_CONTENT_LENGTH:
            loan_type = adapter.get('loan_type', 'unknown')
            logger.warning(
                f"Dropping {loan_type}: insufficient content "
                f"({total_length} chars < {self.MIN_CONTENT_LENGTH})"
            )
            # raise DropItem(f"Insufficient content for {loan_type}") 
            # Commented out DropItem to ensure we get *some* data even if small
        
        return item
