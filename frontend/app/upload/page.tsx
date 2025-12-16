"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, X, Loader2, CheckCircle } from "lucide-react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const router = useRouter();

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported');
      return;
    }
    
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }
    
    setFile(selectedFile);
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    const progressInterval = setInterval(() => {
      setUploadProgress(prev => Math.min(prev + 10, 90));
    }, 200);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      
      setTimeout(() => {
        router.push(`/documents/${data.id}`);
      }, 500);
    } catch (err) {
      clearInterval(progressInterval);
      setError(err instanceof Error ? err.message : 'Failed to upload document');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="max-w-2xl mx-auto animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-3xl font-bold gradient-text">Upload Document</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          Upload a PDF document to extract text, images, and tables for AI chat
        </p>
      </div>

      <div className="card p-8">
        <div
          className={`drop-zone p-12 text-center ${isDragging ? 'active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
            id="file-upload"
            disabled={uploading}
          />
          
          <label htmlFor="file-upload" className="cursor-pointer block">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
              <Upload className="w-8 h-8 text-[var(--accent-primary)]" />
            </div>
            <p className="text-[var(--text-primary)] font-medium mb-1">
              Drop your PDF here or click to browse
            </p>
            <p className="text-sm text-[var(--text-muted)]">
              PDF files up to 50MB
            </p>
          </label>
        </div>

        {file && (
          <div className="mt-6 p-4 bg-[var(--bg-tertiary)] rounded-lg animate-fadeIn">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--accent-primary)]/10 flex items-center justify-center">
                <FileText className="w-5 h-5 text-[var(--accent-primary)]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{file.name}</p>
                <p className="text-sm text-[var(--text-muted)]">
                  {formatFileSize(file.size)}
                </p>
              </div>
              {!uploading && (
                <button
                  onClick={removeFile}
                  className="p-2 text-[var(--text-muted)] hover:text-[var(--error)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              {uploading && uploadProgress === 100 && (
                <CheckCircle className="w-5 h-5 text-[var(--success)]" />
              )}
            </div>

            {uploading && (
              <div className="mt-3">
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  {uploadProgress < 100 ? 'Uploading...' : 'Processing...'}
                </p>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-6 p-4 bg-[var(--error)]/10 border border-[var(--error)]/30 rounded-lg animate-fadeIn">
            <p className="text-sm text-[var(--error)]">{error}</p>
          </div>
        )}

        <div className="mt-6">
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {uploadProgress < 100 ? 'Uploading...' : 'Processing...'}
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload Document
              </>
            )}
          </button>
        </div>

        <div className="mt-6 p-4 bg-[var(--bg-tertiary)] rounded-lg">
          <h3 className="text-sm font-medium mb-2">What happens next?</h3>
          <ul className="text-sm text-[var(--text-secondary)] space-y-1">
            <li>• Your PDF will be parsed to extract text content</li>
            <li>• Images and diagrams will be identified and saved</li>
            <li>• Tables will be extracted and made searchable</li>
            <li>• Content will be indexed for AI-powered chat</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
