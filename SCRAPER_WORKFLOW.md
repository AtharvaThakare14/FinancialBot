# Scraper Workflow: How Data Extraction and Cleaning Works

This document explains the complete workflow of how the scraper extracts data from Bank of Maharashtra website and cleans it for use in the RAG system.

---

## 🔄 Complete Workflow Overview

```
1. Scraper Initialization
   ↓
2. HTTP Request to Website
   ↓
3. HTML Parsing & Content Extraction
   ↓
4. Content Classification
   ↓
5. Data Validation
   ↓
6. JSON Storage
   ↓
7. Data Cleaning (Optional)
   ↓
8. Ready for RAG Pipeline
```

---

## 📋 Step-by-Step Process

### **STEP 1: Scraper Initialization**

**File:** `scraper/run_scraper.py`

```python
# Creates a Scrapy CrawlerProcess
process = CrawlerProcess(settings)
process.crawl(LoansSpider)  # Starts the spider
process.start()
```

**What happens:**
- Loads Scrapy settings from `bom_scraper/settings.py`
- Initializes the spider (`LoansSpider`)
- Sets up pipelines for data processing

---

### **STEP 2: HTTP Request**

**File:** `scraper/bom_scraper/spiders/loans_spider.py`

**Start URLs:**
```python
start_urls = [
    "https://bankofmaharashtra.in/home-loan",
    "https://bankofmaharashtra.in/personal-loan",
    "https://bankofmaharashtra.in/education-loan",
    "https://bankofmaharashtra.in/vehicle-loan",
]
```

