"""
Semantic Storage Layer - Unified System of Record
Combines captured data from all sources into a unified searchable semantic store.

This module provides:
- Entity extraction using spaCy
- Vector embeddings for semantic search using sentence-transformers
- Hybrid search combining SQLite FTS + LanceDB vector similarity
- Unified API for all capture sources

Usage:
    from src.store import SemanticStore

    store = SemanticStore()

    # Add content
    store.add("Meeting notes with John about Q1 revenue of $500K")

    # Search
    results = store.search("revenue")

    # Semantic search
    results = store.semantic_search("financial discussions")

    # Get entities
    entities = store.get_entities("people")
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Any
import json

# Core dependencies
try:
    import spacy
    from spacy.language import Language
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not installed. Entity extraction disabled.")
    print("Install with: pip install spacy && python -m spacy download en_core_web_sm")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Semantic search disabled.")
    print("Install with: pip install sentence-transformers")

try:
    import lancedb
    import pyarrow as pa
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("Warning: lancedb not installed. Vector search disabled.")
    print("Install with: pip install lancedb pyarrow")


EntityType = Literal["person", "org", "date", "money", "gpe", "product", "other"]
SourceType = Literal["screen", "clipboard", "file", "manual"]


class SemanticStore:
    """
    Unified semantic storage layer combining all captured data.
    Provides entity extraction, vector embeddings, and hybrid search.
    """

    def __init__(
        self,
        db_path: Path = Path("~/.unified-ai/capture.db").expanduser(),
        vector_db_path: Path = Path("~/.unified-ai/lancedb").expanduser(),
        model_name: str = "all-MiniLM-L6-v2",
        spacy_model: str = "en_core_web_sm",
    ):
        """
        Initialize semantic store.

        Args:
            db_path: Path to SQLite database
            vector_db_path: Path to LanceDB vector database
            model_name: Sentence transformer model for embeddings
            spacy_model: spaCy model for entity extraction
        """
        self.db_path = db_path
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.spacy_model_name = spacy_model

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize models
        self.nlp: Optional[Language] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.lance_db = None
        self.lance_table = None

        self._init_models()
        self._init_database()
        self._init_vector_db()

    def _init_models(self):
        """Initialize NLP models for entity extraction and embeddings."""
        # Load spaCy model for entity extraction
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(self.spacy_model_name)
            except OSError:
                print(f"spaCy model '{self.spacy_model_name}' not found.")
                print(f"Download with: python -m spacy download {self.spacy_model_name}")
                self.nlp = None

        # Load sentence transformer model for embeddings
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Failed to load embedding model: {e}")
                self.embedding_model = None

    def _init_database(self):
        """Initialize SQLite database for semantic storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Unified semantic content table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER,
                timestamp TEXT NOT NULL,
                metadata JSON,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Entity extraction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                entity_text TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                start_char INTEGER,
                end_char INTEGER,
                confidence REAL,
                metadata JSON,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES semantic_content(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_timestamp
            ON semantic_content(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_source
            ON semantic_content(source_type, source_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type
            ON entities(entity_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_content
            ON entities(content_id)
        """)

        # Full-text search index
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS semantic_content_fts USING fts5(
                content,
                content='semantic_content',
                content_rowid='id'
            )
        """)

        conn.commit()
        conn.close()

    def _init_vector_db(self):
        """Initialize LanceDB for vector embeddings."""
        if not LANCEDB_AVAILABLE:
            return

        try:
            self.lance_db = lancedb.connect(str(self.vector_db_path))

            # Check if table exists, create if not
            table_names = self.lance_db.table_names()
            if "semantic_embeddings" not in table_names:
                # Create empty table with schema
                schema = pa.schema([
                    pa.field("id", pa.int64()),
                    pa.field("vector", pa.list_(pa.float32(), 384)),  # 384 dim for all-MiniLM-L6-v2
                    pa.field("content", pa.string()),
                    pa.field("timestamp", pa.string()),
                    pa.field("source_type", pa.string()),
                ])
                self.lance_table = self.lance_db.create_table(
                    "semantic_embeddings",
                    schema=schema
                )
            else:
                self.lance_table = self.lance_db.open_table("semantic_embeddings")

        except Exception as e:
            print(f"Failed to initialize LanceDB: {e}")
            self.lance_db = None
            self.lance_table = None

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract named entities from text using spaCy.

        Args:
            text: Text to extract entities from

        Returns:
            List of entity dictionaries
        """
        if not self.nlp:
            return []

        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            # Map spaCy entity types to our types
            entity_type = self._map_entity_type(ent.label_)

            entities.append({
                'text': ent.text,
                'type': entity_type,
                'label': ent.label_,  # Original spaCy label
                'start': ent.start_char,
                'end': ent.end_char,
            })

        return entities

    def _map_entity_type(self, spacy_label: str) -> EntityType:
        """
        Map spaCy entity labels to our entity types.

        Args:
            spacy_label: spaCy entity label

        Returns:
            Mapped entity type
        """
        mapping = {
            'PERSON': 'person',
            'ORG': 'org',
            'DATE': 'date',
            'TIME': 'date',
            'MONEY': 'money',
            'GPE': 'gpe',  # Geopolitical entity
            'PRODUCT': 'product',
        }
        return mapping.get(spacy_label, 'other')

    def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """
        Generate vector embedding for text.

        Args:
            text: Text to embed

        Returns:
            Vector embedding or None if unavailable
        """
        if not self.embedding_model:
            return None

        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            return None

    def add(
        self,
        content: str,
        source_type: SourceType = "manual",
        source_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        extract_entities: bool = True,
    ) -> int:
        """
        Add content to semantic store.

        Args:
            content: Text content to store
            source_type: Type of source (screen, clipboard, file, manual)
            source_id: ID from source table (if applicable)
            metadata: Additional metadata
            extract_entities: Whether to extract entities

        Returns:
            ID of stored content
        """
        timestamp = datetime.now().isoformat()

        # Store in SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO semantic_content
            (content, source_type, source_id, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            content,
            source_type,
            source_id,
            timestamp,
            json.dumps(metadata or {})
        ))

        content_id = cursor.lastrowid

        # Update FTS index
        cursor.execute("""
            INSERT INTO semantic_content_fts(rowid, content)
            VALUES (?, ?)
        """, (content_id, content))

        conn.commit()

        # Extract and store entities
        if extract_entities:
            entities = self._extract_entities(content)
            for ent in entities:
                cursor.execute("""
                    INSERT INTO entities
                    (content_id, entity_text, entity_type, start_char, end_char, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    content_id,
                    ent['text'],
                    ent['type'],
                    ent['start'],
                    ent['end'],
                    json.dumps({'spacy_label': ent['label']})
                ))
            conn.commit()

        conn.close()

        # Generate and store embedding
        if self.lance_table is not None:
            embedding = self._generate_embedding(content)
            if embedding:
                try:
                    self.lance_table.add([{
                        'id': content_id,
                        'vector': embedding,
                        'content': content[:1000],  # Store truncated content
                        'timestamp': timestamp,
                        'source_type': source_type,
                    }])
                except Exception as e:
                    print(f"Failed to store embedding: {e}")

        return content_id

    def search(
        self,
        query: str,
        source_type: Optional[SourceType] = None,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Search content using full-text search.

        Args:
            query: Search query
            source_type: Filter by source type
            limit: Maximum results

        Returns:
            List of matching content
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if source_type:
            cursor.execute("""
                SELECT c.id, c.content, c.source_type, c.source_id,
                       c.timestamp, c.metadata
                FROM semantic_content c
                JOIN semantic_content_fts fts ON c.id = fts.rowid
                WHERE semantic_content_fts MATCH ? AND c.source_type = ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (query, source_type, limit))
        else:
            cursor.execute("""
                SELECT c.id, c.content, c.source_type, c.source_id,
                       c.timestamp, c.metadata
                FROM semantic_content c
                JOIN semantic_content_fts fts ON c.id = fts.rowid
                WHERE semantic_content_fts MATCH ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'content': row[1],
                'source_type': row[2],
                'source_id': row[3],
                'timestamp': row[4],
                'metadata': json.loads(row[5]) if row[5] else {}
            })

        conn.close()
        return results

    def semantic_search(
        self,
        query: str,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Search content using semantic similarity (vector search).

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of semantically similar content
        """
        if not self.lance_table:
            print("Vector search not available. Falling back to text search.")
            return self.search(query, limit=limit)

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if not query_embedding:
            print("Failed to generate query embedding. Falling back to text search.")
            return self.search(query, limit=limit)

        try:
            # Search LanceDB
            results = self.lance_table.search(query_embedding).limit(limit).to_list()

            # Enrich with full content from SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            enriched_results = []
            for result in results:
                content_id = result['id']
                cursor.execute("""
                    SELECT id, content, source_type, source_id, timestamp, metadata
                    FROM semantic_content
                    WHERE id = ?
                """, (content_id,))

                row = cursor.fetchone()
                if row:
                    enriched_results.append({
                        'id': row[0],
                        'content': row[1],
                        'source_type': row[2],
                        'source_id': row[3],
                        'timestamp': row[4],
                        'metadata': json.loads(row[5]) if row[5] else {},
                        'distance': result.get('_distance', 0),
                    })

            conn.close()
            return enriched_results

        except Exception as e:
            print(f"Vector search failed: {e}")
            return self.search(query, limit=limit)

    def get_entities(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get extracted entities, optionally filtered by type.

        Args:
            entity_type: Filter by entity type
            limit: Maximum results

        Returns:
            List of entities
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if entity_type:
            cursor.execute("""
                SELECT e.id, e.entity_text, e.entity_type, e.content_id,
                       c.content, c.timestamp, c.source_type
                FROM entities e
                JOIN semantic_content c ON e.content_id = c.id
                WHERE e.entity_type = ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (entity_type, limit))
        else:
            cursor.execute("""
                SELECT e.id, e.entity_text, e.entity_type, e.content_id,
                       c.content, c.timestamp, c.source_type
                FROM entities e
                JOIN semantic_content c ON e.content_id = c.id
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'text': row[1],
                'type': row[2],
                'content_id': row[3],
                'context': row[4][:200] + "..." if len(row[4]) > 200 else row[4],
                'timestamp': row[5],
                'source_type': row[6],
            })

        conn.close()
        return results

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about stored content.

        Returns:
            Dictionary of statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total content
        cursor.execute("SELECT COUNT(*) FROM semantic_content")
        total_content = cursor.fetchone()[0]

        # Content by source
        cursor.execute("""
            SELECT source_type, COUNT(*)
            FROM semantic_content
            GROUP BY source_type
        """)
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        # Total entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]

        # Entities by type
        cursor.execute("""
            SELECT entity_type, COUNT(*)
            FROM entities
            GROUP BY entity_type
        """)
        by_entity_type = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            'total_content': total_content,
            'by_source': by_source,
            'total_entities': total_entities,
            'by_entity_type': by_entity_type,
            'vector_db_available': self.lance_table is not None,
            'entity_extraction_available': self.nlp is not None,
        }

    def sync_from_captures(self):
        """
        Sync all existing capture data into semantic store.
        This imports data from screen captures, clipboard, and file history.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sync screen captures
        try:
            cursor.execute("""
                SELECT id, timestamp, extracted_text
                FROM captures
                WHERE extracted_text IS NOT NULL AND extracted_text != ''
            """)
            for row in cursor.fetchall():
                source_id, timestamp, text = row
                # Check if already synced
                cursor.execute("""
                    SELECT 1 FROM semantic_content
                    WHERE source_type = 'screen' AND source_id = ?
                """, (source_id,))
                if not cursor.fetchone():
                    self.add(text, source_type="screen", source_id=source_id)
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet

        # Sync clipboard history
        try:
            cursor.execute("""
                SELECT id, timestamp, content
                FROM clipboard_history
                WHERE content IS NOT NULL AND content != ''
            """)
            for row in cursor.fetchall():
                source_id, timestamp, content = row
                cursor.execute("""
                    SELECT 1 FROM semantic_content
                    WHERE source_type = 'clipboard' AND source_id = ?
                """, (source_id,))
                if not cursor.fetchone():
                    self.add(content, source_type="clipboard", source_id=source_id)
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet

        # Sync file history
        try:
            cursor.execute("""
                SELECT id, timestamp, content
                FROM file_history
                WHERE content IS NOT NULL AND content != ''
            """)
            for row in cursor.fetchall():
                source_id, timestamp, content = row
                cursor.execute("""
                    SELECT 1 FROM semantic_content
                    WHERE source_type = 'file' AND source_id = ?
                """, (source_id,))
                if not cursor.fetchone():
                    self.add(content, source_type="file", source_id=source_id)
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet

        conn.close()
