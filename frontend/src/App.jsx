import { useRef, useState } from "react";
import Header from "./components/Header";
import UploadPanel from "./components/UploadPanel";
import ImageCanvas from "./components/ImageCanvas";
import QueryConsole from "./components/QueryConsole";
import Landing from "./pages/Landing";
import { submitQuery } from "./api";
import "./App.css";

let msgId = 0;

export default function App() {
  const [showApp, setShowApp] = useState(false);
  const [session, setSession] = useState(null);
  const [sessionMeta, setSessionMeta] = useState(null); // { pairType, previews, modalities }
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const [frozenMs, setFrozenMs] = useState(0);
  const [overlayDataUri, setOverlayDataUri] = useState(null);
  const startRef = useRef(null);

  function handleSessionCreated(newSession, meta) {
    setSession(newSession);
    setSessionMeta(meta);
    setMessages([]);
    setOverlayDataUri(null);
  }

  async function handleSend(question) {
    if (!session) return;
    const userMsg = { id: ++msgId, role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setPending(true);
    startRef.current = performance.now();

    try {
      const result = await submitQuery(session.session_id, question);
      const elapsed = performance.now() - startRef.current;
      setFrozenMs(elapsed);

      if (result.overlay_png_base64) {
        setOverlayDataUri(`data:image/png;base64,${result.overlay_png_base64}`);
      }

      const assistantMsg = {
        id: ++msgId,
        role: "assistant",
        text: result.answer,
        trace: result.execution_trace,
        stats: result.stats,
        benchmarkReference: result.benchmark_reference,
        question,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      const elapsed = performance.now() - startRef.current;
      setFrozenMs(elapsed);
      setMessages((prev) => [
        ...prev,
        { id: ++msgId, role: "assistant", text: e.message || "Query failed", error: true },
      ]);
    } finally {
      setPending(false);
    }
  }

  if (!showApp) {
    return <Landing onLaunch={() => setShowApp(true)} />;
  }

  return (
    <div className="app-shell">
      <Header session={session} />

      {!session ? (
        <UploadPanel onSessionCreated={handleSessionCreated} />
      ) : (
        <main className="app-main">
          <div className="app-main-left">
            <ImageCanvas
              previews={sessionMeta.previews}
              pairType={sessionMeta.pairType}
              overlayDataUri={overlayDataUri}
              loading={pending}
            />
          </div>
          <div className="app-main-right">
            <QueryConsole
              session={session}
              pairType={sessionMeta.pairType}
              messages={messages}
              pending={pending}
              frozenMs={frozenMs}
              onSend={handleSend}
            />
          </div>
        </main>
      )}
    </div>
  );
}
