const API_URL = process.env.SLATE_API_URL ?? "http://localhost:8000";

interface VerdictSummary {
  id: string;
  shot_id: string;
  final_status: string;
  has_panel_review: boolean;
  submitted_at: string;
}

interface VerdictDetail extends VerdictSummary {
  payload: Record<string, unknown>;
}

type ApiParser<T> = (value: unknown) => T;

const E2E_FIXTURE_ENABLED = process.env.SLATE_E2E_API_FIXTURE === "true";
const E2E_TOKEN = "e2e-token";
const E2E_VERDICT: VerdictDetail = {
  id: "e2e-verdict-1",
  shot_id: "village_walk_001",
  final_status: "PANEL_BLOCKED",
  has_panel_review: true,
  submitted_at: "2026-06-18T10:00:00Z",
  payload: {
    panel: {
      per_persona: [
        {
          name: "animator",
          publish_ready: false,
          summary: "Motion risk found.",
          flags: [
            {
              severity: "critical",
              frame: "frame_0005.png",
              description: "Foot sliding survives the sampled frame review.",
            },
          ],
          response_quality: {
            mode: "red_team",
            facts: ["Animator persona reviewed sampled frames."],
            assumptions: ["The manifest context is accurate."],
            unknowns: ["Unsampled frames were not reviewed."],
            confidence_score: 0.76,
            evidence: ["frame_0005.png persona flag"],
            risks: ["Motion defects may survive between samples."],
            counterarguments: ["The slide may be less visible at full speed."],
            recommendation: "Block publish until the motion issue is reviewed.",
            tradeoffs: ["Blocking improves quality but slows delivery."],
            what_would_change_recommendation: [
              "Full-speed review shows the motion reads correctly.",
            ],
          },
        },
      ],
      response_quality: {
        mode: "evidence_based",
        facts: ["Panel recorded one critical animator flag."],
        assumptions: ["Sampled frames represent the shot."],
        unknowns: ["Unsampled frames were not reviewed."],
        confidence_score: 0.82,
        evidence: ["animator critical flag on frame_0005.png"],
        risks: ["The issue could be intentional stylization."],
        counterarguments: ["The motion may read correctly at full speed."],
        recommendation: "Block publish until motion is reviewed.",
        tradeoffs: ["Blocking protects quality but slows delivery."],
        what_would_change_recommendation: [
          "Full-speed review shows the slide is not visible.",
        ],
      },
    },
    response_quality: {
      mode: "evidence_based",
      facts: ["Enhanced final status is PANEL_BLOCKED."],
      assumptions: ["Uploaded verdict JSON is authentic."],
      unknowns: ["Frame bytes were not uploaded to Slate Cloud."],
      confidence_score: 0.82,
      evidence: ["panel.response_quality", "animator persona flag"],
      risks: ["Uploaded metadata could omit source evidence."],
      counterarguments: ["A local evidence bundle may support the verdict."],
      recommendation: "Review the source evidence before publishing.",
      tradeoffs: ["Strict review adds time but protects quality."],
      what_would_change_recommendation: [
        "A source bundle proves the flagged motion is acceptable.",
      ],
    },
  },
};

async function authedFetch<T>(
  token: string,
  path: string,
  parser: ApiParser<T>,
): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return parser(await res.json());
}

export async function listVerdicts(token: string): Promise<VerdictSummary[]> {
  if (isE2EFixtureRequest(token)) {
    const { payload: _payload, ...summary } = E2E_VERDICT;
    return [summary];
  }
  return (await authedFetch(token, "/verdicts", parseVerdictList)) ?? [];
}

export async function getVerdict(
  token: string,
  id: string,
): Promise<VerdictDetail | null> {
  if (isE2EFixtureRequest(token)) {
    return id === E2E_VERDICT.id ? E2E_VERDICT : null;
  }
  return await authedFetch(token, `/verdicts/${id}`, parseVerdictDetail);
}

export interface AccountInfo {
  id: string;
  email: string;
  verdict_count: number;
}

export async function getAccount(token: string): Promise<AccountInfo | null> {
  if (isE2EFixtureRequest(token)) {
    return { id: "e2e-account", email: "e2e@example.com", verdict_count: 1 };
  }
  return await authedFetch(token, "/account", parseAccountInfo);
}

function isE2EFixtureRequest(token: string): boolean {
  return E2E_FIXTURE_ENABLED && token === E2E_TOKEN;
}

function parseVerdictList(value: unknown): VerdictSummary[] {
  if (!Array.isArray(value)) throw new Error("API returned invalid verdict list");
  return value.map(parseVerdictSummary);
}

function parseVerdictDetail(value: unknown): VerdictDetail {
  const summary = parseVerdictSummary(value);
  if (!isRecord(value)) throw new Error("API returned invalid verdict detail");
  return {
    ...summary,
    payload: isRecord(value.payload) ? value.payload : {},
  };
}

function parseVerdictSummary(value: unknown): VerdictSummary {
  if (!isRecord(value)) throw new Error("API returned invalid verdict summary");
  const id = readString(value, "id");
  const shotId = readString(value, "shot_id");
  const finalStatus = readString(value, "final_status");
  const submittedAt = readString(value, "submitted_at");
  const hasPanelReview = value.has_panel_review;
  if (typeof hasPanelReview !== "boolean") {
    throw new Error("API returned invalid verdict summary: has_panel_review");
  }
  return {
    id,
    shot_id: shotId,
    final_status: finalStatus,
    has_panel_review: hasPanelReview,
    submitted_at: submittedAt,
  };
}

function parseAccountInfo(value: unknown): AccountInfo {
  if (!isRecord(value)) throw new Error("API returned invalid account info");
  const verdictCount = value.verdict_count;
  if (typeof verdictCount !== "number") {
    throw new Error("API returned invalid account info: verdict_count");
  }
  return {
    id: readString(value, "id"),
    email: readString(value, "email"),
    verdict_count: verdictCount,
  };
}

function readString(value: Record<string, unknown>, key: string): string {
  const item = value[key];
  if (typeof item !== "string") {
    throw new Error(`API returned invalid string field: ${key}`);
  }
  return item;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
