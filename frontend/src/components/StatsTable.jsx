import { motion } from "framer-motion";
import "./StatsTable.css";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};

const cell = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 25 } },
};

function pct(n) {
  return typeof n === "number" ? `${n.toFixed(1)}%` : "—";
}

function buildCells(task, stats) {
  if (!stats) return [];

  if (task === "caption" && stats.coverage_percent) {
    const c = stats.coverage_percent;
    return [
      { emoji: "💧", label: "Water", value: pct(c.water) },
      { emoji: "🌳", label: "Vegetation", value: pct(c.vegetation) },
      { emoji: "🏙️", label: "Built-up", value: pct(c.built_up) },
    ];
  }

  if (task === "change_detection") {
    return [
      { emoji: "🔄", label: "Change", value: pct(stats.change_percent) },
      { emoji: "📍", label: "Regions", value: String(stats.region_count ?? "—") },
      { emoji: "🎚️", label: "Otsu threshold", value: String(stats.otsu_threshold ?? "—") },
    ];
  }

  if (task === "optical_sar_fusion" && stats.stats) {
    const s = stats.stats;
    return [
      { emoji: "💧", label: "Water · agreed", value: pct(s.water?.high_confidence_percent) },
      { emoji: "🌊", label: "Water · possible", value: pct(s.water?.possible_percent) },
      { emoji: "🏙️", label: "Built-up · agreed", value: pct(s.built_up?.high_confidence_percent) },
      { emoji: "🏗️", label: "Built-up · possible", value: pct(s.built_up?.possible_percent) },
    ];
  }

  if (task === "grounding") {
    return [
      { emoji: stats.matched ? "🎯" : "❌", label: "Matched", value: stats.matched ? "Yes" : "No" },
      { emoji: "🏷️", label: "Category", value: stats.category ?? "—" },
      {
        emoji: "📦",
        label: "Bounding box",
        value: stats.bbox ? `${stats.bbox.width}×${stats.bbox.height}px @ (${stats.bbox.x}, ${stats.bbox.y})` : "—",
      },
    ];
  }

  return [];
}

export default function StatsTable({ task, stats }) {
  const cells = buildCells(task, stats);
  if (cells.length === 0) return null;

  return (
    <motion.div className="stats-table panel" variants={container} initial="hidden" animate="show">
      <span className="faint stats-table-label">Measured stats</span>
      <div className="stats-table-row">
        {cells.map((c) => (
          <motion.div className="stats-cell" key={c.label} variants={cell}>
            <span className="stats-cell-emoji" aria-hidden="true">{c.emoji}</span>
            <span className="stats-cell-value mono">{c.value}</span>
            <span className="faint stats-cell-label">{c.label}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
