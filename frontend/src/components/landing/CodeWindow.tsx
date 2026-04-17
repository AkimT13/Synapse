"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

const SNIPPET_PLAIN = `from storage.vector_store import VectorStore
from jobs.ingest_code   import CodeIngestionJob

# Walk → normalize → embed → upsert, in one pass.
with VectorStore() as store:
    result = CodeIngestionJob(store).run("/path/to/repo")
    print(f"stored {result.chunks_stored} chunks "
          f"from {result.files_processed} files")`;

export function CodeWindow() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(SNIPPET_PLAIN);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard unavailable — ignore */
    }
  };

  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-[#080808]/80 shadow-[0_30px_80px_-30px_rgba(139,92,246,0.25)]">
      {/* toolbar */}
      <div className="flex items-center justify-between border-b border-white/5 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-red-500/60" />
          <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
          <span className="h-3 w-3 rounded-full bg-emerald/60" />
        </div>
        <span className="font-mono text-[11px] text-neutral-500">
          jobs/ingest_code.py
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label="Copy snippet"
          className="flex items-center gap-1 text-neutral-500 transition-colors hover:text-white"
        >
          {copied ? (
            <span className="font-mono text-xs text-emerald-fg inline-flex items-center gap-1">
              <Check size={12} />
              copied
            </span>
          ) : (
            <Copy size={14} />
          )}
        </button>
      </div>

      {/* code */}
      <pre className="overflow-x-auto px-6 py-6 font-mono text-[13.5px] leading-relaxed">
        <code>
          <span className="kw">from</span> <span className="text-white">storage.vector_store</span>{" "}
          <span className="kw">import</span> <span className="cls">VectorStore</span>
          {"\n"}
          <span className="kw">from</span> <span className="text-white">jobs.ingest_code</span>  {" "}
          <span className="kw">import</span> <span className="cls">CodeIngestionJob</span>
          {"\n\n"}
          <span className="com"># Walk → normalize → embed → upsert, in one pass.</span>
          {"\n"}
          <span className="kw">with</span> <span className="cls">VectorStore</span>
          <span className="pun">()</span> <span className="kw">as</span> store
          <span className="pun">:</span>
          {"\n"}
          {"    "}result <span className="pun">=</span> <span className="cls">CodeIngestionJob</span>
          <span className="pun">(</span>store<span className="pun">).</span>
          <span className="fn">run</span>
          <span className="pun">(</span>
          <span className="str">&quot;/path/to/repo&quot;</span>
          <span className="pun">)</span>
          {"\n"}
          {"    "}
          <span className="fn">print</span>
          <span className="pun">(</span>
          <span className="str">f&quot;stored </span>
          <span className="pun">{"{"}</span>result<span className="pun">.</span>chunks_stored
          <span className="pun">{"}"}</span>
          <span className="str"> chunks &quot;</span>
          {"\n"}
          {"          "}
          <span className="str">f&quot;from </span>
          <span className="pun">{"{"}</span>result<span className="pun">.</span>files_processed
          <span className="pun">{"}"}</span>
          <span className="str"> files&quot;</span>
          <span className="pun">)</span>
        </code>
      </pre>
    </div>
  );
}
