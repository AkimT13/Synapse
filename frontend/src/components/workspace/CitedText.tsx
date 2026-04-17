"use client";

import { useCallback, useMemo } from "react";

/**
 * Render an LLM-generated explanation that contains [N] citation
 * markers. Each [N] becomes a clickable badge that scrolls to the
 * matching ResultCard (tagged with `data-citation-index={N}`) and
 * flashes its border briefly.
 *
 * The caller provides a ref pointing at the container the cards live
 * in — typically the right-pane body. That keeps DOM lookup scoped
 * even when multiple panes are on screen at once.
 */
interface CitedTextProps {
  text: string;
  containerRef: React.RefObject<HTMLElement>;
}

const CITATION_SPLIT = /(\[\d+\])/g;
const CITATION_MATCH = /^\[(\d+)\]$/;
const FLASH_DURATION_MS = 900;

export function CitedText({ text, containerRef }: CitedTextProps) {
  const parts = useMemo(() => text.split(CITATION_SPLIT), [text]);

  const activate = useCallback(
    (index: number) => {
      const root = containerRef.current;
      if (!root) return;
      const target = root.querySelector<HTMLElement>(
        `[data-citation-index="${index}"]`,
      );
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("result-highlight");
      window.setTimeout(
        () => target.classList.remove("result-highlight"),
        FLASH_DURATION_MS,
      );
    },
    [containerRef],
  );

  return (
    <>
      {parts.map((part, key) => {
        const match = part.match(CITATION_MATCH);
        if (!match) return <span key={key}>{part}</span>;
        const index = parseInt(match[1], 10);
        return (
          <button
            key={key}
            type="button"
            className="cite"
            onClick={() => activate(index)}
            title={`Jump to source ${index}`}
          >
            {index}
          </button>
        );
      })}
    </>
  );
}
