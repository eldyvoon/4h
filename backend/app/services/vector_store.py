"""
Vector store service using pgvector.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import DocumentChunk, DocumentImage, DocumentTable
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store for document embeddings and similarity search using pgvector.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._client = None
        self._ensure_extension()
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            import httpx
            http_client = httpx.Client()
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=http_client
            )
        return self._client
    
    def _ensure_extension(self):
        """Ensure pgvector extension is enabled."""
        try:
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.db.commit()
        except Exception as e:
            logger.warning(f"pgvector extension setup: {e}")
            self.db.rollback()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI.
        """
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIMENSION
        
        try:
            text = text[:8000]
            
            response = self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def store_chunk(
        self, 
        content: str, 
        document_id: int,
        page_number: int,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentChunk:
        """
        Store a text chunk with its embedding.
        """
        embedding = await self.generate_embedding(content)
        
        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            embedding=embedding,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_metadata=metadata or {}
        )
        
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        
        return chunk
    
    async def similarity_search(
        self,
        query: str,
        document_id: Optional[int] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        """
        query_embedding = await self.generate_embedding(query)
        
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        if document_id:
            sql = text("""
                SELECT 
                    id,
                    document_id,
                    content,
                    page_number,
                    chunk_index,
                    metadata,
                    1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM document_chunks
                WHERE document_id = :document_id
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :k
            """)
            result = self.db.execute(
                sql,
                {
                    "query_embedding": embedding_str,
                    "document_id": document_id,
                    "k": k
                }
            )
        else:
            sql = text("""
                SELECT 
                    id,
                    document_id,
                    content,
                    page_number,
                    chunk_index,
                    metadata,
                    1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM document_chunks
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :k
            """)
            result = self.db.execute(
                sql,
                {
                    "query_embedding": embedding_str,
                    "k": k
                }
            )
        
        rows = result.fetchall()
        
        chunks = []
        for row in rows:
            chunk_data = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "page_number": row.page_number,
                "chunk_index": row.chunk_index,
                "metadata": row.metadata if row.metadata else {},
                "score": float(row.similarity) if row.similarity else 0.0
            }
            chunks.append(chunk_data)
        
        for chunk in chunks:
            related = await self.get_related_content([chunk["id"]])
            chunk["related_images"] = related.get("images", [])
            chunk["related_tables"] = related.get("tables", [])
        
        return chunks
    
    async def get_related_content(
        self,
        chunk_ids: List[int]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get related images and tables for given chunks.
        """
        images = []
        tables = []
        
        if not chunk_ids:
            return {"images": images, "tables": tables}
        
        chunks = self.db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(chunk_ids)
        ).all()
        
        image_ids = set()
        table_ids = set()
        document_ids = set()
        page_numbers = set()
        
        for chunk in chunks:
            document_ids.add(chunk.document_id)
            if chunk.page_number:
                page_numbers.add(chunk.page_number)
            
            if chunk.chunk_metadata:
                if "related_images" in chunk.chunk_metadata:
                    image_ids.update(chunk.chunk_metadata["related_images"])
                if "related_tables" in chunk.chunk_metadata:
                    table_ids.update(chunk.chunk_metadata["related_tables"])
        
        if image_ids:
            db_images = self.db.query(DocumentImage).filter(
                DocumentImage.id.in_(image_ids)
            ).all()
            
            for img in db_images:
                import os
                images.append({
                    "id": img.id,
                    "url": f"/uploads/images/{os.path.basename(img.file_path)}",
                    "caption": img.caption,
                    "page": img.page_number,
                    "width": img.width,
                    "height": img.height
                })
        
        if not images and document_ids and page_numbers:
            db_images = self.db.query(DocumentImage).filter(
                DocumentImage.document_id.in_(document_ids),
                DocumentImage.page_number.in_(page_numbers)
            ).limit(3).all()
            
            for img in db_images:
                import os
                images.append({
                    "id": img.id,
                    "url": f"/uploads/images/{os.path.basename(img.file_path)}",
                    "caption": img.caption,
                    "page": img.page_number,
                    "width": img.width,
                    "height": img.height
                })
        
        if table_ids:
            db_tables = self.db.query(DocumentTable).filter(
                DocumentTable.id.in_(table_ids)
            ).all()
            
            for tbl in db_tables:
                import os
                tables.append({
                    "id": tbl.id,
                    "url": f"/uploads/tables/{os.path.basename(tbl.image_path)}",
                    "caption": tbl.caption,
                    "page": tbl.page_number,
                    "rows": tbl.rows,
                    "columns": tbl.columns,
                    "data": tbl.data
                })
        
        if not tables and document_ids and page_numbers:
            db_tables = self.db.query(DocumentTable).filter(
                DocumentTable.document_id.in_(document_ids),
                DocumentTable.page_number.in_(page_numbers)
            ).limit(2).all()
            
            for tbl in db_tables:
                import os
                tables.append({
                    "id": tbl.id,
                    "url": f"/uploads/tables/{os.path.basename(tbl.image_path)}",
                    "caption": tbl.caption,
                    "page": tbl.page_number,
                    "rows": tbl.rows,
                    "columns": tbl.columns,
                    "data": tbl.data
                })
        
        return {"images": images, "tables": tables}
    
    async def delete_document_chunks(self, document_id: int) -> int:
        """
        Delete all chunks for a document.
        """
        deleted = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()
        self.db.commit()
        return deleted
