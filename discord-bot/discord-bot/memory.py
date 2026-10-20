import os
import logging
import psycopg
from dotenv import load_dotenv
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
from pgvector import Vector
from langchain_ollama import OllamaEmbeddings

load_dotenv()

logger =logging.getLogger("discord_bot.memory")

DATABASE_URL=os.getenv("DATABASE_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
DIMEN=os.getenv("EMBEDDING_DIM")
OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL")

_embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest",
    base_url="http://localhost:11434"
)

DOC_PREFIX ="search_document: "
QUERY_PREFIX="search_query: "

# defining the connection with neon database
pool =  ConnectionPool(
    DATABASE_URL,
    min_size= 1,
    max_size=5,
    open=False,
    kwargs={"autocommit": True},
    configure=lambda conn: register_vector(conn),
    check=ConnectionPool.check_connection, # Neon drops idle connections
    max_idle=120,
)

# initializing database and indexes 
def init_db():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS discord_messages (
                id BIGSERIAL PRIMARY KEY,
                discord_message_id BIGINT UNIQUE NOT NULL,
                guild_id BIGINT, 
                channel_id BIGINT NOT NULL,
                author_id BIGINT,
                author_name TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                embedding vector({DIMEN})
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS msg_channel_time_idx ON discord_messages (channel_id, created_at DESC)")

        conn.execute("CREATE INDEX IF NOT EXISTS msg_embedding_idx ON discord_messages USING hnsw (embedding vector_cosine_ops)")

    pool.open()

# function for converting messages to embedding and return vector
def _embed(text, *, query=False):
    prefix = QUERY_PREFIX if query else DOC_PREFIX
    vector= _embeddings.embed_query(prefix + text[:6000])
    if len(vector) != int(DIMEN):
        raise ValueError(
            f"{EMBEDDING_MODEL} returned{len(vector)} dims but EMBEDDING_DIMEN={DIMEN}"
        )
    return Vector(vector)

# saves the messages in the database 
def save_message(*, discord_message_id, guild_id, channel_id, author_id, author_name, role, content):
    if not content or not content.strip():
        return
    vec=_embed(content)
    with pool.connection() as conn:
        conn.execute(
            """INSERT INTO discord_messages (discord_message_id, guild_id, channel_id, author_id, author_name, role, content, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (discord_message_id) DO NOTHING""",
            (discord_message_id,guild_id,channel_id,author_id,author_name, role,content,vec),
        )

# to retrieve the last 10 messages from the discord history (small term memory)
def recent_history(channel_id, limit=10):
    """LAST N messages in the channel oldest first (rows have .role/.content)."""
    with pool.connection() as conn:
        cursor = conn.cursor(row_factory=namedtuple_row)
        cursor.execute(
            """SELECT * FROM (SELECT role, author_name, content, created_at FROM discord_messages WHERE channel_id = %s ORDER BY created_at DESC LIMIT %s) t ORDER BY created_at ASC""",
            (channel_id,limit),
        )
        return cursor.fetchall()

def search_similar(query,channel_id, k=5):
    qvec = _embed(query, query=True)
    with pool.connection() as conn:
        cursor = conn.cursor(row_factory=namedtuple_row)
        cursor.execute(
            """SELECT author_name, role, content, created_at FROM discord_messages WHERE channel_id = %s ORDER BY embedding <=> %s LIMIT %s""",
            (channel_id, qvec, k)
        )
        return cursor.fetchall()