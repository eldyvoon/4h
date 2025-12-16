"""
Unit tests for VectorStore service.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.vector_store import VectorStore
from app.models.document import Document, DocumentChunk, DocumentImage, DocumentTable


class TestVectorStore:
    """Tests for VectorStore class."""
    
    def test_init(self, db_session):
        """Test VectorStore initialization."""
        store = VectorStore(db_session)
        assert store.db == db_session
        assert store._client is None
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty(self, db_session):
        """Test embedding generation with empty text."""
        store = VectorStore(db_session)
        embedding = await store.generate_embedding("")
        
        assert len(embedding) == 1536
        assert all(v == 0.0 for v in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_whitespace(self, db_session):
        """Test embedding generation with whitespace."""
        store = VectorStore(db_session)
        embedding = await store.generate_embedding("   ")
        
        assert len(embedding) == 1536
        assert all(v == 0.0 for v in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_with_mock(self, db_session, mock_openai_embedding):
        """Test embedding generation with mocked OpenAI."""
        store = VectorStore(db_session)
        store._client = mock_openai_embedding
        
        embedding = await store.generate_embedding("Test text")
        
        assert len(embedding) == 1536
        mock_openai_embedding.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_chunk(self, db_session, mock_openai_embedding):
        """Test storing a text chunk with embedding."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="completed"
        )
        db_session.add(document)
        db_session.commit()
        
        store = VectorStore(db_session)
        store._client = mock_openai_embedding
        
        chunk = await store.store_chunk(
            content="Test content",
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            metadata={"test": "value"}
        )
        
        assert chunk is not None
        assert chunk.content == "Test content"
        assert chunk.document_id == document.id
        assert chunk.page_number == 1
        assert chunk.chunk_index == 0
    
    @pytest.mark.asyncio
    async def test_get_related_content_empty(self, db_session):
        """Test getting related content with no chunks."""
        store = VectorStore(db_session)
        result = await store.get_related_content([])
        
        assert result == {"images": [], "tables": []}
    
    @pytest.mark.asyncio
    async def test_get_related_content_with_images(self, db_session):
        """Test getting related content with images."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="completed"
        )
        db_session.add(document)
        db_session.commit()
        
        image = DocumentImage(
            document_id=document.id,
            file_path="/tmp/images/test.png",
            page_number=1,
            caption="Test image",
            width=100,
            height=100
        )
        db_session.add(image)
        db_session.commit()
        
        chunk = DocumentChunk(
            document_id=document.id,
            content="Test content",
            page_number=1,
            chunk_index=0,
            chunk_metadata={"related_images": [image.id]}
        )
        db_session.add(chunk)
        db_session.commit()
        
        store = VectorStore(db_session)
        result = await store.get_related_content([chunk.id])
        
        assert len(result["images"]) == 1
        assert result["images"][0]["id"] == image.id
    
    @pytest.mark.asyncio
    async def test_delete_document_chunks(self, db_session, mock_openai_embedding):
        """Test deleting all chunks for a document."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="completed"
        )
        db_session.add(document)
        db_session.commit()
        
        store = VectorStore(db_session)
        store._client = mock_openai_embedding
        
        await store.store_chunk("Chunk 1", document.id, 1, 0)
        await store.store_chunk("Chunk 2", document.id, 1, 1)
        await store.store_chunk("Chunk 3", document.id, 2, 0)
        
        chunks_before = db_session.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).count()
        assert chunks_before == 3
        
        deleted = await store.delete_document_chunks(document.id)
        assert deleted == 3
        
        chunks_after = db_session.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).count()
        assert chunks_after == 0

