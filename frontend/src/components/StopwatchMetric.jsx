import { useEffect, useRef, useState } from "react";
import "./StopwatchMetric.css";

function formatElapsed(ms) {
  const s = ms / 1000;
  return s.toFixed(2);
}

export default function StopwatchMetric({ running, frozenMs }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (running) {
      startRef.current = performance.now();
      const tick = () => {
        setElapsed(performance.now() - startRef.current);
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(rafRef.current);
    }
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
  }, [running]);

  const displayMs = running ? elapsed : (frozenMs ?? 0);

  return (
    <div className="stopwatch panel">
      <div className="stopwatch-row">
        <span className="faint stopwatch-label">Time to answer</span>
        <span className={`status-dot ${running ? "pending stopwatch-live" : "ok"}`} />
      </div>
      <div className="stopwatch-value mono">
        {formatElapsed(displayMs)}
        <span className="stopwatch-unit">s</span>
      </div>
      <div className="stopwatch-compare mono faint">
        manual GIS equivalent: ~2-4 hrs
      </div>
    </div>
  );
}
