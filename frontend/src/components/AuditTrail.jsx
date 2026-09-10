import { motion } from "framer-motion";
import jsPDF from "jspdf";
import "./AuditTrail.css";

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.08 },
  },
};

const item = {
  hidden: { opacity: 0, x: -8 },
  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300, damping: 25 } },
};

function buildSteps(trace) {
  if (!trace) return [];
  const steps = [];

  steps.push({
    title: "Input validation",
    detail: trace.input_check?.passed
      ? `${trace.input_check.images_provided} image(s) provided, requirements satisfied${
          trace.input_check.pair_type_required ? ` (pair type: ${trace.input_check.pair_type_provided})` : ""
        }`
      : "requirements not met for the requested tool, degraded to a fallback",
    ok: !!trace.input_check?.passed,
  });

  steps.push({
    title: "Task classification",
    detail: trace.parameters?.degraded_from
      ? `requested "${trace.parameters.degraded_from}", degraded to "${trace.task}"`
      : `classified as "${trace.task}"`,
    ok: true,
  });

  (trace.tools || []).forEach((tool) => {
    steps.push({
      title: "Tool invoked",
      detail: tool,
      ok: true,
    });
  });

  return steps;
}

export function exportAuditPDF({ question, answer, trace, sessionId }) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const marginX = 48;
  let y = 56;

  // Caps stay here deliberately: this is a printed report letterhead, a
  // different convention from the on-screen UI (which uses sentence case).
  doc.setFont("courier", "bold");
  doc.setFontSize(16);
  doc.text("SATQUERY AI - SIGNED ANALYSIS REPORT", marginX, y);
  y += 18;
  doc.setDrawColor(60, 70, 90);
  doc.line(marginX, y, 547, y);
  y += 22;

  doc.setFont("courier", "normal");
  doc.setFontSize(9);
  doc.text(`SESSION ID   : ${sessionId ?? "n/a"}`, marginX, y);
  y += 14;
  doc.text(`GENERATED    : ${new Date().toISOString()}`, marginX, y);
  y += 14;
  doc.text(`TASK         : ${trace?.task ?? "n/a"}`, marginX, y);
  y += 14;
  doc.text(`CONFIDENCE   : ${trace ? Math.round(trace.confidence * 100) + "%" : "n/a"}`, marginX, y);
  y += 22;

  doc.setFont("courier", "bold");
  doc.setFontSize(10);
  doc.text("QUERY", marginX, y);
  y += 14;
  doc.setFont("courier", "normal");
  y = writeWrapped(doc, question || "", marginX, y);
  y += 16;

  doc.setFont("courier", "bold");
  doc.setFontSize(10);
  doc.text("ANSWER", marginX, y);
  y += 14;
  doc.setFont("courier", "normal");
  y = writeWrapped(doc, answer || "", marginX, y);
  y += 16;

  doc.setFont("courier", "bold");
  doc.setFontSize(10);
  doc.text("EXECUTION TRACE", marginX, y);
  y += 14;
  doc.setFont("courier", "normal");
  const traceText = JSON.stringify(trace ?? {}, null, 2);
  y = writeWrapped(doc, traceText, marginX, y, 8);

  doc.setFont("courier", "normal");
  doc.setFontSize(8);
  doc.setTextColor(140, 140, 140);
  doc.text(
    "This report is a machine-generated chain-of-custody record produced by the SatQuery orchestrator.",
    marginX,
    800,
  );

  doc.save(`satquery-report-${(sessionId || "session").slice(0, 8)}.pdf`);
}

function writeWrapped(doc, text, x, y, fontSize = 9) {
  doc.setFontSize(fontSize);
  const lines = doc.splitTextToSize(text, 500);
  for (const line of lines) {
    if (y > 780) {
      doc.addPage();
      y = 56;
    }
    doc.text(line, x, y);
    y += fontSize + 3;
  }
  return y;
}

export default function AuditTrail({ trace, question, answer, sessionId }) {
  const steps = buildSteps(trace);
  const confidencePct = trace ? Math.round(trace.confidence * 100) : 0;

  return (
    <motion.div className="audit-trail panel" variants={container} initial="hidden" animate="show">
      <div className="audit-header">
        <span className="faint">Audit trail</span>
        <button
          type="button"
          className="btn btn-ghost audit-export"
          onClick={() => exportAuditPDF({ question, answer, trace, sessionId })}
        >
          Export signed report (PDF)
        </button>
      </div>

      <div className="audit-timeline">
        {steps.map((s, i) => (
          <motion.div className="audit-step" key={i} variants={item}>
            <div className="audit-step-marker">
              <span className={`status-dot ${s.ok ? "ok" : "danger"}`} />
              {i < steps.length - 1 && <span className="audit-step-line" />}
            </div>
            <div className="audit-step-body">
              <span className="audit-step-title">{s.title}</span>
              <span className="dim audit-step-detail">{s.detail}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <motion.div className="audit-confidence" variants={item}>
        <span className="faint">Confidence</span>
        <div className="confidence-bar-track">
          <motion.div
            className="confidence-bar-fill"
            initial={{ width: 0 }}
            animate={{ width: `${confidencePct}%` }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          />
        </div>
        <span className="mono confidence-value">{confidencePct}%</span>
      </motion.div>
    </motion.div>
  );
}
