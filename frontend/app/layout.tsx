"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Upload, MessageSquare, Sparkles } from "lucide-react";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Documents", icon: FileText },
    { href: "/upload", label: "Upload", icon: Upload },
    { href: "/chat", label: "Chat", icon: MessageSquare },
  ];

  return (
    <html lang="en">
      <head>
        <title>DocChat - Multimodal Document Chat</title>
        <meta name="description" content="Chat with your documents using AI" />
      </head>
      <body>
        <div className="min-h-screen flex flex-col">
          <nav className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center gap-8">
                  <Link href="/" className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-lg gradient-text">DocChat</span>
                  </Link>
                  
                  <div className="hidden sm:flex items-center gap-1">
                    {navLinks.map((link) => {
                      const Icon = link.icon;
                      const isActive = pathname === link.href || 
                        (link.href === "/chat" && pathname?.startsWith("/chat"));
                      
                      return (
                        <Link
                          key={link.href}
                          href={link.href}
                          className={`nav-link flex items-center gap-2 ${isActive ? 'active' : ''}`}
                        >
                          <Icon className="w-4 h-4" />
                          {link.label}
                        </Link>
                      );
                    })}
                  </div>
                </div>

                <div className="flex items-center">
                  <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
                  >
                    API Docs
                  </a>
                </div>
              </div>
            </div>
          </nav>

          <main className="flex-1">
            <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </main>

          <footer className="border-t border-[var(--border-color)] py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <p className="text-center text-sm text-[var(--text-muted)]">
                Multimodal Document Chat System • Powered by AI
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
