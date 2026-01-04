"""
LLM Client for interacting with local (Ollama) and cloud models.
"""
from typing import Optional, Dict, Any, List, Union
import logging
import json
import os
import aiohttp

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified client for LLM interactions.
    Defaults to local Ollama instance.
    """
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize LLM Client.
        
        Args:
            ollama_base_url: Base URL for Ollama API.
        """
        self.ollama_base_url = ollama_base_url.rstrip("/")
        
    async def generate(
        self, 
        prompt: str, 
        model: str, 
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: User prompt.
            model: Model name (e.g., "llama3").
            system: System prompt/context.
            json_mode: detailed JSON output.
            temperature: Creativity (0.0 to 1.0).
            
        Returns:
            Dict containing 'content' and usage stats.
        """
        # Determine provider based on model name (simple heuristic)
        if model.startswith("claude") or model.startswith("gpt"):
             return await self._generate_cloud(prompt, model, system, json_mode, temperature)
        else:
             return await self._generate_ollama(prompt, model, system, json_mode, temperature)

    async def _generate_ollama(
        self, 
        prompt: str, 
        model: str, 
        system: Optional[str],
        json_mode: bool,
        temperature: float
    ) -> Dict[str, Any]:
        """Call Ollama API."""
        url = f"{self.ollama_base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
        }
        
        if system:
            payload["system"] = system
            
        if json_mode:
            payload["format"] = "json"
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise RuntimeError(f"Ollama API Error ({response.status}): {text}")
                    
                    data = await response.json()
                    return {
                        "content": data.get("response", ""),
                        "model": model,
                        "provider": "ollama",
                        "done": data.get("done", False)
                    }
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def _generate_cloud(
        self, 
        prompt: str, 
        model: str, 
        system: Optional[str],
        json_mode: bool,
        temperature: float
    ) -> Dict[str, Any]:
        """
        Stub for Cloud API (e.g. Anthropic/OpenAI).
        Real implementation would use SDKs or REST APIs.
        """
        logger.warning(f"Cloud generation requested for {model} but not implemented. Returning stub.")
        print(f"[STUB] Generating with {model}...\nPrompt: {prompt[:50]}...")
        return {
            "content": f"[Stub response from {model}]",
            "model": model,
            "provider": "cloud_stub"
        }
