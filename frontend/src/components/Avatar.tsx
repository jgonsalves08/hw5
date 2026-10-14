// Hand-built SVG characters, one per agent role (no generated images).
// Each is the same friendly "bean" with a prop that says what it does.
import type { AgentKey } from "../types";

export type Mood = "idle" | "working" | "done" | "error" | "benched";

const SHADES: Record<AgentKey, [string, string, string]> = {
  // [highlight, base, shadow]
  boss: ["#5d6e62", "#2f3a33", "#1a221d"],
  inventory: ["#ffb877", "#e8823a", "#b85a1c"],
  accounting: ["#7cc77f", "#3f8f4a", "#24622e"],
  facilities: ["#ffe08a", "#e2b234", "#b5861a"],
  customer_service: ["#ffa3b0", "#e0677a", "#b2404f"],
};

function Face({ mood, dark }: { mood: Mood; dark: string }) {
  const happy = mood === "done";
  return (
    <g className="face">
      {happy ? (
        <>
          <path d="M56 90 q8 -10 16 0" stroke={dark} strokeWidth="4.5" fill="none" strokeLinecap="round" />
          <path d="M88 90 q8 -10 16 0" stroke={dark} strokeWidth="4.5" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <g className="eyes">
          <ellipse cx="64" cy="88" rx="9.5" ry="10.5" fill="#fff" />
          <ellipse cx="96" cy="88" rx="9.5" ry="10.5" fill="#fff" />
          <g className="pupils">
            <circle cx="66" cy="90" r="5.2" fill="#14181a" />
            <circle cx="98" cy="90" r="5.2" fill="#14181a" />
            <circle cx="68" cy="87.5" r="1.8" fill="#fff" />
            <circle cx="100" cy="87.5" r="1.8" fill="#fff" />
          </g>
        </g>
      )}
      <ellipse cx="52" cy="104" rx="7" ry="4.5" fill="#ff8fa0" opacity="0.45" />
      <ellipse cx="108" cy="104" rx="7" ry="4.5" fill="#ff8fa0" opacity="0.45" />
      {mood === "working" ? (
        <ellipse cx="80" cy="110" rx="5" ry="5.5" fill={dark} />
      ) : mood === "error" ? (
        <path d="M71 113 q9 -7 18 0" stroke={dark} strokeWidth="3.5" fill="none" strokeLinecap="round" />
      ) : (
        <path d="M70 106 q10 11 20 0" stroke={dark} strokeWidth="3.5" fill="none" strokeLinecap="round" />
      )}
      {mood === "error" && <path d="M118 66 q6 9 0 13 q-6 -4 0 -13z" fill="#7fc4ff" />}
    </g>
  );
}

