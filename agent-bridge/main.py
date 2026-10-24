from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

# Direct import from server.bot.main (flattened layout)
from server.bot.main import main as bot_main
from api import app  # Expose FastAPI application for uvicorn (e.g. uvicorn main:app)

__all__ = ["app", "bot_main"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Bridge Bot")
    parser.add_argument(
        "--config",
        default="data/config.json",
        help="Path to config.json (default: data/config.json)",
    )
    args = parser.parse_args()
    asyncio.run(bot_main(args.config))
