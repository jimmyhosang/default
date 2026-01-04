"""
MCP Server Implementation for Unified AI System

Implements the Model Context Protocol (MCP) to expose system capabilities as tools
that can be used by LLMs like Claude.

The server provides:
- Search tools (text and semantic search)
- Content management tools
- Entity extraction tools
- Action execution tools

Usage:
    # Start the MCP server
    python -m src.mcp.server

    # Or use as a library
    from src.mcp import create_mcp_server
    server = create_mcp_server()
    await server.run()
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ToolResultType(Enum):
    """Types of tool results."""
    TEXT = "text"
    JSON = "json"
    ERROR = "error"


@dataclass
class ToolResult:
    """Result from executing a tool."""
    type: ToolResultType
    content: Any
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "error": self.error,
        }


@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: callable = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPServer:
    """
    MCP Server for Unified AI System.

    Exposes system capabilities as MCP tools that LLMs can use.
    Communicates via stdin/stdout using JSON-RPC.
    """

    def __init__(self):
        """Initialize MCP server."""
        self.tools: Dict[str, ToolDefinition] = {}
        self.store = None
        self.executor = None
        self.running = False

        # Register default tools
        self._register_default_tools()

    def _register_default_tools(self):
        """Register the default set of tools."""
        # Search tools
        self.register_tool(ToolDefinition(
            name="search_content",
            description="Search through captured content (screenshots, clipboard, files) using text matching. Returns matching items with their content and metadata.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["screen", "clipboard", "file", "manual", "browser"],
                        "description": "Filter by content source type (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search_content
        ))

        self.register_tool(ToolDefinition(
            name="semantic_search",
            description="Search using semantic similarity (meaning-based). Better for finding conceptually related content even if exact words don't match.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what you're looking for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_semantic_search
        ))

        # Content management tools
        self.register_tool(ToolDefinition(
            name="get_recent_content",
            description="Get recently captured content from the system. Useful for understanding what the user has been working on.",
            input_schema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["screen", "clipboard", "file", "manual", "browser"],
                        "description": "Filter by content source type (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items (default: 20)",
                        "default": 20
                    }
                },
                "required": []
            },
            handler=self._handle_get_recent
        ))

        self.register_tool(ToolDefinition(
            name="add_content",
            description="Add new content to the system for storage and indexing.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content to store"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["manual", "browser", "api"],
                        "description": "Type of content source",
                        "default": "manual"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)",
                        "additionalProperties": True
                    }
                },
                "required": ["content"]
            },
            handler=self._handle_add_content
        ))

        # Entity tools
        self.register_tool(ToolDefinition(
            name="get_entities",
            description="Get extracted entities (people, organizations, dates, etc.) from captured content.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["person", "org", "date", "money", "gpe", "product"],
                        "description": "Filter by entity type (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entities (default: 50)",
                        "default": 50
                    }
                },
                "required": []
            },
            handler=self._handle_get_entities
        ))

        self.register_tool(ToolDefinition(
            name="find_person",
            description="Find mentions of a specific person across all captured content.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to search for"
                    }
                },
                "required": ["name"]
            },
            handler=self._handle_find_person
        ))

        # Statistics and summaries
        self.register_tool(ToolDefinition(
            name="get_stats",
            description="Get statistics about the captured data (total items, breakdown by source, etc.).",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_get_stats
        ))

        self.register_tool(ToolDefinition(
            name="summarize_day",
            description="Get a summary of captured content for a specific day.",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    }
                },
                "required": []
            },
            handler=self._handle_summarize_day
        ))

        # Action tools
        self.register_tool(ToolDefinition(
            name="list_files",
            description="List files in a directory on the user's system.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files"
                    }
                },
                "required": ["path"]
            },
            handler=self._handle_list_files
        ))

    def register_tool(self, tool: ToolDefinition):
        """Register a tool with the server."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def _init_store(self):
        """Lazily initialize the semantic store."""
        if self.store is None:
            try:
                from src.store.semantic_store import SemanticStore
                self.store = SemanticStore()
            except Exception as e:
                logger.warning(f"Failed to initialize store: {e}")
                self.store = None

    def _init_executor(self):
        """Lazily initialize the action executor."""
        if self.executor is None:
            try:
                from src.action.executor import ActionExecutor
                self.executor = ActionExecutor()
            except Exception as e:
                logger.warning(f"Failed to initialize executor: {e}")
                self.executor = None

    # Tool handlers
    async def _handle_search_content(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle search_content tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        query = arguments.get("query", "")
        source_type = arguments.get("source_type")
        limit = arguments.get("limit", 10)

        try:
            results = self.store.search(query, source_type=source_type, limit=limit)
            return ToolResult(ToolResultType.JSON, results)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_semantic_search(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle semantic_search tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        try:
            results = self.store.semantic_search(query, limit=limit)
            return ToolResult(ToolResultType.JSON, results)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_get_recent(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle get_recent_content tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        days = arguments.get("days", 7)
        source_type = arguments.get("source_type")
        limit = arguments.get("limit", 20)

        try:
            results = self.store.get_timeline(
                days=days,
                source_type=source_type,
                limit=limit
            )
            return ToolResult(ToolResultType.JSON, results)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_add_content(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle add_content tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        content = arguments.get("content", "")
        source_type = arguments.get("source_type", "manual")
        metadata = arguments.get("metadata", {})

        try:
            content_id = self.store.add_content(
                content=content,
                source_type=source_type,
                metadata=metadata
            )
            return ToolResult(
                ToolResultType.JSON,
                {"success": True, "content_id": content_id}
            )
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_get_entities(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle get_entities tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        entity_type = arguments.get("entity_type")
        limit = arguments.get("limit", 50)

        try:
            entities = self.store.get_entities(entity_type=entity_type, limit=limit)
            return ToolResult(ToolResultType.JSON, entities)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_find_person(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle find_person tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        name = arguments.get("name", "")

        try:
            # Search in entities
            entities = self.store.get_entities(entity_type="person", limit=100)
            matches = [e for e in entities if name.lower() in e.get("text", "").lower()]

            # Also search in content
            content_results = self.store.search(name, limit=10)

            return ToolResult(ToolResultType.JSON, {
                "entity_matches": matches,
                "content_mentions": content_results
            })
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_get_stats(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle get_stats tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        try:
            stats = self.store.get_stats()
            return ToolResult(ToolResultType.JSON, stats)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_summarize_day(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle summarize_day tool calls."""
        self._init_store()
        if not self.store:
            return ToolResult(ToolResultType.ERROR, None, "Store not available")

        date_str = arguments.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return ToolResult(
                    ToolResultType.ERROR,
                    None,
                    "Invalid date format. Use YYYY-MM-DD"
                )
        else:
            target_date = datetime.now()

        try:
            # Get content for that day
            results = self.store.get_timeline(days=1, limit=100)

            # Filter to specific date
            day_content = [
                r for r in results
                if r.get("timestamp", "").startswith(target_date.strftime("%Y-%m-%d"))
            ]

            summary = {
                "date": target_date.strftime("%Y-%m-%d"),
                "total_items": len(day_content),
                "by_source": {},
                "sample_content": []
            }

            for item in day_content:
                source = item.get("source_type", "unknown")
                summary["by_source"][source] = summary["by_source"].get(source, 0) + 1

                if len(summary["sample_content"]) < 5:
                    summary["sample_content"].append({
                        "timestamp": item.get("timestamp"),
                        "source": item.get("source_type"),
                        "preview": item.get("content", "")[:200]
                    })

            return ToolResult(ToolResultType.JSON, summary)
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    async def _handle_list_files(self, arguments: Dict[str, Any]) -> ToolResult:
        """Handle list_files tool calls."""
        path_str = arguments.get("path", "")
        pattern = arguments.get("pattern", "*")

        try:
            path = Path(path_str).expanduser()

            if not path.exists():
                return ToolResult(
                    ToolResultType.ERROR,
                    None,
                    f"Path does not exist: {path}"
                )

            if not path.is_dir():
                return ToolResult(
                    ToolResultType.ERROR,
                    None,
                    f"Path is not a directory: {path}"
                )

            files = []
            for item in path.glob(pattern):
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })

            return ToolResult(ToolResultType.JSON, files[:100])  # Limit to 100 items
        except PermissionError:
            return ToolResult(
                ToolResultType.ERROR,
                None,
                f"Permission denied: {path_str}"
            )
        except Exception as e:
            return ToolResult(ToolResultType.ERROR, None, str(e))

    # MCP Protocol handlers
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "unified-ai-mcp",
                "version": "1.0.0",
            }
        }

    async def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/list request."""
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }

    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Unknown tool: {tool_name}"
                }],
                "isError": True
            }

        tool = self.tools[tool_name]
        result = await tool.handler(arguments)

        if result.type == ToolResultType.ERROR:
            return {
                "content": [{
                    "type": "text",
                    "text": result.error or "Unknown error"
                }],
                "isError": True
            }

        if result.type == ToolResultType.JSON:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result.content, indent=2, default=str)
                }]
            }

        return {
            "content": [{
                "type": "text",
                "text": str(result.content)
            }]
        }

    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an incoming JSON-RPC message."""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        response = {"jsonrpc": "2.0", "id": msg_id}

        try:
            if method == "initialize":
                response["result"] = await self.handle_initialize(params)
            elif method == "initialized":
                return None  # Notification, no response
            elif method == "tools/list":
                response["result"] = await self.handle_list_tools(params)
            elif method == "tools/call":
                response["result"] = await self.handle_call_tool(params)
            elif method == "notifications/cancelled":
                return None  # Notification
            elif method == "ping":
                response["result"] = {}
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
        except Exception as e:
            logger.exception(f"Error handling {method}")
            response["error"] = {
                "code": -32603,
                "message": str(e)
            }

        return response

    async def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        self.running = True
        logger.info("MCP server starting...")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin
        )

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        try:
            while self.running:
                try:
                    # Read content-length header
                    header = await reader.readline()
                    if not header:
                        break

                    header_str = header.decode('utf-8').strip()
                    if not header_str.startswith('Content-Length:'):
                        continue

                    content_length = int(header_str.split(':')[1].strip())

                    # Read empty line
                    await reader.readline()

                    # Read content
                    content = await reader.readexactly(content_length)
                    message = json.loads(content.decode('utf-8'))

                    # Handle message
                    response = await self.handle_message(message)

                    if response:
                        response_bytes = json.dumps(response).encode('utf-8')
                        header = f"Content-Length: {len(response_bytes)}\r\n\r\n"
                        writer.write(header.encode('utf-8'))
                        writer.write(response_bytes)
                        await writer.drain()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception("Error in message loop")

        finally:
            self.running = False
            logger.info("MCP server stopped")


def create_mcp_server() -> MCPServer:
    """Create and return an MCP server instance."""
    return MCPServer()


# CLI entry point
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr  # Log to stderr, keep stdout for MCP protocol
    )

    server = create_mcp_server()

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
