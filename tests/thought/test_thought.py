"""Tests for thought module."""
import pytest
from unittest.mock import AsyncMock, patch
from src.thought.llm_client import LLMClient
from src.thought.router import ModelRouter

class TestModelRouter:
    """Tests for ModelRouter."""
    
    def test_default_routing(self):
        """Test default model routing."""
        router = ModelRouter()
        assert router.route("fast") == "llama3.2"
        assert router.route("balanced") == "mistral"
        assert router.route("powerful") == "claude-3-5-sonnet-20241022"
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = {"fast": "tiny-model"}
        router = ModelRouter(config)
        assert router.route("fast") == "tiny-model"
        # Falls back to balanced
        assert router.route("unknown") == "mistral" 

class TestLLMClient:
    """Tests for LLMClient."""
    
    @pytest.mark.asyncio
    async def test_generate_pollama(self):
        """Test Ollama generation mocking."""
        client = LLMClient()
        
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": "Hello from Ollama",
            "done": True
        }
        
        # Patch aiohttp.ClientSession
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await client.generate("Hi", "llama3")
            
            assert result["content"] == "Hello from Ollama"
            assert result["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_generate_cloud_stub(self):
        """Test Cloud stub."""
        client = LLMClient()
        result = await client.generate("Hi", "claude-3-opus")
        
        assert "Stub response" in result["content"]
        assert result["provider"] == "cloud_stub"
