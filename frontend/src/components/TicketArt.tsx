// Small product-style illustrations that pop out of each ticket card.
export default function TicketArt({ type, size = 92 }: { type: string; size?: number }) {
  if (type === "customer_order") {
    // white Bulldog tee
    return (
      <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="ticket-art">
        <ellipse cx="60" cy="112" rx="34" ry="5" fill="#000" opacity="0.15" />
        <path d="M40 14 L22 22 L6 44 L22 54 L30 44 L30 106 Q60 112 90 106 L90 44 L98 54 L114 44 L98 22 L80 14 Q60 28 40 14 Z"
          fill="#fbfbf7" stroke="#d7d9d0" strokeWidth="2" strokeLinejoin="round" />
        <path d="M40 14 Q60 30 80 14" fill="none" stroke="#d7d9d0" strokeWidth="3" />
        <circle cx="60" cy="62" r="17" fill="#1f5b2c" />
        <text x="60" y="69" fontSize="20" fontWeight="800" fill="#fbfbf7" textAnchor="middle" fontFamily="inherit">Y</text>
      </svg>
    );
  }
  if (type === "rent_notice") {
    // the Chapel Street shop
    return (
      <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="ticket-art">
        <ellipse cx="60" cy="112" rx="40" ry="5" fill="#000" opacity="0.15" />
        <rect x="18" y="40" width="84" height="68" rx="4" fill="#f6f2e8" stroke="#d8cfb8" strokeWidth="2" />
        <rect x="12" y="24" width="96" height="18" rx="4" fill="#2f3a33" />
        <text x="60" y="37" fontSize="10" fontWeight="800" fill="#b9e28c" textAnchor="middle" letterSpacing="1">CAMPUS CUSTOMS</text>
        <path d="M16 42 h88 l-6 12 h-76 z" fill="#3f8f4a" />
        <path d="M22 54 q7 6 14 0 q7 6 14 0 q7 6 14 0 q7 6 14 0 q7 6 14 0 q7 6 14 0" fill="#3f8f4a" />
        <rect x="28" y="64" width="26" height="22" rx="2" fill="#a9d6f2" />
        <rect x="66" y="64" width="24" height="44" rx="2" fill="#e8823a" />
        <circle cx="85" cy="88" r="2" fill="#7a3e12" />
        <rect x="80" y="2" width="30" height="18" rx="3" fill="#fff" stroke="#d8cfb8" strokeWidth="1.5" transform="rotate(8 95 11)" />
        <text x="95" y="15" fontSize="9" fontWeight="800" fill="#c8453c" textAnchor="middle" transform="rotate(8 95 11)">RENT</text>
      </svg>
    );
  }
  // navy hoodie
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="ticket-art">
      <ellipse cx="60" cy="112" rx="36" ry="5" fill="#000" opacity="0.15" />
      <path d="M42 16 Q60 4 78 16 L100 26 L116 70 L100 76 L92 56 L92 106 Q60 112 28 106 L28 56 L20 76 L4 70 L20 26 Z"
        fill="#1f3b6e" stroke="#142a52" strokeWidth="2" strokeLinejoin="round" />
      <path d="M42 16 Q60 44 78 16 Q60 30 42 16 Z" fill="#142a52" />
      <path d="M56 32 v18 M64 32 v18" stroke="#e8edf6" strokeWidth="2" strokeLinecap="round" />
      <rect x="40" y="76" width="40" height="18" rx="6" fill="#18325e" />
      <text x="60" y="68" fontSize="13" fontWeight="800" fill="#e8edf6" textAnchor="middle" letterSpacing="1.5">YALE</text>
    </svg>
  );
}
