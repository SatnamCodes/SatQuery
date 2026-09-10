import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import GlobeScene from "./GlobeScene";
import StaticGlobeFallback from "./StaticGlobeFallback";
import { isWebGLAvailable } from "../lib/webgl";
import "./Hero.css";

gsap.registerPlugin(ScrollTrigger);

export default function Hero({ onLaunch }) {
  const sectionRef = useRef(null);
  const stickyRef = useRef(null);
  const copyRef = useRef(null);
  const progressRef = useRef(0);
  const [webglOk, setWebglOk] = useState(true);
  const [heroVisible, setHeroVisible] = useState(true);

  useEffect(() => {
    setWebglOk(isWebGLAvailable());
  }, []);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setHeroVisible(entry.isIntersecting),
      { threshold: 0 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const trigger = ScrollTrigger.create({
        trigger: sectionRef.current,
        start: "top top",
        end: "bottom top",
        scrub: 1,
        pin: stickyRef.current,
        onUpdate: (self) => {
          progressRef.current = self.progress;
          gsap.set(copyRef.current, {
            opacity: self.progress < 0.6 ? 1 : 1 - (self.progress - 0.6) / 0.4,
            y: self.progress * -60,
          });
        },
      });
      return () => trigger.kill();
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section className="hero-section" ref={sectionRef}>
      <div className="hero-sticky" ref={stickyRef}>
        <div className="hero-canvas-wrap">
          {webglOk ? (
            <GlobeScene progressRef={progressRef} active={heroVisible} />
          ) : (
            <StaticGlobeFallback />
          )}
        </div>

        <div className="hero-copy" ref={copyRef}>
          <h1 className="hero-headline">
            An officer waiting hours for a GIS analyst.
            <br />
            Now waiting seconds.
          </h1>
          <p className="hero-subhead">
            SatQuery AI answers remote-sensing questions with a documented trail, even offline.
          </p>
          <button type="button" className="hero-cta" onClick={onLaunch}>
            Launch console
          </button>
        </div>
      </div>
    </section>
  );
}
