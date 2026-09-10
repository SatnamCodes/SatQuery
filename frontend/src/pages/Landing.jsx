import Hero from "../components/Hero";
import Reveal from "../components/Reveal";
import CompareSlider from "../components/CompareSlider";
import DemoStopwatch from "../components/DemoStopwatch";
import HoverPreview from "../components/HoverPreview";
import useLenis from "../lib/useLenis";
import demoBefore from "../assets/previews/landing_demo_before.png";
import demoAfter from "../assets/previews/landing_demo_after.png";
import previewVqa from "../assets/previews/vqa.png";
import previewChange from "../assets/previews/change_detection.png";
import previewGrounding from "../assets/previews/grounding.png";
import previewFusion from "../assets/previews/fusion.png";
import "./Landing.css";

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
            <CompareSlider before={demoBefore} after={demoAfter} labels={["Before", "After"]} />
          </div>
          <div className="landing-demo-footer">
            <DemoStopwatch />
            <span className="faint landing-demo-caption">
              Real Sentinel-1 BigEarthNet patches — 24.2% measured change, amber boxes and red heat wash from our own pipeline
            </span>
          </div>
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
          <HoverPreview items={REPRESENTATIVE_QUERIES} />
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
        <button type="button" className="landing-final-cta-btn" onClick={onLaunch}>
          Launch console
        </button>
      </Reveal>
    </div>
  );
}
