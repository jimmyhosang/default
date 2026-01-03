#!/usr/bin/env python3
"""
Semantic Store CLI - Query and manage semantic storage

Usage:
    python -m src.store.cli search "query text"
    python -m src.store.cli semantic "query text"
    python -m src.store.cli entities --type person
    python -m src.store.cli add "content to add"
    python -m src.store.cli sync
    python -m src.store.cli stats
"""

import argparse
from pathlib import Path
from typing import Optional

from .semantic_store import SemanticStore, EntityType


def format_result(result: dict, show_full: bool = False) -> str:
    """Format search result for display."""
    lines = []
    lines.append(f"ID: {result['id']}")
    lines.append(f"Timestamp: {result['timestamp']}")
    lines.append(f"Source: {result['source_type']}")

    if 'distance' in result:
        lines.append(f"Similarity: {1 - result['distance']:.3f}")

    content = result['content']
    if not show_full and len(content) > 300:
        content = content[:300] + "..."

    lines.append(f"Content:\n  {content.replace(chr(10), chr(10) + '  ')}")

    return "\n".join(lines)


def format_entity(entity: dict) -> str:
    """Format entity for display."""
    return f"{entity['text']:30s} ({entity['type']:8s}) - {entity['context']}"


def cmd_search(args):
    """Execute text search."""
    store = SemanticStore()

    print(f"\nSearching for: '{args.query}'")
    if args.source:
        print(f"Filtering by source: {args.source}")

    results = store.search(args.query, source_type=args.source, limit=args.limit)

    print(f"\nFound {len(results)} results:\n")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print("-" * 80)
        print(format_result(result, show_full=args.full))

    if not results:
        print("No results found.")


def cmd_semantic_search(args):
    """Execute semantic search."""
    store = SemanticStore()

    print(f"\nSemantic search for: '{args.query}'")
    results = store.semantic_search(args.query, limit=args.limit)

    print(f"\nFound {len(results)} semantically similar results:\n")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print("-" * 80)
        print(format_result(result, show_full=args.full))

    if not results:
        print("No results found.")


def cmd_entities(args):
    """List entities."""
    store = SemanticStore()

    entity_type = args.type if args.type else None

    print(f"\nListing entities")
    if entity_type:
        print(f"Filtered by type: {entity_type}")

    entities = store.get_entities(entity_type=entity_type, limit=args.limit)

    print(f"\nFound {len(entities)} entities:\n")
    print("=" * 80)

    # Group by type for better display
    by_type: dict = {}
    for entity in entities:
        ent_type = entity['type']
        if ent_type not in by_type:
            by_type[ent_type] = []
        by_type[ent_type].append(entity)

    for ent_type, ents in sorted(by_type.items()):
        print(f"\n{ent_type.upper()}:")
        print("-" * 80)
        for entity in ents[:20]:  # Limit per type for readability
            print(f"  {format_entity(entity)}")

    if not entities:
        print("No entities found.")


def cmd_add(args):
    """Add content to store."""
    store = SemanticStore()

    content_id = store.add(
        args.content,
        source_type="manual",
        metadata={'cli': True}
    )

    print(f"\nContent added with ID: {content_id}")

    # Show extracted entities if available
    entities = store.get_entities(limit=1000)
    content_entities = [e for e in entities if e['content_id'] == content_id]

    if content_entities:
        print(f"\nExtracted {len(content_entities)} entities:")
        for entity in content_entities:
            print(f"  - {entity['text']} ({entity['type']})")


def cmd_sync(args):
    """Sync from capture sources."""
    store = SemanticStore()

    print("\nSyncing data from capture sources...")
    print("This may take a while for large datasets.\n")

    store.sync_from_captures()

    print("\nSync complete!")

    # Show updated stats
    stats = store.get_stats()
    print(f"\nTotal content items: {stats['total_content']}")
    print(f"Total entities: {stats['total_entities']}")


def cmd_stats(args):
    """Show statistics."""
    store = SemanticStore()

    stats = store.get_stats()

    print("\nSemantic Store Statistics")
    print("=" * 80)

    print(f"\nTotal content items: {stats['total_content']}")

    print(f"\nBy source:")
    for source, count in sorted(stats['by_source'].items()):
        print(f"  {source:12s}: {count:6d}")

    print(f"\nTotal entities: {stats['total_entities']}")

    if stats['by_entity_type']:
        print(f"\nBy entity type:")
        for ent_type, count in sorted(stats['by_entity_type'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {ent_type:12s}: {count:6d}")

    print(f"\nCapabilities:")
    print(f"  Vector search: {'✓' if stats['vector_db_available'] else '✗'}")
    print(f"  Entity extraction: {'✓' if stats['entity_extraction_available'] else '✗'}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic Store CLI - Query and manage semantic storage"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Search command
    search_parser = subparsers.add_parser('search', help='Text search')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument('--source', type=str, choices=['screen', 'clipboard', 'file', 'manual'],
                              help='Filter by source type')
    search_parser.add_argument('--limit', type=int, default=20, help='Maximum results')
    search_parser.add_argument('--full', action='store_true', help='Show full content')

    # Semantic search command
    semantic_parser = subparsers.add_parser('semantic', help='Semantic similarity search')
    semantic_parser.add_argument('query', type=str, help='Search query')
    semantic_parser.add_argument('--limit', type=int, default=20, help='Maximum results')
    semantic_parser.add_argument('--full', action='store_true', help='Show full content')

    # Entities command
    entities_parser = subparsers.add_parser('entities', help='List extracted entities')
    entities_parser.add_argument('--type', type=str,
                                choices=['person', 'org', 'date', 'money', 'gpe', 'product', 'other'],
                                help='Filter by entity type')
    entities_parser.add_argument('--limit', type=int, default=100, help='Maximum results')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add content to store')
    add_parser.add_argument('content', type=str, help='Content to add')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync from capture sources')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    commands = {
        'search': cmd_search,
        'semantic': cmd_semantic_search,
        'entities': cmd_entities,
        'add': cmd_add,
        'sync': cmd_sync,
        'stats': cmd_stats,
    }

    command_func = commands.get(args.command)
    if command_func:
        try:
            command_func(args)
        except KeyboardInterrupt:
            print("\n\nInterrupted.")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
