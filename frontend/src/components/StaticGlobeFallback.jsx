export default function StaticGlobeFallback() {
  return (
    <div className="static-globe-fallback">
      <svg viewBox="0 0 400 400" className="static-globe-svg" aria-hidden="true">
        <circle cx="200" cy="200" r="170" fill="none" stroke="#b0aea5" strokeOpacity="0.6" strokeWidth="1" />
        <ellipse cx="200" cy="200" rx="170" ry="60" fill="none" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
        <ellipse cx="200" cy="200" rx="170" ry="110" fill="none" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
        <ellipse cx="200" cy="200" rx="60" ry="170" fill="none" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
        <ellipse cx="200" cy="200" rx="110" ry="170" fill="none" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
        <line x1="30" y1="200" x2="370" y2="200" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
        <line x1="200" y1="30" x2="200" y2="370" stroke="#b0aea5" strokeOpacity="0.4" strokeWidth="1" />
      </svg>
    </div>
  );
}
