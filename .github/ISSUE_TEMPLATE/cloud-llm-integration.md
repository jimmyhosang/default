---
name: "feat: Implement Cloud LLM Integration (Claude API)"
about: Implement full Claude API integration for the "powerful" tier in the model router
title: "feat: Implement Cloud LLM Integration (Claude API)"
labels: enhancement, high-priority
---

## Summary

Implement full Claude API integration for the "powerful" tier in the model router. Currently, cloud LLM generation is stubbed out and returns placeholder text, blocking complex reasoning workflows that require more capable models than local Ollama options.

## Background

The model router (`src/thought/router.py`) already routes "powerful" complexity queries to `claude-3-5-sonnet`, but the actual implementation in `src/thought/llm_client.py` is a stub:

```python
async def _generate_cloud(self, prompt: str, model: str, ...) -> str:
    # Cloud provider implementation (Claude, GPT, etc.)
    return "Cloud generation not yet implemented"
```

## Requirements

### Core Implementation

- [ ] Implement `_generate_cloud()` method using the Anthropic Python SDK
- [ ] Support Claude 3.5 Sonnet (and optionally Opus) models
- [ ] Handle API key configuration via environment variable (`ANTHROPIC_API_KEY`)
- [ ] Support streaming responses for better UX
- [ ] Implement proper error handling for rate limits, token limits, and API errors
- [ ] Add retry logic with exponential backoff for transient failures

### Configuration

- [ ] Add API key management to settings (store securely, not in plaintext)
- [ ] Allow model selection in config (default: `claude-3-5-sonnet-20241022`)
- [ ] Configure max tokens, temperature defaults
- [ ] Add fallback behavior when API key is not configured (graceful degradation to local)

### Integration

- [ ] Update RAG engine to leverage Claude for complex queries
- [ ] Add complexity detection to auto-route queries (simple → local, complex → Claude)
- [ ] Ensure system prompts and context formatting work correctly with Claude

### Testing

- [ ] Unit tests with mocked API responses
- [ ] Integration test with actual API (optional, CI-skippable)
- [ ] Test graceful fallback when API unavailable

## Technical Notes

- The Anthropic SDK is already in dependencies (`anthropic` in requirements)
- Follow existing async patterns in `llm_client.py`
- Respect privacy principles: never send sensitive captured data to cloud without user consent
- Consider cost tracking/budgeting features for API usage

## Acceptance Criteria

1. `LLMClient.generate()` successfully calls Claude API when complexity is "powerful"
2. Streaming responses work for real-time output in the UI
3. System gracefully falls back to local models if API key missing or quota exceeded
4. RAG queries can use Claude for better answer quality
5. Tests pass with >80% coverage on new code

## Priority

**High** - This unblocks the "System of Thought" capabilities for complex reasoning tasks.

## Related Files

- `src/thought/llm_client.py` - Main implementation file
- `src/thought/router.py` - Model routing logic
- `src/thought/rag.py` - RAG engine that will use this
