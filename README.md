# Bank of Maharashtra Loan Product Assistant

A production-ready **Retrieval-Augmented Generation (RAG)** application that provides accurate, grounded answers about Bank of Maharashtra loan products using official website data and PDF documents.

## 🎯 Overview

This application uses RAG (Retrieval-Augmented Generation) to answer customer questions about loan products without hallucination. All answers are based strictly on scraped data from the official Bank of Maharashtra website and uploaded PDF documents.

### Key Features

✅ **Accurate & Grounded**: Answers based only on official data  
✅ **No Hallucination**: Strict prompt engineering prevents made-up information  
✅ **Fast Inference**: Powered by Groq's high-speed LLM infrastructure  
✅ **Production-Ready**: Clean architecture, error handling, logging  
✅ **Easy to Deploy**: FastAPI with Docker support  
✅ **PDF Support**: Upload PDF documents to expand knowledge base  
✅ **CI/CD Pipeline**: Automated testing and deployment workflows  

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                        │
│                    (Web Browser / API Client)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ HTTP/REST API
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      FastAPI Application Layer                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                                │  │
│  │  • POST /query          - Query loan information          │  │
│  │  • POST /upload-pdf     - Add PDF to knowledge base      │  │
│  │  • GET  /health         - Health check                    │  │
│  │  • GET  /stats          - System statistics              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      RAG Pipeline Layer                          │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Query      │───▶│  Embedding   │───▶│   FAISS      │      │
│  │  Processing  │    │    Model     │    │ Vector Store │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                    │                    │              │
│         │                    │                    │              │
│         └────────────────────┼────────────────────┘             │
│                              │                                   │
│                              ▼                                   │
│                    ┌──────────────────┐                          │
│                    │  Context Builder │                          │
│                    └────────┬─────────┘                          │
│                             │                                    │
│                             ▼                                    │
│                    ┌──────────────────┐                          │
│                    │  Groq LLM        │                          │
│                    │  (Llama 3.3 70B) │                          │
│                    └────────┬─────────┘                          │
│                             │                                    │
│                             ▼                                    │
│                    ┌──────────────────┐                          │
│                    │  Answer + Sources│                          │
│                    └──────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
                               │
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      Data Layer                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  • Scraped HTML data (data/raw/*.json)                    │  │
│  │  • Processed chunks (data/processed/chunks.json)           │  │
│  │  • FAISS index (data/processed/faiss_index)                │  │
│  │  • Metadata (data/processed/metadata.json)                │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. **API Layer** (`main.py`)
- **FastAPI Application**: RESTful API with automatic OpenAPI documentation
- **Lifespan Management**: Handles startup/shutdown of RAG components
- **Error Handling**: Comprehensive exception handling and logging
- **CORS Support**: Configured for cross-origin requests

#### 2. **RAG Pipeline Components**

**a. Embedding Model** (`rag/embeddings.py`)
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384
- Purpose: Converts text to dense vector representations
- Features: Batch processing, CPU-optimized

**b. Vector Store** (`rag/vector_store.py`)
- Technology: FAISS (Facebook AI Similarity Search)
- Index Type: IndexFlatL2 (exact L2 distance search)
- Normalization: L2 normalization for cosine similarity
- Persistence: Save/load index and metadata to disk

**c. Retriever** (`rag/retriever.py`)
- Top-K Retrieval: Returns top 4 most relevant chunks
- Similarity Threshold: Filters results below 0.3 similarity
- Context Building: Formats retrieved chunks for LLM

**d. QA Chain** (`rag/qa_chain.py`)
- LLM: Groq (Llama 3.3 70B Versatile)
- Temperature: 0.0 (deterministic responses)
- Max Tokens: 1024
- Prompt Engineering: Strict instructions to prevent hallucination

#### 3. **Data Processing Pipeline**

**a. Scraper** (`scraper/`)
- Technology: Playwright for dynamic content
- Output: Structured JSON files per loan type
- Storage: `data/raw/*.json`

**b. Chunker** (`processing/chunker.py`)
- Strategy: Semantic boundary detection
- Chunk Size: 450 tokens (~300-350 words)
- Overlap: 50 tokens to maintain context
- Tokenizer: tiktoken (cl100k_base)

**c. Vector Store Builder** (`build_vector_store.py`)
- Orchestrates: Scraping → Cleaning → Chunking → Embedding → Indexing
- Output: FAISS index + metadata JSON

#### 4. **Configuration** (`app/config.py`)
- Technology: Pydantic Settings
- Environment Variables: Loads from `.env` file
- Defaults: Sensible defaults for all settings

---

## 📁 Project Structure

```
Loan_Product_Assistant_chatbot/
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml              # GitHub Actions CI/CD pipeline
│
├── app/
│   └── config.py                 # Application configuration & settings
│
├── data/
│   ├── raw/                       # Scraped loan data (JSON files)
│   │   ├── education_loan.json
│   │   ├── home_loan.json
│   │   ├── personal_loan.json
│   │   └── vehicle_loan.json
│   └── processed/                 # Processed data & vector store
│       ├── chunks.json            # Text chunks with metadata
│       ├── faiss_index            # FAISS vector index
│       └── metadata.json          # Chunk metadata
│
├── processing/
│   ├── __init__.py
│   ├── chunker.py                 # Intelligent text chunking
│   └── cleaner.py                 # HTML cleaning & extraction
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py              # Embedding model wrapper
│   ├── vector_store.py            # FAISS vector database
│   ├── retriever.py                # Similarity search & retrieval
│   ├── qa_chain.py                 # RAG pipeline with Groq LLM
│   └── agent/                      # LangGraph agent (optional)
│       ├── __init__.py
│       ├── graph.py
│       ├── nodes.py
│       └── state.py
│
├── schemas/
│   └── query.py                    # Pydantic request/response models
│
├── scraper/
│   ├── __init__.py
│   ├── scraper.py                 # Web scraper utilities
│   ├── run_scraper.py             # Scraper runner
│   └── bom_scraper/               # Scrapy-based scraper
│       ├── __init__.py
│       ├── items.py
│       ├── pipelines.py
│       ├── settings.py
│       └── spiders/
│           └── loans_spider.py
│
├── .env.example                   # Environment variables template
├── .gitignore
├── build_vector_store.py          # Pipeline to build vector store
├── Dockerfile                     # Docker container definition
├── docker-compose.yml             # Docker Compose configuration
├── main.py                        # FastAPI application entry point
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.10 or higher
- **Groq API Key**: [Get one here](https://console.groq.com/keys)
- **Operating System**: Windows, Linux, or macOS

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Loan_Product_Assistant_chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy example file
   cp .env.example .env
   
   # Edit .env and add your Groq API key
   GROQ_API_KEY=your_actual_api_key_here
   ```

5. **Build the knowledge base**
   ```bash
   python build_vector_store.py
   ```
   
   This will:
   - Scrape loan product pages from Bank of Maharashtra website
   - Clean and normalize the data
   - Create text chunks
   - Generate embeddings
   - Build FAISS vector store

6. **Start the API server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API**
   - **API**: http://localhost:8000
   - **Interactive Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

---

## 📖 API Documentation

### Endpoints

#### 1. **Query Loan Information**
**POST** `/query`

Query the RAG system for loan product information.

**Request:**
```json
{
  "question": "What is the interest rate for home loans?"
}
```

**Response:**
```json
{
  "answer": "The interest rate for Bank of Maharashtra home loans starts from 8.5% p.a. for eligible customers.",
  "sources": [
    {
      "loan_type": "home_loan",
      "text": "Interest rates for home loans start from 8.5%...",
      "score": 0.92,
      "url": "https://www.bankofmaharashtra.in/home-loan"
    }
  ],
  "metadata": {
    "retrieved_chunks": 4,
    "model": "llama-3.3-70b-versatile"
  }
}
```

#### 2. **Upload PDF Document**
**POST** `/upload-pdf`

Upload a PDF document to add its content to the vector store.

**Request:**
- `file`: PDF file (multipart/form-data)
- `loan_type`: Optional, default "custom_pdf_loan"
- `title`: Optional, default "Custom PDF Loan Document"
- `source_url`: Optional, default ""

**Response:**
```json
{
  "status": "success",
  "message": "PDF added to vector store.",
  "file_name": "loan_terms.pdf",
  "loan_type": "custom_pdf_loan",
  "chunks_added": 15,
  "total_vectors": 28
}
```

#### 3. **Health Check**
**GET** `/health`

Check system health and readiness.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_store_loaded": true,
  "total_chunks": 13
}
```

#### 4. **System Statistics**
**GET** `/stats`

Get system statistics and configuration.

**Response:**
```json
{
  "vector_store": {
    "total_vectors": 13,
    "embedding_dimension": 384,
    "metadata_count": 13,
    "index_type": "IndexFlatL2"
  },
  "config": {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "llm_model": "llama-3.3-70b-versatile",
    "chunk_size": 450,
    "chunk_overlap": 50,
    "top_k": 4
  }
}
```

---

## 🔧 Configuration

All configuration is managed through `app/config.py` and can be overridden via environment variables in `.env`:

```python
# API Settings
API_TITLE = "Loan Product Assistant API"
API_VERSION = "1.0.0"

# LLM Settings (Groq)
GROQ_API_KEY = ""  # Required: Set in .env
GROQ_MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.0
MAX_TOKENS = 1024

# Embedding Settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Chunking Settings
CHUNK_SIZE = 450
CHUNK_OVERLAP = 50

# Retrieval Settings
TOP_K_RESULTS = 4
SIMILARITY_THRESHOLD = 0.3

# Vector Store Paths
FAISS_INDEX_PATH = "data/processed/faiss_index"
FAISS_METADATA_PATH = "data/processed/metadata.json"
```

---

## 🧠 RAG Strategy

### Data Collection
- **Source**: Official Bank of Maharashtra website
- **Scope**: Home, Personal, Education, Vehicle loans
- **Format**: Structured JSON with sections (interest rates, eligibility, tenure, fees)

### Chunking Strategy
- **Size**: 450 tokens (~300-350 words)
- **Overlap**: 50 tokens
- **Method**: Semantic boundary detection (preserves sections, paragraphs)
- **Rationale**: 
  - 450 tokens: Enough for complete loan product information
  - 50 token overlap: Prevents information loss at boundaries
  - Semantic chunking: Maintains logical coherence

### Retrieval Strategy
- **Top-K**: 4 chunks
- **Similarity Metric**: L2 distance with L2 normalization (equivalent to cosine similarity)
- **Threshold**: 0.3 minimum similarity score
- **Rationale**: 
  - 4 chunks: Provides enough context without overwhelming LLM
  - 0.3 threshold: Filters out very irrelevant results

### Generation Strategy
- **Model**: Llama 3.3 70B Versatile (via Groq)
- **Temperature**: 0.0 (deterministic)
- **Max Tokens**: 1024
- **Prompt Engineering**: 
  - Strict instructions to answer ONLY from context
  - Explicit "I don't know" response when information is missing
  - No inference or assumption allowed

---

## 🧪 Testing

### Manual Testing

```bash
# Test embedding model
python -m rag.embeddings

# Test vector store
python -m rag.vector_store

# Test retriever
python -m rag.retriever

# Test QA chain
python -m rag.qa_chain
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Query example
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the interest rate for home loans?"}'
```

---

## 🚢 Deployment

### Docker Deployment

1. **Build Docker image**
   ```bash
   docker build -t loan-assistant .
   ```

2. **Run container**
   ```bash
   docker run -p 8000:8000 \
     -e GROQ_API_KEY=your_key \
     -v $(pwd)/data:/app/data \
     loan-assistant
   ```

### Docker Compose

```bash
docker-compose up -d
```

### Production Considerations

- Set `reload=False` in uvicorn
- Use environment variables for all secrets
- Configure proper CORS origins
- Set up reverse proxy (nginx)
- Enable HTTPS
- Monitor logs and metrics
- Set up backup for vector store

---

## 🔄 CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that:

1. **Linting**: Runs flake8 and black for code quality
2. **Type Checking**: Runs mypy for type validation
3. **Import Testing**: Verifies all modules can be imported
4. **Build Verification**: Ensures the application builds successfully

The pipeline runs on:
- Push to `main` branch
- Pull requests to `main` branch

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Average Response Time** | ~2-3 seconds |
| **Embedding Generation** | ~50ms per query |
| **Vector Search** | ~10ms for 1000 chunks |
| **LLM Generation** | ~1-2 seconds (Groq) |
| **Accuracy** | Based on official data (no hallucination) |

---

## 🛡️ Security

- ✅ API key stored in environment variables
- ✅ Input validation with Pydantic
- ✅ CORS configuration
- ✅ Error handling without exposing internals
- ⚠️ **Recommended**: Add rate limiting in production
- ⚠️ **Recommended**: Add authentication/authorization

---

## 🔮 Future Improvements

1. **Multi-language Support**: Add Hindi, Marathi support
2. **Conversation Memory**: Track conversation history
3. **Advanced Reranking**: Use cross-encoder for better precision
4. **Caching**: Cache frequent queries
5. **Monitoring**: Add Prometheus metrics
6. **A/B Testing**: Compare different retrieval strategies
7. **Fine-tuning**: Fine-tune embeddings on banking domain

---

## 📝 License

This project is for educational and evaluation purposes.

---

## 👥 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

---

##  Support

For questions or issues:
1. Check the `/docs` endpoint for API documentation
2. Review logs in console output
3. Verify `.env` configuration
4. Ensure vector store is built (`build_vector_store.py`)

---

##  Acknowledgments

- **Bank of Maharashtra**: Data source
- **Groq**: Fast LLM inference
- **Sentence Transformers**: Embedding models
- **FAISS**: Efficient vector search
- **FastAPI**: Modern Python web framework

---

