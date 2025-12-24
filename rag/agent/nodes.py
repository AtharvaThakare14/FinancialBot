import logging
from typing import Dict, Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from rag.agent.state import AgentState
from rag.retriever import LoanRetriever
from app.config import settings

logger = logging.getLogger(__name__)

class RAGNodes:
    def __init__(self, retriever: LoanRetriever):
        self.retriever = retriever
        
        # Initialize LLM
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS
        )
    
    def retrieve(self, state: AgentState) -> Dict[str, Any]:
        question = state['question']
        logger.info(f"Node 'retrieve': fetching docs for question='{question}'")
        
        try:
            chunks = self.retriever.retrieve(question)
            
            context_text = "\n\n".join([c.get('text', '') for c in chunks])

            preview = context_text[:300].replace("\n", " ")
            logger.info(
                "Node 'retrieve': got %d chunks, context length=%d chars, preview='%s...'",
                len(chunks),
                len(context_text),
                preview,
            )
            
            return {
                "context": context_text,
                "retrieved_chunks": chunks,
                "error": None
            }
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return {"error": f"Retrieval failed: {str(e)}"}

    def generate(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates an answer using the LLM and retrieved context.
        """
        question = state['question']
        context = state.get('context', '')

        logger.info(
            "Node 'generate': synthesizing answer (context length=%d chars)",
            len(context),
        )
        
        if not context:
            return {"answer": "I couldn't find any relevant information to answer your question."}
        
        template = """You are a helpful assistant for Bank of Maharashtra loan products.
Answer the user's question based ONLY on the context below.
If the answer is not in the context, say "I don't have that information in the available loan product details."
Be specific and cite the loan type when relevant.
Do not make up or infer information.

You answer user questions ONLY using the provided context.
You do not guess, assume, or use general banking knowledge.

━━━━━━━━━━━━━━━━━━━━
STEP 1: AGENT RESPONSIBILITY
━━━━━━━━━━━━━━━━━━━━
• Act as a loan information expert for Bank of Maharashtra.
• Provide factual, context-grounded responses.
• Maintain accuracy and financial safety.

━━━━━━━━━━━━━━━━━━━━
STEP 2: NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━
1. Use ONLY the context provided to you.
2. Never fabricate interest rates, tenure, fees, or benefits.
3. Never infer information that is not explicitly stated.
4. If the answer is missing, respond EXACTLY with:
   "I don't have that information in the available loan product details."
5. Clearly specify the loan or scheme name in every answer.

━━━━━━━━━━━━━━━━━━━━
STEP 3: HOW TO ANSWER
━━━━━━━━━━━━━━━━━━━━
• Interest rate questions → return exact rate from context
• Tenure questions → return maximum tenure only if available
• Scheme questions → briefly explain scheme features
• Fee / concession questions → answer only if explicitly stated

━━━━━━━━━━━━━━━━━━━━
STEP 4: CONTEXT
━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━
STEP 5: QUESTION
━━━━━━━━━━━━━━━━━━━━
{question}

━━━━━━━━━━━━━━━━━━━━
STEP 6: FINAL ANSWER
━━━━━━━━━━━━━━━━━━━━
Generate a concise, accurate answer strictly based on the context.
"""
            
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm | StrOutputParser()
            
        try:
            response = chain.invoke({"context": context, "question": question})
            return {"answer": response}
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"error": f"Generation failed: {str(e)}"}
