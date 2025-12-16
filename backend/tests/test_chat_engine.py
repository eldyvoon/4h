"""
Unit tests for ChatEngine service.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.chat_engine import ChatEngine
from app.models.document import Document
from app.models.conversation import Conversation, Message


class TestChatEngine:
    """Tests for ChatEngine class."""
    
    def test_init(self, db_session):
        """Test ChatEngine initialization."""
        engine = ChatEngine(db_session)
        assert engine.db == db_session
        assert engine.vector_store is not None
        assert engine._client is None
    
    @pytest.mark.asyncio
    async def test_load_conversation_history_empty(self, db_session):
        """Test loading history for conversation with no messages."""
        conversation = Conversation(title="Test", document_id=None)
        db_session.add(conversation)
        db_session.commit()
        
        engine = ChatEngine(db_session)
        history = await engine._load_conversation_history(conversation.id)
        
        assert history == []
    
    @pytest.mark.asyncio
    async def test_load_conversation_history_with_messages(self, db_session):
        """Test loading history with messages."""
        conversation = Conversation(title="Test", document_id=None)
        db_session.add(conversation)
        db_session.commit()
        
        msg1 = Message(
            conversation_id=conversation.id,
            role="user",
            content="Hello"
        )
        msg2 = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Hi there!"
        )
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        engine = ChatEngine(db_session)
        history = await engine._load_conversation_history(conversation.id)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
    
    @pytest.mark.asyncio
    async def test_find_related_media_empty(self, db_session):
        """Test finding related media with no context."""
        engine = ChatEngine(db_session)
        result = await engine._find_related_media([], None, "test query")
        
        assert "images" in result
        assert "tables" in result
    
    @pytest.mark.asyncio
    async def test_find_related_media_image_keywords(self, db_session):
        """Test that image keywords trigger image search."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="completed"
        )
        db_session.add(document)
        db_session.commit()
        
        engine = ChatEngine(db_session)
        
        result = await engine._find_related_media(
            [], 
            document.id, 
            "Show me the architecture diagram"
        )
        
        assert "images" in result
        assert "tables" in result
    
    @pytest.mark.asyncio
    async def test_find_related_media_table_keywords(self, db_session):
        """Test that table keywords trigger table search."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="completed"
        )
        db_session.add(document)
        db_session.commit()
        
        engine = ChatEngine(db_session)
        
        result = await engine._find_related_media(
            [], 
            document.id, 
            "What are the experimental results?"
        )
        
        assert "images" in result
        assert "tables" in result
    
    def test_build_system_prompt(self, db_session):
        """Test system prompt building."""
        engine = ChatEngine(db_session)
        
        prompt = engine._build_system_prompt({"images": [], "tables": []})
        assert "document assistant" in prompt.lower()
        
        prompt_with_images = engine._build_system_prompt({
            "images": [{"id": 1}], 
            "tables": []
        })
        assert "1 relevant image" in prompt_with_images
        
        prompt_with_tables = engine._build_system_prompt({
            "images": [], 
            "tables": [{"id": 1}, {"id": 2}]
        })
        assert "2 relevant table" in prompt_with_tables
    
    def test_build_context_text_empty(self, db_session):
        """Test context text building with no context."""
        engine = ChatEngine(db_session)
        context_text = engine._build_context_text([])
        
        assert "No relevant context" in context_text
    
    def test_build_context_text_with_chunks(self, db_session):
        """Test context text building with chunks."""
        engine = ChatEngine(db_session)
        chunks = [
            {"content": "First chunk", "page_number": 1, "score": 0.95},
            {"content": "Second chunk", "page_number": 2, "score": 0.85},
        ]
        
        context_text = engine._build_context_text(chunks)
        
        assert "First chunk" in context_text
        assert "Second chunk" in context_text
        assert "Page 1" in context_text
        assert "Page 2" in context_text
    
    def test_format_sources(self, db_session):
        """Test source formatting."""
        engine = ChatEngine(db_session)
        
        context = [
            {"content": "Test content", "page_number": 1, "score": 0.9}
        ]
        media = {
            "images": [{"id": 1, "url": "/test.png", "caption": "Test", "page": 1}],
            "tables": [{"id": 1, "url": "/table.png", "caption": "Table", "page": 2, "data": {}}]
        }
        
        sources = engine._format_sources(context, media)
        
        assert len(sources) == 3
        
        text_sources = [s for s in sources if s["type"] == "text"]
        image_sources = [s for s in sources if s["type"] == "image"]
        table_sources = [s for s in sources if s["type"] == "table"]
        
        assert len(text_sources) == 1
        assert len(image_sources) == 1
        assert len(table_sources) == 1
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, db_session):
        """Test that process_message handles errors gracefully."""
        conversation = Conversation(title="Test", document_id=None)
        db_session.add(conversation)
        db_session.commit()
        
        engine = ChatEngine(db_session)
        
        with patch.object(engine, '_search_context', side_effect=Exception("Test error")):
            result = await engine.process_message(
                conversation.id,
                "Test message",
                None
            )
        
        assert "answer" in result
        assert "sources" in result
        assert "processing_time" in result

