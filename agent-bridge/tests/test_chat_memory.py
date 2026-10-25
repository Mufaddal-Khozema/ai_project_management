"""
tests/test_chat_memory.py — Tests for channel chat message persistence,
chunking, semantic search, consolidation indexing, and agent tools.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock


def _ensure_mock_langchain():
    if "langchain_core" not in sys.modules:
        lc = MagicMock()
        lc_tools = MagicMock()

        def mock_tool_decorator(func=None, *args, **kwargs):
            if func is not None:
                func.invoke = lambda x: func(**x) if isinstance(x, dict) else func()
                func.name = func.__name__
                return func

            def wrapper(f):
                f.invoke = lambda x: f(**x) if isinstance(x, dict) else f()
                f.name = f.__name__
                return f
            return wrapper

        lc_tools.tool = mock_tool_decorator
        class BaseMessage:
            def __init__(self, content="", **kwargs):
                self.content = content
                for k, v in kwargs.items():
                    setattr(self, k, v)
        class HumanMessage(BaseMessage):
            type = "human"
        class AIMessage(BaseMessage):
            type = "ai"
        class SystemMessage(BaseMessage):
            type = "system"
        class ToolMessage(BaseMessage):
            type = "tool"

        lc_messages = MagicMock()
        lc_messages.BaseMessage = BaseMessage
        lc_messages.HumanMessage = HumanMessage
        lc_messages.AIMessage = AIMessage
        lc_messages.SystemMessage = SystemMessage
        lc_messages.ToolMessage = ToolMessage
        sys.modules["langchain_core"] = lc
        sys.modules["langchain_core.tools"] = lc_tools
        sys.modules["langchain_core.messages"] = lc_messages

    if "langchain_google_genai" not in sys.modules:
        lgg = MagicMock()
        sys.modules["langchain_google_genai"] = lgg


_ensure_mock_langchain()


def _ensure_consumer_on_path():
    root = os.path.join(os.path.dirname(__file__), "..", "python-consumer")
    if root not in sys.path:
        sys.path.insert(0, root)


class TestChunkChatMessages(unittest.TestCase):
    def test_chunk_chat_messages_clusters_turns(self):
        from core.embeddings import chunk_chat_messages

        messages = [
            {"author_name": "Alice", "content": "Did we finalize the OAuth redirect URI?", "channel_id": "c1", "channel_name": "general", "project_key": "p1"},
            {"author_name": "Bob", "content": "Yes, it is /integrations/:orgId/:provider/callback.", "channel_id": "c1", "channel_name": "general", "project_key": "p1"},
            {"author_name": "Charlie", "content": "Great, deploying now.", "channel_id": "c1", "channel_name": "general", "project_key": "p1"},
        ]

        chunks = chunk_chat_messages(messages, max_tokens=200)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Alice", chunks[0]["text"])
        self.assertIn("Bob", chunks[0]["text"])
        self.assertEqual(chunks[0]["channel_id"], "c1")


class TestDualMemoryStoreChat(unittest.TestCase):
    def test_save_chat_message_inserts_doc(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo)

        msg = {
            "message_id": "12345",
            "channel_id": "c-100",
            "project_key": "my-project",
            "author_name": "Alice",
            "content": "We agreed to deploy on Friday.",
        }

        store.save_chat_message(msg)
        mock_mongo.channel_messages.insert_one.assert_called_once()
        inserted_doc = mock_mongo.channel_messages.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc["message_id"], "12345")
        self.assertEqual(inserted_doc["content"], "We agreed to deploy on Friday.")

    def test_save_chat_message_indexes_realtime_embedding(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()
        mock_mongo.channel_messages.insert_one.return_value.inserted_id = "obj-id-1"

        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo, embeddings=mock_embeddings)

        msg = {
            "message_id": "12345",
            "channel_id": "c-100",
            "channel_name": "dev",
            "project_key": "my-project",
            "author_name": "Alice",
            "content": "Real-time vector indexing test.",
        }

        store.save_chat_message(msg)
        mock_mongo.chat_chunks.insert_one.assert_called_once()
        inserted_chunk = mock_mongo.chat_chunks.insert_one.call_args[0][0]
        self.assertEqual(inserted_chunk["embedding"], [0.1, 0.2, 0.3])
        mock_mongo.channel_messages.update_one.assert_called_once()

    def test_record_chat_message_enriches_org_id_with_workspace_uuid(self):
        from agent.agent import AgentBridge
        from core.identity_client import IdentityResult

        mock_comm = MagicMock()
        mock_comm._org_id = "default"
        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_id_client = MagicMock()
        mock_id_client.is_configured.return_value = True

        mock_id_res = IdentityResult(
            linked=True,
            user={"name": "Ghulam Hasnain"},
            workspace={"company_name": "Acme", "uuid": "889effbc-56c8-41f8-b28e-1f5666bbec67"},
            project={"project_slug": "maheennaseem-ai-project-management-tool"},
        )
        mock_id_client.resolve_discord_identity.return_value = mock_id_res

        from unittest.mock import patch
        with patch("agent.agent.ChatGoogleGenerativeAI"):
            bridge = AgentBridge(
                comm_platform=mock_comm,
                pm_platform=mock_pm,
                gemini_api_key="fake-key",
                memory_store=mock_memory,
                identity_client=mock_id_client,
            )

            raw_doc = {
                "message_id": "1563911987203674144",
                "channel_id": "1489127884319625279",
                "author_id": "1319579537012424797",
                "content": "What are current tasks in due",
            }
            bridge.record_chat_message(raw_doc)

            mock_memory.save_chat_message.assert_called_once()
            saved_doc = mock_memory.save_chat_message.call_args[0][0]
            self.assertEqual(saved_doc["org_id"], "889effbc-56c8-41f8-b28e-1f5666bbec67")
            self.assertEqual(saved_doc["project_key"], "maheennaseem-ai-project-management-tool")

    def test_get_recent_channel_messages(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()

        sample_messages = [
            {"author_name": "Bob", "content": "I fixed the login issue."},
            {"author_name": "Alice", "content": "Great, thanks!"},
        ]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = sample_messages
        mock_mongo.channel_messages.find.return_value = mock_cursor

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo)
        results = store.get_recent_channel_messages("c-100", limit=10)

        self.assertEqual(len(results), 2)
        mock_mongo.channel_messages.find.assert_called_with({"channel_id": "c-100"})

    def test_search_chat_messages_keyword(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()

        sample_match = [
            {
                "message_id": "m1",
                "author_name": "Alice",
                "content": "Database migration is planned for tomorrow.",
                "created_at": "2026-08-29T10:00:00Z",
            }
        ]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = sample_match
        mock_mongo.channel_messages.find.return_value = mock_cursor

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo)
        results = store.search_chat_messages("database migration", project_key="proj-1")

        self.assertEqual(len(results), 1)
        self.assertIn("Database migration", results[0]["content"])


class TestChatTools(unittest.TestCase):
    def test_search_chat_history_tool(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.search_chat_messages.return_value = [
            {
                "author_name": "Charlie",
                "content": "API endpoint /v2/tasks is live.",
                "channel_name": "dev-chat",
                "created_at": "2026-08-29",
            }
        ]

        tools = build_tools(mock_pm, "proj-123", "read", memory_store=mock_memory, project_key="slug-123")
        search_tool = next((t for t in tools if getattr(t, "name", None) == "search_chat_history"), None)
        self.assertIsNotNone(search_tool)

        output = search_tool.invoke({"query": "API endpoint"})
        self.assertIn("API endpoint /v2/tasks is live", output)
        self.assertIn("Charlie", output)

    def test_get_recent_channel_chat_tool(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.get_recent_channel_messages.return_value = [
            {"author_name": "Alice", "content": "Deploying now."},
            {"author_name": "Bob", "content": "Watching the logs."},
        ]

        tools = build_tools(mock_pm, "proj-123", "read", memory_store=mock_memory, project_key="slug-123")
        recent_tool = next((t for t in tools if getattr(t, "name", None) == "get_recent_channel_chat"), None)
        self.assertIsNotNone(recent_tool)

        output = recent_tool.invoke({"limit": 10})
        self.assertIn("Alice: Deploying now", output)
        self.assertIn("Bob: Watching the logs", output)

    def test_get_chat_summary_tool(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.search_chat_messages.return_value = [
            {"author_name": "Alice", "content": "We decided on Fastify for JWT verification.", "channel_name": "architecture"},
        ]

        tools = build_tools(mock_pm, "proj-123", "read", memory_store=mock_memory, project_key="slug-123")
        summary_tool = next((t for t in tools if getattr(t, "name", None) == "get_chat_summary"), None)
        self.assertIsNotNone(summary_tool)

        output = summary_tool.invoke({"topic": "Fastify JWT"})
        self.assertIn("We decided on Fastify", output)
        self.assertIn("architecture", output)


class TestConsolidationChatIndexing(unittest.TestCase):
    def test_index_unindexed_chats_batch(self):
        _ensure_consumer_on_path()
        from memory.consolidation import ConsolidationWorker

        mock_mongo = MagicMock()
        mock_llm = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.embed_documents.return_value = [[0.1, 0.2, 0.3]]

        unindexed_sample = [
            {
                "_id": "id-1",
                "message_id": "m1",
                "channel_id": "c1",
                "channel_name": "general",
                "project_key": "p1",
                "author_name": "Alice",
                "content": "Remember to run migrations before testing.",
                "created_at": "2026-08-29",
            }
        ]
        mock_mongo.channel_messages.find.return_value.limit.return_value = unindexed_sample

        worker = ConsolidationWorker(mongo_db=mock_mongo, llm=mock_llm, embeddings=mock_embeddings)
        worker._index_unindexed_chats()

        mock_mongo.chat_chunks.insert_many.assert_called_once()
        inserted_chunks = mock_mongo.chat_chunks.insert_many.call_args[0][0]
        self.assertEqual(len(inserted_chunks), 1)
        self.assertEqual(inserted_chunks[0]["embedding"], [0.1, 0.2, 0.3])
        mock_mongo.channel_messages.update_many.assert_called_once()


class TestEmbeddingProviderFallback(unittest.TestCase):
    def test_embedding_provider_no_key(self):
        from core.embeddings import EmbeddingProvider
        ep = EmbeddingProvider(api_key="")
        self.assertFalse(ep.available)
        self.assertIsNone(ep.embed_query("test"))
        self.assertIsNone(ep.embed_documents(["test"]))

    def test_embedding_provider_fallback_on_404(self):
        from unittest.mock import patch, MagicMock
        from core.embeddings import EmbeddingProvider

        with patch("langchain_google_genai.GoogleGenerativeAIEmbeddings") as MockEmbed:
            client1 = MagicMock()
            client1.embed_query.side_effect = Exception("404 NOT_FOUND models/text-embedding-004 is not found")
            client2 = MagicMock()
            client2.embed_query.return_value = [0.1, 0.2, 0.3]

            MockEmbed.side_effect = [client1, client2]

            ep = EmbeddingProvider(api_key="fake-key")
            self.assertTrue(ep.available)
            vec = ep.embed_query("hello")
            self.assertEqual(vec, [0.1, 0.2, 0.3])
            self.assertTrue(ep.available)
            self.assertEqual(ep.model, "gemini-embedding-001")

    def test_embedding_provider_disables_gracefully_when_all_fail(self):
        from unittest.mock import patch, MagicMock
        from core.embeddings import EmbeddingProvider

        with patch("langchain_google_genai.GoogleGenerativeAIEmbeddings") as MockEmbed:
            failing_client = MagicMock()
            failing_client.embed_query.side_effect = Exception("404 NOT_FOUND: model not found")
            MockEmbed.return_value = failing_client

            ep = EmbeddingProvider(api_key="fake-key")
            self.assertTrue(ep.available)
            vec = ep.embed_query("hello")
            self.assertIsNone(vec)
            self.assertFalse(ep.available)
            # Subsequent calls return None immediately
            self.assertIsNone(ep.embed_query("another query"))


if __name__ == "__main__":
    unittest.main()
