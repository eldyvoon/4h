"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Send, Image, Table, FileText, Sparkles, AlertCircle } from "lucide-react";

interface Message {
  id: number;
  role: string;
  content: string;
  sources?: Source[];
  created_at: string;
}

interface Source {
  type: 'text' | 'image' | 'table';
  content?: string;
  url?: string;
  caption?: string;
  page?: number;
  score?: number;
  data?: any;
}

function ChatContent() {
  const searchParams = useSearchParams();
  const documentId = searchParams.get('document');
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [documentName, setDocumentName] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (documentId) {
      fetchDocumentInfo();
    }
  }, [documentId]);

  const fetchDocumentInfo = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/documents/${documentId}`);
      const data = await response.json();
      setDocumentName(data.filename);
    } catch (error) {
      console.error('Error fetching document:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput('');
    setLoading(true);

    const tempUserMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: conversationId,
          document_id: documentId ? parseInt(documentId) : null
        }),
      });

      const data = await response.json();
      
      if (!conversationId) {
        setConversationId(data.conversation_id);
      }

      const assistantMessage: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        created_at: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderSource = (source: Source, idx: number) => {
    if (source.type === 'image') {
      return (
        <div key={idx} className="source-card">
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-2">
            <Image className="w-3 h-3" />
            <span>{source.caption || 'Image'}</span>
            {source.page && <span>• Page {source.page}</span>}
          </div>
          <img
            src={`http://localhost:8000${source.url}`}
            alt={source.caption || 'Document image'}
            className="w-full"
          />
        </div>
      );
    }
    
    if (source.type === 'table') {
      return (
        <div key={idx} className="source-card">
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-2">
            <Table className="w-3 h-3" />
            <span>{source.caption || 'Table'}</span>
            {source.page && <span>• Page {source.page}</span>}
          </div>
          <img
            src={`http://localhost:8000${source.url}`}
            alt={source.caption || 'Document table'}
            className="w-full"
          />
        </div>
      );
    }
    
    if (source.type === 'text') {
      return (
        <div key={idx} className="source-card">
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-2">
            <FileText className="w-3 h-3" />
            <span>Source</span>
            {source.page && <span>• Page {source.page}</span>}
            {source.score && <span>• {(source.score * 100).toFixed(0)}% match</span>}
          </div>
          <p className="text-sm text-[var(--text-secondary)] line-clamp-3">
            {source.content}
          </p>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex flex-col animate-fadeIn">
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1">
          <h1 className="text-2xl font-bold gradient-text">Chat</h1>
          {documentName && (
            <p className="text-sm text-[var(--text-secondary)] mt-1 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Chatting with: {documentName}
            </p>
          )}
          {!documentId && (
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Select a document from the home page to start chatting
            </p>
          )}
        </div>
      </div>

      <div className="card flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-medium mb-2">Start a Conversation</h3>
              <p className="text-[var(--text-secondary)] max-w-md">
                Ask questions about the document content. I can help you find information, 
                explain diagrams, and analyze tables.
              </p>
              {!documentId && (
                <div className="mt-4 p-3 bg-[var(--warning)]/10 border border-[var(--warning)]/30 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-[var(--warning)]" />
                  <span className="text-sm text-[var(--warning)]">
                    No document selected. Please select a document first.
                  </span>
                </div>
              )}
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  "What is this document about?",
                  "Show me the main figures",
                  "Summarize the key findings",
                  "What tables are in this document?"
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion)}
                    className="px-3 py-1.5 text-sm bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-full hover:border-[var(--accent-primary)] transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slideUp`}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className={`chat-message ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'} p-4`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {msg.sources.map((source, sidx) => renderSource(source, sidx))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          
          {loading && (
            <div className="flex justify-start">
              <div className="chat-assistant p-4">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-[var(--border-color)]">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={documentId ? "Ask a question about the document..." : "Select a document to start chatting..."}
              className="input-field resize-none"
              rows={1}
              disabled={loading || !documentId}
              style={{ minHeight: '44px', maxHeight: '120px' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = Math.min(target.scrollHeight, 120) + 'px';
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading || !documentId}
              className="btn-primary px-4"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-[calc(100vh-12rem)]">
        <div className="w-10 h-10 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
