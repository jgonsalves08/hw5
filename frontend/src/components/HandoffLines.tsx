// Draws one arrow per hand-off between agent cards: from the agent who handed off
// to the agent who received the work. Repeated hand-offs get their own parallel line.
import { useLayoutEffect, useState, type RefObject } from "react";
import { AGENT_BY_KEY } from "../agents";
import type { Handoff } from "../useBoard";

interface Line {
  h: Handoff;
  d: string;
  label: { x: number; y: number };
  color: string;
}

type Box = { left: number; right: number; top: number; bottom: number; cx: number; cy: number; w: number; h: number };

const SPACING = 14; // px between parallel lines for the same pair
const LATERAL_DROP = 46; // how far below the cards a side-by-side arrow dips
const LATERAL_STEP = 22;

export default function HandoffLines({
  handoffs,
  container,
  onExtraSpace,
}: {
  handoffs: Handoff[];
  container: RefObject<HTMLDivElement | null>;
  onExtraSpace: (px: number) => void;
}) {
  const [lines, setLines] = useState<Line[]>([]);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useLayoutEffect(() => {
    const root = container.current;
    if (!root) return;

    const measure = () => {
      const base = root.getBoundingClientRect();
      const box = (key: string): Box | null => {
        const el = root.querySelector<HTMLElement>(`[data-agent="${key}"]`);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const left = r.left - base.left;
        const top = r.top - base.top;
        return { left, top, right: left + r.width, bottom: top + r.height, cx: left + r.width / 2, cy: top + r.height / 2, w: r.width, h: r.height };
      };

      // count lines per unordered pair so repeats sit side by side
      const pairTotals = new Map<string, number>();
      const pairKey = (h: Handoff) => [h.from, h.to].sort().join("|");
      for (const h of handoffs) pairTotals.set(pairKey(h), (pairTotals.get(pairKey(h)) ?? 0) + 1);
      const pairSeen = new Map<string, number>();

      let extra = 0;
      const out: Line[] = [];
      for (const h of handoffs) {
        const a = box(h.from);
        const b = box(h.to);
        if (!a || !b) continue;
        const key = pairKey(h);
        const k = pairSeen.get(key) ?? 0;
        pairSeen.set(key, k + 1);
        const total = pairTotals.get(key) ?? 1;
        const shift = (k - (total - 1) / 2) * SPACING;
        const color = h.status === "refused" ? "#c8453c" : AGENT_BY_KEY[h.from]?.accent ?? "#b9e28c";

        const sameRow = Math.abs(a.cy - b.cy) < Math.min(a.h, b.h) / 2;
        let d: string;
        let label: { x: number; y: number };
        if (sameRow) {
          // side by side: dip below the row, bottom edge to bottom edge
          const x1 = a.cx + shift;
          const x2 = b.cx + shift;
          const y = Math.max(a.bottom, b.bottom);
          const depth = LATERAL_DROP + k * LATERAL_STEP;
          d = `M ${x1} ${a.bottom} C ${x1} ${y + depth}, ${x2} ${y + depth}, ${x2} ${b.bottom + 6}`;
          label = { x: (x1 + x2) / 2, y: y + depth * 0.75 };
          extra = Math.max(extra, depth + 12);
        } else {
          // different rows: bottom edge of the upper card to top edge of the lower card,
          // landing in the lower card's top-left corner, clear of its avatar and status pill
          const upper = a.top < b.top ? a : b;
          const lower = upper === a ? b : a;
          const xLow = lower.left + Math.min(lower.w * 0.16, 44) + shift;
          const xUp = Math.min(Math.max(xLow, upper.left + 28), upper.right - 28);
          const yUp = upper.bottom;
          const yLow = lower.top;
          const mid = (yUp + yLow) / 2;
          const [sx, sy, ex, ey] = upper === a ? [xUp, yUp, xLow, yLow - 6] : [xLow, yLow, xUp, yUp + 6];
          d = `M ${sx} ${sy} C ${sx} ${mid}, ${ex} ${mid}, ${ex} ${ey}`;
          label = { x: (sx + ex) / 2, y: mid };
        }
        out.push({ h, d, label, color });
      }
      setLines(out);
      setSize({ w: root.clientWidth, h: root.clientHeight });
      onExtraSpace(extra);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(root);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [handoffs, container, onExtraSpace]);

  if (!lines.length) return null;
  const colors = [...new Set(lines.map((l) => l.color))];

  return (
    <svg className="handoff-layer" width={size.w} height={size.h} aria-hidden>
      <defs>
        {colors.map((c) => (
          <marker key={c} id={`arrow-${c.slice(1)}`} viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={c} />
          </marker>
        ))}
      </defs>
      {lines.map(({ h, d, color }) => (
        <g key={h.n} className={`handoff handoff-${h.status}`}>
          <path d={d} className="handoff-halo" />
          <path d={d} className="handoff-path" stroke={color} markerEnd={`url(#arrow-${color.slice(1)})`} />
        </g>
      ))}
      {lines.map(({ h, label, color }) => (
        // position on the outer <g>, fade-in animation on the inner one (a CSS animation would override the SVG transform)
        <g key={`l${h.n}`} transform={`translate(${label.x} ${label.y})`}>
          <g className="handoff-label">
            <circle r="11" fill="#111312" stroke={color} strokeWidth="2.5" />
            <text y="4" textAnchor="middle">
              {h.status === "refused" ? "✕" : h.n}
            </text>
          </g>
        </g>
      ))}
    </svg>
  );
}
