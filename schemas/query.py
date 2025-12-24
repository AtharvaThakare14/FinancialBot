from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class QueryRequest(BaseModel):
    """
    Request schema for loan product queries.
    
    Example:
        {
            "question": "What is the interest rate for home loans?"
        }
    """
    question: str = Field(
        ...,
        description="User question about loan products",
        min_length=5,
        max_length=500,
        example="What is the interest rate for Bank of Maharashtra home loans?"
    )
    
    @validator('question')
    def question_must_not_be_empty(cls, v):
        """Ensure question is not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()


class SourceInfo(BaseModel):
    """
    Information about a source chunk.
    """
    loan_type: str = Field(
        ...,
        description="Type of loan (e.g., home_loan, personal_loan)",
        example="home_loan"
    )
    text: str = Field(
        ...,
        description="Excerpt from the source document",
        example="Home loans are available at competitive interest rates..."
    )
    score: float = Field(
        ...,
        description="Relevance score (0-1, higher is better)",
        ge=0.0,
        le=1.0,
        example=0.85
    )
    url: Optional[str] = Field(
        None,
        description="Source URL",
        example="https://www.bankofmaharashtra.in/home-loan"
    )


class QueryResponse(BaseModel):
    """
    Response schema for loan product queries.
    
    Example:
        {
            "answer": "The interest rate for home loans is 8.5% p.a.",
            "sources": [
                {
                    "loan_type": "home_loan",
                    "text": "Interest rates starting from 8.5%...",
                    "score": 0.92,
                    "url": "https://..."
                }
            ],
            "metadata": {
                "retrieved_chunks": 4,
                "model": "llama-3.3-70b-versatile"
            }
        }
    """
    answer: str = Field(
        ...,
        description="Generated answer to the question",
        example="The interest rate for Bank of Maharashtra home loans starts from 8.5% p.a."
    )
    sources: List[SourceInfo] = Field(
        default_factory=list,
        description="List of source chunks used to generate the answer"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response"
    )


class HealthResponse(BaseModel):
    """
    Health check response schema.
    """
    status: str = Field(
        ...,
        description="Service status",
        example="healthy"
    )
    version: str = Field(
        ...,
        description="API version",
        example="1.0.0"
    )
    vector_store_loaded: bool = Field(
        ...,
        description="Whether vector store is loaded",
        example=True
    )
    total_chunks: int = Field(
        ...,
        description="Number of chunks in vector store",
        example=150
    )


class ErrorResponse(BaseModel):
    """
    Error response schema.
    """
    error: str = Field(
        ...,
        description="Error message",
        example="Invalid question format"
    )
    detail: Optional[str] = Field(
        None,
        description="Detailed error information",
        example="Question must be at least 5 characters long"
    )
