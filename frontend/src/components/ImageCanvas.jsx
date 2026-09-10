import { useState } from "react";
import { motion } from "framer-motion";
import CompareSlider from "./CompareSlider";
import "./ImageCanvas.css";

const SPRING = { stiffness: 300, damping: 25 };

function ScanSweep() {
  return (
    <motion.div
      className="scan-sweep"
      initial={{ top: "-10%" }}
      animate={{ top: "110%" }}
      transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
    />
  );
}

export default function ImageCanvas({ previews, pairType, overlayDataUri, loading }) {
  const [showOverlay, setShowOverlay] = useState(true);
  const isPair = previews.length === 2;

  const labels =
    pairType === "bi_temporal"
      ? ["Before", "After"]
      : pairType === "cross_modal"
        ? ["Optical", "SAR"]
        : null;

  return (
    <div className="image-canvas panel">
      <div className="image-canvas-header">
        {overlayDataUri ? (
          <button
            type="button"
            className={`btn btn-ghost overlay-toggle ${showOverlay ? "overlay-toggle-active" : ""}`}
            onClick={() => setShowOverlay((s) => !s)}
          >
            <span className={`status-dot ${showOverlay ? "ok" : "pending"}`} />
            {showOverlay ? "Hide overlay" : "Show overlay"}
          </button>
        ) : (
          <span className="faint">No analysis run yet</span>
        )}
      </div>

      <div className="image-canvas-body">
        {isPair ? (
          <CompareSlider before={previews[0]} after={previews[1]} labels={labels} />
        ) : (
          <div className="single-image-view">
            <img src={previews[0]} alt="scene" className="compare-img" />
          </div>
        )}

        {overlayDataUri && showOverlay && (
          <motion.img
            key={overlayDataUri}
            src={overlayDataUri}
            alt="analysis overlay"
            className="analysis-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.92 }}
            transition={{ type: "spring", ...SPRING }}
          />
        )}

        {loading && <ScanSweep />}
      </div>
    </div>
  );
}
