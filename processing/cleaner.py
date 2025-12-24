"""
HTML content cleaner for loan product data.

This module cleans scraped HTML content, removing noise and extracting
only loan-relevant information.

Cleaning steps:
1. Remove HTML tags and formatting
2. Remove navigation, ads, and boilerplate
3. Normalize whitespace
4. Extract structured loan information
5. Preserve important formatting (lists, tables)
"""

import re
import json
from typing import Dict, List, Optional
from pathlib import Path
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class LoanContentCleaner:
    """
    Cleans and extracts loan-relevant content from scraped HTML.
    
    Focuses on preserving:
    - Interest rates
    - Eligibility criteria
    - Tenure information
    - Processing fees
    - Special concessions
    - Terms and conditions
    """
    
    def __init__(self):
        """Initialize the cleaner with loan-specific patterns."""
        # Keywords that indicate loan-relevant content
        self.relevant_keywords = [
            'interest rate', 'rate of interest', 'roi',
            'eligibility', 'eligible', 'criteria',
            'tenure', 'period', 'duration',
            'processing fee', 'charges', 'fees',
            'concession', 'discount', 'benefit',
            'loan amount', 'maximum', 'minimum',
            'income', 'salary', 'age',
            'document', 'required', 'documentation',
            'repayment', 'emi', 'installment',
            'collateral', 'security', 'guarantee',
            'women', 'senior citizen', 'defence', 'government',
        ]
        
        # Patterns to remove (noise)
        self.noise_patterns = [
            r'©\s*\d{4}.*?All rights reserved',
            r'Privacy Policy',
            r'Terms (?:and|&) Conditions',
            r'Cookie Policy',
            r'Follow us on',
            r'Subscribe to.*?newsletter',
            r'Click here to.*?',
            r'Download.*?(?:app|application)',
        ]
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content and extract text.
        
        Args:
            html_content: Raw HTML string
        
        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 
                        'iframe', 'noscript', 'aside', 'form']):
            tag.decompose()
        
        # Remove elements with common noise classes/ids
        noise_selectors = [
            {'class': re.compile(r'(nav|menu|sidebar|footer|header|ad|banner|cookie)', re.I)},
            {'id': re.compile(r'(nav|menu|sidebar|footer|header|ad|banner)', re.I)},
        ]
        
        for selector in noise_selectors:
            for element in soup.find_all(attrs=selector):
                element.decompose()
        
        # Extract text with structure preservation
        text = soup.get_text(separator='\n', strip=True)
        
        return text
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text content.
        
        Args:
            text: Raw text string
        
        Returns:
            Normalized text
        """
        # Remove noise patterns
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r' +', ' ', text)  # Single spaces
        text = re.sub(r'\t+', ' ', text)  # Tabs to spaces
        
        # Remove lines that are too short (likely noise)
        lines = text.split('\n')
        lines = [line.strip() for line in lines if len(line.strip()) > 3]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def extract_loan_sections(self, text: str) -> Dict[str, str]:
        """
        Extract structured loan information sections.
        
        Args:
            text: Cleaned text content
        
        Returns:
            Dictionary of section name to content
        """
        sections = {}
        
        # Common section headers in loan pages
        section_patterns = {
            'interest_rate': r'(?:interest rate|rate of interest|roi).*?(?=\n[A-Z]|\n\n|$)',
            'eligibility': r'(?:eligibility|eligible|criteria).*?(?=\n[A-Z]|\n\n|$)',
            'tenure': r'(?:tenure|period|duration|repayment period).*?(?=\n[A-Z]|\n\n|$)',
            'fees': r'(?:processing fee|charges|fees).*?(?=\n[A-Z]|\n\n|$)',
            'amount': r'(?:loan amount|maximum|minimum).*?(?=\n[A-Z]|\n\n|$)',
            'documents': r'(?:document|required|documentation).*?(?=\n[A-Z]|\n\n|$)',
            'features': r'(?:feature|benefit|highlight).*?(?=\n[A-Z]|\n\n|$)',
        }
        
        for section_name, pattern in section_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            content = ' '.join([m.group(0) for m in matches])
            if content:
                sections[section_name] = content.strip()
        
        return sections
    
    def is_relevant_content(self, text: str) -> bool:
        """
        Check if text contains loan-relevant information.
        
        Args:
            text: Text to check
        
        Returns:
            True if relevant, False otherwise
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.relevant_keywords)
    
    def clean_loan_data(self, raw_data: Dict) -> Dict:
        """
        Clean complete loan data dictionary.
        
        Args:
            raw_data: Raw scraped data
        
        Returns:
            Cleaned data dictionary
        """
        logger.info(f"Cleaning {raw_data.get('loan_type', 'unknown')} data")
        
        # Clean HTML content
        if 'html_content' in raw_data:
            cleaned_text = self.clean_html(raw_data['html_content'])
        else:
            cleaned_text = raw_data.get('text_content', '')
        
        # Normalize text
        normalized_text = self.normalize_text(cleaned_text)
        
        # Extract sections
        sections = self.extract_loan_sections(normalized_text)
        
        # Build cleaned data
        cleaned_data = {
            'loan_type': raw_data.get('loan_type', 'unknown'),
            'url': raw_data.get('url', ''),
            'title': raw_data.get('title', ''),
            'cleaned_text': normalized_text,
            'sections': sections,
            'metadata': {
                'original_length': len(raw_data.get('text_content', '')),
                'cleaned_length': len(normalized_text),
                'sections_found': list(sections.keys()),
            }
        }
        
        logger.info(
            f"Cleaned {cleaned_data['loan_type']}: "
            f"{cleaned_data['metadata']['original_length']} → "
            f"{cleaned_data['metadata']['cleaned_length']} chars, "
            f"{len(sections)} sections"
        )
        
        return cleaned_data
    
    def clean_all_files(self, input_dir: str = "data/raw", 
                       output_dir: str = "data/processed") -> List[Dict]:
        """
        Clean all scraped loan files.
        
        Args:
            input_dir: Directory containing raw data
            output_dir: Directory to save cleaned data
        
        Returns:
            List of cleaned data dictionaries
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cleaned_data_list = []
        
        # Process all JSON files
        for json_file in input_path.glob('*.json'):
            if json_file.name == 'scraping_summary.json':
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                cleaned_data = self.clean_loan_data(raw_data)
                cleaned_data_list.append(cleaned_data)
                
                # Save cleaned data
                output_file = output_path / f"cleaned_{json_file.name}"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved cleaned data to {output_file}")
                
            except Exception as e:
                logger.error(f"Error cleaning {json_file}: {e}", exc_info=True)
        
        # Save consolidated cleaned data
        consolidated_file = output_path / "all_loans_cleaned.json"
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data_list, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved consolidated data to {consolidated_file}")
        
        return cleaned_data_list


def main():
    """Main function to run the cleaner."""
    cleaner = LoanContentCleaner()
    cleaned_data = cleaner.clean_all_files()
    
    print(f"\n✓ Successfully cleaned {len(cleaned_data)} loan product pages")
    print(f"✓ Cleaned data saved to data/processed/")
    
    # Print summary
    for data in cleaned_data:
        print(f"\n{data['loan_type'].upper()}:")
        print(f"  - Original: {data['metadata']['original_length']} chars")
        print(f"  - Cleaned: {data['metadata']['cleaned_length']} chars")
        print(f"  - Sections: {', '.join(data['metadata']['sections_found'])}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
