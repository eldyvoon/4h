"""
Document management API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db, SessionLocal
from app.models.document import Document
from app.services.document_processor import DocumentProcessor
from app.core.config import settings
import os
import uuid
from datetime import datetime
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_document_task(document_id: int, file_path: str):
    """Background task to process document."""
    db = SessionLocal()
    try:
        processor = DocumentProcessor(db)
        result = await processor.process_document(file_path, document_id)
        logger.info(f"Document {document_id} processing result: {result}")
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = "error"
            document.error_message = str(e)
            db.commit()
    finally:
        db.close()


def run_async_task(coro):
    """Run async task in background."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for processing
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_FILE_SIZE / 1024 / 1024}MB limit")
    
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, "documents", unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    document = Document(
        filename=file.filename,
        file_path=file_path,
        processing_status="pending"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    if background_tasks:
        import threading
        thread = threading.Thread(
            target=run_async_task,
            args=(process_document_task(document.id, file_path),)
        )
        thread.start()
    
    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.processing_status,
        "message": "Document uploaded successfully. Processing will begin shortly."
    }


@router.post("/{document_id}/process")
async def trigger_processing(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger document processing (useful for retries)
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.processing_status == "processing":
        raise HTTPException(status_code=400, detail="Document is already being processed")
    
    document.processing_status = "pending"
    document.error_message = None
    db.commit()
    
    import threading
    thread = threading.Thread(
        target=run_async_task,
        args=(process_document_task(document.id, document.file_path),)
    )
    thread.start()
    
    return {
        "id": document.id,
        "filename": document.filename,
        "status": "pending",
        "message": "Document processing has been triggered."
    }


@router.get("")
async def list_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get list of all documents
    """
    documents = db.query(Document).order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "upload_date": doc.upload_date,
                "status": doc.processing_status,
                "total_pages": doc.total_pages,
                "text_chunks": doc.text_chunks_count,
                "images": doc.images_count,
                "tables": doc.tables_count
            }
            for doc in documents
        ],
        "total": db.query(Document).count()
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document details including extracted images and tables
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "filename": document.filename,
        "upload_date": document.upload_date,
        "status": document.processing_status,
        "error_message": document.error_message,
        "total_pages": document.total_pages,
        "text_chunks": document.text_chunks_count,
        "images": [
            {
                "id": img.id,
                "url": f"/uploads/images/{os.path.basename(img.file_path)}",
                "page": img.page_number,
                "caption": img.caption,
                "width": img.width,
                "height": img.height
            }
            for img in document.images
        ],
        "tables": [
            {
                "id": tbl.id,
                "url": f"/uploads/tables/{os.path.basename(tbl.image_path)}",
                "page": tbl.page_number,
                "caption": tbl.caption,
                "rows": tbl.rows,
                "columns": tbl.columns,
                "data": tbl.data
            }
            for tbl in document.tables
        ]
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all associated data
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    for img in document.images:
        if os.path.exists(img.file_path):
            os.remove(img.file_path)
    
    for tbl in document.tables:
        if os.path.exists(tbl.image_path):
            os.remove(tbl.image_path)
    
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}
