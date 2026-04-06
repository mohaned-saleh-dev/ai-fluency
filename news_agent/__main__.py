"""
Entry point for `python -m news_agent`.

Usage:
    python -m news_agent              # Launch the interactive CLI agent
    python -m news_agent --dashboard  # Launch the web dashboard
"""

import sys


def main():
    if "--dashboard" in sys.argv or "-d" in sys.argv:
        from .dashboard import app
        import os
        port = int(os.getenv("NEWS_AGENT_PORT", "5050"))
        print(f"\n  News Intelligence Dashboard: http://localhost:{port}\n")
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        import asyncio
        from .agent import main as agent_main
        asyncio.run(agent_main())


if __name__ == "__main__":
    main()
