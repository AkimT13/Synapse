"use client";

/**
 * The primary retrieval trigger for each workspace pane. Lives in the
 * center pane's header, right-aligned. Consistent position across the
 * code and knowledge panes replaces the earlier floating selection
 * button, which was fragile over variable-height prose.
 */
interface HeaderActionProps {
  label: string;
  // Optional highlight pill inside the chip, e.g. a function name or a
  // truncated preview of the selected passage.
  target?: string | null;
  onActivate: () => void;
  disabled?: boolean;
  // Render a "working" label instead of the normal one while retrieval
  // is in flight. Keeps the chip disabled for the duration.
  busy?: boolean;
}

export function HeaderAction({
  label,
  target,
  onActivate,
  disabled = false,
  busy = false,
}: HeaderActionProps) {
  const isDisabled = disabled || busy;
  return (
    <button
      type="button"
      className="header-action"
      onClick={onActivate}
      disabled={isDisabled}
    >
      <span className="arrow">↳</span>
      {busy ? "Searching…" : label}
      {!busy && target ? <span className="target">{target}</span> : null}
      <span className="kbd">⌘ ↵</span>
    </button>
  );
}
