# GitHub Issues to Create for Claude Code

Copy each of these as GitHub issues in your repo. Tag @claude to get implementation help.

---

## Issue #1: Screen Capture Daemon

**Title:** Implement screen capture daemon with OCR

**Labels:** `enhancement`, `system-of-record`, `sprint-1`

**Body:**
```markdown
## Description
Create a background daemon that captures screenshots periodically and extracts text using OCR.

## Requirements
- Capture screenshots every 5 seconds (configurable)
- Use perceptual hashing to detect significant screen changes
- Only store captures when content changes (>10% difference)
- Extract text using pytesseract with preprocessing
- Store in SQLite with full-text search index
- Detect active window and application name
- CPU usage should stay below 5%

## Technical Notes
- Use `mss` for cross-platform screenshot capture
- Use `pytesseract` for OCR
- Store in `~/.unified-ai/capture.db`
- Include FTS5 virtual table for text search

## Acceptance Criteria
- [ ] Daemon runs in background
- [ ] Captures are stored in SQLite
- [ ] Full-text search works
- [ ] Deduplication prevents storing identical screens
- [ ] Can be started/stopped gracefully

@claude please implement this based on the starter code in src/capture/screen_capture.py
```

---

## Issue #2: Clipboard Monitor

**Title:** Implement clipboard monitoring with content classification

**Labels:** `enhancement`, `system-of-record`, `sprint-1`

**Body:**
```markdown
## Description
Monitor clipboard for copy operations and store content with automatic classification.

## Requirements
- Detect all clipboard copy operations
- Classify content type (text, code, URL, data, image)
- Link clipboard content to source application
- Store with timestamp and metadata
- Enable semantic search across clipboard history

## Content Classification
- **code**: Detect programming languages (Python, JS, SQL, etc.)
- **url**: URLs and links
- **data**: JSON, CSV, tabular data
- **text**: General text content
- **image**: Image data (store as hash/reference)

## Technical Notes
- Use `pyperclip` or platform-specific clipboard APIs
- Poll every 500ms or use native hooks
- Store in same SQLite database as screen captures

## Acceptance Criteria
- [ ] Clipboard changes detected within 1 second
- [ ] Content classified correctly
- [ ] Source app identified when possible
- [ ] Searchable history

@claude please implement a clipboard monitor module
```

---

## Issue #3: File System Watcher

**Title:** Implement file system monitoring with content extraction

**Labels:** `enhancement`, `system-of-record`, `sprint-1`

**Body:**
```markdown
## Description
Monitor key directories for file changes and extract/index content.

## Requirements
- Monitor ~/Documents, ~/Desktop, ~/Downloads (configurable)
- Detect create, modify, delete, move operations
- Extract text from common formats:
  - PDF (using pypdf2 or pdfplumber)
  - DOCX (using python-docx)
  - TXT, MD, JSON, CSV
  - Code files (.py, .js, .ts, etc.)
- Create embeddings for semantic search
- Track file relationships and versions

## Technical Notes
- Use `watchdog` library for cross-platform monitoring
- Debounce rapid changes (save → save → save)
- Handle large files gracefully (stream processing)
- Respect .gitignore patterns

## Acceptance Criteria
- [ ] File changes detected within 2 seconds
- [ ] Text extracted from supported formats
- [ ] Embeddings generated and stored
- [ ] File version history maintained

@claude please implement a file watcher module
```

---

## Issue #4: Semantic Storage Layer

**Title:** Build unified semantic storage with vector search

**Labels:** `enhancement`, `system-of-record`, `sprint-2`

**Body:**
```markdown
## Description
Create a unified storage layer that combines structured data, full-text search, and vector embeddings.

## Requirements
- Single API for all storage operations
- Automatic entity extraction (people, companies, dates, amounts)
- Vector embeddings for semantic search
- Relationship mapping between entities
- Export to standard formats (JSON, CSV, SQL)

## Architecture
```python
class SemanticStore:
    def add(self, content: str, metadata: dict) -> str
    def search(self, query: str, limit: int = 10) -> list[Result]
    def semantic_search(self, query: str, limit: int = 10) -> list[Result]
    def get_entities(self, content_id: str) -> list[Entity]
    def get_related(self, entity_id: str) -> list[Relation]
```

## Technical Notes
- SQLite for structured data
- LanceDB for vector storage
- sentence-transformers for embeddings
- spaCy for entity extraction

## Acceptance Criteria
- [ ] Unified API works
- [ ] Full-text + semantic search both functional
- [ ] Entities extracted and linked
- [ ] Export functions work

@claude please implement the semantic storage layer
```

---

## Issue #5: Local LLM Integration

**Title:** Set up local LLM inference with Ollama

**Labels:** `enhancement`, `system-of-thought`, `sprint-3`

**Body:**
```markdown
## Description
Integrate local LLM inference using Ollama with smart model routing.

## Requirements
- Install and configure Ollama
- Implement model routing based on task complexity:
  - Simple tasks → small model (phi-3, llama-3.2-3b)
  - Medium tasks → larger model (llama-3.1-8b)
  - Complex tasks → Claude API (fallback)
- Response caching for repeated queries
- Token usage tracking

## Model Routing Logic
```python
def route_task(task: str, complexity: str) -> str:
    if complexity == "simple":
        return "phi3"  # classification, extraction
    elif complexity == "medium":
        return "llama3.1"  # summarization, analysis
    else:
        return "claude"  # complex reasoning
```

## Technical Notes
- Use ollama Python package
- Cache responses in SQLite
- Log all API calls with costs

## Acceptance Criteria
- [ ] Ollama running with multiple models
- [ ] Smart routing working
- [ ] Caching reduces redundant calls
- [ ] Cost tracking for cloud API

@claude please implement local LLM integration
```

---

## Issue #6: Basic Agent Controller

**Title:** Create minimal agent that answers questions about captured data

**Labels:** `enhancement`, `system-of-thought`, `sprint-3`

**Body:**
```markdown
## Description
Build a basic agent that can answer natural language questions about captured data.

## Requirements
- Accept natural language queries
- Search semantic store for relevant context
- Generate answers using local LLM
- Cite sources (which capture/file)
- Handle follow-up questions with context

## Example Interactions
```
User: "What was I working on yesterday afternoon?"
Agent: Based on your screen captures from yesterday 2-6pm, you were:
- Writing code in VS Code (src/api/routes.py)
- Reviewing a PR on GitHub
- Researching "async Python patterns"
[Sources: captures #142, #145, #151]

User: "What did that PR change?"
Agent: The PR (#47) modified the authentication flow...
```

## Technical Notes
- Use semantic search to gather context
- Construct prompts with relevant captures
- Maintain conversation history

## Acceptance Criteria
- [ ] Answers questions about captured data
- [ ] Cites specific sources
- [ ] Handles follow-ups
- [ ] Works offline with local models

@claude please implement a basic question-answering agent
```

---

## Quick Start Commands

After creating these issues, go to your repo and start working:

```bash
# Clone your repo
git clone https://github.com/jimmyhosang/your-repo-name
cd your-repo-name

# Copy the starter files
# (Upload the files from this plan)

# Install dependencies
pip install -r requirements.txt

# Run Claude Code from your repo directory
claude

# Ask Claude to work on an issue
> Work on issue #1 - screen capture daemon
```
