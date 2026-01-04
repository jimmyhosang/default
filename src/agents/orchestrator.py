"""
Main Agent Orchestrator.
"""
from typing import Dict, Any, Optional
import logging

from src.thought.llm_client import LLMClient
from src.thought.router import ModelRouter

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Central controller for the AI agent.
    Receives user input, plans, and executing actions.
    """
    
    def __init__(self):
        self.llm = LLMClient()
        self.router = ModelRouter()
        
    async def process(self, user_input: str) -> str:
        """
        Process user input and return a response.
        (Currently a simple pass-through to LLM).
        """
        logger.info(f"Processing user input: {user_input[:50]}...")
        
        # 1. Decide complexity (hardcoded for now)
        model = self.router.route("fast")
        
        # 2. Generate response
        try:
            result = await self.llm.generate(
                prompt=user_input,
                model=model,
                system="You are a helpful AI assistant running locally."
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return f"Error processing request: {e}"
