// In production this must point at the deployed backend, set via
// VITE_API_BASE_URL at build time — never hardcode a localhost URL into
// the shipped bundle. Falls back to local dev only when unset.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8811";

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`health check failed: ${res.status}`);
  return res.json();
}

export async function createSession({
  image1,
  modality1,
  image2,
  modality2,
  pairType,
}) {
  const form = new FormData();
  form.append("image_1", image1);
  form.append("modality_1", modality1);
  if (image2) {
    form.append("image_2", image2);
    form.append("modality_2", modality2);
    form.append("pair_type", pairType);
  }

  const res = await fetch(`${BASE_URL}/api/session`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `session creation failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchSamples() {
  const res = await fetch(`${BASE_URL}/api/samples`);
  if (!res.ok) throw new Error(`sample catalog fetch failed: ${res.status}`);
  return res.json();
}

export async function createSessionFromSample(sampleId) {
  const res = await fetch(`${BASE_URL}/api/session/sample`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample_id: sampleId }),
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `sample session creation failed: ${res.status}`);
  }
  return res.json();
}

export async function submitQuery(sessionId, question) {
  const res = await fetch(`${BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question }),
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `query failed: ${res.status}`);
  }
  return res.json();
}

async function safeDetail(res) {
  try {
    const body = await res.json();
    return body.detail;
  } catch {
    return null;
  }
}

export { BASE_URL };
