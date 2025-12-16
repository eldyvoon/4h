"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  FileText, MessageSquare, ArrowLeft, RefreshCw, 
  Layers, Image, Table, Clock, AlertCircle, CheckCircle
} from "lucide-react";

interface DocumentDetail {
  id: number;
  filename: string;
  upload_date: string;
  status: string;
  error_message?: string;
  total_pages: number;
  text_chunks: number;
  images: Array<{
    id: number;
    url: string;
    page: number;
    caption?: string;
    width: number;
    height: number;
  }>;
  tables: Array<{
    id: number;
    url: string;
    page: number;
    caption?: string;
    rows: number;
    columns: number;
    data?: any;
  }>;
}

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'images' | 'tables'>('images');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    fetchDocument();
    
    const interval = setInterval(() => {
      if (document?.status === 'processing' || document?.status === 'pending') {
        fetchDocument();
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [params.id]);

  useEffect(() => {
    if (document?.status === 'processing' || document?.status === 'pending') {
      const interval = setInterval(fetchDocument, 3000);
      return () => clearInterval(interval);
    }
  }, [document?.status]);

  const fetchDocument = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/documents/${params.id}`);
      const data = await response.json();
      setDocument(data);
    } catch (error) {
      console.error('Error fetching document:', error);
    } finally {
      setLoading(false);
    }
  };

  const retryProcessing = async () => {
    try {
      await fetch(`http://localhost:8000/api/documents/${params.id}/process`, {
        method: "POST",
      });
      fetchDocument();
    } catch (error) {
      console.error("Error retrying processing:", error);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'processing': return 'status-processing';
      case 'error': return 'status-error';
      default: return 'status-pending';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-[var(--success)]" />;
      case 'error': return <AlertCircle className="w-5 h-5 text-[var(--error)]" />;
      default: return <RefreshCw className="w-5 h-5 text-[var(--warning)] animate-spin" />;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-10 h-10 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
        <p className="mt-4 text-[var(--text-secondary)]">Loading document...</p>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="text-center py-20">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-[var(--error)]" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Document not found</h2>
        <p className="text-[var(--text-secondary)] mb-6">
          The document you're looking for doesn't exist or has been deleted.
        </p>
        <Link href="/" className="btn-primary">
          Back to Documents
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.push('/')}
          className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{document.filename}</h1>
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)] mt-1">
            <Clock className="w-3.5 h-3.5" />
            Uploaded {formatDate(document.upload_date)}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {(document.status === 'error' || document.status === 'pending') && (
            <button
              onClick={retryProcessing}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          )}
          {document.status === 'completed' && (
            <Link
              href={`/chat?document=${document.id}`}
              className="btn-primary flex items-center gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              Chat with Document
            </Link>
          )}
        </div>
      </div>

      <div className="card p-6 mb-6">
        <div className="flex items-center gap-4 mb-6">
          {getStatusIcon(document.status)}
          <div>
            <div className="flex items-center gap-3">
              <span className={`status-badge ${getStatusClass(document.status)}`}>
                {document.status}
              </span>
              {document.status === 'processing' && (
                <span className="text-sm text-[var(--text-muted)]">
                  Processing document...
                </span>
              )}
            </div>
          </div>
        </div>

        {document.error_message && (
          <div className="p-4 bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-lg mb-6">
            <p className="text-sm text-[var(--error)]">{document.error_message}</p>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-[var(--bg-tertiary)] rounded-lg">
            <div className="flex items-center gap-2 text-[var(--text-muted)] mb-1">
              <Layers className="w-4 h-4" />
              <span className="text-sm">Pages</span>
            </div>
            <p className="text-2xl font-semibold">{document.total_pages}</p>
          </div>
          <div className="p-4 bg-[var(--bg-tertiary)] rounded-lg">
            <div className="flex items-center gap-2 text-[var(--text-muted)] mb-1">
              <FileText className="w-4 h-4" />
              <span className="text-sm">Text Chunks</span>
            </div>
            <p className="text-2xl font-semibold">{document.text_chunks}</p>
          </div>
          <div className="p-4 bg-[var(--bg-tertiary)] rounded-lg">
            <div className="flex items-center gap-2 text-[var(--text-muted)] mb-1">
              <Image className="w-4 h-4" />
              <span className="text-sm">Images</span>
            </div>
            <p className="text-2xl font-semibold">{document.images.length}</p>
          </div>
          <div className="p-4 bg-[var(--bg-tertiary)] rounded-lg">
            <div className="flex items-center gap-2 text-[var(--text-muted)] mb-1">
              <Table className="w-4 h-4" />
              <span className="text-sm">Tables</span>
            </div>
            <p className="text-2xl font-semibold">{document.tables.length}</p>
          </div>
        </div>
      </div>

      {(document.images.length > 0 || document.tables.length > 0) && (
        <div className="card">
          <div className="flex border-b border-[var(--border-color)]">
            <button
              onClick={() => setActiveTab('images')}
              className={`flex-1 py-4 px-6 text-sm font-medium transition-colors ${
                activeTab === 'images'
                  ? 'text-[var(--accent-primary)] border-b-2 border-[var(--accent-primary)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Image className="w-4 h-4 inline mr-2" />
              Images ({document.images.length})
            </button>
            <button
              onClick={() => setActiveTab('tables')}
              className={`flex-1 py-4 px-6 text-sm font-medium transition-colors ${
                activeTab === 'tables'
                  ? 'text-[var(--accent-primary)] border-b-2 border-[var(--accent-primary)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Table className="w-4 h-4 inline mr-2" />
              Tables ({document.tables.length})
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'images' && (
              <div>
                {document.images.length === 0 ? (
                  <div className="text-center py-12 text-[var(--text-muted)]">
                    <Image className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No images extracted from this document</p>
                  </div>
                ) : (
                  <div className="media-grid">
                    {document.images.map((image) => (
                      <div 
                        key={image.id} 
                        className="media-card cursor-pointer"
                        onClick={() => setSelectedImage(`http://localhost:8000${image.url}`)}
                      >
                        <img
                          src={`http://localhost:8000${image.url}`}
                          alt={image.caption || 'Document image'}
                        />
                        <div className="media-overlay">
                          <div className="text-sm text-white">
                            <p className="font-medium truncate">
                              {image.caption || `Image from page ${image.page}`}
                            </p>
                            <p className="text-xs opacity-70">
                              Page {image.page} • {image.width}×{image.height}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'tables' && (
              <div>
                {document.tables.length === 0 ? (
                  <div className="text-center py-12 text-[var(--text-muted)]">
                    <Table className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No tables extracted from this document</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {document.tables.map((table) => (
                      <div key={table.id} className="bg-[var(--bg-tertiary)] rounded-lg overflow-hidden">
                        <div className="p-4 border-b border-[var(--border-color)]">
                          <h4 className="font-medium">
                            {table.caption || `Table from page ${table.page}`}
                          </h4>
                          <p className="text-sm text-[var(--text-muted)] mt-1">
                            Page {table.page} • {table.rows} rows × {table.columns} columns
                          </p>
                        </div>
                        <div className="p-4">
                          <img
                            src={`http://localhost:8000${table.url}`}
                            alt={table.caption || 'Document table'}
                            className="w-full rounded"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {selectedImage && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-4xl max-h-[90vh] overflow-auto">
            <img
              src={selectedImage}
              alt="Full size image"
              className="w-full h-auto rounded-lg"
            />
          </div>
        </div>
      )}
    </div>
  );
}
