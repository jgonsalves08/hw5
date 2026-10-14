// "What do I do now?" — three steps across the top; the current one is lit up.
export type Step = 1 | 2 | 3;

export default function GuideBar({
  current,
  running,
  pending,
  onStep,
}: {
  current: Step;
  running: boolean;
  pending: number;
  onStep: (s: Step) => void;
}) {
  const steps: { n: Step; title: string; hint: string }[] = [
    { n: 1, title: "Pick a ticket", hint: "Click a ticket card on the right" },
    {
      n: 2,
      title: running ? "The team is working" : "Send the team in",
      hint: running ? "Watch the agents on the left" : "Click the green “Send the team in” button on the left",
    },
    {
      n: 3,
      title: "Approve what they queue",
      hint: pending > 0 ? `${pending} waiting — type your name, then click Approve` : "Nothing waiting right now",
    },
  ];
  return (
    <nav className="guide" aria-label="How to use the desk">
      {steps.map((s) => (
        <button
          key={s.n}
          className={`guide-step ${current === s.n ? "is-now" : current > s.n ? "is-done" : ""} ${s.n === 3 && pending > 0 ? "has-pending" : ""}`}
          onClick={() => onStep(s.n)}
        >
          <span className="guide-num">{current > s.n ? "✓" : s.n}</span>
          <span className="guide-text">
            <strong>{s.title}</strong>
            <small>{s.hint}</small>
          </span>
          {current === s.n && <span className="guide-now">You are here</span>}
        </button>
      ))}
    </nav>
  );
}
