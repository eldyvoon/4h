"""
Chat engine service for multimodal RAG.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentImage, DocumentTable
from app.services.vector_store import VectorStore
from app.core.config import settings
import time
import logging
import os

logger = logging.getLogger(__name__)


class ChatEngine:
    """
    Multimodal chat engine with RAG support.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db)
        self._client = None
    
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
    
    async def process_message(
        self,
        conversation_id: int,
        message: str,
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate multimodal response.
        """
        start_time = time.time()
        
        try:
            history = await self._load_conversation_history(conversation_id)
            
            context = await self._search_context(message, document_id, k=settings.TOP_K_RESULTS)
            
            media = await self._find_related_media(context, document_id, message)
            
            answer = await self._generate_response(message, context, history, media)
            
            sources = self._format_sources(context, media)
            
            processing_time = time.time() - start_time
            
            return {
                "answer": answer,
                "sources": sources,
                "processing_time": round(processing_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "answer": f"I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": [],
                "processing_time": time.time() - start_time
            }
    
    async def _load_conversation_history(
        self,
        conversation_id: int,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Load recent conversation history.
        """
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit * 2).all()
        
        messages = list(reversed(messages))
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return history
    
    async def _search_context(
        self,
        query: str,
        document_id: Optional[int] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant context using vector store.
        """
        try:
            results = await self.vector_store.similarity_search(
                query=query,
                document_id=document_id,
                k=k
            )
            return results
        except Exception as e:
            logger.error(f"Error searching context: {str(e)}")
            return []
    
    async def _find_related_media(
        self,
        context_chunks: List[Dict[str, Any]],
        document_id: Optional[int] = None,
        query: str = ""
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find related images and tables from context chunks.
        """
        images = []
        tables = []
        seen_image_ids = set()
        seen_table_ids = set()
        
        for chunk in context_chunks:
            for img in chunk.get("related_images", []):
                if isinstance(img, dict) and img.get("id") not in seen_image_ids:
                    images.append(img)
                    seen_image_ids.add(img.get("id"))
            
            for tbl in chunk.get("related_tables", []):
                if isinstance(tbl, dict) and tbl.get("id") not in seen_table_ids:
                    tables.append(tbl)
                    seen_table_ids.add(tbl.get("id"))
        
        query_lower = query.lower()
        wants_image = any(word in query_lower for word in [
            'image', 'figure', 'diagram', 'picture', 'show', 'visual',
            'architecture', 'illustration', 'graph', 'chart', 'plot'
        ])
        wants_table = any(word in query_lower for word in [
            'table', 'results', 'data', 'numbers', 'comparison',
            'statistics', 'metrics', 'performance', 'benchmark'
        ])
        
        if document_id and (wants_image or not images):
            db_images = self.db.query(DocumentImage).filter(
                DocumentImage.document_id == document_id
            ).limit(5).all()
            
            for img in db_images:
                if img.id not in seen_image_ids:
                    images.append({
                        "id": img.id,
                        "url": f"/uploads/images/{os.path.basename(img.file_path)}",
                        "caption": img.caption,
                        "page": img.page_number,
                        "width": img.width,
                        "height": img.height
                    })
                    seen_image_ids.add(img.id)
        
        if document_id and (wants_table or not tables):
            db_tables = self.db.query(DocumentTable).filter(
                DocumentTable.document_id == document_id
            ).limit(3).all()
            
            for tbl in db_tables:
                if tbl.id not in seen_table_ids:
                    tables.append({
                        "id": tbl.id,
                        "url": f"/uploads/tables/{os.path.basename(tbl.image_path)}",
                        "caption": tbl.caption,
                        "page": tbl.page_number,
                        "rows": tbl.rows,
                        "columns": tbl.columns,
                        "data": tbl.data
                    })
                    seen_table_ids.add(tbl.id)
        
        if wants_image:
            images = images[:3]
        else:
            images = images[:2]
        
        if wants_table:
            tables = tables[:2]
        else:
            tables = tables[:1]
        
        return {"images": images, "tables": tables}
    
    async def _generate_response(
        self,
        message: str,
        context: List[Dict[str, Any]],
        history: List[Dict[str, str]],
        media: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate response using LLM.
        """
        system_prompt = self._build_system_prompt(media)
        context_text = self._build_context_text(context)
        user_prompt = self._build_user_prompt(message, context_text, media)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for hist_msg in history[-6:]:
            messages.append({
                "role": hist_msg["role"],
                "content": hist_msg["content"][:1000]
            })
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def _build_system_prompt(self, media: Dict[str, List[Dict[str, Any]]]) -> str:
        """Build system prompt for the LLM."""
        prompt = """You are a helpful document assistant that answers questions based on the provided document context. 

Key guidelines:
1. Answer questions accurately based on the document content provided
2. If relevant images or tables are available, mention them in your response (e.g., "As shown in Figure 1..." or "The results in Table 1 indicate...")
3. If you're not sure about something, say so rather than making up information
4. Keep responses concise but informative
5. Use the conversation history to maintain context for follow-up questions
6. Format your responses with clear structure when appropriate (bullet points, numbered lists)"""

        if media.get("images"):
            prompt += f"\n\nNote: {len(media['images'])} relevant image(s) will be displayed with your response."
        
        if media.get("tables"):
            prompt += f"\n\nNote: {len(media['tables'])} relevant table(s) will be displayed with your response."
        
        return prompt
    
    def _build_context_text(self, context: List[Dict[str, Any]]) -> str:
        """Build context text from retrieved chunks."""
        if not context:
            return "No relevant context found in the document."
        
        context_parts = []
        for i, chunk in enumerate(context, 1):
            page = chunk.get("page_number", "?")
            score = chunk.get("score", 0)
            content = chunk.get("content", "")[:500]
            context_parts.append(f"[Source {i}, Page {page}, Relevance: {score:.2f}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _build_user_prompt(
        self, 
        message: str, 
        context_text: str,
        media: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Build user prompt with context and media info."""
        prompt = f"""Based on the following document context, please answer this question: {message}

--- DOCUMENT CONTEXT ---
{context_text}
--- END CONTEXT ---"""

        if media.get("images"):
            image_info = []
            for img in media["images"]:
                caption = img.get("caption", "No caption")
                page = img.get("page", "?")
                image_info.append(f"- {caption} (Page {page})")
            prompt += f"\n\nAvailable images:\n" + "\n".join(image_info)
        
        if media.get("tables"):
            table_info = []
            for tbl in media["tables"]:
                caption = tbl.get("caption", "No caption")
                page = tbl.get("page", "?")
                rows = tbl.get("rows", 0)
                cols = tbl.get("columns", 0)
                table_info.append(f"- {caption} (Page {page}, {rows}x{cols})")
            prompt += f"\n\nAvailable tables:\n" + "\n".join(table_info)
        
        prompt += "\n\nPlease provide a helpful answer, referencing the images and tables when relevant."
        
        return prompt
    
    def _format_sources(
        self,
        context: List[Dict[str, Any]],
        media: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Format sources for response."""
        sources = []
        
        for chunk in context[:3]:
            sources.append({
                "type": "text",
                "content": chunk.get("content", "")[:300] + "...",
                "page": chunk.get("page_number"),
                "score": round(chunk.get("score", 0), 2)
            })
        
        for image in media.get("images", []):
            sources.append({
                "type": "image",
                "url": image.get("url"),
                "caption": image.get("caption"),
                "page": image.get("page")
            })
        
        for table in media.get("tables", []):
            sources.append({
                "type": "table",
                "url": table.get("url"),
                "caption": table.get("caption"),
                "page": table.get("page"),
                "data": table.get("data")
            })
        
        return sources
