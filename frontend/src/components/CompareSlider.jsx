import { useEffect, useRef, useState } from "react";
import { animate, motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import "./CompareSlider.css";

const SPRING = { stiffness: 300, damping: 25 };
const RESUME_DELAY_MS = 2600;

export default function CompareSlider({ before, after, labels, autoPlay = false }) {
  const containerRef = useRef(null);
  const rawPercent = useMotionValue(50);
  const percent = useSpring(rawPercent, SPRING);
  const clipPath = useTransform(percent, (p) => `inset(0 ${100 - p}% 0 0)`);
  const handleLeft = useTransform(percent, (p) => `${p}%`);
  const [dragging, setDragging] = useState(false);
  const [paused, setPaused] = useState(false);
  const resumeTimerRef = useRef(null);

  useEffect(() => {
    if (!autoPlay || paused) return undefined;
    const controls = animate(rawPercent, [rawPercent.get(), 80, 20, 50], {
      duration: 11,
      ease: "easeInOut",
      repeat: Infinity,
    });
    return () => controls.stop();
  }, [autoPlay, paused, rawPercent]);

  useEffect(() => () => window.clearTimeout(resumeTimerRef.current), []);

  function updateFromClientX(clientX) {
    const rect = containerRef.current.getBoundingClientRect();
    const p = ((clientX - rect.left) / rect.width) * 100;
    rawPercent.set(Math.min(100, Math.max(0, p)));
  }

  function onPointerDown(e) {
    setDragging(true);
    setPaused(true);
    window.clearTimeout(resumeTimerRef.current);
    updateFromClientX(e.clientX);
    e.target.setPointerCapture?.(e.pointerId);
  }

  function onPointerMove(e) {
    if (!dragging) return;
    updateFromClientX(e.clientX);
  }

  function endDrag() {
    setDragging(false);
    if (!autoPlay) return;
    window.clearTimeout(resumeTimerRef.current);
    resumeTimerRef.current = window.setTimeout(() => setPaused(false), RESUME_DELAY_MS);
  }

  return (
    <div
      className="compare-slider"
      ref={containerRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerLeave={endDrag}
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
