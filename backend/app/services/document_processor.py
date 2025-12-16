"""
Document processing service using Docling
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk, DocumentImage, DocumentTable
from app.services.vector_store import VectorStore
from app.core.config import settings
import os
import time
import uuid
import json
import logging
from PIL import Image
import io

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Process PDF documents and extract multimodal content using Docling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(f"{self.upload_dir}/images", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/tables", exist_ok=True)
    
    async def process_document(self, file_path: str, document_id: int) -> Dict[str, Any]:
        """
        Process a PDF document using Docling.
        """
        start_time = time.time()
        
        try:
            await self._update_document_status(document_id, "processing")
            
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption
            
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True
            pipeline_options.generate_page_images = True
            pipeline_options.generate_picture_images = True
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            result = converter.convert(file_path)
            doc = result.document
            
            total_pages = len(doc.pages) if hasattr(doc, 'pages') else 0
            
            page_images: Dict[int, List[int]] = {}
            page_tables: Dict[int, List[int]] = {}
            
            images_saved = await self._extract_and_save_images(doc, document_id, page_images)
            tables_saved = await self._extract_and_save_tables(doc, document_id, page_tables)
            
            text_content = doc.export_to_markdown()
            chunks = self._chunk_text(text_content, document_id, page_images, page_tables)
            
            chunks_stored = await self._save_text_chunks(chunks, document_id)
            
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "completed"
                document.total_pages = total_pages
                document.text_chunks_count = chunks_stored
                document.images_count = images_saved
                document.tables_count = tables_saved
                self.db.commit()
            
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "text_chunks": chunks_stored,
                "images": images_saved,
                "tables": tables_saved,
                "total_pages": total_pages,
                "processing_time": round(processing_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            await self._update_document_status(document_id, "error", str(e))
            return {
                "status": "error",
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _chunk_text(
        self, 
        text: str, 
        document_id: int,
        page_images: Dict[int, List[int]],
        page_tables: Dict[int, List[int]]
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks for vector storage.
        """
        if not text or not text.strip():
            return []
        
        raw_chunks = self.text_splitter.split_text(text)
        
        chunks = []
        for idx, chunk_content in enumerate(raw_chunks):
            if not chunk_content.strip():
                continue
            
            estimated_page = min(idx // 3 + 1, max(page_images.keys()) if page_images else 1)
            
            related_images = []
            related_tables = []
            
            for page in range(max(1, estimated_page - 1), estimated_page + 2):
                if page in page_images:
                    related_images.extend(page_images[page])
                if page in page_tables:
                    related_tables.extend(page_tables[page])
            
            chunks.append({
                "content": chunk_content,
                "page_number": estimated_page,
                "chunk_index": idx,
                "metadata": {
                    "related_images": related_images[:3],
                    "related_tables": related_tables[:2],
                    "char_count": len(chunk_content)
                }
            })
        
        return chunks
    
    async def _save_text_chunks(self, chunks: List[Dict[str, Any]], document_id: int) -> int:
        """
        Save text chunks to database with embeddings.
        """
        stored_count = 0
        
        for chunk in chunks:
            try:
                await self.vector_store.store_chunk(
                    content=chunk["content"],
                    document_id=document_id,
                    page_number=chunk["page_number"],
                    chunk_index=chunk["chunk_index"],
                    metadata=chunk["metadata"]
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing chunk {chunk['chunk_index']}: {str(e)}")
                continue
        
        return stored_count
    
    async def _extract_and_save_images(
        self,
        doc: Any,
        document_id: int,
        page_images: Dict[int, List[int]]
    ) -> int:
        """
        Extract and save images from document.
        """
        images_saved = 0
        
        try:
            if hasattr(doc, 'pictures') and doc.pictures:
                for idx, picture in enumerate(doc.pictures):
                    try:
                        page_num = getattr(picture, 'page_no', idx + 1) or (idx + 1)
                        
                        image_data = None
                        if hasattr(picture, 'image') and picture.image:
                            if hasattr(picture.image, 'pil_image'):
                                pil_img = picture.image.pil_image
                                img_buffer = io.BytesIO()
                                pil_img.save(img_buffer, format='PNG')
                                image_data = img_buffer.getvalue()
                            elif isinstance(picture.image, bytes):
                                image_data = picture.image
                        
                        if image_data:
                            caption = getattr(picture, 'caption', None) or f"Image {idx + 1} from page {page_num}"
                            
                            doc_image = await self._save_image(
                                image_data=image_data,
                                document_id=document_id,
                                page_number=page_num,
                                metadata={
                                    "caption": caption,
                                    "index": idx
                                }
                            )
                            
                            if doc_image:
                                if page_num not in page_images:
                                    page_images[page_num] = []
                                page_images[page_num].append(doc_image.id)
                                images_saved += 1
                    except Exception as e:
                        logger.warning(f"Error extracting image {idx}: {str(e)}")
                        continue
            
            if hasattr(doc, 'pages'):
                for page_idx, page in enumerate(doc.pages):
                    page_num = page_idx + 1
                    if hasattr(page, 'image') and page.image:
                        try:
                            if hasattr(page.image, 'pil_image'):
                                pil_img = page.image.pil_image
                                img_buffer = io.BytesIO()
                                pil_img.save(img_buffer, format='PNG')
                                image_data = img_buffer.getvalue()
                                
                                doc_image = await self._save_image(
                                    image_data=image_data,
                                    document_id=document_id,
                                    page_number=page_num,
                                    metadata={
                                        "caption": f"Page {page_num}",
                                        "is_page_image": True
                                    }
                                )
                                
                                if doc_image and page_num not in page_images:
                                    page_images[page_num] = []
                                    page_images[page_num].append(doc_image.id)
                                    images_saved += 1
                        except Exception as e:
                            logger.warning(f"Error saving page image {page_num}: {str(e)}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error in image extraction: {str(e)}")
        
        return images_saved
    
    async def _extract_and_save_tables(
        self,
        doc: Any,
        document_id: int,
        page_tables: Dict[int, List[int]]
    ) -> int:
        """
        Extract and save tables from document.
        """
        tables_saved = 0
        
        try:
            if hasattr(doc, 'tables') and doc.tables:
                for idx, table in enumerate(doc.tables):
                    try:
                        page_num = getattr(table, 'page_no', idx + 1) or (idx + 1)
                        
                        table_data = None
                        if hasattr(table, 'export_to_dataframe'):
                            df = table.export_to_dataframe()
                            table_data = df.to_dict('records')
                        elif hasattr(table, 'data'):
                            table_data = table.data
                        
                        caption = getattr(table, 'caption', None) or f"Table {idx + 1} from page {page_num}"
                        
                        doc_table = await self._save_table(
                            table_data=table_data,
                            document_id=document_id,
                            page_number=page_num,
                            metadata={
                                "caption": caption,
                                "index": idx
                            }
                        )
                        
                        if doc_table:
                            if page_num not in page_tables:
                                page_tables[page_num] = []
                            page_tables[page_num].append(doc_table.id)
                            tables_saved += 1
                            
                    except Exception as e:
                        logger.warning(f"Error extracting table {idx}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in table extraction: {str(e)}")
        
        return tables_saved
    
    async def _save_image(
        self, 
        image_data: bytes, 
        document_id: int, 
        page_number: int,
        metadata: Dict[str, Any]
    ) -> Optional[DocumentImage]:
        """
        Save an extracted image to filesystem and database.
        """
        try:
            image_id = str(uuid.uuid4())
            filename = f"{document_id}_{image_id}.png"
            file_path = os.path.join(self.upload_dir, "images", filename)
            
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(file_path, 'PNG', optimize=True)
            
            caption = metadata.get("caption", f"Image from page {page_number}")
            
            doc_image = DocumentImage(
                document_id=document_id,
                file_path=file_path,
                page_number=page_number,
                caption=caption,
                width=width,
                height=height,
                image_metadata=metadata
            )
            
            self.db.add(doc_image)
            self.db.commit()
            self.db.refresh(doc_image)
            
            return doc_image
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            self.db.rollback()
            return None
    
    async def _save_table(
        self,
        table_data: Any,
        document_id: int,
        page_number: int,
        metadata: Dict[str, Any]
    ) -> Optional[DocumentTable]:
        """
        Save an extracted table as image and structured data.
        """
        try:
            table_id = str(uuid.uuid4())
            filename = f"{document_id}_{table_id}.png"
            file_path = os.path.join(self.upload_dir, "tables", filename)
            
            table_image = self._render_table_as_image(table_data, metadata.get("caption", "Table"))
            table_image.save(file_path, 'PNG')
            
            rows = 0
            columns = 0
            if isinstance(table_data, list) and len(table_data) > 0:
                rows = len(table_data)
                if isinstance(table_data[0], dict):
                    columns = len(table_data[0])
            
            caption = metadata.get("caption", f"Table from page {page_number}")
            
            doc_table = DocumentTable(
                document_id=document_id,
                image_path=file_path,
                data=table_data,
                page_number=page_number,
                caption=caption,
                rows=rows,
                columns=columns,
                table_metadata=metadata
            )
            
            self.db.add(doc_table)
            self.db.commit()
            self.db.refresh(doc_table)
            
            return doc_table
            
        except Exception as e:
            logger.error(f"Error saving table: {str(e)}")
            self.db.rollback()
            return None
    
    def _render_table_as_image(self, table_data: Any, title: str = "Table") -> Image.Image:
        """
        Render table data as an image using PIL.
        """
        from PIL import ImageDraw, ImageFont
        
        cell_padding = 10
        cell_height = 30
        min_cell_width = 80
        max_cell_width = 200
        
        if not table_data or not isinstance(table_data, list):
            img = Image.new('RGB', (300, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), "Empty table", fill='black')
            return img
        
        if isinstance(table_data[0], dict):
            headers = list(table_data[0].keys())
            rows_data = [[str(row.get(h, '')) for h in headers] for row in table_data]
        else:
            headers = [f"Col {i+1}" for i in range(len(table_data[0]) if table_data else 0)]
            rows_data = [[str(cell) for cell in row] for row in table_data]
        
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows_data:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(min(max(min_cell_width, max_width * 8 + cell_padding * 2), max_cell_width))
        
        table_width = sum(col_widths) + 2
        table_height = (len(rows_data) + 1) * cell_height + cell_height + 2
        
        img = Image.new('RGB', (table_width, table_height), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            bold_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
        except:
            font = ImageFont.load_default()
            bold_font = font
        
        draw.text((10, 5), title[:50], fill='black', font=bold_font)
        
        y = cell_height
        draw.rectangle([0, y, table_width, y + cell_height], fill='#e0e0e0')
        
        x = 1
        for i, header in enumerate(headers):
            draw.text((x + cell_padding, y + 8), header[:15], fill='black', font=bold_font)
            x += col_widths[i]
            draw.line([(x, y), (x, table_height)], fill='gray')
        
        for row_idx, row in enumerate(rows_data):
            y = (row_idx + 2) * cell_height
            
            if row_idx % 2 == 1:
                draw.rectangle([0, y, table_width, y + cell_height], fill='#f5f5f5')
            
            x = 1
            for col_idx, cell in enumerate(row):
                if col_idx < len(col_widths):
                    text = str(cell)[:20]
                    draw.text((x + cell_padding, y + 8), text, fill='black', font=font)
                    x += col_widths[col_idx]
            
            draw.line([(0, y), (table_width, y)], fill='lightgray')
        
        draw.rectangle([0, 0, table_width - 1, table_height - 1], outline='gray')
        
        return img
    
    async def _update_document_status(
        self, 
        document_id: int, 
        status: str, 
        error_message: str = None
    ):
        """
        Update document processing status.
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = status
            if error_message:
                document.error_message = error_message
            self.db.commit()
