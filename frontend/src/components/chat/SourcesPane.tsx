"use client";

import { Code2, FileText } from "lucide-react";
import Link from "next/link";
import { forwardRef, useImperativeHandle, useRef } from "react";

import type { SourceRef, WorkspaceStats } from "@/lib/api";
import { cn } from "@/lib/cn";

interface SourcesPaneProps {
  sources: SourceRef[];
  stats?: WorkspaceStats | null;
}

export interface SourcesPaneHandle {
  flash: (index: number) => void;
}

// Code paths go to /code?file=<path>, knowledge to /knowledge?file=<path>.
// The workspace pages read the `file` param and open that file.
function hrefFor(source: SourceRef): string {
  const prefix = source.chunk_type === "code" ? "/code" : "/knowledge";
  return `${prefix}?file=${encodeURIComponent(source.source_file)}`;
}

export const SourcesPane = forwardRef<SourcesPaneHandle, SourcesPaneProps>(
  function SourcesPane({ sources, stats }, ref) {
    const itemRefs = useRef<Map<number, HTMLAnchorElement>>(new Map());

    useImperativeHandle(ref, () => ({
      flash(index: number) {
        const el = itemRefs.current.get(index);
        if (!el) return;
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("flash");
        window.setTimeout(() => el.classList.remove("flash"), 900);
      },
    }));

    const code = sources.filter((s) => s.chunk_type === "code");
    const knowledge = sources.filter((s) => s.chunk_type === "knowledge");
    const count = sources.length;

    return (
      <section className="pane">
        <div className="pane-head">
          <span className="pane-title">Sources used</span>
          <span className="pane-sub">
            {count === 0 ? "none yet" : `${count} cited`}
          </span>
        </div>
        <div className="pane-body">
          {count === 0 ? (
            <div className="empty" style={{ padding: 20, fontSize: 12 }}>
              Send a message to see its sources.
            </div>
          ) : (
            <>
              {code.length > 0 && (
                <div className="src-group">
                  <h4>From your code</h4>
                  {code.map((source) => (
                    <Link
                      key={`code-${source.index}`}
                      ref={(el) => {
                        if (el) itemRefs.current.set(source.index, el);
                        else itemRefs.current.delete(source.index);
                      }}
                      className="src-item"
                      href={hrefFor(source)}
                    >
                      <span className={cn("num cite")}>{source.index}</span>
                      <span className="ico">
                        <Code2 size={14} />
                      </span>
                      <span className="label">
                        {source.source_file}
                        {source.title ? ` · ${source.title}` : ""}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
              {knowledge.length > 0 && (
                <div className="src-group">
                  <h4>From your knowledge</h4>
                  {knowledge.map((source) => (
                    <Link
                      key={`kn-${source.index}`}
                      ref={(el) => {
                        if (el) itemRefs.current.set(source.index, el);
                        else itemRefs.current.delete(source.index);
                      }}
                      className="src-item"
                      href={hrefFor(source)}
                    >
                      <span className={cn("num cite c")}>{source.index}</span>
                      <span className="ico">
                        <FileText size={14} />
                      </span>
                      <span className="label">
                        {source.source_file}
                        {source.title ? ` · ${source.title}` : ""}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}

          <div className="src-group">
            <h4>Search over</h4>
            <div className="src-stats">
              <div className="row">
                <span>Code chunks</span>
                <span>{formatCount(stats?.total_code_chunks)}</span>
              </div>
              <div className="row">
                <span>Knowledge chunks</span>
                <span>{formatCount(stats?.total_knowledge_chunks)}</span>
              </div>
              <div className="row">
                <span>Distance</span>
                <span>cosine</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    );
  },
);

function formatCount(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString();
}
