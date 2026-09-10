import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import StopwatchMetric from "./StopwatchMetric";
import PipelineVisualizer from "./PipelineVisualizer";
import AuditTrail from "./AuditTrail";
import { SUGGESTED_QUERIES, guessTask } from "../taskMeta";
import "./QueryConsole.css";

const SPRING = { type: "spring", stiffness: 300, damping: 25 };

export default function QueryConsole({
  session,
  pairType,
  messages,
  pending,
  frozenMs,
  onSend,
}) {
  const [input, setInput] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const suggestions = SUGGESTED_QUERIES[pairType] ?? SUGGESTED_QUERIES.single;
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  const guessedTask = pending ? guessTask(input || messages.at(-1)?.text || "") : null;

  function handleSubmit(e) {
    e?.preventDefault();
    const q = input.trim();
    if (!q || pending) return;
    setInput("");
    onSend(q);
  }

  return (
    <div className="query-console">
      <div className="query-console-metrics">
        <StopwatchMetric running={pending} frozenMs={frozenMs} />
        <PipelineVisualizer
          pending={pending}
          guessedTask={guessedTask}
          resolvedTask={lastAssistant?.trace?.task}
          confidence={lastAssistant?.trace?.confidence}
        />
      </div>

      <div className="query-log scrollbar-thin" ref={logRef}>
        {messages.length === 0 && (
          <div className="query-log-empty">
            <span className="faint">
              Session linked. Ask a question about the imagery below to get started.
            </span>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              className={`chat-msg chat-msg-${m.role}`}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={SPRING}
            >
              <div className="chat-msg-meta faint">
                {m.role === "user" ? "Field officer" : "SatQuery"}
              </div>
              <div className="chat-msg-bubble panel">
                {m.error ? <span className="chat-msg-error">{m.text}</span> : m.text}
              </div>
              {m.role === "assistant" && m.benchmarkReference && (
                <div className="benchmark-reference panel">
                  <span className="faint benchmark-reference-label">Benchmark reference answer (CDVQA)</span>
                  <p className="benchmark-reference-text">{m.benchmarkReference}</p>
                </div>
              )}
              {m.role === "assistant" && m.trace && (
                <AuditTrail
                  trace={m.trace}
                  question={m.question}
                  answer={m.text}
                  sessionId={session?.session_id}
                />
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {pending && (
          <motion.div
            className="chat-msg chat-msg-assistant"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING}
          >
            <div className="chat-msg-meta faint">SatQuery</div>
            <div className="chat-msg-bubble panel chat-msg-pending">
              <span className="pending-dot" />
              <span className="pending-dot" />
              <span className="pending-dot" />
            </div>
          </motion.div>
        )}
      </div>

      <div className="query-suggestions">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            className="suggestion-chip"
            disabled={pending}
            onClick={() => onSend(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <form className="query-input-row" onSubmit={handleSubmit}>
        <input
          className="query-input"
          placeholder="Ask about this imagery…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={pending}
        />
        <motion.button
          type="submit"
          className="btn btn-accent"
          whileTap={{ scale: 0.97 }}
          transition={SPRING}
          disabled={pending || !input.trim()}
        >
          Send
        </motion.button>
      </form>
    </div>
  );
}
