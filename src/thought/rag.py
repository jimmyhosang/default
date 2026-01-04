"""
RAG Engine (Retrieval Augmented Generation) for Unified AI System.
Connects the Semantic Store (Memory) with the LLM (Brain) to answer questions about captured data.
"""
from typing import List, Dict, Any, Optional
import logging
from src.store.semantic_store import SemanticStore
from src.thought.llm_client import LLMClient
from src.thought.router import ModelRouter

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Engine for "Ask my Data" functionality.
    Retrieves relevant context from SemanticStore and generates answers using LLM.
    """
    
    def __init__(self, store: SemanticStore = None, llm_client: LLMClient = None):
        """
        Initialize RAG Engine.
        
        Args:
            store: SemanticStore instance (defaults to new instance)
            llm_client: LLMClient instance (defaults to new instance)
        """
        self.store = store or SemanticStore()
        self.llm_client = llm_client or LLMClient()
        self.router = ModelRouter()
        
    async def query(self, user_query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Answer a user question based on their data.
        
        Args:
            user_query: The question to answer
            limit: Number of context items to retrieve
            
        Returns:
            Dict containing 'answer', 'context', and 'metadata'
        """
        # 1. Retrieve relevant context
        # Try semantic search first (vector), fall back to text search if needed
        context_items = self.store.semantic_search(user_query, limit=limit)
        
        # 2. Format context for LLM
        context_text = self._format_context(context_items)
        
        # 3. separate logic if no context found?
        # For now, we still send to LLM but with empty context, 
        # allowing it to use general knowledge or state it doesn't know.
        
        # 4. Select Model
        # Use 'balanced' model for RAG (good reasoning, decent speed)
        model = self.router.route("balanced")
        
        # 5. Generate Answer
        system_prompt = (
            "You are a helpful AI assistant with access to the user's recorded digital history "
            "(screen captures, clipboard, files). \n"
            "Use the provided CONTEXT to answer the user's question.\n"
            "If the answer is found in the context, cite the source type (e.g., 'According to your screen history...').\n"
            "If the answer is NOT in the context, state that you couldn't find it in their history, "
            "then provide a general knowledge answer if possible, clearly distinguishing it from their data."
        )
        
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {user_query}"
        
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {user_query}"
        
        try:
            response = await self.llm_client.generate(
                prompt=user_prompt,
                model=model,
                system=system_prompt
            )
            answer = response["content"]
        except Exception as e:
            logger.error(f"RAG Generation failed: {e}")
            answer = (
                "⚠️ **Local AI Offline**\n\n"
                "I found relevant content in your history (see below), but I couldn't generate a summary "
                "because the local LLM (Ollama) is not reachable.\n\n"
                "Please ensure Ollama is running (`ollama serve`)."
            )
        
        return {
            "answer": answer,
            "context": context_items,
            "model_used": model
        }

    def _format_context(self, items: List[Dict[str, Any]]) -> str:
        """Format retrieved items into a string for the prompt."""
        if not items:
            return "No relevant data found in history."
            
        formatted = []
        for i, item in enumerate(items, 1):
            source = f"[{item.get('source_type', 'unknown')} - {item.get('timestamp', 'unknown')}]"
            content = item.get('content', '').strip()
            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."
                
            formatted.append(f"{i}. {source}\n   {content}")
            
        return "\n\n".join(formatted)
