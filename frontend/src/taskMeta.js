// Shared metadata for the 5 orchestrator tools, mirrored from the backend
// registry so the console can label pipeline nodes and give a best-effort
// client-side guess of the task while a query is in flight (the real
// classification happens server-side and arrives with the response).

export const TASKS = [
  { id: "vqa", label: "VQA" },
  { id: "caption", label: "Caption" },
  { id: "grounding", label: "Ground" },
  { id: "change_detection", label: "Change" },
  { id: "optical_sar_fusion", label: "Fusion" },
];

const CHANGE_KEYWORDS = [
  "change",
  "differ",
  "compare",
  "before and after",
  "appeared",
  "disappeared",
  "new construction",
  "what changed",
];
const FUSION_KEYWORDS = [
  "fusion",
  "sar",
  "radar",
  "confidence",
  "cross-modal",
  "cross modal",
  "backscatter",
];
const GROUNDING_KEYWORDS = [
  "where",
  "locate",
  "find",
  "point out",
  "show me",
  "which part",
];
const CAPTION_KEYWORDS = [
  "describe",
  "caption",
  "summarize",
  "summarise",
  "what is in this image",
  "what's in this image",
];

export function guessTask(question) {
  const q = question.toLowerCase();
  if (FUSION_KEYWORDS.some((k) => q.includes(k))) return "optical_sar_fusion";
  if (CHANGE_KEYWORDS.some((k) => q.includes(k))) return "change_detection";
  if (GROUNDING_KEYWORDS.some((k) => q.includes(k))) return "grounding";
  if (CAPTION_KEYWORDS.some((k) => q.includes(k))) return "caption";
  return "vqa";
}

export const SUGGESTED_QUERIES = {
  single: [
    "What is in this image?",
    "Where is the water body?",
    "Describe the land cover in this scene.",
  ],
  bi_temporal: [
    "What changed between these two images?",
    "How much area changed?",
    "Is there new construction?",
  ],
  cross_modal: [
    "Run a SAR fusion confidence check on this area.",
    "Where is water confirmed by both sensors?",
    "How confident are you there's built-up area here?",
  ],
};
