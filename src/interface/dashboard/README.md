# Unified AI System Dashboard

A local web dashboard for visualizing all captured data from the Unified AI System.

## Features

### 1. Overview Tab
- **Statistics Dashboard**: Total captured items, entities extracted, and source breakdowns
- **Daily Activity Chart**: Visual representation of capture activity over the past week
- **Capability Status**: Shows which AI features are enabled (vector search, entity extraction)

### 2. Activity Timeline
- View chronological history of all captured data
- Filter by source type (screen, clipboard, files, manual)
- Filter by time period (24 hours, 7 days, 30 days)
- Real-time timestamps and content previews

### 3. Search Interface
- **Full-Text Search**: Fast keyword-based search across all content
- **Semantic Search**: AI-powered similarity search using vector embeddings
- Filter results by source type
- View search results with relevance scores

### 4. Entity View
- **People**: Aggregated view of all people mentioned with frequency counts
- **Organizations**: Companies and organizations extracted from content
- **Other Entities**: Dates, money amounts, locations, products
- Context snippets showing where entities appear

### 5. Relationship Graph
- Visual representation of entity co-occurrences
- See which people, organizations, and concepts appear together
- Connection strength based on frequency

## Installation

### Prerequisites

Ensure you have the required dependencies installed:

```bash
# Install from project root
pip install -r requirements.txt

# Or install specific dashboard dependencies
pip install fastapi uvicorn
```

### Optional AI Features

For full functionality, install these additional dependencies:

```bash
# For entity extraction
pip install spacy
python -m spacy download en_core_web_sm

# For semantic/vector search
pip install sentence-transformers lancedb pyarrow
```

## Running the Dashboard

### Method 1: Direct Python Execution

```bash
# From project root
python src/interface/dashboard/server.py
```

### Method 2: Using Uvicorn

```bash
# From project root
python -m uvicorn src.interface.dashboard.server:app --reload

# Or with custom host/port
python -m uvicorn src.interface.dashboard.server:app --host 0.0.0.0 --port 8080
```

### Method 3: Using the Module

```bash
# From project root
python -m src.interface.dashboard.server
```

## Accessing the Dashboard

Once started, open your browser and navigate to:

```
http://localhost:8000
```

You should see the dashboard interface with tabs for:
- Overview
- Activity Timeline
- Search
- Entities
- Relationships

## API Endpoints

The dashboard provides a REST API that you can also use programmatically:

### Statistics
```bash
GET /api/stats
# Returns overall statistics about captured data
```

### Timeline
```bash
GET /api/timeline?days=7&source_type=screen&limit=100
# Parameters:
#   - days: Number of days to look back (1-90)
#   - source_type: Filter by source (screen, clipboard, file, manual)
#   - limit: Maximum items to return (1-1000)
```

### Search
```bash
GET /api/search?q=meeting&semantic=false&source_type=&limit=20
# Parameters:
#   - q: Search query (required)
#   - semantic: Use semantic/vector search (true/false)
#   - source_type: Filter by source type
#   - limit: Maximum results (1-100)
```

### Entities
```bash
GET /api/entities?entity_type=person&limit=100
# Parameters:
#   - entity_type: Filter by type (person, org, date, money, gpe, product)
#   - limit: Maximum results (1-500)
```

### People
```bash
GET /api/entities/people?limit=50
# Returns aggregated view of all people with mention counts
```

### Organizations
```bash
GET /api/entities/organizations?limit=50
# Returns aggregated view of all organizations with mention counts
```

### Relationships
```bash
GET /api/relationships?limit=50
# Returns graph data showing entity co-occurrences
```

### Content Detail
```bash
GET /api/content/{content_id}
# Returns full details for a specific content item including entities
```

## Usage Tips

### 1. First Time Setup

If you're running the dashboard for the first time with no data:

```python
from src.store.semantic_store import SemanticStore

# Initialize store and add some sample data
store = SemanticStore()

# Add sample content
store.add("Had a meeting with John about Q1 revenue of $500K", source_type="manual")
store.add("Discussed new features with the team at Acme Corp", source_type="manual")
store.add("Follow up with Sarah about the project deadline", source_type="manual")

# Sync existing capture data (if any)
store.sync_from_captures()
```

### 2. Enabling Semantic Search

Semantic search requires the sentence-transformers and lancedb libraries:

```bash
pip install sentence-transformers lancedb pyarrow
```

The first time you run semantic search, it will download the embedding model (all-MiniLM-L6-v2, ~90MB).

### 3. Enabling Entity Extraction

Entity extraction requires spaCy and a language model:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### 4. Data Location

All data is stored locally:
- **SQLite Database**: `~/.unified-ai/capture.db`
- **Vector Database**: `~/.unified-ai/lancedb/`

You can change these locations by modifying the SemanticStore initialization in `server.py`.

## Development

### Running in Development Mode

```bash
# Auto-reload on file changes
python -m uvicorn src.interface.dashboard.server:app --reload --log-level debug
```

### Customizing the Dashboard

- **Frontend**: Edit `index.html` - it's a single-page application with vanilla JavaScript
- **Backend**: Edit `server.py` - add new API endpoints or modify existing ones
- **Styling**: CSS is embedded in `index.html` - modify the `<style>` section

## Troubleshooting

### "No data captured yet" message

The dashboard shows empty states when there's no data. To populate it:

1. Run the capture daemons (screen, clipboard, file monitoring)
2. Or manually add data using the SemanticStore API
3. Or run `store.sync_from_captures()` to import existing data

### Semantic search not available

If you see "Vector search not available":

1. Install required packages: `pip install sentence-transformers lancedb pyarrow`
2. Restart the dashboard server
3. The first embedding generation may take a few seconds

### Entity extraction not working

If entities aren't being extracted:

1. Install spaCy: `pip install spacy`
2. Download the model: `python -m spacy download en_core_web_sm`
3. Restart the dashboard server
4. Re-add content or run sync to extract entities from existing data

### Port already in use

If port 8000 is already in use:

```bash
# Use a different port
python -m uvicorn src.interface.dashboard.server:app --port 8080
```

## Architecture

The dashboard follows a simple client-server architecture:

```
┌─────────────────────────────────────┐
│   Browser (index.html)              │
│   - Vanilla JavaScript              │
│   - No external dependencies        │
│   - Responsive CSS                  │
└─────────────────┬───────────────────┘
                  │ HTTP/JSON
                  │
┌─────────────────▼───────────────────┐
│   FastAPI Server (server.py)        │
│   - REST API endpoints              │
│   - CORS enabled                    │
│   - Runs on localhost:8000          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   SemanticStore                     │
│   - SQLite (FTS)                    │
│   - LanceDB (vectors)               │
│   - spaCy (entities)                │
└─────────────────────────────────────┘
```

## Security Notes

- The dashboard runs on localhost only by default (not exposed to network)
- CORS is enabled for local development
- No authentication is implemented (local-first, single-user system)
- To expose to network, modify the `host` parameter in uvicorn config

## Performance

- Timeline is limited to 1000 items max to prevent memory issues
- Search results are paginated (max 100 items)
- Entity graphs are limited to top 50 entities for performance
- Large content items are truncated in list views

## Future Enhancements

Potential improvements for future versions:

- [ ] Export functionality (CSV, JSON)
- [ ] Advanced filtering and date range selection
- [ ] Interactive graph visualization using D3.js or similar
- [ ] Real-time updates using WebSockets
- [ ] User preferences and saved searches
- [ ] Dark mode theme
- [ ] Mobile-responsive design improvements
- [ ] Performance metrics and analytics
