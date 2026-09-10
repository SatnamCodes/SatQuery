import { motion } from "framer-motion";
import { TASKS } from "../taskMeta";
import "./PipelineVisualizer.css";

export default function PipelineVisualizer({ pending, guessedTask, resolvedTask, confidence }) {
  return (
    <div className="pipeline panel">
      <span className="faint pipeline-label">Pipeline</span>
      <div className="pipeline-nodes">
        {TASKS.map((t) => {
          const isPendingGuess = pending && guessedTask === t.id;
          const isResolved = !pending && resolvedTask === t.id;
          return (
            <div key={t.id} className="pipeline-node">
              <motion.div
                className={`pipeline-light ${isPendingGuess ? "pipeline-light-pending" : ""} ${
                  isResolved ? "pipeline-light-resolved" : ""
                }`}
                animate={
                  isPendingGuess
                    ? { opacity: [0.35, 1, 0.35] }
                    : { opacity: isResolved ? 1 : 0.35 }
                }
                transition={
                  isPendingGuess
                    ? { duration: 0.9, repeat: Infinity, ease: "easeInOut" }
                    : { type: "spring", stiffness: 300, damping: 25 }
                }
              />
              <span className="pipeline-node-label">{t.label}</span>
              <span className="mono pipeline-node-confidence">
                {isResolved && typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : " "}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
