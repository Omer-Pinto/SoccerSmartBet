#!/usr/bin/env python
"""
Run the SoccerSmartBet Web Tool Tester.

Usage:
    cd <project_root>
    uv run python tests/web/run_web_tester.py [--port PORT] [--host HOST]

Requirements:
    uv sync --extra web
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


def main():
    parser = argparse.ArgumentParser(description="Run the SoccerSmartBet Web Tool Tester")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: uv pip install -e '.[web]'")
        sys.exit(1)

    print(f"""
    ⚽ SoccerSmartBet Web Tool Tester
    ================================
    Starting server at http://{args.host}:{args.port}

    Open your browser and navigate to:
    → http://localhost:{args.port}

    Press Ctrl+C to stop.
    """)

    uvicorn.run(
        "web_app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
