import { motion } from "framer-motion";
import "./Header.css";

function shortId(id) {
  if (!id) return null;
  return id.split("-")[0];
}

export default function Header({ session }) {
  return (
    <header className="hdr">
      <div className="hdr-wordmark">
        <span className="hdr-wordmark-main">SatQuery</span>
        <span className="hdr-wordmark-sub">Remote-sensing console</span>
      </div>

      {session && (
        <motion.div
          className="hdr-session"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
        >
          <span className="hdr-session-field">
            <span className="faint">Session</span>
            <span className="hdr-session-id mono">{shortId(session.session_id)}</span>
          </span>
          <span className="hdr-session-field">
            <span className="faint">Pair</span>
            <span>{session.pair_type ?? "single"}</span>
          </span>
          <span className="hdr-session-field">
            <span className="faint">Modality</span>
            <span>{session.modalities.join(" + ")}</span>
          </span>
        </motion.div>
      )}
    </header>
  );
}
