"use client";

import { useEffect, useRef } from "react";

/**
 * Ambient canvas animation for the landing page — a living graph of
 * violet and cyan nodes wired into a mesh of persistent relationships
 * plus local proximity connections.
 *
 * Design notes:
 *   - Motion is parametric (sin/cos of time with per-node frequencies
 *     and phases) rather than velocity-stepped. That's the key to the
 *     fluid feel: no edge bounces, no perturbation jitter, no frame-
 *     rate-dependent speed drift, just continuous drift.
 *   - Each node gets a binary tint at seed time (roughly 50/50 violet
 *     vs cyan). Same-tint edges read as a solid color, mixed-tint
 *     edges use a fixed midpoint — avoids a smooth gradient across
 *     the viewport in favor of a "two species" feel.
 *   - Two edge systems layer on top of each other:
 *       * partner edges — a k-nearest-neighbor graph computed at
 *         seed, rendered regardless of instantaneous distance up to
 *         a longer threshold. Each edge has its own slow pulse
 *         (independent sin phase) so relationships breathe
 *         continuously. This is the "building relationships" layer.
 *       * proximity edges — classic distance-threshold lines,
 *         dimmer, for local ambient texture.
 *   - An intro fade ramps edge and node alpha from 0 → 1 over ~2s on
 *     first paint. Visually, the nodes "come online and start
 *     connecting to each other" as the page loads.
 *   - Alphas are deliberately low so the effect reads as "living
 *     background" rather than "foreground decoration".
 *   - Respects ``prefers-reduced-motion``: one static frame after
 *     the intro, no rAF loop.
 *   - Device-pixel-ratio aware so points and lines stay crisp on
 *     retina. On window resize we re-seed nodes and edges — a rare
 *     jump is preferable to keeping nodes packed in one corner.
 */

const NODE_COUNT = 60;
const PARTNER_K = 2; // each node wires to its K nearest at seed
const CONNECTION_DISTANCE = 160; // px — proximity edge threshold
const PARTNER_MAX_DISTANCE = 340; // px — partner edge visibility cap
const NODE_RADIUS = 1.5; // px
const MAX_LINE_ALPHA = 0.085; // proximity edges
const MAX_PARTNER_ALPHA = 0.18; // partner edges
const NODE_ALPHA = 0.55;
const INTRO_MS = 2000;
const PULSE_RATE = 0.00075; // rad / ms — partner edge breathing
const PULSE_DEPTH = 0.45; // 0–1 alpha modulation amplitude

// Purple + blue — the two species.
const VIOLET = { r: 139, g: 92, b: 246 };
const CYAN = { r: 6, g: 182, b: 212 };
const TINTS = [VIOLET, CYAN] as const;

// Fixed midpoint for mixed-tint edges. Precomputed so we don't blend
// per-frame per-edge.
const MIX = {
  r: Math.round((VIOLET.r + CYAN.r) / 2),
  g: Math.round((VIOLET.g + CYAN.g) / 2),
  b: Math.round((VIOLET.b + CYAN.b) / 2),
};

type TintIndex = 0 | 1;

interface Node {
  cx: number;
  cy: number;
  ax: number;
  ay: number;
  phaseX: number;
  phaseY: number;
  freqX: number;
  freqY: number;
  tint: TintIndex;
}

interface Edge {
  a: number; // index into nodes[], guaranteed a < b
  b: number;
  phase: number; // per-edge pulse offset
}

function pairColor(ta: TintIndex, tb: TintIndex) {
  if (ta === tb) return TINTS[ta];
  return MIX;
}

