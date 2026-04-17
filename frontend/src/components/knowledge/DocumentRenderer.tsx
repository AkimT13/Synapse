"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

import { corpora } from "@/lib/api";

// Render a knowledge document based on its file extension.
//   - .md / .markdown -> react-markdown with GFM + highlight.js
//   - .txt / plain -> monospace <pre>
//   - .pdf / .docx / .html -> preview-not-supported placeholder
interface DocumentRendererProps {
  path: string;
  content: string;
}

function extensionOf(path: string): string {
  const idx = path.lastIndexOf(".");
  if (idx < 0) return "";
  return path.slice(idx + 1).toLowerCase();
}

export function DocumentRenderer({ path, content }: DocumentRendererProps) {
  const ext = extensionOf(path);

  if (ext === "md" || ext === "markdown") {
    return (
      <div className="max-w-[760px] text-[15px] leading-relaxed text-white/85">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            h1: ({ children }) => (
              <h1 className="font-serif text-4xl mt-8 mb-4 text-white tracking-tight">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="font-serif text-3xl mt-8 mb-4 text-white tracking-tight">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="font-serif text-2xl mt-6 mb-3 text-white tracking-tight">
                {children}
              </h3>
            ),
            h4: ({ children }) => (
              <h4 className="mt-5 mb-2 text-[13px] uppercase tracking-[0.2em] text-white/50">
                {children}
              </h4>
            ),
            p: ({ children }) => (
              <p className="my-4 text-white/80 leading-relaxed">{children}</p>
            ),
            code: ({ className, children }) =>
              className ? (
                <code className={className}>{children}</code>
              ) : (
                <code className="font-mono text-sm bg-white/5 px-1.5 py-0.5 rounded text-white/90">
                  {children}
                </code>
              ),
            pre: ({ children }) => (
              <pre className="my-4 p-4 rounded-lg bg-black/60 border border-white/5 overflow-x-auto text-[13px]">
                {children}
              </pre>
            ),
            ul: ({ children }) => (
              <ul className="list-disc pl-6 my-4 space-y-2">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal pl-6 my-4 space-y-2">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="text-white/80">{children}</li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-cyan-400/40 pl-4 my-4 text-white/70 italic">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                className="text-cyan-300 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {children}
              </a>
            ),
            hr: () => <hr className="border-white/10 my-8" />,
            strong: ({ children }) => (
              <strong className="font-semibold text-white">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-violet-300/90">{children}</em>
            ),
            table: ({ children }) => (
              <div className="my-4 overflow-x-auto">
                <table className="min-w-full border border-white/10 text-sm">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="border-b border-white/10 px-3 py-2 text-left text-white/80 font-medium">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border-b border-white/5 px-3 py-2 text-white/70">
                {children}
              </td>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  if (ext === "txt" || ext === "" || ext === "log") {
    return (
      <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-white/80 max-w-[900px]">
        {content}
      </pre>
    );
  }

  // Unsupported preview — show a friendly card with a download link.
  return (
    <div className="max-w-[560px] rounded-xl border border-white/10 bg-white/[0.02] p-6">
      <div className="text-[11px] uppercase tracking-[0.22em] text-white/40 mb-2">
        Preview not supported
      </div>
      <h3 className="font-serif text-2xl text-white mb-2 tracking-tight">
        {path.split("/").pop() ?? path}
      </h3>
      <p className="text-sm text-white/70 leading-relaxed mb-4">
        This file type cannot be previewed in the browser. The contents have
        been ingested into the vector index and are searchable via Ask.
      </p>
      <a
        href={corpora.knowledgeFileUrl(path)}
        className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white hover:bg-white/[0.08]"
        target="_blank"
        rel="noreferrer"
        download
      >
        Download file
      </a>
    </div>
  );
}
