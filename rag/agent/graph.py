from langgraph.graph import StateGraph, END
from rag.agent.state import AgentState
from rag.agent.nodes import RAGNodes
from rag.retriever import LoanRetriever

def create_rag_graph(retriever: LoanRetriever):
    """
    Builds and compiles the RAG StateGraph.
    
    Workflow: START -> retrieve -> generate -> END
    """
    # Initialize nodes
    nodes = RAGNodes(retriever)
    
    # Define Graph
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("retrieve", nodes.retrieve)
    workflow.add_node("generate", nodes.generate)
    
    # Define Edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    # Compile
    app = workflow.compile()
    return app
