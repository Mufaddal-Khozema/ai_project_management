import os
from dotenv import load_dotenv
import uuid
import logging
from datetime import datetime, timezone
load_dotenv()

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

logger =logging.getLogger("discord_bot.db")

CHROMA_PERSIST_DIR = "./chroma_data"
CHROMA_COLLECTION = "discord_messages"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL =  "http://localhost:11434"

_store = None

# initialize chroma database
def init_db():
    """Create the Chroma-backend vector store. Safe to call more than once"""
    global _store
    if _store is not None:
        return

    logger.info(
        "Connecting to Chroma persist_dir=%s collection=%s embed_model=%s",CHROMA_PERSIST_DIR, CHROMA_COLLECTION, OLLAMA_EMBED_MODEL,
    )

    embeddings = OllamaEmbeddings(
        model = OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    _store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    logger.info(f"Chroma Ready")

# to be edited
