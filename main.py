import os
# Fix for OMP: Error #15
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

# Set event loop policy for Windows to support subprocesses (required for Playwright)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from schemas.query import QueryRequest, QueryResponse, HealthResponse, ErrorResponse
from rag.embeddings import EmbeddingModel
from rag.vector_store import FAISSVectorStore
from rag.retriever import LoanRetriever
from rag.qa_chain import LoanQAChain
from processing.chunker import LoanContentChunker
from pypdf import PdfReader
from io import BytesIO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for RAG components
embedding_model: Optional[EmbeddingModel] = None
vector_store: Optional[FAISSVectorStore] = None
retriever: Optional[LoanRetriever] = None
qa_chain: Optional[LoanQAChain] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Startup:
    - Load embedding model
    - Load FAISS vector store
    - Initialize retriever and QA chain

    Shutdown:
    - Cleanup resources
    """
    global embedding_model, vector_store, retriever, qa_chain
    
    logger.info("Starting up Loan Product Assistant API...")
    
    try:
        # Initialize embedding model
        logger.info("Loading embedding model...")
        embedding_model = EmbeddingModel(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu"
        )
        
        # Load vector store
        logger.info("Loading vector store...")
        vector_store = FAISSVectorStore(
            embedding_dim=settings.EMBEDDING_DIMENSION,
            index_path=settings.FAISS_INDEX_PATH,
            metadata_path=settings.FAISS_METADATA_PATH
        )
        
        # Initialize retriever
        logger.info("Initializing retriever...")
        retriever = LoanRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            top_k=settings.TOP_K_RESULTS,
            score_threshold=settings.SIMILARITY_THRESHOLD
        )

        # Initialize QA Chain (RAG pipeline)
        logger.info("Initializing QA Chain...")
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Please add it to your .env file."
            )

        qa_chain = LoanQAChain(
            retriever=retriever,
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
        
        logger.info("✓ API startup complete")
        logger.info(f"✓ Vector store loaded: {vector_store.index.ntotal} chunks")
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.API_VERSION.startswith("dev") else None
        }
    )


# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": "RAG-based assistant for Bank of Maharashtra loan products",
        "endpoints": {
            "query": "/query",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and vector store information.
    """
    if not vector_store or not qa_chain:
        raise HTTPException(
            status_code=503,
            detail="Service not ready. RAG components not initialized."
        )
    
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION,
        vector_store_loaded=vector_store.index.ntotal > 0,
        total_chunks=vector_store.index.ntotal
    )


@app.post("/query", response_model=QueryResponse, tags=["Loan Products"])
async def query_loans(request: QueryRequest):
    """
    Query loan product information using the RAG QA chain.
    """
    if not qa_chain:
        raise HTTPException(
            status_code=503,
            detail="Service not ready. QA chain not initialized."
        )
    
    try:
        logger.info(f"Processing query: {request.question}")

        # Use QA chain to answer question
        result = qa_chain.answer_question(request.question, return_sources=True)

        answer = result.get("answer", "No answer generated.")
        metadata = result.get("metadata", {})
        raw_sources = result.get("sources", []) or []

        # Ensure metadata includes model name for consistency
        metadata.setdefault("model", settings.GROQ_MODEL)

        # FastAPI / Pydantic will coerce these dicts into SourceInfo models
        return QueryResponse(
            answer=answer,
            sources=raw_sources,
            metadata=metadata,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@app.get("/stats", tags=["General"])
async def get_stats():
    """
    Get system statistics.
    
    Returns information about the vector store and configuration.
    """
    if not vector_store:
        raise HTTPException(
            status_code=503,
            detail="Service not ready."
        )
    
    return {
        "vector_store": vector_store.get_stats(),
        "config": {
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_model": settings.GROQ_MODEL,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "top_k": settings.TOP_K_RESULTS,
        }
    }


@app.post("/scrape-url", tags=["Admin"])
async def scrape_new_url(url: str):
    """
    Endpoint to scrape a specific URL and extract text.
    """
    from scraper.scraper import scrape_url
    
    logger.info(f"Received request to scrape: {url}")
    try:
        data = await scrape_url(url)
        if data:
            # Optionally save to file as well, or process it
            return {"status": "success", "url": url, "data_length": len(data), "preview": data[:200]}
        else:
            raise HTTPException(status_code=500, detail="Scraping failed or returned empty data")
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extract plain text from a PDF file given as bytes."""
    reader = PdfReader(BytesIO(data))
    pages_text = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    return "\n\n".join(pages_text)


@app.post("/upload-pdf", tags=["Admin"])
async def upload_pdf(
    file: UploadFile = File(...),
    loan_type: str = Form("custom_pdf_loan"),
    title: str = Form("Custom PDF Loan Document"),
    source_url: str = Form(""),
):
    """
    Upload a PDF and add its content to the vector store.

    - Reads the PDF
    - Chunks the text using the same strategy as other loans
    - Generates embeddings
    - Appends them to the existing FAISS index
    """
    if not vector_store or not embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Vector store or embedding model not initialized.",
        )

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Empty PDF file.")

        full_text = _extract_text_from_pdf_bytes(raw_bytes)
        if not full_text.strip():
            raise HTTPException(
                status_code=400, detail="No text could be extracted from the PDF."
            )

        # Chunk the text
        chunker = LoanContentChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        base_metadata = {
            "loan_type": loan_type,
            "source_url": source_url,
            "title": title,
        }
        chunks = chunker.create_chunks(full_text, base_metadata)

        if not chunks:
            raise HTTPException(
                status_code=400, detail="Chunking produced no chunks from the PDF."
            )

        texts = [c.text for c in chunks]

        # Generate embeddings
        embeddings = embedding_model.embed_texts(texts, show_progress=False)

        # Prepare metadata entries (include text for retriever)
        metadata_list = [
            {
                **c.metadata,
                "text": c.text,
            }
            for c in chunks
        ]

        # Add to vector store and save
        vector_store.add_embeddings(embeddings, metadata_list)
        vector_store.save(
            index_path=settings.FAISS_INDEX_PATH,
            metadata_path=settings.FAISS_METADATA_PATH,
        )

        return {
            "status": "success",
            "message": "PDF added to vector store.",
            "file_name": file.filename,
            "loan_type": loan_type,
            "chunks_added": len(chunks),
            "total_vectors": vector_store.index.ntotal,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """
    Run the FastAPI application.
    
    For development: python -m app.main
    For production: Use uvicorn directly or gunicorn
    """
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Set to False in production
        log_level="info"
    )


if __name__ == "__main__":
    main()
