"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, MessageSquare, Trash2, RefreshCw, Clock, Layers, Image, Table } from "lucide-react";

interface Document {
  id: number;
  filename: string;
  upload_date: string;
  status: string;
  total_pages: number;
  text_chunks: number;
  images: number;
  tables: number;
}

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/documents");
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error("Error fetching documents:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (id: number) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    
    try {
      await fetch(`http://localhost:8000/api/documents/${id}`, {
        method: "DELETE",
      });
      fetchDocuments();
    } catch (error) {
      console.error("Error deleting document:", error);
    }
  };

  const retryProcessing = async (id: number) => {
    try {
      await fetch(`http://localhost:8000/api/documents/${id}/process`, {
        method: "POST",
      });
      fetchDocuments();
    } catch (error) {
      console.error("Error retrying processing:", error);
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'processing': return 'status-processing';
      case 'error': return 'status-error';
      default: return 'status-pending';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="animate-fadeIn">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold gradient-text">My Documents</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Upload and manage your PDF documents for AI-powered chat
          </p>
        </div>
        <Link href="/upload" className="btn-primary flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Upload Document
        </Link>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-10 h-10 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-[var(--text-secondary)]">Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
            <FileText className="w-8 h-8 text-[var(--text-muted)]" />
          </div>
          <h3 className="text-lg font-medium mb-2">No documents yet</h3>
          <p className="text-[var(--text-secondary)] mb-6">
            Upload your first PDF document to get started
          </p>
          <Link href="/upload" className="btn-primary inline-flex items-center gap-2">
            Upload Document
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc, idx) => (
            <div 
              key={doc.id} 
              className="card p-5 animate-slideUp"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-[var(--accent-primary)]" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium truncate">{doc.filename}</h3>
                      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                        <Clock className="w-3 h-3" />
                        {formatDate(doc.upload_date)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-3 mt-3">
                    <span className={`status-badge ${getStatusClass(doc.status)}`}>
                      {doc.status}
                    </span>
                    
                    {doc.status === 'completed' && (
                      <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                        <span className="flex items-center gap-1">
                          <Layers className="w-3.5 h-3.5" />
                          {doc.total_pages} pages
                        </span>
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          {doc.text_chunks} chunks
                        </span>
                        <span className="flex items-center gap-1">
                          <Image className="w-3.5 h-3.5" />
                          {doc.images} images
                        </span>
                        <span className="flex items-center gap-1">
                          <Table className="w-3.5 h-3.5" />
                          {doc.tables} tables
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/documents/${doc.id}`}
                    className="btn-secondary px-3 py-2 text-sm"
                  >
                    View
                  </Link>
                  
                  {doc.status === 'completed' && (
                    <Link
                      href={`/chat?document=${doc.id}`}
                      className="btn-primary px-3 py-2 text-sm flex items-center gap-1"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      Chat
                    </Link>
                  )}
                  
                  {(doc.status === 'error' || doc.status === 'pending') && (
                    <button
                      onClick={() => retryProcessing(doc.id)}
                      className="btn-secondary px-3 py-2 text-sm flex items-center gap-1"
                      title="Retry processing"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  )}
                  
                  <button
                    onClick={() => deleteDocument(doc.id)}
                    className="p-2 text-[var(--text-muted)] hover:text-[var(--error)] transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
