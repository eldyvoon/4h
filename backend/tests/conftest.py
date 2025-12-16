"""
Pytest configuration and fixtures for testing.
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before importing app modules."""
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    from app.db.session import Base
    
    Base.metadata.create_all(bind=db_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture(scope="function")
def client(db_session, db_engine):
    """Create a test client with overridden database dependency."""
    from fastapi.testclient import TestClient
    from app.db.session import get_db, Base
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    with patch('app.main.engine', db_engine):
        with patch.object(Base.metadata, 'create_all'):
            from app.main import app
            app.dependency_overrides[get_db] = override_get_db
            with TestClient(app) as test_client:
                yield test_client
            app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_content():
    """Generate minimal PDF content for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
    return pdf_content


@pytest.fixture
def temp_upload_dir():
    """Create a temporary upload directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "documents"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "images"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "tables"), exist_ok=True)
        yield tmpdir


@pytest.fixture
def mock_openai_embedding(mocker):
    """Mock OpenAI embedding response."""
    mock_response = mocker.MagicMock()
    mock_response.data = [mocker.MagicMock(embedding=[0.1] * 1536)]
    
    mock_client = mocker.MagicMock()
    mock_client.embeddings.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_openai_chat(mocker):
    """Mock OpenAI chat completion response."""
    mock_message = mocker.MagicMock()
    mock_message.content = "This is a test response from the AI."
    
    mock_choice = mocker.MagicMock()
    mock_choice.message = mock_message
    
    mock_response = mocker.MagicMock()
    mock_response.choices = [mock_choice]
    
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client
