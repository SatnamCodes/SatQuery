import { useEffect, useMemo, useState } from "react";
import Hero from "../components/Hero";
import LaunchButton from "../components/LaunchButton";
import Reveal from "../components/Reveal";
import CompareSlider from "../components/CompareSlider";
import DemoStopwatch from "../components/DemoStopwatch";
import DiracMosaic from "../components/DiracMosaic";
import useLenis from "../lib/useLenis";
import { BASE_URL, fetchSamples } from "../api";
import demoBefore from "../assets/previews/landing_demo_before.png";
import demoAfter from "../assets/previews/landing_demo_after.png";
import previewVqa from "../assets/previews/vqa.png";
import previewChange from "../assets/previews/change_detection.png";
import previewGrounding from "../assets/previews/grounding.png";
import previewFusion from "../assets/previews/fusion.png";
import "./Landing.css";

const STATIC_DEMO_EXAMPLE = {
  before: demoBefore,
  after: demoAfter,
  caption:
    "Real Sentinel-1 BigEarthNet patches — 24.2% measured change, amber boxes and red heat wash from our own pipeline",
};

const REPRESENTATIVE_QUERIES = [
  {
    id: "vqa",
    label: "What kind of land cover is shown in this scene?",
    tool: "VQA — real EuroSAT Sentinel-2 chip",
    image: previewVqa,
  },
  {
    id: "change",
    label: "What changed between these two dates, and where did the change occur?",
    tool: "Change detection — real BigEarthNet Sentinel-1 pair",
    image: previewChange,
  },
  {
    id: "grounding",
    label: "Where is the vegetation in this image?",
    tool: "Grounding — real EuroSAT Sentinel-2 chip",
    image: previewGrounding,
  },
  {
    id: "fusion",
    label: "Where does optical and SAR agree there's built-up area?",
    tool: "Optical + SAR fusion — real BigEarthNet/EuroSAT pair",
    image: previewFusion,
  },
];

const EXTRA_MOSAIC_QUERIES = [
  {
    id: "demo-before",
    label: "Before: the same scene ahead of the measured change.",
    tool: "Bi-temporal — real BigEarthNet Sentinel-1 patch",
    image: demoBefore,
  },
  {
    id: "demo-after",
    label: "After: 24.2% of the area measured as changed.",
    tool: "Bi-temporal — real BigEarthNet Sentinel-1 patch",
    image: demoAfter,
  },
];

const AUDIT_CALLOUTS = [
  {
    title: "Input validation",
    detail: "2 images received, both Sentinel-1, requirements for change detection satisfied",
  },
  {
    title: "Task classification",
    detail: 'question matched keywords for "change_detection", not a guess — the same classifier runs on every query',
  },
  {
    title: "Confidence",
    detail: "91%, because the grayscale-diff mask and the Otsu-thresholded contours agree on region bounds",
  },
];

const OFFLINE_ROWS = [
  { label: "Change detection (grayscale diff, Otsu threshold, contours)", ok: true },
  { label: "Land-cover segmentation (HSV heuristics for water, vegetation, built-up)", ok: true },
  { label: "Optical + SAR fusion (backscatter thresholds, no trained model)", ok: true },
  { label: "Visual grounding (keyword-to-region lookup)", ok: true },
  { label: "Natural-language narration (calls the Gemini API)", ok: false },
];

