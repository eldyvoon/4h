"""
Unit tests for DocumentProcessor service.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.document_processor import DocumentProcessor
from app.models.document import Document


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""
    
    def test_init(self, db_session):
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor(db_session)
        assert processor.db == db_session
        assert processor.vector_store is not None
        assert processor.text_splitter is not None
    
    def test_chunk_text_empty(self, db_session):
        """Test text chunking with empty input."""
        processor = DocumentProcessor(db_session)
        chunks = processor._chunk_text("", 1, {}, {})
        assert chunks == []
    
    def test_chunk_text_whitespace(self, db_session):
        """Test text chunking with whitespace only."""
        processor = DocumentProcessor(db_session)
        chunks = processor._chunk_text("   \n\n  ", 1, {}, {})
        assert chunks == []
    
    def test_chunk_text_basic(self, db_session):
        """Test basic text chunking."""
        processor = DocumentProcessor(db_session)
        text = "This is a test document. " * 100
        chunks = processor._chunk_text(text, 1, {}, {})
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert "content" in chunk
            assert "page_number" in chunk
            assert "chunk_index" in chunk
            assert "metadata" in chunk
    
    def test_chunk_text_with_related_media(self, db_session):
        """Test text chunking with related images and tables."""
        processor = DocumentProcessor(db_session)
        text = "This is page one content. " * 50
        page_images = {1: [101, 102], 2: [103]}
        page_tables = {1: [201]}
        
        chunks = processor._chunk_text(text, 1, page_images, page_tables)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert "related_images" in chunk["metadata"]
            assert "related_tables" in chunk["metadata"]
    
    @pytest.mark.asyncio
    async def test_update_document_status(self, db_session):
        """Test document status update."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="pending"
        )
        db_session.add(document)
        db_session.commit()
        
        processor = DocumentProcessor(db_session)
        await processor._update_document_status(document.id, "processing")
        
        db_session.refresh(document)
        assert document.processing_status == "processing"
    
    @pytest.mark.asyncio
    async def test_update_document_status_with_error(self, db_session):
        """Test document status update with error message."""
        document = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            processing_status="processing"
        )
        db_session.add(document)
        db_session.commit()
        
        processor = DocumentProcessor(db_session)
        await processor._update_document_status(
            document.id, 
            "error", 
            "Test error message"
        )
        
        db_session.refresh(document)
        assert document.processing_status == "error"
        assert document.error_message == "Test error message"
    
    def test_render_table_as_image_empty(self, db_session):
        """Test table rendering with empty data."""
        processor = DocumentProcessor(db_session)
        img = processor._render_table_as_image(None, "Test Table")
        
        assert img is not None
        assert img.width > 0
        assert img.height > 0
    
    def test_render_table_as_image_dict_data(self, db_session):
        """Test table rendering with dictionary data."""
        processor = DocumentProcessor(db_session)
        table_data = [
            {"Name": "Alice", "Age": "25", "City": "NYC"},
            {"Name": "Bob", "Age": "30", "City": "LA"},
        ]
        img = processor._render_table_as_image(table_data, "People Table")
        
        assert img is not None
        assert img.width > 0
        assert img.height > 0
    
    def test_render_table_as_image_list_data(self, db_session):
        """Test table rendering with list data."""
        processor = DocumentProcessor(db_session)
        table_data = [
            ["Name", "Age", "City"],
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
        ]
        img = processor._render_table_as_image(table_data, "People Table")
        
        assert img is not None
        assert img.width > 0
        assert img.height > 0

