# Unified AI MCP Server

Model Context Protocol (MCP) server that exposes Unified AI System capabilities as tools for LLMs like Claude.

## Overview

The MCP server allows LLMs to:
- Search captured content (text and semantic search)
- Retrieve recent activity
- Access extracted entities
- Add new content
- List files on the system

## Installation

The MCP server is included with the Unified AI System. No additional installation needed.

## Usage with Claude Desktop

Add to your Claude Desktop configuration file (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "unified-ai": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/unified-ai-system"
    }
  }
}
```

## Available Tools

### Search Tools

#### `search_content`
Search through captured content using text matching.

**Parameters:**
- `query` (required): Search query string
- `source_type` (optional): Filter by source (screen, clipboard, file, manual, browser)
- `limit` (optional): Maximum results (default: 10)

#### `semantic_search`
Search using semantic similarity (meaning-based).

**Parameters:**
- `query` (required): Natural language query
- `limit` (optional): Maximum results (default: 10)

### Content Tools

#### `get_recent_content`
Get recently captured content.

**Parameters:**
- `days` (optional): Days to look back (default: 7)
- `source_type` (optional): Filter by source
- `limit` (optional): Maximum items (default: 20)

#### `add_content`
Add new content to the system.

**Parameters:**
- `content` (required): Text content to store
- `source_type` (optional): Source type (default: manual)
- `metadata` (optional): Additional metadata object

### Entity Tools

#### `get_entities`
Get extracted entities from captured content.

**Parameters:**
- `entity_type` (optional): Filter by type (person, org, date, money, gpe, product)
- `limit` (optional): Maximum entities (default: 50)

#### `find_person`
Find mentions of a specific person.

**Parameters:**
- `name` (required): Name of person to search for

### Utility Tools

#### `get_stats`
Get statistics about captured data.

**Parameters:** None

#### `summarize_day`
Get summary of captured content for a specific day.

**Parameters:**
- `date` (optional): Date in YYYY-MM-DD format (default: today)

#### `list_files`
List files in a directory.

**Parameters:**
- `path` (required): Directory path
- `pattern` (optional): Glob pattern to filter files

## Example Conversations

### Finding information from past captures

**User:** "What was I working on yesterday?"

**Claude:** (uses `get_recent_content` with days=1)
"Based on your captured content from yesterday, you were working on:
- A Python project related to data processing (from screen captures)
- Reading documentation about FastAPI (from browser content)
- Editing a document about project requirements (from file changes)"

### Searching for specific content

**User:** "Find any mentions of the meeting with Sarah"

**Claude:** (uses `search_content` with query="meeting Sarah")
"I found 3 mentions of meetings with Sarah:
1. Calendar entry: 'Team standup with Sarah - 10am'
2. Email snippet: 'Following up on our meeting with Sarah...'
3. Notes: 'Sarah suggested we prioritize the authentication feature'"

### Getting entity information

**User:** "Who have I been communicating with this week?"

**Claude:** (uses `get_entities` with entity_type="person")
"Based on extracted entities, you've been in contact with:
- Sarah Johnson (12 mentions)
- Mike Chen (8 mentions)
- Customer Support team (5 mentions)"

## Development

### Adding New Tools

1. Create a `ToolDefinition` with name, description, and JSON schema
2. Implement the handler function
3. Register with `server.register_tool()`

```python
server.register_tool(ToolDefinition(
    name="my_tool",
    description="Description of what the tool does",
    input_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    },
    handler=my_handler_function
))
```

### Running Standalone

For testing:

```bash
python -m src.mcp.server
```

The server communicates via stdin/stdout using the MCP JSON-RPC protocol.

## Protocol Details

The server implements MCP protocol version 2024-11-05 and supports:
- `initialize` / `initialized` handshake
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `ping` - Health check

All communication uses JSON-RPC 2.0 with Content-Length headers.
