export type ReviewMode =
  | "standard"
  | "evidence_based"
  | "red_team"
  | "executive_memo"
  | "technical_review"
  | "legal_risk_review";

export interface ResponseQuality {
  mode?: ReviewMode;
  facts?: string[];
  assumptions?: string[];
  unknowns?: string[];
  confidence_score?: number;
  evidence?: string[];
  risks?: string[];
  counterarguments?: string[];
  recommendation?: string;
  tradeoffs?: string[];
  what_would_change_recommendation?: string[];
}

export const RESPONSE_QUALITY_SECTIONS = [
  "Response mode",
  "Facts",
  "Assumptions",
  "Unknowns",
  "Confidence score",
  "Evidence / citations",
  "Risks",
  "Counterarguments",
  "Recommendation",
  "Tradeoffs",
  "What would change the recommendation",
] as const;

export const REVIEW_MODES: { id: ReviewMode; label: string }[] = [
  { id: "standard", label: "Standard Answer" },
  { id: "evidence_based", label: "Accuracy Mode" },
  { id: "red_team", label: "Red Team Mode" },
  { id: "executive_memo", label: "CEO Review Mode" },
  { id: "technical_review", label: "Technical Review Mode" },
  { id: "legal_risk_review", label: "Legal Risk Review Mode" },
];

export function modeTitle(mode: ReviewMode): string {
  if (mode === "standard") return "Standard answer";
  if (mode === "red_team") return "Hostile red-team review";
  if (mode === "executive_memo") return "Executive decision memo";
  if (mode === "technical_review") return "Technical review";
  if (mode === "legal_risk_review") return "Legal risk review";
  return "Evidence-based answer";
}

export function formatConfidence(value?: number): string {
  if (typeof value !== "number") return "not provided";
  return `${Math.round(value * 100)}%`;
}
