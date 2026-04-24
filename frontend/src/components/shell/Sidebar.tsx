"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Code2,
  FlaskConical,
  type LucideIcon,
  MessageSquare,
  Settings,
  Upload,
} from "lucide-react";

import { cn } from "@/lib/cn";

interface NavEntry {
  href: string;
  label: string;
  icon: LucideIcon;
  matchPrefix: string;
}

const PRIMARY_NAV: NavEntry[] = [
  { href: "/code", label: "Code", icon: Code2, matchPrefix: "/code" },
  { href: "/drift", label: "Drift", icon: FlaskConical, matchPrefix: "/drift" },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen, matchPrefix: "/knowledge" },
  { href: "/ask", label: "Ask", icon: MessageSquare, matchPrefix: "/ask" },
];

const SECONDARY_NAV: NavEntry[] = [
  { href: "/onboarding", label: "Sources", icon: Upload, matchPrefix: "/onboarding" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      {PRIMARY_NAV.map((entry) => (
        <NavButton key={entry.href} entry={entry} pathname={pathname} />
      ))}
      <hr className="hair w-8 my-1 opacity-40" />
      {SECONDARY_NAV.map((entry) => (
        <NavButton key={entry.href} entry={entry} pathname={pathname} />
      ))}
      <div className="mt-auto">
        <Link href="/" className="nav-btn" aria-label="Home">
          <Settings size={18} />
          <span className="tip">Home</span>
        </Link>
      </div>
    </aside>
  );
}

function NavButton({ entry, pathname }: { entry: NavEntry; pathname: string }) {
  const Icon = entry.icon;
  const active = pathname === entry.href || pathname.startsWith(`${entry.matchPrefix}/`);
  return (
    <Link
      href={entry.href}
      className={cn("nav-btn", active && "active")}
      aria-label={entry.label}
    >
      <Icon size={18} />
      <span className="tip">{entry.label}</span>
    </Link>
  );
}
