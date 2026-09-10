import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import "./DiracMosaic.css";

const SPRING = { type: "spring", stiffness: 320, damping: 20 };
const CYCLE_MS = 900;

// 5x7 dot-matrix bitmaps, one string per row ("1" = filled cell).
const LETTERS = {
  D: ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
  I: ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
  R: ["11100", "10010", "10010", "11100", "10100", "10010", "10001"],
  A: ["00100", "01010", "10001", "10001", "11111", "10001", "10001"],
  C: ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
};
const WORD = ["D", "I", "R", "A", "C"];
const ROWS = 7;

function buildGrid() {
  const grid = Array.from({ length: ROWS }, () => []);
  WORD.forEach((letter, li) => {
    const bitmap = LETTERS[letter];
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < 5; c++) {
        grid[r].push(bitmap[r][c] === "1");
      }
      if (li < WORD.length - 1) grid[r].push(false);
    }
  });
  return grid;
}

const GRID = buildGrid();
const COLS = GRID[0].length;
const ON_CELLS = GRID.flatMap((row, r) => row.map((on, c) => ({ r, c, on })).filter((cell) => cell.on));

export default function DiracMosaic({ items }) {
  const [tick, setTick] = useState(0);
  const [hovered, setHovered] = useState(null);

  useEffect(() => {
    if (items.length < 2) return undefined;
    const id = window.setInterval(() => setTick((t) => t + 1), CYCLE_MS);
    return () => window.clearInterval(id);
  }, [items.length]);

  return (
    <div className="dirac-mosaic-wrap">
      <div
        className="dirac-mosaic"
        style={{ gridTemplateColumns: `repeat(${COLS}, 1fr)`, gridTemplateRows: `repeat(${ROWS}, 1fr)` }}
      >
        {GRID.flatMap((row, r) =>
          row.map((on, c) => {
            const key = `${r}-${c}`;
            if (!on) {
              return <div key={key} className="dirac-cell" style={{ gridRow: r + 1, gridColumn: c + 1 }} />;
            }
            const onIndex = ON_CELLS.findIndex((cell) => cell.r === r && cell.c === c);
            const item = items[(onIndex + tick) % items.length];
            return (
              <motion.button
                key={key}
                type="button"
                className="dirac-cell dirac-cell-on"
                style={{ gridRow: r + 1, gridColumn: c + 1 }}
                whileHover={{ scale: 1.5, zIndex: 6 }}
                transition={SPRING}
                onMouseEnter={() => setHovered(item)}
                onMouseLeave={() => setHovered((h) => (h === item ? null : h))}
                onFocus={() => setHovered(item)}
                onBlur={() => setHovered((h) => (h === item ? null : h))}
              >
                <AnimatePresence initial={false}>
                  <motion.img
                    key={item.id ?? item.image}
                    src={item.image}
                    alt={item.label}
                    loading="lazy"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.85 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.35 }}
                  />
                </AnimatePresence>
              </motion.button>
            );
          }),
        )}
      </div>

      <div className="dirac-preview panel">
        {hovered ? (
          <>
            <img src={hovered.image} alt={hovered.label} className="dirac-preview-image" />
            <div className="dirac-preview-body">
              <span className="dirac-preview-tool faint mono">{hovered.tool}</span>
              <p className="dirac-preview-label">{hovered.label}</p>
            </div>
          </>
        ) : (
          <div className="dirac-preview-empty faint">Hover a tile to see the real result behind it.</div>
        )}
      </div>
    </div>
  );
}
