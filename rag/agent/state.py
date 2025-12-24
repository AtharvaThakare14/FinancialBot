"""
State definition for the LangGraph RAG Agent.
"""

from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """
    Represents the state of the RAG agent workflow.
    """
    question: str
    context: Optional[str]
    retrieved_chunks: List[Dict[str, Any]]
    answer: Optional[str]
    error: Optional[str]