**Settings (from `settings.py`):**
- `USER_AGENT`: Browser-like user agent to avoid blocking
- `DOWNLOAD_DELAY`: 1 second delay between requests (polite scraping)
- `CONCURRENT_REQUESTS`: 1 (one at a time)
- `ROBOTSTXT_OBEY`: False (doesn't check robots.txt)

**What happens:**
- Scrapy sends HTTP GET request to each URL
- Receives HTML response
- Passes response to `parse()` method

---

### **STEP 3: HTML Parsing & Content Extraction**

**File:** `scraper/bom_scraper/spiders/loans_spider.py` → `parse()` method

#### **3.1 Find Main Content Area**

```python
def _find_main_content(self, response):
    selectors = [
        'div.field--name-body',    # Drupal content field
        'div.node__content',       # Drupal node content
        'div.region-content',       # Content region
        'article.node',             # Article node
        'main',                     # HTML5 main tag
        'div.content',              # Generic content div
        'div#content',              # Content ID
        'div.main-content',         # Main content class
    ]
```

**Strategy:**
- Tries multiple CSS selectors (website structure varies)
- Checks if content has >100 characters (filters out empty/navigation)
- Falls back to `<body>` if nothing found

#### **3.2 Extract Headings and Paragraphs**

```python
def _extract_headings_and_paragraphs(self, content, item):
    for element in content.css('h2, h3, h4, p, li'):
        text = element.css('::text').get()  # Extract text
        text = text.strip()                  # Remove whitespace
        
        if self._is_noise(text):            # Filter noise
            continue
        
        section = self._classify_content(text)  # Classify content
        item[section].append(text)               # Add to appropriate section
```

**What it extracts:**
- All `<h2>`, `<h3>`, `<h4>` headings
- All `<p>` paragraphs
- All `<li>` list items

**Noise Filter:**
```python
def _is_noise(self, text):
    if not text or len(text) < 10:  # Too short = noise
        return True
    return False
```

#### **3.3 Extract Tables**

```python
def _extract_tables(self, content, item):
    for table in content.css('table'):
        rows = []
        for tr in table.css('tr'):
            cells = [c.css('::text').get().strip() 
                    for c in tr.css('th, td') 
                    if c.css('::text').get()]
            if cells:
                rows.append(' | '.join(cells))  # Join cells with |
        if rows:
            item['other_details'].extend(rows)
```

**What it does:**
- Finds all `<table>` elements
- Extracts each row (`<tr>`)
- Extracts cells (`<th>`, `<td>`)
- Joins cells with ` | ` separator
- Stores in `other_details` section

---

### **STEP 4: Content Classification**

**File:** `scraper/bom_scraper/spiders/loans_spider.py` → `_classify_content()`

```python
def _classify_content(self, text):
    t = text.lower()
    
    # Interest rates
    if any(x in t for x in ['interest', 'rate', '%']): 
        return 'interest_rates'
    
    # Eligibility
    if any(x in t for x in ['eligib', 'criteria']): 
        return 'eligibility'
    
    # Tenure
    if any(x in t for x in ['tenure', 'period']): 
        return 'tenure'
    
    # Fees
    if any(x in t for x in ['fee', 'charge']): 
        return 'fees_and_charges'
    
    # Default: overview
    return 'overview'
```

**Classification Logic:**
- Uses keyword matching (case-insensitive)
- Categorizes text into sections:
  - `interest_rates`: Contains "interest", "rate", or "%"
  - `eligibility`: Contains "eligib" or "criteria"
  - `tenure`: Contains "tenure" or "period"
  - `fees_and_charges`: Contains "fee" or "charge"
  - `overview`: Everything else

**Result:** Each text snippet is placed in the appropriate section of the `LoanItem`.

---

### **STEP 5: Data Structure**

**File:** `scraper/bom_scraper/items.py`

```python
class LoanItem(scrapy.Item):
    # Metadata
    loan_type = scrapy.Field()        # e.g., "home_loan"
    source_url = scrapy.Field()       # URL scraped from
    scraped_at = scrapy.Field()       # Timestamp
    
    # Content sections (all are lists of strings)
    overview = scrapy.Field()          # General information
    interest_rates = scrapy.Field()   # Interest rate details
    eligibility = scrapy.Field()      # Eligibility criteria
    tenure = scrapy.Field()           # Loan tenure
    fees_and_charges = scrapy.Field() # Processing fees
    special_concessions = scrapy.Field() # Discounts/benefits
    other_details = scrapy.Field()    # Tables, misc info
```

**Initialization:**
- All content fields default to empty lists `[]`
- `scraped_at` set to current UTC timestamp

---

### **STEP 6: Pipeline Processing**

**File:** `scraper/bom_scraper/pipelines.py`

#### **6.1 Content Validation Pipeline**

```python
class ContentValidationPipeline:
    MIN_CONTENT_LENGTH = 50
    
    def process_item(self, item, spider):
        # Calculate total content length
        total_length = 0
        for field in ['overview', 'interest_rates', ...]:
            items = adapter.get(field, [])
            total_length += sum(len(text) for text in items)
        
        if total_length < MIN_CONTENT_LENGTH:
            logger.warning("Insufficient content")
            # Note: Doesn't drop item (commented out DropItem)
```

**What it does:**
- Validates that scraped content meets minimum quality
- Checks total character count across all sections
- Logs warning if content is too short (but doesn't reject it)

#### **6.2 JSON Storage Pipeline**

```python
class LoanJsonPipeline:
    def __init__(self):
        self.output_dir = Path("../data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_item(self, item, spider):
        loan_type = adapter.get('loan_type', 'unknown')
        output_file = self.output_dir / f"{loan_type}.json"
        
        # Convert to dict and save as JSON
        item_dict = dict(adapter)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(item_dict, f, indent=2, ensure_ascii=False)
```

**What it does:**
- Creates `data/raw/` directory if it doesn't exist
- Converts Scrapy item to Python dictionary
- Saves as JSON file: `data/raw/{loan_type}.json`
- Uses UTF-8 encoding with 2-space indentation

**Output Example:**
```json
{
  "loan_type": "home_loan",
  "source_url": "https://bankofmaharashtra.in/home-loan",
  "scraped_at": "2025-12-24T12:00:00",
  "overview": ["Maha Super Housing Loan Scheme...", ...],
  "interest_rates": ["Interest Rate 7.10% P.A*", ...],
  "eligibility": ["Individual salaried employees...", ...],
  "tenure": ["Maximum tenure up to 30 years...", ...],
  "fees_and_charges": ["Processing fee is 0.25%...", ...],
  "special_concessions": ["0.05% concession to women...", ...],
  "other_details": ["Interest Rate | 7.10% | P.A", ...]
}
```

---

### **STEP 7: Data Cleaning (Optional)**

**File:** `processing/cleaner.py`

**Note:** This cleaner is available but may not be used in the current pipeline. The scraper already does basic cleaning during extraction.

#### **7.1 HTML Cleaning**

```python
def clean_html(self, html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 
                    'iframe', 'noscript', 'aside', 'form']):
        tag.decompose()
    
    # Remove noise elements
    noise_selectors = [
        {'class': re.compile(r'(nav|menu|sidebar|footer|header|ad|banner|cookie)', re.I)},
        {'id': re.compile(r'(nav|menu|sidebar|footer|header|ad|banner)', re.I)},
    ]
    
    # Extract text
    text = soup.get_text(separator='\n', strip=True)
    return text
```

**What it removes:**
- `<script>`, `<style>` tags
- Navigation, header, footer elements
- Ads, banners, cookie notices
- Forms, iframes, aside content

#### **7.2 Text Normalization**

```python
def normalize_text(self, text: str) -> str:
    # Remove noise patterns
    for pattern in self.noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Normalize whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
    text = re.sub(r' +', ' ', text)                 # Single spaces
    text = re.sub(r'\t+', ' ', text)                # Tabs to spaces
    
    # Remove short lines (likely noise)
    lines = text.split('\n')
    lines = [line.strip() for line in lines if len(line.strip()) > 3]
    text = '\n'.join(lines)
    
    return text.strip()
```

**What it does:**
- Removes copyright notices, privacy policy links, etc.
- Normalizes whitespace (multiple spaces → single space)
- Removes lines shorter than 3 characters
- Cleans up formatting

---

## 🎯 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Scrapy Spider (LoansSpider)                              │
│    ├─ Sends HTTP request to website                         │
│    ├─ Receives HTML response                                 │
│    └─ Calls parse() method                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Content Extraction (parse method)                        │
│    ├─ _find_main_content() → Locates main content area      │
│    ├─ _extract_headings_and_paragraphs() → Extracts text  │
│    ├─ _extract_tables() → Extracts table data              │
│    ├─ _is_noise() → Filters out noise                       │
│    └─ _classify_content() → Categorizes into sections      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. LoanItem Creation                                        │
│    ├─ loan_type: "home_loan"                               │
│    ├─ source_url: "https://..."                             │
│    ├─ scraped_at: "2025-12-24T12:00:00"                    │
│    ├─ overview: ["text1", "text2", ...]                    │
│    ├─ interest_rates: ["7.10% P.A", ...]                   │
│    ├─ eligibility: ["Individual salaried...", ...]         │
│    └─ ... (other sections)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pipeline Processing                                      │
│    ├─ ContentValidationPipeline → Validates content quality │
│    └─ LoanJsonPipeline → Saves to JSON file                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. JSON Storage                                             │
│    └─ data/raw/{loan_type}.json                            │
│       Example: data/raw/home_loan.json                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Ready for RAG Pipeline                                    │
│    └─ build_vector_store.py reads JSON files               │
│    └─ Chunks the text                                       │
│    └─ Creates embeddings                                    │
│    └─ Builds FAISS index                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Key Features

### **1. Robust Content Finding**
- Tries multiple CSS selectors
- Falls back to `<body>` if needed
- Validates content length (>100 chars)

### **2. Smart Classification**
- Keyword-based content categorization
- Automatically sorts text into relevant sections
- Handles variations in website structure

### **3. Noise Filtering**
- Removes very short text (<10 chars)
- Filters out navigation, ads, headers, footers
- Preserves only loan-relevant content

### **4. Structured Output**
- Each loan type saved as separate JSON file
- All sections are lists (easy to process)
- Includes metadata (URL, timestamp)

### **5. Error Handling**
- Logs warnings for insufficient content
- Doesn't crash on missing elements
- Gracefully handles website structure changes

---

## 📊 Example Output Structure

**File:** `data/raw/home_loan.json`

```json
{
  "loan_type": "home_loan",
  "source_url": "https://bankofmaharashtra.in/home-loan",
  "scraped_at": "2025-12-24T12:00:00",
  "overview": [
    "Maha Super Housing Loan Scheme",
    "Embarking on the journey to homeownership...",
    "Choose Bank of Maharashtra..."
  ],
  "interest_rates": [
    "Interest Rate 7.10% P.A*",
    "Housing Loan Interest Rate 7.10% P.A*"
  ],
  "eligibility": [
    "Individual salaried employees...",
    "Self-Employed Professionals...",
    "Non-resident Indians (NRIs)..."
  ],
  "tenure": [
    "Maximum tenure up to 30 years / up to 75 years of age"
  ],
  "fees_and_charges": [
    "Processing fee is 0.25% of the loan amount plus applicable GST",
    "No Pre-Payment / Pre-Closure / Part-Payment Charges"
  ],
  "special_concessions": [
    "0.05% concession to women and defence personal"
  ],
  "other_details": [
    "Interest Rate | 7.10 | %P.A*",
    "Maximum Tenure | 30 Years | up to 75 years of age"
  ]
}
```

---

## 🛠️ Configuration

**File:** `scraper/bom_scraper/settings.py`

```python
# Scraper behavior
CONCURRENT_REQUESTS = 1          # One request at a time
DOWNLOAD_DELAY = 1               # 1 second delay (polite)
DOWNLOAD_TIMEOUT = 30            # 30 second timeout
ROBOTSTXT_OBEY = False           # Don't check robots.txt

# User agent (appears as browser)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."

# Pipelines (order matters!)
ITEM_PIPELINES = {
    "bom_scraper.pipelines.ContentValidationPipeline": 100,  # Runs first
    "bom_scraper.pipelines.LoanJsonPipeline": 300,          # Runs second
}
```

---

## 🚀 Running the Scraper

### **Method 1: Direct Scrapy Command**
```bash
cd scraper
scrapy crawl bom_loans
```

### **Method 2: Using run_scraper.py**
```bash
python scraper/run_scraper.py
```

### **Method 3: Via build_vector_store.py**
```bash
python build_vector_store.py  # Runs scraper as part of pipeline
```

---

## 📝 Summary

**The scraper workflow:**

1. **Requests** → Sends HTTP GET to loan product pages
2. **Parses** → Extracts HTML content using CSS selectors
3. **Classifies** → Categorizes text into sections (interest, eligibility, etc.)
4. **Validates** → Checks content quality
5. **Stores** → Saves as structured JSON files in `data/raw/`
6. **Cleans** → (Optional) Further cleaning with `processing/cleaner.py`

**Result:** Clean, structured JSON files ready for chunking and embedding in the RAG pipeline!

