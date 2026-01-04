"""
LLM Client for interacting with local (Ollama) and cloud models.

Supports:
- Local: Ollama (llama, mistral, etc.)
- Cloud: Anthropic Claude, OpenAI GPT

Environment variables for cloud:
- ANTHROPIC_API_KEY: For Claude models
- OPENAI_API_KEY: For GPT models
"""
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging
import json
import os
import aiohttp

logger = logging.getLogger(__name__)


def load_api_keys() -> Dict[str, str]:
    """Load API keys from environment or settings file."""
    keys = {
        'anthropic': os.environ.get('ANTHROPIC_API_KEY', ''),
        'openai': os.environ.get('OPENAI_API_KEY', '')
    }

    # Also try to load from settings file
    settings_file = Path.home() / ".unified-ai" / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            llm_settings = settings.get('llm', {})
            if not keys['anthropic'] and llm_settings.get('anthropic_api_key'):
                keys['anthropic'] = llm_settings['anthropic_api_key']
            if not keys['openai'] and llm_settings.get('openai_api_key'):
                keys['openai'] = llm_settings['openai_api_key']
        except Exception:
            pass

    return keys


class LLMClient:
    """
    Unified client for LLM interactions.
    Supports local Ollama and cloud providers (Anthropic, OpenAI).
    """

    # Model to provider mapping
    MODEL_PROVIDERS = {
        'claude': 'anthropic',
        'gpt': 'openai',
    }

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize LLM Client.

        Args:
            ollama_base_url: Base URL for Ollama API.
            anthropic_api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.ollama_base_url = ollama_base_url.rstrip("/")

        # Load API keys
        keys = load_api_keys()
        self.anthropic_api_key = anthropic_api_key or keys['anthropic']
        self.openai_api_key = openai_api_key or keys['openai']

        # API endpoints
        self.anthropic_url = "https://api.anthropic.com/v1/messages"
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        
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
        Generate using cloud API (Anthropic or OpenAI).
        """
        # Determine provider
        if model.startswith("claude"):
            return await self._generate_anthropic(prompt, model, system, json_mode, temperature)
        elif model.startswith("gpt"):
            return await self._generate_openai(prompt, model, system, json_mode, temperature)
        else:
            raise ValueError(f"Unknown cloud model: {model}")

    async def _generate_anthropic(
        self,
        prompt: str,
        model: str,
        system: Optional[str],
        json_mode: bool,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate using Anthropic Claude API."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY environment variable or configure in settings."
            )

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": messages
        }

        if system:
            payload["system"] = system

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.anthropic_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Anthropic API error: {text}")
                        raise RuntimeError(f"Anthropic API Error ({response.status}): {text}")

                    data = await response.json()

                    # Extract content from response
                    content = ""
                    if data.get("content"):
                        for block in data["content"]:
                            if block.get("type") == "text":
                                content += block.get("text", "")

                    return {
                        "content": content,
                        "model": model,
                        "provider": "anthropic",
                        "usage": data.get("usage", {}),
                        "stop_reason": data.get("stop_reason")
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Anthropic request failed: {e}")
            raise RuntimeError(f"Failed to connect to Anthropic API: {e}")

    async def _generate_openai(
        self,
        prompt: str,
        model: str,
        system: Optional[str],
        json_mode: bool,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate using OpenAI GPT API."""
        if not self.openai_api_key:
            raise RuntimeError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable or configure in settings."
            )

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.openai_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"OpenAI API error: {text}")
                        raise RuntimeError(f"OpenAI API Error ({response.status}): {text}")

                    data = await response.json()

                    # Extract content from response
                    content = ""
                    if data.get("choices"):
                        content = data["choices"][0].get("message", {}).get("content", "")

                    return {
                        "content": content,
                        "model": model,
                        "provider": "openai",
                        "usage": data.get("usage", {}),
                        "finish_reason": data["choices"][0].get("finish_reason") if data.get("choices") else None
                    }
        except aiohttp.ClientError as e:
            logger.error(f"OpenAI request failed: {e}")
            raise RuntimeError(f"Failed to connect to OpenAI API: {e}")

    async def check_ollama_available(self) -> bool:
        """Check if Ollama is running and available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def list_ollama_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        return []
