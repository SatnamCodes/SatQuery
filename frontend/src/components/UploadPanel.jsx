import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BASE_URL, createSession, createSessionFromSample, fetchSamples } from "../api";
import "./UploadPanel.css";

const SPRING = { type: "spring", stiffness: 300, damping: 25 };

const PAIR_CARDS = [
  {
    id: "single",
    title: "Single image",
    tag: "VQA / Caption / Grounding",
    desc: "One scene. Ask what's in it, describe it, or locate a feature.",
  },
  {
    id: "bi_temporal",
    title: "Bi-temporal pair",
    tag: "Change detection",
    desc: "Two same-sensor images of the same scene, different dates.",
  },
  {
    id: "cross_modal",
    title: "Cross-modal pair",
    tag: "Optical + SAR fusion",
    desc: "One optical image and one SAR image of the same scene.",
  },
];

function Dropzone({ label, file, preview, onFile, accentModality }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  }

  return (
    <div
      className={`dropzone ${dragOver ? "dropzone-over" : ""} ${file ? "dropzone-filled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />
      {preview ? (
        <img src={preview} alt={label} className="dropzone-preview" />
      ) : (
        <div className="dropzone-empty">
          <span className="dropzone-plus">+</span>
          <span className="dropzone-label">{label}</span>
          <span className="faint dropzone-hint">drag &amp; drop or click</span>
        </div>
      )}
      {accentModality && (
        <span className={`dropzone-modality-chip chip-${accentModality}`}>
          {accentModality === "sar" ? "SAR" : "Optical"}
        </span>
      )}
    </div>
  );
}

function ModalityToggle({ value, onChange }) {
  return (
    <div className="modality-toggle">
      {["optical", "sar"].map((m) => (
        <button
          key={m}
          type="button"
          className={`modality-toggle-btn ${value === m ? "active" : ""}`}
          onClick={() => onChange(m)}
        >
          {m === "sar" ? "SAR" : "Optical"}
        </button>
      ))}
    </div>
  );
}

function SampleGallery({ pairType, samples, loadingId, onPick }) {
  const entries = pairType === "single" ? samples.single : samples[pairType] ?? [];
  if (!entries.length) return null;

  return (
    <div className="sample-gallery">
      <span className="faint sample-gallery-label">
        Or load a real sample ({entries.length} from BigEarthNet, VRSBench, RSVQA and EuroSAT)
      </span>
      <div className="sample-gallery-row">
        {entries.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`sample-thumb ${loadingId === s.id ? "sample-thumb-loading" : ""}`}
            title={s.caption || s.source}
            disabled={!!loadingId}
            onClick={() => onPick(s)}
          >
            <img src={`${BASE_URL}${s.thumbnail_url}`} alt={s.caption || s.id} />
            {s.thumbnail_url_2 && <img src={`${BASE_URL}${s.thumbnail_url_2}`} alt="" />}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function UploadPanel({ onSessionCreated }) {
  const [pairType, setPairType] = useState(null);
  const [samples, setSamples] = useState({ single: [], bi_temporal: [], cross_modal: [] });
  const [loadingSampleId, setLoadingSampleId] = useState(null);
  const [image1, setImage1] = useState(null);
  const [preview1, setPreview1] = useState(null);
  const [modality1, setModality1] = useState("optical");
  const [image2, setImage2] = useState(null);
  const [preview2, setPreview2] = useState(null);
  const [modality2, setModality2] = useState("sar");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSamples()
      .then((catalog) => setSamples(catalog))
      .catch(() => {
        // Sample gallery is a bonus affordance; a fetch failure just
        // leaves the manual upload flow as the only path, silently.
      });
  }, []);

  async function handlePickSample(sample) {
    if (loadingSampleId) return;
    setLoadingSampleId(sample.id);
    setError(null);
    try {
      const session = await createSessionFromSample(sample.id);
      const previews = [`${BASE_URL}${sample.thumbnail_url}`];
      if (sample.thumbnail_url_2) previews.push(`${BASE_URL}${sample.thumbnail_url_2}`);
      onSessionCreated(session, {
        pairType: sample.pair_type ?? "single",
        previews,
        modalities: session.modalities,
      });
    } catch (e) {
      setError(e.message || "Loading the sample failed");
    } finally {
      setLoadingSampleId(null);
    }
  }

  function reset(nextPairType) {
    setPairType(nextPairType);
    setImage1(null);
    setPreview1(null);
    setImage2(null);
    setPreview2(null);
    setModality1("optical");
    setModality2("sar");
    setError(null);
  }

  function pickFile(which, file) {
    const url = URL.createObjectURL(file);
    if (which === 1) {
      setImage1(file);
      setPreview1(url);
    } else {
      setImage2(file);
      setPreview2(url);
    }
  }

  const ready =
    pairType === "single"
      ? !!image1
      : pairType === "bi_temporal"
        ? !!image1 && !!image2
        : pairType === "cross_modal"
          ? !!image1 && !!image2
          : false;

  async function handleSubmit() {
    if (!ready || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const params =
        pairType === "single"
          ? { image1, modality1 }
          : pairType === "bi_temporal"
            ? { image1, modality1, image2, modality2: modality1, pairType: "bi_temporal" }
            : { image1, modality1: "optical", image2, modality2: "sar", pairType: "cross_modal" };

      const session = await createSession(params);
      onSessionCreated(session, {
        pairType,
        previews: [preview1, preview2].filter(Boolean),
        modalities: pairType === "cross_modal" ? ["optical", "sar"] : [modality1, modality1].slice(0, image2 ? 2 : 1),
      });
    } catch (e) {
      setError(e.message || "Session creation failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="upload-panel">
      <div className="upload-intro">
        <h1>Start an analysis session</h1>
        <p className="dim">
          Select an input configuration, upload imagery, and hand off to the
          orchestrator. No GIS training required.
        </p>
      </div>

      <div className="pair-cards">
        {PAIR_CARDS.map((card) => (
          <button
            key={card.id}
            type="button"
            className={`pair-card panel ${pairType === card.id ? "pair-card-active" : ""}`}
            onClick={() => reset(card.id)}
          >
            <span className="pair-card-tag">{card.tag}</span>
            <span className="pair-card-title">{card.title}</span>
            <span className="pair-card-desc dim">{card.desc}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {pairType && (
          <motion.div
            key={pairType}
            className="upload-body panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={SPRING}
          >
            {pairType === "single" && (
              <div className="upload-row">
                <div className="upload-slot">
                  <Dropzone label="Image" file={image1} preview={preview1} onFile={(f) => pickFile(1, f)} />
                  <ModalityToggle value={modality1} onChange={setModality1} />
                </div>
              </div>
            )}

            {pairType === "bi_temporal" && (
              <>
                <div className="upload-row">
                  <div className="upload-slot">
                    <Dropzone label="Before" file={image1} preview={preview1} onFile={(f) => pickFile(1, f)} />
                  </div>
                  <div className="upload-slot">
                    <Dropzone label="After" file={image2} preview={preview2} onFile={(f) => pickFile(2, f)} />
                  </div>
                </div>
                <div className="upload-shared-modality">
                  <span className="faint">Sensor (same for both)</span>
                  <ModalityToggle value={modality1} onChange={setModality1} />
                </div>
              </>
            )}

            {pairType === "cross_modal" && (
              <div className="upload-row">
                <div className="upload-slot">
                  <Dropzone
                    label="Optical"
                    file={image1}
                    preview={preview1}
                    onFile={(f) => pickFile(1, f)}
                    accentModality="optical"
                  />
                </div>
                <div className="upload-slot">
                  <Dropzone
                    label="SAR"
                    file={image2}
                    preview={preview2}
                    onFile={(f) => pickFile(2, f)}
                    accentModality="sar"
                  />
                </div>
              </div>
            )}

            <SampleGallery
              pairType={pairType}
              samples={samples}
              loadingId={loadingSampleId}
              onPick={handlePickSample}
            />

            {error && <div className="upload-error">{error}</div>}

            <motion.button
              type="button"
              className="btn btn-accent upload-submit"
              disabled={!ready || submitting}
              whileTap={{ scale: 0.97 }}
              transition={SPRING}
              onClick={handleSubmit}
            >
              {submitting ? "Establishing session…" : "Establish session"}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
