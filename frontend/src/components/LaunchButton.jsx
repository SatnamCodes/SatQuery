import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./LaunchButton.css";

const TRANSITION_MS = 650;

export default function LaunchButton({ onLaunch, label = "Launch console", className = "" }) {
  const [launching, setLaunching] = useState(false);

  function handleClick() {
    if (launching) return;
    setLaunching(true);
    window.setTimeout(onLaunch, TRANSITION_MS);
  }

  return (
    <>
      <motion.button
        type="button"
        className={`launch-btn ${className}`}
        onClick={handleClick}
        disabled={launching}
        whileHover={{ y: launching ? 0 : -1 }}
        whileTap={{ scale: 0.97 }}
        transition={{ type: "spring", stiffness: 400, damping: 22 }}
      >
        <span className="launch-btn-label">{launching ? "Opening" : label}</span>
        <span className="launch-btn-arrow" aria-hidden="true">
          →
        </span>
      </motion.button>

      <AnimatePresence>
        {launching && (
          <motion.div
            className="launch-transition"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
