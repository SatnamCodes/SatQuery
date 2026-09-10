import { useRef, useState } from "react";
import { motion } from "framer-motion";

const TARGET_SECONDS = 8.2;
const DURATION_MS = 1100;

export default function DemoStopwatch() {
  const [value, setValue] = useState(0);
  const [done, setDone] = useState(false);
  const rafRef = useRef(null);
  const startedRef = useRef(false);

  function start() {
    if (startedRef.current) return;
    startedRef.current = true;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / DURATION_MS);
      setValue(p * TARGET_SECONDS);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setDone(true);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
  }

  return (
    <motion.div
      className="demo-stopwatch"
      onViewportEnter={start}
      viewport={{ once: true, amount: 0.6 }}
    >
      <span className="mono demo-stopwatch-value">{value.toFixed(1)}s</span>
      <span className="faint demo-stopwatch-label">
        {done ? "answer delivered" : "analyzing…"}
      </span>
    </motion.div>
  );
}
