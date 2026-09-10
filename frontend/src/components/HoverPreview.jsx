import { useRef, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import "./HoverPreview.css";

const SPRING = { stiffness: 220, damping: 26, mass: 0.6 };
const CURSOR_OFFSET = { x: 26, y: 26 };

export default function HoverPreview({ items }) {
  const [active, setActive] = useState(null);
  const [pinned, setPinned] = useState(null); // {x, y} for keyboard focus
  const containerRef = useRef(null);

  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const x = useSpring(rawX, SPRING);
  const y = useSpring(rawY, SPRING);

  function handleMouseMove(e) {
    if (pinned) return;
    rawX.set(e.clientX + CURSOR_OFFSET.x);
    rawY.set(e.clientY + CURSOR_OFFSET.y);
  }

  function handleFocus(item, e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = { x: rect.right + 16, y: rect.top };
    setPinned(pos);
    rawX.set(pos.x);
    rawY.set(pos.y);
    setActive(item);
  }

  function handleBlur() {
    setPinned(null);
    setActive(null);
  }

  const visible = !!active;

  return (
    <div
      className="hover-preview-list"
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        if (!pinned) setActive(null);
      }}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className="hover-preview-item"
          onMouseEnter={() => {
            if (!pinned) setActive(item);
          }}
          onFocus={(e) => handleFocus(item, e)}
          onBlur={handleBlur}
        >
          {item.label}
        </button>
      ))}

      <motion.div
        className="hover-preview-panel"
        style={{ left: x, top: y }}
        initial={false}
        animate={{
          opacity: visible ? 1 : 0,
          scale: visible ? 1 : 0.92,
        }}
        transition={{ type: "spring", stiffness: 260, damping: 24 }}
      >
        {active && (
          <>
            <img src={active.image} alt="" className="hover-preview-image" />
            <span className="hover-preview-caption">{active.tool}</span>
          </>
        )}
      </motion.div>
    </div>
  );
}
