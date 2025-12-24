"""Application configuration and defaults.

Settings are loaded from environment variables (or a local `.env` file)
with sensible defaults that match the values documented in README.md.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # API metadata
    API_TITLE: str = "Loan Product Assistant API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "RAG-based assistant for Bank of Maharashtra loan products"

    # LLM (Groq)
    GROQ_API_KEY: str = Field(default="", env="GROQ_API_KEY")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")
    TEMPERATURE: float = Field(default=0.0, env="TEMPERATURE")
    MAX_TOKENS: int = Field(default=1024, env="MAX_TOKENS")

    # Embeddings
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL"
    )
    EMBEDDING_DIMENSION: int = Field(default=384, env="EMBEDDING_DIMENSION")

    # Chunking
    CHUNK_SIZE: int = Field(default=450, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=50, env="CHUNK_OVERLAP")

    # Retrieval
    TOP_K_RESULTS: int = Field(default=4, env="TOP_K_RESULTS")
    SIMILARITY_THRESHOLD: float = Field(default=0.3, env="SIMILARITY_THRESHOLD")

    # Vector store paths
    FAISS_INDEX_PATH: str = Field(
        default="data/processed/faiss_index", env="FAISS_INDEX_PATH"
    )
    FAISS_METADATA_PATH: str = Field(
        default="data/processed/metadata.json", env="FAISS_METADATA_PATH"
    )


settings = Settings()

