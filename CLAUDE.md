# CLAUDE.md - Unified AI System Project Guidelines

## Project Overview

This is a local-first AI system that unifies:
- **System of Record**: Automatic desktop/app data capture
- **System of Action**: AI-driven workflow automation  
- **System of Thought**: LLM reasoning and decision making

## Architecture Principles

1. **Local-First**: All data stored locally by default. Cloud is optional.
2. **Privacy-Preserving**: User controls what gets captured and stored.
3. **API-Optional**: Prefer browser automation over API dependencies.
4. **Cost-Efficient**: Use local models when possible, cloud only for complex reasoning.
5. **Incremental**: Build working features, not perfect features.

## Code Standards

### Python
- Python 3.11+ required
- Type hints on all public functions
- Async/await for I/O operations
- Use `pathlib` for file paths
- Docstrings in Google style

### Dependencies
- Prefer stdlib over external packages
- Pin versions in pyproject.toml
- Audit new dependencies for security

### Testing
- pytest for all tests
- Minimum 80% coverage on core modules
- Integration tests for capture and action modules

## Key Decisions

### Storage
- SQLite for structured data (simple, portable, reliable)
- LanceDB for vector embeddings (local, fast)
- JSON files for configuration

### Local LLM
- Ollama for model management
- Route simple tasks to small models (phi-3, llama-3.2-3b)
- Reserve Claude API for complex multi-step reasoning

### Capture
- Screenshots via `mss` (cross-platform, fast)
- OCR via `pytesseract` with preprocessing
- File monitoring via `watchdog`

## Directory Structure

```
src/
├── capture/        # Data capture modules
├── store/          # Storage and retrieval
├── action/         # Workflow execution
├── thought/        # LLM integration
├── agents/         # Agent orchestration
└── utils/          # Shared utilities
```

## Common Tasks

### Adding a new capture source
1. Create module in `src/capture/`
2. Implement `CaptureSource` protocol
3. Register in capture manager
4. Add privacy controls

### Adding a new action
1. Create tool in `src/action/tools/`
2. Define input/output schema
3. Add safety checks and approval flow
4. Register with action executor

### Adding a new integration
1. Prefer MCP protocol when available
2. Fall back to browser automation
3. Cache data locally
4. Handle offline gracefully

## Security Guidelines

- Never log sensitive data (passwords, tokens, PII)
- Sandbox all automated actions
- Require explicit approval for destructive actions
- Encrypt any synced data end-to-end

## Getting Help

When implementing features:
1. Check existing modules for patterns
2. Reference the architecture plan
3. Ask @claude with full context
4. Write tests before complex implementations

## Current Sprint Focus

Sprint 1: Core capture infrastructure
- Screen capture daemon
- Clipboard monitoring  
- File system watcher
- SQLite storage layer
