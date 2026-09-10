import { useRef, useState } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import "./CompareSlider.css";

const SPRING = { stiffness: 300, damping: 25 };

export default function CompareSlider({ before, after, labels }) {
  const containerRef = useRef(null);
  const rawPercent = useMotionValue(50);
  const percent = useSpring(rawPercent, SPRING);
  const clipPath = useTransform(percent, (p) => `inset(0 ${100 - p}% 0 0)`);
  const handleLeft = useTransform(percent, (p) => `${p}%`);
  const [dragging, setDragging] = useState(false);

  function updateFromClientX(clientX) {
    const rect = containerRef.current.getBoundingClientRect();
    const p = ((clientX - rect.left) / rect.width) * 100;
    rawPercent.set(Math.min(100, Math.max(0, p)));
  }

  function onPointerDown(e) {
    setDragging(true);
    updateFromClientX(e.clientX);
    e.target.setPointerCapture?.(e.pointerId);
  }

  function onPointerMove(e) {
    if (!dragging) return;
    updateFromClientX(e.clientX);
  }

  return (
    <div
      className="compare-slider"
      ref={containerRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={() => setDragging(false)}
      onPointerLeave={() => setDragging(false)}
    >
      <img src={before} alt={labels?.[0] ?? "before"} className="compare-img compare-img-base" />
      <motion.img
        src={after}
        alt={labels?.[1] ?? "after"}
        className="compare-img compare-img-top"
        style={{ clipPath }}
      />
      <motion.div className="compare-handle" style={{ left: handleLeft }}>
        <div className="compare-handle-line" />
        <div className="compare-handle-grip">⇔</div>
      </motion.div>
      <span className="compare-tag compare-tag-left">{labels?.[0] ?? "Before"}</span>
      <span className="compare-tag compare-tag-right">{labels?.[1] ?? "After"}</span>
    </div>
  );
}