export default function Landing({ onLaunch }) {
  useLenis();

  const [biTemporalSamples, setBiTemporalSamples] = useState([]);
  const [singleSamples, setSingleSamples] = useState([]);
  const [demoIndex, setDemoIndex] = useState(0);

  useEffect(() => {
    fetchSamples()
      .then((catalog) => {
        setBiTemporalSamples(catalog.bi_temporal || []);
        setSingleSamples(catalog.single || []);
      })
      .catch(() => {
        // Landing page has to work without a live backend — the static
        // bundled examples below stay as the fallback.
      });
  }, []);

  const demoExamples = useMemo(() => {
    const fromBackend = biTemporalSamples.slice(0, 3).map((s) => ({
      before: `${BASE_URL}${s.thumbnail_url}`,
      after: `${BASE_URL}${s.thumbnail_url_2}`,
      caption: s.caption,
    }));
    return [STATIC_DEMO_EXAMPLE, ...fromBackend];
  }, [biTemporalSamples]);

  const activeDemo = demoExamples[demoIndex] ?? demoExamples[0];

  const mosaicItems = useMemo(() => {
    const fromBackend = singleSamples.slice(0, 8).map((s) => ({
      id: s.id,
      image: `${BASE_URL}${s.thumbnail_url}`,
      label: s.caption || s.source,
      tool: s.source,
    }));
    return [...REPRESENTATIVE_QUERIES, ...EXTRA_MOSAIC_QUERIES, ...fromBackend];
  }, [singleSamples]);

  return (
    <div className="landing">
      <Hero onLaunch={onLaunch} />

      <section className="landing-section">
        <Reveal className="landing-section-head">
          <span className="faint landing-eyebrow">Bi-temporal comparison</span>
          <h2 className="landing-heading">
            A field officer drags a slider instead of opening a GIS desktop.
          </h2>
        </Reveal>
        <Reveal delay={0.08} className="landing-demo-slider-wrap">
          <div className="landing-demo-slider panel">
            <CompareSlider
              key={demoIndex}
              before={activeDemo.before}
              after={activeDemo.after}
              labels={["Before", "After"]}
              autoPlay
            />
          </div>
          <div className="landing-demo-footer">
            <DemoStopwatch />
            <span className="faint landing-demo-caption">{activeDemo.caption}</span>
          </div>
          {demoExamples.length > 1 && (
            <div className="landing-demo-tabs">
              {demoExamples.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  className={`landing-demo-tab ${i === demoIndex ? "active" : ""}`}
                  onClick={() => setDemoIndex(i)}
                  aria-label={`Example ${i + 1}`}
                />
              ))}
            </div>
          )}
        </Reveal>
      </section>

      <section className="landing-section">
        <Reveal className="landing-section-head">
          <span className="faint landing-eyebrow">Audit trail</span>
          <h2 className="landing-heading">
            Every answer names the exact steps that produced it.
          </h2>
        </Reveal>
        <div className="landing-audit-recreation">
          {AUDIT_CALLOUTS.map((c, i) => (
            <Reveal key={c.title} delay={i * 0.08} className="landing-audit-callout panel">
              <span className="status-dot ok" />
              <div>
                <div className="landing-audit-title">{c.title}</div>
                <div className="dim landing-audit-detail">{c.detail}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <Reveal className="landing-section-head">
          <span className="faint landing-eyebrow">Representative queries</span>
          <h2 className="landing-heading">One question, one tool, one real answer.</h2>
        </Reveal>
        <Reveal delay={0.08}>
          <DiracMosaic items={mosaicItems} />
        </Reveal>
      </section>

      <section className="landing-section">
        <Reveal className="landing-section-head">
          <span className="faint landing-eyebrow">Field-ready</span>
          <h2 className="landing-heading">
            Four of these five tools never leave the device.
          </h2>
        </Reveal>
        <Reveal delay={0.08} className="offline-row panel">
          {OFFLINE_ROWS.map((r) => (
            <div className="offline-row-item" key={r.label}>
              <span className={`status-dot ${r.ok ? "ok" : "pending"}`} />
              <span className="offline-row-label">{r.label}</span>
              <span className="faint offline-row-tag">
                {r.ok ? "Works offline" : "Needs internet"}
              </span>
            </div>
          ))}
        </Reveal>
      </section>

      <Reveal as="section" className="landing-final-cta">
        <span className="faint">Ready when you are</span>
        <LaunchButton onLaunch={onLaunch} className="launch-btn-lg" />
      </Reveal>
    </div>
  );
}
