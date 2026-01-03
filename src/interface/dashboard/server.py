"""
FastAPI Dashboard Server - Visualization Interface for Captured Data

This module provides a web dashboard that visualizes all captured data:
- Activity timeline
- Search interface across all captured data
- Entity views (people, projects, companies)
- Daily/weekly summary statistics
- Relationship graph between entities

Usage:
    python -m uvicorn src.interface.dashboard.server:app --reload

    Or run: python src/interface/dashboard/server.py
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.store.semantic_store import SemanticStore

app = FastAPI(
    title="Unified AI System Dashboard",
    description="Local web dashboard for visualizing captured data",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize semantic store
store = SemanticStore()

# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard HTML page."""
    index_path = DASHBOARD_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("""
            <html><body>
                <h1>Dashboard not found</h1>
                <p>The index.html file is missing. Please ensure all dashboard files are present.</p>
            </body></html>
        """, status_code=404)

    return FileResponse(index_path)


@app.get("/api/timeline")
async def get_timeline(
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items")
) -> List[Dict[str, Any]]:
    """
    Get activity timeline showing captured data over time.

    Args:
        days: Number of days to look back
        source_type: Optional filter by source type (screen, clipboard, file)
        limit: Maximum number of results

    Returns:
        List of timeline items with content, timestamp, and metadata
    """
    import sqlite3

    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    # Calculate date threshold
    threshold = (datetime.now() - timedelta(days=days)).isoformat()

    if source_type:
        cursor.execute("""
            SELECT id, content, source_type, source_id, timestamp, metadata
            FROM semantic_content
            WHERE timestamp >= ? AND source_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (threshold, source_type, limit))
    else:
        cursor.execute("""
            SELECT id, content, source_type, source_id, timestamp, metadata
            FROM semantic_content
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (threshold, limit))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'content': row[1][:500] + "..." if len(row[1]) > 500 else row[1],
            'content_preview': row[1][:200] + "..." if len(row[1]) > 200 else row[1],
            'source_type': row[2],
            'source_id': row[3],
            'timestamp': row[4],
            'metadata': json.loads(row[5]) if row[5] else {}
        })

    conn.close()
    return results


@app.get("/api/search")
async def search_content(
    q: str = Query(..., min_length=1, description="Search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    semantic: bool = Query(False, description="Use semantic search"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
) -> Dict[str, Any]:
    """
    Search across all captured data using full-text or semantic search.

    Args:
        q: Search query
        source_type: Optional filter by source type
        semantic: Use semantic/vector search instead of text search
        limit: Maximum number of results

    Returns:
        Dictionary with search results and metadata
    """
    if semantic:
        results = store.semantic_search(q, limit=limit)
    else:
        results = store.search(q, source_type=source_type, limit=limit)

    return {
        'query': q,
        'search_type': 'semantic' if semantic else 'text',
        'count': len(results),
        'results': results
    }


@app.get("/api/entities")
async def get_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results")
) -> Dict[str, Any]:
    """
    Get extracted entities (people, organizations, dates, etc.).

    Args:
        entity_type: Optional filter (person, org, date, money, gpe, product)
        limit: Maximum number of results

    Returns:
        Dictionary with entities grouped by type and aggregated stats
    """
    entities = store.get_entities(entity_type=entity_type, limit=limit)

    # Group entities by type
    by_type = defaultdict(list)
    entity_counts = defaultdict(int)

    for entity in entities:
        by_type[entity['type']].append(entity)
        entity_counts[entity['text']] += 1

    # Get top entities by frequency
    top_entities = sorted(
        entity_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]

    return {
        'total': len(entities),
        'by_type': {k: len(v) for k, v in by_type.items()},
        'entities': entities,
        'top_entities': [{'text': text, 'count': count} for text, count in top_entities]
    }


