from typing import List
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper for sentence transformer embedding model.
    
    Provides a simple interface for generating embeddings from text.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Initialize the embedding model.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run model on ('cpu' or 'cuda')
        
        Why all-MiniLM-L6-v2?
        - Optimized for semantic search
        - Fast on CPU (important for deployment)
        - Good performance on financial/business text
        - Widely used and well-tested
        """
        self.model_name = model_name
        self.device = device
        
        logger.info(f"Loading embedding model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"Model loaded successfully. "
                f"Embedding dimension: {self.embedding_dim}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(self.embedding_dim)
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(self.embedding_dim)
    
    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Uses batching for efficiency.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar
        
        Returns:
            Array of embeddings (shape: [num_texts, embedding_dim])
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return np.array([])
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )
            
            logger.info(
                f"Generated {len(embeddings)} embeddings "
                f"(shape: {embeddings.shape})"
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        return self.embedding_dim


def main():
    """Test the embedding model."""
    embedding_model = EmbeddingModel()
    test_text = "What is the interest rate for home loans?"
    embedding = embedding_model.embed_text(test_text)
    logger.info(f"Test embedding generated. Shape: {embedding.shape}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