export function NetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let nodes: Node[] = [];
    let edges: Edge[] = [];
    let width = 0;
    let height = 0;
    let dpr = window.devicePixelRatio || 1;
    // tMs of first paint — used to compute the intro fade window.
    // `null` until the first paint sets it.
    let startMs: number | null = null;

    const buildPartnerEdges = () => {
      // For each node, pick the K nearest (by seed center distance)
      // other nodes, and record each pair once. The distance metric
      // uses seed centers (not animated positions) so the graph is
      // stable across frames — partners stay partners.
      const seen = new Set<number>();
      edges = [];
      const tmp: { j: number; d: number }[] = [];
      for (let i = 0; i < nodes.length; i++) {
        tmp.length = 0;
        for (let j = 0; j < nodes.length; j++) {
          if (j === i) continue;
          const dx = nodes[i].cx - nodes[j].cx;
          const dy = nodes[i].cy - nodes[j].cy;
          tmp.push({ j, d: dx * dx + dy * dy });
        }
        tmp.sort((a, b) => a.d - b.d);
        for (let k = 0; k < PARTNER_K && k < tmp.length; k++) {
          const j = tmp[k].j;
          const a = Math.min(i, j);
          const b = Math.max(i, j);
          // Encode pair as integer key — no string allocation per check.
          const key = a * 10000 + b;
          if (seen.has(key)) continue;
          seen.add(key);
          edges.push({ a, b, phase: Math.random() * Math.PI * 2 });
        }
      }
    };

    const seed = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Loose grid with jitter — avoids obvious rows while still
      // giving reasonable coverage. Columns biased by aspect ratio.
      const cols = Math.max(
        4,
        Math.ceil(Math.sqrt(NODE_COUNT * (width / Math.max(height, 1)))),
      );
      const rows = Math.ceil(NODE_COUNT / cols);
      const cellW = width / cols;
      const cellH = height / rows;

      nodes = [];
      for (let i = 0; i < rows && nodes.length < NODE_COUNT; i++) {
        for (let j = 0; j < cols && nodes.length < NODE_COUNT; j++) {
          const baseX = (j + 0.5) * cellW;
          const baseY = (i + 0.5) * cellH;
          nodes.push({
            cx: baseX + (Math.random() - 0.5) * cellW * 0.6,
            cy: baseY + (Math.random() - 0.5) * cellH * 0.6,
            ax: cellW * 0.22 + Math.random() * cellW * 0.28,
            ay: cellH * 0.22 + Math.random() * cellH * 0.28,
            phaseX: Math.random() * Math.PI * 2,
            phaseY: Math.random() * Math.PI * 2,
            // rad/ms — slow, ~3–10s for a full cycle.
            freqX: 0.00018 + Math.random() * 0.00024,
            freqY: 0.00018 + Math.random() * 0.00024,
            // Binary tint: roughly 50/50 split, random assignment so
            // neighbors aren't forced to be the same color.
            tint: Math.random() < 0.5 ? 0 : 1,
          });
        }
      }

      buildPartnerEdges();
    };

    const paint = (tMs: number) => {
      if (startMs === null) startMs = tMs;
      const elapsed = tMs - startMs;
      const intro = Math.min(1, Math.max(0, elapsed / INTRO_MS));
      // Smoothstep eases the intro in and out.
      const introEased = intro * intro * (3 - 2 * intro);

      ctx.clearRect(0, 0, width, height);

      // Positions once per frame — shared by both edge passes and
      // the node pass.
      const positions = new Array<{ x: number; y: number; tint: TintIndex }>(
        nodes.length,
      );
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        positions[i] = {
          x: n.cx + n.ax * Math.sin(tMs * n.freqX + n.phaseX),
          y: n.cy + n.ay * Math.cos(tMs * n.freqY + n.phaseY),
          tint: n.tint,
        };
      }

      // ---- Partner edges: always drawn up to a longer range. ----
      // Each edge pulses independently so the whole mesh subtly
      // breathes. This is the "relationships" layer.
      const partnerMaxSq = PARTNER_MAX_DISTANCE * PARTNER_MAX_DISTANCE;
      ctx.lineWidth = 0.9;
      for (let e = 0; e < edges.length; e++) {
        const edge = edges[e];
        const a = positions[edge.a];
        const b = positions[edge.b];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distSq = dx * dx + dy * dy;
        if (distSq > partnerMaxSq) continue;
        const dist = Math.sqrt(distSq);
        const falloff = 1 - dist / PARTNER_MAX_DISTANCE;
        // Pulse ranges from (1 - PULSE_DEPTH) to 1 — never fully dims.
        const pulse =
          1 - PULSE_DEPTH * 0.5 +
          (PULSE_DEPTH * 0.5) * Math.sin(tMs * PULSE_RATE + edge.phase);
        const alpha = falloff * pulse * MAX_PARTNER_ALPHA * introEased;
        const c = pairColor(a.tint, b.tint);
        ctx.strokeStyle = `rgba(${c.r},${c.g},${c.b},${alpha})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      // ---- Proximity edges: dimmer, for local ambient texture. ----
      ctx.lineWidth = 0.7;
      const connSq = CONNECTION_DISTANCE * CONNECTION_DISTANCE;
      for (let i = 0; i < positions.length; i++) {
        const a = positions[i];
        for (let j = i + 1; j < positions.length; j++) {
          const b = positions[j];
          const dx = a.x - b.x;
          if (dx > CONNECTION_DISTANCE || dx < -CONNECTION_DISTANCE) continue;
          const dy = a.y - b.y;
          if (dy > CONNECTION_DISTANCE || dy < -CONNECTION_DISTANCE) continue;
          const distSq = dx * dx + dy * dy;
          if (distSq > connSq) continue;
          const dist = Math.sqrt(distSq);
          const falloff = 1 - dist / CONNECTION_DISTANCE;
          const alpha = falloff * MAX_LINE_ALPHA * introEased;
          const c = pairColor(a.tint, b.tint);
          ctx.strokeStyle = `rgba(${c.r},${c.g},${c.b},${alpha})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      // ---- Nodes last so they sit on top of their own web. ----
      // Nodes fade in slightly slower than zero (start at 0.4x) so
      // they're visible from the first frame but still participate
      // in the intro ramp.
      const nodeIntro = 0.4 + 0.6 * introEased;
      for (let i = 0; i < positions.length; i++) {
        const p = positions[i];
        const c = TINTS[p.tint];
        ctx.fillStyle = `rgba(${c.r},${c.g},${c.b},${NODE_ALPHA * nodeIntro})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, NODE_RADIUS, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const loop = (tMs: number) => {
      paint(tMs);
      rafRef.current = requestAnimationFrame(loop);
    };

    seed();
    if (reduceMotion) {
      // Skip intro fade and motion entirely — paint one static frame
      // with full intro progress so the scene is fully formed.
      startMs = -INTRO_MS;
      paint(0);
    } else {
      rafRef.current = requestAnimationFrame(loop);
    }

    const onResize = () => {
      dpr = window.devicePixelRatio || 1;
      seed();
      // Don't replay the intro on resize — the scene jumps but stays
      // fully formed, which reads better than a re-fade.
      startMs = performance.now() - INTRO_MS;
      if (reduceMotion) paint(0);
    };
    window.addEventListener("resize", onResize);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0"
      style={{ zIndex: 0 }}
    />
  );
}
