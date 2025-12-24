"""
Retriever module for RAG pipeline.

This module handles the retrieval phase of RAG:
1. Takes a user query
2. Generates query embedding
3. Searches vector store for relevant chunks
4. Returns ranked results with metadata

The retriever is the bridge between user questions and relevant loan information.
"""

from typing import List, Dict, Tuple
import logging
from rag.embeddings import EmbeddingModel
from rag.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class LoanRetriever:
    """
    Retriever for loan product information.
    
    Combines embedding model and vector store to find relevant
    loan information for user queries.
    """
    
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: FAISSVectorStore,
        top_k: int = 4,
        score_threshold: float = 0.3
    ):
        """
        Initialize the retriever.
        
        Args:
            embedding_model: Model for generating embeddings
            vector_store: FAISS vector store
            top_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score
        
        Why top_k=4?
        - Provides enough context without overwhelming the LLM
        - Balances between recall and precision
        - Fits comfortably in most LLM context windows
        
        Why score_threshold=0.3?
        - Filters out very irrelevant results
        - Tuned empirically for financial/loan content
        - Can be adjusted based on performance
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.top_k = top_k
        self.score_threshold = score_threshold
        
        logger.info(
            f"Retriever initialized (top_k={top_k}, "
            f"threshold={score_threshold})"
        )
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        score_threshold: float = None
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: User question
            top_k: Override default top_k
            score_threshold: Override default threshold
        
        Returns:
            List of dictionaries containing:
            - text: Chunk text
            - metadata: Chunk metadata
            - score: Similarity score
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        # Use defaults if not provided
        top_k = top_k or self.top_k
        score_threshold = score_threshold or self.score_threshold
        
        logger.info(f"Retrieving for query: '{query[:100]}...'")
        
        # Generate query embedding
        query_embedding = self.embedding_model.embed_text(query)
        
        # Search vector store
        results = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            score_threshold=score_threshold
        )
        
        # Format results
        formatted_results = []
        for metadata, score in results:
            formatted_results.append({
                'text': metadata.get('text', ''),
                'metadata': metadata,
                'score': score
            })
        
        logger.info(f"Retrieved {len(formatted_results)} relevant chunks")
        
        # Log top result for debugging
        if formatted_results:
            top_result = formatted_results[0]
            logger.debug(
                f"Top result (score={top_result['score']:.3f}): "
                f"{top_result['text'][:100]}..."
            )
        
        return formatted_results
    
    def retrieve_with_reranking(
        self,
        query: str,
        initial_k: int = 10,
        final_k: int = 4
    ) -> List[Dict]:
        """
        Retrieve with two-stage reranking.
        
        Strategy:
        1. Retrieve more candidates (initial_k)
        2. Rerank by relevance to query
        3. Return top final_k results
        
        This can improve precision for complex queries.
        
        Args:
            query: User question
            initial_k: Number of initial candidates
            final_k: Number of final results
        
        Returns:
            List of reranked results
        """
        # Get initial candidates
        candidates = self.retrieve(query, top_k=initial_k)
        
        if len(candidates) <= final_k:
            return candidates
        
        # Simple reranking: already sorted by similarity score
        # In a more advanced system, could use:
        # - Cross-encoder reranking
        # - Query-specific scoring
        # - Diversity-based selection
        
        reranked = candidates[:final_k]
        
        logger.info(f"Reranked {len(candidates)} → {len(reranked)} results")
        return reranked
    
    def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 2000
    ) -> str:
        """
        Get formatted context string for LLM.
        
        Retrieves relevant chunks and formats them into a single
        context string for the LLM.
        
        Args:
            query: User question
            max_context_length: Maximum context length in characters
        
        Returns:
            Formatted context string
        """
        results = self.retrieve(query)
        
        if not results:
            return "No relevant information found."
        
        # Build context from chunks
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            chunk_text = result['text']
            loan_type = result['metadata'].get('loan_type', 'unknown')
            
            # Format chunk with source information
            chunk_context = f"[Source {i} - {loan_type}]\n{chunk_text}\n"
            
            # Check if adding this chunk exceeds limit
            if current_length + len(chunk_context) > max_context_length:
                logger.info(
                    f"Reached context length limit, using {i-1} chunks"
                )
                break
            
            context_parts.append(chunk_context)
            current_length += len(chunk_context)
        
        context = "\n".join(context_parts)
        
        logger.info(
            f"Built context from {len(context_parts)} chunks "
            f"({len(context)} characters)"
        )
        
        return context


def main():
    """Test the retriever."""
    from pathlib import Path
    
    # Check if vector store exists
    index_path = "data/processed/faiss_index"
    metadata_path = "data/processed/metadata.json"
    
    if not Path(index_path).exists():
        print("Error: Vector store not found. Run the full pipeline first.")
        return
    
    # Initialize components
    embedding_model = EmbeddingModel()
    vector_store = FAISSVectorStore(
        embedding_dim=embedding_model.get_embedding_dimension(),
        index_path=index_path,
        metadata_path=metadata_path
    )
    
    # Initialize retriever
    retriever = LoanRetriever(embedding_model, vector_store)
    
    # Test queries
    test_queries = [
        "What is the interest rate for home loans?",
        "What are the eligibility criteria for personal loans?",
        "What is the maximum tenure for education loans?"
    ]
    
    print("\n" + "="*60)
    print("Testing Retriever")
    print("="*60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = retriever.retrieve(query)
        
        print(f"Retrieved {len(results)} chunks:")
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. Score: {result['score']:.3f}")
            print(f"     Loan Type: {result['metadata'].get('loan_type')}")
            print(f"     Text: {result['text'][:150]}...")
    
    # Test context generation
    print("\n" + "="*60)
    print("Testing Context Generation")
    print("="*60)
    
    query = test_queries[0]
    context = retriever.get_context_for_query(query)
    print(f"\nQuery: {query}")
    print(f"Context ({len(context)} chars):")
    print(context[:500] + "...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
