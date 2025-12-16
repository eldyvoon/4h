# Multimodal Document Chat System

A full-stack application that enables users to upload PDF documents, extract text, images, and tables using Docling, and engage in AI-powered multimodal chat based on the extracted content.

## Features

### Core Features (Implemented)

- **Document Processing Pipeline**

  - PDF parsing using Docling library
  - Text extraction with intelligent chunking
  - Image extraction and storage
  - Table extraction and rendering as images
  - Background processing with status tracking

- **Vector Store Integration**

  - OpenAI text-embedding-3-small for embeddings
  - PostgreSQL + pgvector for vector storage
  - Cosine similarity search
  - Metadata linking chunks to related images/tables

- **Multimodal Chat Engine**
  - RAG (Retrieval-Augmented Generation) implementation
  - Multi-turn conversation support
  - Context-aware responses
  - Automatic inclusion of relevant images/tables
  - OpenAI GPT-4o-mini for response generation

### Frontend Features

- Modern dark theme UI with gradient accents
- Drag-and-drop document upload with progress indicator
- Real-time processing status updates
- Interactive chat interface with source citations
- Image/table gallery with lightbox view
- Responsive design for all screen sizes

## Tech Stack

### Backend

- **Framework**: FastAPI (Python 3.11+)
- **PDF Processing**: Docling
- **Vector Database**: PostgreSQL 15 + pgvector
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: OpenAI GPT-4o-mini
- **Cache**: Redis

### Frontend

- **Framework**: Next.js 14 (App Router)
- **Styling**: TailwindCSS
- **Icons**: Lucide React
- **Language**: TypeScript

### Infrastructure

- **Containerization**: Docker + Docker Compose
- **Database**: PostgreSQL with pgvector extension
- **File Storage**: Local filesystem

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key

### Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd 4h

# 2. Create environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Environment Variables

| Variable                 | Description                    | Default                                             |
| ------------------------ | ------------------------------ | --------------------------------------------------- |
| `DATABASE_URL`           | PostgreSQL connection string   | `postgresql://docuser:docpass@localhost:5432/docdb` |
| `REDIS_URL`              | Redis connection string        | `redis://localhost:6379/0`                          |
| `OPENAI_API_KEY`         | OpenAI API key                 | Required                                            |
| `OPENAI_MODEL`           | Chat model to use              | `gpt-4o-mini`                                       |
| `OPENAI_EMBEDDING_MODEL` | Embedding model                | `text-embedding-3-small`                            |
| `UPLOAD_DIR`             | Directory for uploaded files   | `./uploads`                                         |
| `MAX_FILE_SIZE`          | Maximum upload size in bytes   | `52428800` (50MB)                                   |
| `CHUNK_SIZE`             | Text chunk size for embeddings | `1000`                                              |
| `CHUNK_OVERLAP`          | Overlap between chunks         | `200`                                               |
| `TOP_K_RESULTS`          | Number of search results       | `5`                                                 |

## API Endpoints

### Documents

| Method   | Endpoint                      | Description           |
| -------- | ----------------------------- | --------------------- |
| `POST`   | `/api/documents/upload`       | Upload a PDF document |
| `GET`    | `/api/documents`              | List all documents    |
| `GET`    | `/api/documents/{id}`         | Get document details  |
| `POST`   | `/api/documents/{id}/process` | Retry processing      |
| `DELETE` | `/api/documents/{id}`         | Delete a document     |

### Chat

| Method   | Endpoint                       | Description              |
| -------- | ------------------------------ | ------------------------ |
| `POST`   | `/api/chat`                    | Send a chat message      |
| `GET`    | `/api/chat/conversations`      | List conversations       |
| `GET`    | `/api/chat/conversations/{id}` | Get conversation history |
| `DELETE` | `/api/chat/conversations/{id}` | Delete conversation      |

## API Examples

### Upload Document

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@document.pdf"
```

### Send Chat Message

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this document about?",
    "document_id": 1
  }'
```

### List Documents

```bash
curl "http://localhost:8000/api/documents"
```

## Project Structure

```
4h/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   └── documents.py    # Document endpoints
│   │   ├── core/
│   │   │   └── config.py       # Configuration
│   │   ├── db/
│   │   │   └── session.py      # Database session
│   │   ├── models/
│   │   │   ├── conversation.py # Chat models
│   │   │   └── document.py     # Document models
│   │   ├── services/
│   │   │   ├── chat_engine.py      # RAG chat engine
│   │   │   ├── document_processor.py # PDF processing
│   │   │   └── vector_store.py     # Vector operations
│   │   └── main.py             # FastAPI app
│   ├── tests/                  # Unit & integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── chat/
│   │   │   └── page.tsx        # Chat interface
│   │   ├── documents/
│   │   │   └── [id]/page.tsx   # Document details
│   │   ├── upload/
│   │   │   └── page.tsx        # Upload page
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # App layout
│   │   └── page.tsx            # Home page
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Running Tests

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_chat_engine.py -v
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Features Implemented

- [x] Document upload and processing
- [x] PDF text extraction with Docling
- [x] Image extraction and storage
- [x] Table extraction and rendering
- [x] Vector embeddings with OpenAI
- [x] Similarity search with pgvector
- [x] RAG-based chat engine
- [x] Multi-turn conversation support
- [x] Multimodal responses (text + images + tables)
- [x] Modern dark theme UI
- [x] Upload progress indicator
- [x] Document processing status polling
- [x] Source citations in chat
- [x] Unit tests for services
- [x] Integration tests for API

## Known Limitations

1. **Docling Compatibility**: Some complex PDF layouts may not extract perfectly
2. **Large Documents**: Very large PDFs may take significant time to process
3. **Image Quality**: Extracted images depend on source PDF quality
4. **Table Detection**: Complex nested tables may not be detected accurately
5. **Memory Usage**: Large documents may require significant memory during processing

## Future Improvements

- [ ] WebSocket-based real-time chat
- [ ] Multi-document search across all uploaded documents
- [ ] OCR support for scanned PDFs
- [ ] Advanced table structure detection
- [ ] Export conversation history
- [ ] User authentication and authorization
- [ ] Rate limiting for API endpoints
- [ ] Caching layer for frequent queries
- [ ] Production deployment configuration

## Troubleshooting

### Document Processing Issues

**Problem**: Document stuck in "processing" status
**Solution**:

- Check backend logs: `docker-compose logs -f backend`
- Retry processing via API: `POST /api/documents/{id}/process`
- Verify Docling can handle the PDF format

### Chat Not Responding

**Problem**: Chat returns errors
**Solution**:

- Verify OPENAI_API_KEY is set correctly
- Check document is in "completed" status
- Review backend logs for errors

### Database Connection Issues

**Problem**: Cannot connect to PostgreSQL
**Solution**:

- Ensure Docker containers are running: `docker-compose ps`
- Check database logs: `docker-compose logs postgres`
- Verify DATABASE_URL in environment
