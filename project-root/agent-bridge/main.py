from __future__ import annotations

import argparse
import asyncio

import sys
from pathlib import Path

# Add backend directory to sys.path so platforms, core, and agent modules resolve
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Thin wrapper to keep `python main.py` working while runtime code moves to
# `server/bot/main.py` for clearer repo layout.
from backend.server.bot.main import main as bot_main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Bridge Bot (wrapper)")
    parser.add_argument("--config", default="backend/data/config.json",
        help="Path to config.json (default: backend/data/config.json)")
    args = parser.parse_args()
    asyncio.run(bot_main(args.config))
