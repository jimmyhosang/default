"""
MCP (Model Context Protocol) Server for Unified AI System

This module exposes the Unified AI System's capabilities as MCP tools,
allowing LLMs like Claude to interact with captured data, perform searches,
and execute actions.
"""

from .server import MCPServer, create_mcp_server

__all__ = ["MCPServer", "create_mcp_server"]