function Prop({ role }: { role: AgentKey }) {
  switch (role) {
    case "boss":
      return (
        <g>
          {/* crown */}
          <path d="M54 40 L58 14 L70 30 L80 8 L90 30 L102 14 L106 40 Z" fill="#f2c94c" stroke="#c99a1e" strokeWidth="2" strokeLinejoin="round" />
          <rect x="54" y="36" width="52" height="8" rx="3" fill="#e0b33a" />
          <circle cx="80" cy="22" r="3.5" fill="#e05a5a" />
          <circle cx="62" cy="27" r="2.6" fill="#5aa9e0" />
          <circle cx="98" cy="27" r="2.6" fill="#7cc77f" />
          {/* collar + tie */}
          <path d="M62 124 L80 134 L98 124 L94 140 L80 136 L66 140 Z" fill="#f4f4ef" />
          <path d="M76 133 L84 133 L86 138 L80 142 L74 138 Z" fill="#c8453c" />
          <path d="M75 141 L85 141 L88 158 L80 164 L72 158 Z" fill="#d9534a" />
        </g>
      );
    case "inventory":
      return (
        <g>
          {/* cap */}
          <path d="M44 62 Q46 30 80 30 Q114 30 116 62 Z" fill="#2f6f3a" />
          <path d="M100 58 Q128 56 138 64 Q122 68 100 66 Z" fill="#245a2e" />
          <circle cx="80" cy="31" r="4" fill="#245a2e" />
          {/* box */}
          <g transform="translate(0 2)">
            <rect x="50" y="118" width="60" height="42" rx="4" fill="#c8915a" stroke="#9c6a38" strokeWidth="2" />
            <path d="M50 128 H110" stroke="#9c6a38" strokeWidth="2" />
            <rect x="74" y="118" width="12" height="42" fill="#e2b98a" />
            <rect x="57" y="138" width="14" height="10" rx="1.5" fill="#fff" opacity="0.9" />
            <path d="M59 141 h10 M59 145 h7" stroke="#9c6a38" strokeWidth="1.4" />
            <circle cx="49" cy="138" r="7" fill="#e8823a" stroke="#b85a1c" strokeWidth="1.5" />
            <circle cx="111" cy="138" r="7" fill="#e8823a" stroke="#b85a1c" strokeWidth="1.5" />
          </g>
        </g>
      );
    case "accounting":
      return (
        <g>
          {/* glasses */}
          <g fill="none" stroke="#14181a" strokeWidth="3">
            <circle cx="64" cy="88" r="13" />
            <circle cx="96" cy="88" r="13" />
            <path d="M77 87 q3 -3 6 0" />
          </g>
          {/* calculator */}
          <g transform="rotate(-6 80 140)">
            <rect x="56" y="116" width="48" height="46" rx="6" fill="#23292b" />
            <rect x="61" y="121" width="38" height="11" rx="2" fill="#b9e28c" />
            <text x="96" y="130" fontSize="8" fontFamily="monospace" fill="#24622e" textAnchor="end">$$$</text>
            {[0, 1, 2].map((r) =>
              [0, 1, 2, 3].map((c) => (
                <rect key={`${r}-${c}`} x={62 + c * 9.5} y={137 + r * 8} width="7" height="5.5" rx="1.5"
                  fill={c === 3 ? "#e8823a" : "#d9ddd6"} />
              )),
            )}
          </g>
          <circle cx="54" cy="142" r="7" fill="#3f8f4a" stroke="#24622e" strokeWidth="1.5" />
          <circle cx="106" cy="138" r="7" fill="#3f8f4a" stroke="#24622e" strokeWidth="1.5" />
          {/* coin */}
          <circle cx="128" cy="128" r="10" fill="#f2c94c" stroke="#c99a1e" strokeWidth="2" />
          <text x="128" y="132.5" fontSize="12" fontWeight="800" fill="#a87c12" textAnchor="middle">$</text>
        </g>
      );
    case "facilities":
      return (
        <g>
          {/* hard hat */}
          <path d="M42 60 Q42 26 80 24 Q118 26 118 60 Z" fill="#f28c28" />
          <rect x="36" y="56" width="88" height="9" rx="4.5" fill="#d9731a" />
          <rect x="74" y="24" width="12" height="34" rx="5" fill="#ffa64d" />
          {/* little shop */}
          <g transform="translate(0 4)">
            <rect x="56" y="128" width="48" height="32" rx="2" fill="#fbfaf5" stroke="#c9c4b0" strokeWidth="1.5" />
            <path d="M50 130 L80 110 L110 130 Z" fill="#3f8f4a" />
            <path d="M58 128 h44" stroke="#24622e" strokeWidth="3" strokeDasharray="6 4" />
            <rect x="74" y="140" width="12" height="20" rx="1.5" fill="#e8823a" />
            <rect x="61" y="138" width="9" height="8" rx="1" fill="#9fd0f0" />
            <rect x="90" y="138" width="9" height="8" rx="1" fill="#9fd0f0" />
            <circle cx="50" cy="146" r="7" fill="#e2b234" stroke="#b5861a" strokeWidth="1.5" />
            <circle cx="110" cy="146" r="7" fill="#e2b234" stroke="#b5861a" strokeWidth="1.5" />
          </g>
          {/* key */}
          <g transform="translate(126 112) rotate(30)">
            <circle r="7" fill="none" stroke="#c99a1e" strokeWidth="4" />
            <path d="M6 0 h16 M16 0 v5 M21 0 v4" stroke="#c99a1e" strokeWidth="4" strokeLinecap="round" />
          </g>
        </g>
      );
    case "customer_service":
      return (
        <g>
          {/* headset */}
          <path d="M34 92 Q34 36 80 36 Q126 36 126 92" fill="none" stroke="#23292b" strokeWidth="6" strokeLinecap="round" />
          <rect x="24" y="80" width="16" height="26" rx="7" fill="#23292b" />
          <rect x="120" y="80" width="16" height="26" rx="7" fill="#23292b" />
          <path d="M128 104 Q126 122 96 116" fill="none" stroke="#23292b" strokeWidth="4" strokeLinecap="round" />
          <circle cx="94" cy="116" r="5" fill="#23292b" />
          {/* envelope */}
          <g transform="rotate(5 80 142)">
            <rect x="54" y="126" width="52" height="34" rx="4" fill="#fff" stroke="#d9d4cc" strokeWidth="1.5" />
            <path d="M55 128 L80 146 L105 128" fill="none" stroke="#d9d4cc" strokeWidth="2" />
            <path d="M88 150 c0 -4 6 -4 6 0 c0 -4 6 -4 6 0 c0 4 -6 7 -6 9 c0 -2 -6 -5 -6 -9z" fill="#e0677a" />
          </g>
          <circle cx="52" cy="146" r="7" fill="#e0677a" stroke="#b2404f" strokeWidth="1.5" />
          <circle cx="108" cy="146" r="7" fill="#e0677a" stroke="#b2404f" strokeWidth="1.5" />
        </g>
      );
  }
}

export default function Avatar({ role, mood = "idle", size = 120 }: { role: AgentKey; mood?: Mood; size?: number }) {
  const [hi, base, dark] = SHADES[role];
  const id = `grad-${role}`;
  const propOnTop = role === "accounting" || role === "customer_service";
  return (
    <svg className={`avatar mood-${mood}`} width={size} height={size * 1.12} viewBox="0 0 160 180" aria-hidden>
      <defs>
        <radialGradient id={id} cx="36%" cy="30%" r="80%">
          <stop offset="0%" stopColor={hi} />
          <stop offset="55%" stopColor={base} />
          <stop offset="100%" stopColor={dark} />
        </radialGradient>
      </defs>
      <ellipse className="ground" cx="80" cy="172" rx="44" ry="6" fill="#000" opacity="0.18" />
      <g className="bean">
        <path d="M80 36 C118 36 136 66 136 106 C136 144 112 164 80 164 C48 164 24 144 24 106 C24 66 42 36 80 36 Z"
          fill={`url(#${id})`} />
        <ellipse cx="62" cy="58" rx="16" ry="9" fill="#fff" opacity="0.22" transform="rotate(-20 62 58)" />
        {!propOnTop && <Prop role={role} />}
        <Face mood={mood} dark={role === "boss" ? "#f4efe2" : dark} />
        {propOnTop && <Prop role={role} />}
      </g>
    </svg>
  );
}
