import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import faiss
import logging

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store for loan product chunks.
    
    Provides:
    - Efficient similarity search
    - Persistence (save/load)
    - Metadata management
    - Batch operations
    """
    
    def __init__(
        self,
        embedding_dim: int = 384,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None
    ):
        """
        Initialize FAISS vector store.
        
        Args:
            embedding_dim: Dimension of embeddings
            index_path: Path to save/load FAISS index
            metadata_path: Path to save/load metadata
        
        Why IndexFlatL2?
        - Exact search (no approximation)
        - Fast for small-medium datasets (<100K vectors)
        - Simple and reliable
        - L2 distance works well for normalized embeddings
        """
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.metadata_path = metadata_path
        
        # Initialize FAISS index
        # Using IndexFlatL2 for exact search with L2 distance
        self.index = faiss.IndexFlatL2(embedding_dim)
        
        # Store metadata for each vector
        self.metadata: List[Dict] = []
        
        # Try to load existing index
        if index_path and Path(index_path).exists():
            self.load()
        else:
            logger.info(f"Created new FAISS index (dim={embedding_dim})")
    
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict]
    ) -> None:
        """
        Add embeddings to the index.
        
        Args:
            embeddings: Array of embeddings (shape: [num_vectors, embedding_dim])
            metadata: List of metadata dicts (one per embedding)
        
        Raises:
            ValueError: If embeddings and metadata lengths don't match
        """
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"Embeddings ({len(embeddings)}) and metadata ({len(metadata)}) "
                "must have same length"
            )
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension ({embeddings.shape[1]}) doesn't match "
                f"index dimension ({self.embedding_dim})"
            )
        
        # Ensure embeddings are float32 (FAISS requirement)
        embeddings = embeddings.astype('float32')
        
        # Normalize embeddings for better similarity search
        # L2 normalization makes cosine similarity equivalent to dot product
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.index.add(embeddings)
        
        # Store metadata
        self.metadata.extend(metadata)
        
        logger.info(
            f"Added {len(embeddings)} embeddings to index. "
            f"Total vectors: {self.index.ntotal}"
        )
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 4,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector (shape: [embedding_dim])
            top_k: Number of results to return
            score_threshold: Minimum similarity score (optional)
        
        Returns:
            List of (metadata, score) tuples, sorted by relevance
        
        Note: Lower scores = more similar (L2 distance)
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty, no results to return")
            return []
        
        # Ensure query is 2D array
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Ensure float32 and normalize
        query_embedding = query_embedding.astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Convert to list of (metadata, score) tuples
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for missing results
                continue
            
            # Convert L2 distance to similarity score (0-1, higher is better)
            # Using exponential decay: similarity = exp(-distance)
            similarity = np.exp(-dist)
            
            # Apply threshold if specified
            if score_threshold is not None and similarity < score_threshold:
                continue
            
            results.append((self.metadata[idx], float(similarity)))
        
        logger.info(f"Found {len(results)} results for query")
        return results
    
    def save(self, index_path: Optional[str] = None, 
             metadata_path: Optional[str] = None) -> None:
        """
        Save index and metadata to disk.
        
        Args:
            index_path: Path to save FAISS index (optional, uses self.index_path)
            metadata_path: Path to save metadata (optional, uses self.metadata_path)
        """
        index_path = index_path or self.index_path
        metadata_path = metadata_path or self.metadata_path
        
        if not index_path or not metadata_path:
            raise ValueError("Must provide index_path and metadata_path")
        
        # Create directories if needed
        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        logger.info(f"Saved FAISS index to {index_path}")
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved metadata to {metadata_path}")
    
    def load(self, index_path: Optional[str] = None,
             metadata_path: Optional[str] = None) -> None:
        """
        Load index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index (optional, uses self.index_path)
            metadata_path: Path to metadata (optional, uses self.metadata_path)
        """
        index_path = index_path or self.index_path
        metadata_path = metadata_path or self.metadata_path
        
        if not index_path or not metadata_path:
            raise ValueError("Must provide index_path and metadata_path")
        
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        logger.info(
            f"Loaded FAISS index from {index_path} "
            f"({self.index.ntotal} vectors)"
        )
        
        # Load metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        logger.info(f"Loaded {len(self.metadata)} metadata entries")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_vectors': self.index.ntotal,
            'embedding_dimension': self.embedding_dim,
            'metadata_count': len(self.metadata),
            'index_type': type(self.index).__name__,
        }


def main():
    """Test the vector store."""
    import numpy as np
    
    # Create test embeddings
    embedding_dim = 384
    num_vectors = 10
    
    embeddings = np.random.randn(num_vectors, embedding_dim).astype('float32')
    metadata = [
        {
            'chunk_id': f'test_{i}',
            'text': f'Test chunk {i}',
            'loan_type': 'home_loan'
        }
        for i in range(num_vectors)
    ]
    
    # Initialize vector store
    vector_store = FAISSVectorStore(embedding_dim=embedding_dim)
    
    # Add embeddings
    vector_store.add_embeddings(embeddings, metadata)
    
    query = np.random.randn(embedding_dim).astype('float32')
    results = vector_store.search(query, top_k=3)
    
    logger.info(f"Vector store initialized with {num_vectors} vectors")
    logger.info(f"Search returned {len(results)} results")
    logger.info(f"Stats: {vector_store.get_stats()}")
    
    test_index_path = "data/processed/test_faiss_index"
    test_metadata_path = "data/processed/test_metadata.json"
    
    vector_store.save(test_index_path, test_metadata_path)
    logger.info("Saved index and metadata")
    
    new_store = FAISSVectorStore(
        embedding_dim=embedding_dim,
        index_path=test_index_path,
        metadata_path=test_metadata_path
    )
    logger.info(f"Loaded index with {new_store.index.ntotal} vectors")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
