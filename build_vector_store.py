
import json
import logging
from pathlib import Path
import sys
import os

# Fix for OMP: Error #15
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_pipeline():
    """
    Run the complete RAG pipeline.
    """
    logger.info("="*60)
    logger.info("Starting RAG Pipeline")
    logger.info("="*60)
    
    # Step 1: Scrape data (Using Playwright)
    logger.info("\n[1/5] Scraping loan product pages (Playwright)...")
    try:
        import subprocess
        
        # Run the Playwright scraper
        # It handles browser automation and saves JSONs to data/raw
        
        logger.info("Running Playwright scraper...")
        result = subprocess.run(
            [sys.executable, "scraper.py"], 
            cwd="scraper",
            capture_output=True, 
            text=True
        )
        
        # Log stderr for debugging
        if result.stderr:
            logger.info(f"Scraper logs:\n{result.stderr}")
        
        if result.returncode != 0:
            logger.error(f"Scraper failed with error:\n{result.stderr}")
            return False
            
        logger.info(f"✓ Scraper finished successfully")
        logger.info(f"Output:\n{result.stdout}")
        
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}")
        return False
    
    # Step 2: Clean and Normalize Data
    logger.info("\n[2/5] normalizing data...")
    try:
        # The scraper outputs structured JSONs in data/raw
        # We read them and format them into 'cleaned_data' list
        raw_dir = Path("data/raw")
        cleaned_data = []
        
        for json_file in raw_dir.glob("*.json"):
            if json_file.name == "scraped_data.json": continue # skip temp files if any
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Skipping invalid JSON: {json_file}")
                continue
                
            # Construct a full text representation
            full_text = f"Loan Type: {data.get('loan_type', 'Unknown')}\n\n"
            
            # Add overview (which contains the full scraped text in our Playwright scraper)
            for item in data.get('overview', []):
                full_text += str(item) + "\n"
            
            # Add other sections if they exist (compatibility with Scrapy format)
            for section in ['interest_rates', 'eligibility', 'tenure', 'fees_and_charges', 'special_concessions', 'other_details']:
                content_list = data.get(section, [])
                if content_list:
                    section_title = section.replace('_', ' ').title()
                    full_text += f"\n## {section_title}\n" + "\n".join(content_list) + "\n"
            
            # Prepare data structure for chunker
            item_data = {
                'cleaned_text': full_text,
                'url': data.get('source_url', ''),
                'title': f"{data.get('loan_type', 'Loan')} Product",
                'loan_type': data.get('loan_type', ''),
                'source_url': data.get('source_url', ''),
                'sections': {} # Optional
            }
            
            cleaned_data.append(item_data)
            
        logger.info(f"✓ Loaded and normalized {len(cleaned_data)} loan files")
        
    except Exception as e:
        logger.error(f"✗ Data normalization failed: {e}")
        return False
    
    # Step 3: Create chunks (using normalized data)
    logger.info("\n[3/5] Creating chunks...")
    try:
        from processing.chunker import LoanContentChunker
        
        chunker = LoanContentChunker()
        # The chunker expects list of dicts with 'text' and 'metadata', which we prepared above
        chunks = chunker.chunk_all_loans(cleaned_data)
        
        # Save chunks
        chunks_data = [
            {
                'text': chunk.text,
                'metadata': chunk.metadata,
                'token_count': chunk.token_count,
                'chunk_id': chunk.chunk_id
            }
            for chunk in chunks
        ]
        
        output_file = Path('data/processed/chunks.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Created {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"✗ Chunking failed: {e}")
        return False
    
    # Step 4: Generate embeddings
    logger.info("\n[4/5] Generating embeddings...")
    try:
        from rag.embeddings import EmbeddingModel
        
        embedding_model = EmbeddingModel()
        
        # Extract texts from chunks
        texts = [chunk.text for chunk in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        
        if not texts:
            logger.warning("No texts to embed!")
            return False

        # Generate embeddings
        embeddings = embedding_model.embed_texts(texts, show_progress=True)
        logger.info(f"✓ Generated embeddings. Shape: {embeddings.shape}")
        
    except Exception as e:
        logger.error(f"✗ Embedding generation failed: {e}")
        return False
    
    # Step 5: Build vector store
    logger.info("\n[5/5] Building FAISS vector store...")
    try:
        from rag.vector_store import FAISSVectorStore
        
        vector_store = FAISSVectorStore(
            embedding_dim=embedding_model.get_embedding_dimension()
        )
        
        # Prepare metadata (include text so retriever/agent can build context)
        metadata = [
            {
                **chunk.metadata,
                "text": chunk.text,
            }
            for chunk in chunks
        ]

        # Add to vector store
        vector_store.add_embeddings(embeddings, metadata)
        
        # Save vector store
        vector_store.save(
            index_path='data/processed/faiss_index',
            metadata_path='data/processed/metadata.json'
        )
        
        logger.info(f"Vector store built with {vector_store.index.ntotal} vectors")
        
    except Exception as e:
        logger.error(f"Vector store creation failed: {e}")
        return False
    
    # Success!
    logger.info("✓ Pipeline completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Set GROQ_API_KEY in .env file")
    logger.info("2. Run: python -m app.main")
    logger.info("3. Visit: http://localhost:8000/docs")
    
    return True


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