@app.get("/api/entities/people")
async def get_people(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get all people entities."""
    entities = store.get_entities(entity_type="person", limit=limit)

    # Aggregate by person name
    people = defaultdict(lambda: {'name': '', 'mentions': 0, 'contexts': [], 'last_seen': None})

    for entity in entities:
        name = entity['text']
        people[name]['name'] = name
        people[name]['mentions'] += 1
        people[name]['contexts'].append({
            'content_id': entity['content_id'],
            'context': entity['context'],
            'timestamp': entity['timestamp'],
            'source_type': entity['source_type']
        })

        # Update last seen
        if not people[name]['last_seen'] or entity['timestamp'] > people[name]['last_seen']:
            people[name]['last_seen'] = entity['timestamp']

    # Sort by mention count
    result = sorted(people.values(), key=lambda x: x['mentions'], reverse=True)

    # Limit contexts to most recent 3
    for person in result:
        person['contexts'] = sorted(person['contexts'], key=lambda x: x['timestamp'], reverse=True)[:3]

    return result


@app.get("/api/entities/organizations")
async def get_organizations(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Get all organization entities."""
    entities = store.get_entities(entity_type="org", limit=limit)

    # Aggregate by org name
    orgs = defaultdict(lambda: {'name': '', 'mentions': 0, 'contexts': [], 'last_seen': None})

    for entity in entities:
        name = entity['text']
        orgs[name]['name'] = name
        orgs[name]['mentions'] += 1
        orgs[name]['contexts'].append({
            'content_id': entity['content_id'],
            'context': entity['context'],
            'timestamp': entity['timestamp'],
            'source_type': entity['source_type']
        })

        # Update last seen
        if not orgs[name]['last_seen'] or entity['timestamp'] > orgs[name]['last_seen']:
            orgs[name]['last_seen'] = entity['timestamp']

    # Sort by mention count
    result = sorted(orgs.values(), key=lambda x: x['mentions'], reverse=True)

    # Limit contexts to most recent 3
    for org in result:
        org['contexts'] = sorted(org['contexts'], key=lambda x: x['timestamp'], reverse=True)[:3]

    return result


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get overall statistics about captured data."""
    stats = store.get_stats()

    # Get time-based stats
    import sqlite3
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    # Content by day (last 7 days)
    cursor.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM semantic_content
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """)
    daily_counts = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

    # Content by hour (last 24 hours)
    cursor.execute("""
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
        FROM semantic_content
        WHERE timestamp >= datetime('now', '-1 day')
        GROUP BY hour
        ORDER BY hour
    """)
    hourly_counts = [{'hour': int(row[0]), 'count': row[1]} for row in cursor.fetchall()]

    conn.close()

    return {
        **stats,
        'daily_activity': daily_counts,
        'hourly_activity': hourly_counts
    }


@app.get("/api/relationships")
async def get_relationships(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    """
    Get relationship graph data showing connections between entities.

    Returns nodes (entities) and edges (co-occurrences in same content).
    """
    import sqlite3

    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    # Get all entities with their content_id
    cursor.execute("""
        SELECT content_id, entity_text, entity_type
        FROM entities
        ORDER BY content_id
        LIMIT ?
    """, (limit * 10,))

    entity_data = cursor.fetchall()
    conn.close()

    # Build nodes and edges
    nodes = {}
    edges = defaultdict(int)

    # Group entities by content_id
    content_entities = defaultdict(list)
    for content_id, entity_text, entity_type in entity_data:
        content_entities[content_id].append((entity_text, entity_type))

        # Add to nodes
        if entity_text not in nodes:
            nodes[entity_text] = {
                'id': entity_text,
                'label': entity_text,
                'type': entity_type,
                'count': 0
            }
        nodes[entity_text]['count'] += 1

    # Find co-occurrences
    for content_id, entities_list in content_entities.items():
        # Only process content with multiple entities
        if len(entities_list) < 2:
            continue

        # Create edges between all pairs
        for i, (e1_text, e1_type) in enumerate(entities_list):
            for e2_text, e2_type in entities_list[i+1:]:
                # Sort to ensure consistent edge key
                edge_key = tuple(sorted([e1_text, e2_text]))
                edges[edge_key] += 1

    # Convert to list format
    nodes_list = list(nodes.values())
    edges_list = [
        {
            'source': source,
            'target': target,
            'weight': weight
        }
        for (source, target), weight in edges.items()
        if weight > 0  # Only include edges with at least 1 co-occurrence
    ]

    # Limit nodes to top ones by count
    nodes_list = sorted(nodes_list, key=lambda x: x['count'], reverse=True)[:limit]

    # Filter edges to only include nodes in our limited set
    node_ids = {n['id'] for n in nodes_list}
    edges_list = [e for e in edges_list if e['source'] in node_ids and e['target'] in node_ids]

    return {
        'nodes': nodes_list,
        'edges': edges_list[:100]  # Limit edges for performance
    }


@app.get("/api/content/{content_id}")
async def get_content_detail(content_id: int) -> Dict[str, Any]:
    """Get detailed information about a specific content item."""
    import sqlite3

    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    # Get content
    cursor.execute("""
        SELECT id, content, source_type, source_id, timestamp, metadata
        FROM semantic_content
        WHERE id = ?
    """, (content_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Content not found")

    content_data = {
        'id': row[0],
        'content': row[1],
        'source_type': row[2],
        'source_id': row[3],
        'timestamp': row[4],
        'metadata': json.loads(row[5]) if row[5] else {}
    }

    # Get associated entities
    cursor.execute("""
        SELECT entity_text, entity_type, start_char, end_char
        FROM entities
        WHERE content_id = ?
        ORDER BY start_char
    """, (content_id,))

    content_data['entities'] = [
        {
            'text': row[0],
            'type': row[1],
            'start': row[2],
            'end': row[3]
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return content_data


if __name__ == "__main__":
    import uvicorn
    print("Starting Unified AI System Dashboard on http://localhost:8000")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="localhost", port=8000)
