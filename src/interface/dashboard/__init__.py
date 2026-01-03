"""
Dashboard - Web visualization interface for captured data

Provides a local FastAPI-based web dashboard for exploring and searching
all captured data from the Unified AI System.

Quick Start:
    python src/interface/dashboard/server.py

    Then open http://localhost:8000 in your browser.
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = ["server"]

DASHBOARD_DIR = Path(__file__).parent
