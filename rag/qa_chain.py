from typing import Dict, List, Optional
import logging
from groq import Groq
from rag.retriever import LoanRetriever

logger = logging.getLogger(__name__)


class LoanQAChain:
    """
    Question-Answering chain for loan products.
    
    Implements RAG pattern:
    - Retrieval: Get relevant loan information
    - Augmentation: Add context to prompt
    - Generation: Generate grounded answer
    """
    
    def __init__(
        self,
        retriever: LoanRetriever,
        groq_api_key: str,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.0,
        max_tokens: int = 1024
    ):
        
        self.retriever = retriever
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Groq client
        self.client = Groq(api_key=groq_api_key)
        
        logger.info(
            f"QA Chain initialized with {model_name} "
            f"(temp={temperature}, max_tokens={max_tokens})"
        )
    
    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build the prompt for the LLM.
        
        Critical instructions:
        - Answer ONLY from context
        - Admit when information is not available
        - Be specific and accurate
        - Cite sources when possible
        
        Args:
            query: User question
            context: Retrieved context
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a Financial Question Answering Assistant for Bank of Maharashtra loan products.

Your responsibility is to answer user questions by using ONLY the information
present in the retrieved context from official Bank of Maharashtra documents.

STEP 1: ROLE DEFINITION

• You answer questions only about Bank of Maharashtra loan products.
• You do not provide general banking advice.
• You rely strictly on the retrieved context.

STEP 2: STRICT ANSWERING RULES

1. Use ONLY the information provided in the context.
2. Do NOT use external knowledge or assumptions.
3. Do NOT infer missing values.
4. If the answer is not clearly available in the context, reply EXACTLY with:
   "I don't have that information in the available loan product details."
5. Always mention the loan or scheme name in your answer.
6. If the question asks about:
   - Interest rate → give exact rate only if present
   - Tenure → give maximum tenure only if present
   - Fees / concessions → mention only if explicitly stated
7. Keep the answer simple, clear, and professional.

STEP 3: ANSWER FORMAT

When information is available, respond in a structured format:

• Loan / Scheme Name:
• Interest Rate:
• Maximum Tenure:
• Key Features / Concessions:

(Include only fields available in the context.)

━━━━━━━━━━━━━━━━━━━━
STEP 4: CONTEXT
━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━
STEP 5: USER QUESTION
━━━━━━━━━━━━━━━━━━━━
{query}

━━━━━━━━━━━━━━━━━━━━
STEP 6: FINAL ANSWER
━━━━━━━━━━━━━━━━━━━━
Answer the question strictly following the rules above."""

        
        return prompt
    
    def answer_question(
        self,
        question: str,
        return_sources: bool = True
    ) -> Dict:
        if not question or not question.strip():
            return {
                'answer': "Please provide a question.",
                'sources': [],
                'metadata': {'error': 'empty_question'}
            }
        
        logger.info(f"Answering question: '{question[:100]}...'")
        
        try:
            # Step 1: Retrieve relevant context
            retrieved_chunks = self.retriever.retrieve(question)
            
            if not retrieved_chunks:
                return {
                    'answer': (
                        "available Bank of Maharashtra loan product details. "
                        "Please try rephrasing your question or contact the bank directly."
                    ),
                    'sources': [],
                    'metadata': {'retrieved_chunks': 0}
                }
            
            # Step 2: Build context from chunks
            context = self.retriever.get_context_for_query(question)
            
            # Step 3: Build prompt
            prompt = self._build_prompt(question, context)
            
            # Step 4: Generate answer using Groq
            logger.info("Generating answer with Groq LLM")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Step 5: Format response
            result = {
                'answer': answer,
                'metadata': {
                    'retrieved_chunks': len(retrieved_chunks),
                    'model': self.model_name,
                    'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None
                }
            }
            
            # Add sources if requested
            if return_sources:
                sources = []
                for chunk in retrieved_chunks:
                    sources.append({
                        'loan_type': chunk['metadata'].get('loan_type', 'unknown'),
                        'text': chunk['text'][:200] + '...',  # Truncate for brevity
                        'score': chunk['score'],
                        'url': chunk['metadata'].get('url', '')
                    })
                result['sources'] = sources
            
            logger.info(
                f"Answer generated successfully "
                f"({result['metadata']['retrieved_chunks']} chunks used)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            return {
                'answer': (
                    "I encountered an error while processing your question. "
                    "Please try again or rephrase your question."
                ),
                'sources': [],
                'metadata': {'error': str(e)}
            }
    
    def batch_answer(self, questions: List[str]) -> List[Dict]:
        """
        Answer multiple questions.
        
        Args:
            questions: List of questions
        
        Returns:
            List of answer dictionaries
        """
        logger.info(f"Answering {len(questions)} questions")
        
        results = []
        for question in questions:
            result = self.answer_question(question)
            results.append(result)
        
        return results


def main():
    """Test the QA chain."""
    import os
    from pathlib import Path
    from rag.embeddings import EmbeddingModel
    from rag.vector_store import FAISSVectorStore
    
    # Check environment
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        logger.error("GROQ_API_KEY environment variable not set")
        return
    
    index_path = "data/processed/faiss_index"
    metadata_path = "data/processed/metadata.json"
    
    if not Path(index_path).exists():
        logger.error("Vector store not found. Run the full pipeline first.")
        return
    
    embedding_model = EmbeddingModel()
    vector_store = FAISSVectorStore(
        embedding_dim=embedding_model.get_embedding_dimension(),
        index_path=index_path,
        metadata_path=metadata_path
    )
    retriever = LoanRetriever(embedding_model, vector_store)
    
    qa_chain = LoanQAChain(
        retriever=retriever,
        groq_api_key=groq_api_key
    )
    
    logger.info("QA Chain test completed successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
