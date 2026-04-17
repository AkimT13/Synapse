"use client";

import Link from "next/link";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { workspace } from "@/lib/api";

export function Topbar() {
  const stats = useQuery({
    queryKey: ["workspace", "stats"],
    queryFn: workspace.stats,
  });
  const ready =
    (stats.data?.code_files ?? 0) + (stats.data?.knowledge_files ?? 0) > 0;

  return (
    <header className="topbar">
      <div className="flex items-center gap-3">
        <Link href="/" className="brand">
          <span className="brand-dot" />
          <span className="brand-word">Synapse</span>
        </Link>
        <span className="text-white/20">/</span>
        <div className="project-chip">
          <span className="swatch" />
          <span>synapse · demo</span>
        </div>
      </div>

      <div className="hidden md:flex items-center gap-2 w-[340px] max-w-[40vw]">
        <label className="search-box !m-0 w-full">
          <Search size={14} />
          <input placeholder="Quick search..." />
          <span className="shortcut">⌘K</span>
        </label>
      </div>

      <div className="flex items-center gap-3">
        <span className="status-pill">
          <span className="status-dot" />
          {ready ? "Synced" : "Empty"}
        </span>
        <span className="avatar">S</span>
      </div>
    </header>
  );
}
