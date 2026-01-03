# Semantic Storage Layer

Unified semantic storage layer that combines all captured data (screen, clipboard, files) into one searchable store with entity extraction and vector embeddings.

## Features

- **Unified Storage**: Combines data from all capture sources (screen, clipboard, files)
- **Entity Extraction**: Extracts people, companies, dates, amounts using spaCy
- **Vector Embeddings**: Generates semantic embeddings using sentence-transformers
- **Hybrid Search**: Combines SQLite FTS (keyword) + LanceDB (semantic) search
- **Simple API**: `add()`, `search()`, `semantic_search()`, `get_entities()`

## Installation

Ensure dependencies are installed:

```bash
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

## Usage

### Python API

```python
from src.store import SemanticStore

# Initialize store
store = SemanticStore()

# Add content
content_id = store.add("Meeting with John about Q1 revenue of $500K")

# Keyword search
results = store.search("revenue")

# Semantic search (finds similar meaning)
results = store.semantic_search("financial discussions")

# Get extracted entities
people = store.get_entities(entity_type="person")
companies = store.get_entities(entity_type="org")
amounts = store.get_entities(entity_type="money")

# Get statistics
stats = store.get_stats()
print(f"Total content: {stats['total_content']}")
print(f"Total entities: {stats['total_entities']}")

# Sync from existing captures
store.sync_from_captures()
```

### CLI

The semantic store includes a CLI for easy querying:

```bash
# Text search
python -m src.store.cli search "revenue"

# Semantic search
python -m src.store.cli semantic "financial discussions"

# List entities
python -m src.store.cli entities --type person
python -m src.store.cli entities --type org

# Add content manually
python -m src.store.cli add "Content to store"

# Sync from capture sources
python -m src.store.cli sync

# View statistics
python -m src.store.cli stats
```

## Architecture

### Storage

- **SQLite**: Structured data + metadata + FTS (full-text search)
  - `semantic_content`: All captured content
  - `entities`: Extracted named entities
  - `semantic_content_fts`: Full-text search index

- **LanceDB**: Vector embeddings for semantic search
  - Local-first vector database
  - Stores 384-dimensional embeddings (all-MiniLM-L6-v2)

### Entity Types

Extracted entities are classified as:
- `person`: People names
- `org`: Organizations/companies
- `date`: Dates and times
- `money`: Monetary amounts
- `gpe`: Geopolitical entities (countries, cities)
- `product`: Product names
- `other`: Other named entities

### Models

- **Entity Extraction**: spaCy `en_core_web_sm`
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (384 dimensions)
  - Fast, efficient, good quality
  - Runs locally, no API calls needed

## Data Flow

```
Capture Sources → Semantic Store → Search APIs
    ↓                    ↓              ↓
 Screen            SQLite (FTS)    search()
 Clipboard         LanceDB (vec)   semantic_search()
 Files             Entities        get_entities()
```

## Performance

- **Entity extraction**: ~100ms for typical document
- **Embedding generation**: ~50ms for typical text
- **Search**: <10ms for FTS, ~50ms for vector search
- **Storage**: ~1KB per content item (excluding embeddings)

## Testing

Run tests:

```bash
pytest tests/store/test_semantic_store.py -v
```

## Future Enhancements

- [ ] Temporal entity linking (track entities over time)
- [ ] Relationship extraction (who works at which company)
- [ ] Topic modeling for content categorization
- [ ] Incremental embedding updates
- [ ] Multi-modal search (text + images)
