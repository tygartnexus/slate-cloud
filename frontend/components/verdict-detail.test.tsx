import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { VerdictDetail } from "./verdict-detail";

const baseReport = {
  mode: "evidence_based",
  facts: ["One sampled frame was reviewed."],
  assumptions: ["Sampled frames represent the shot."],
  unknowns: ["Unsampled frames were not reviewed."],
  confidence_score: 0.8,
  evidence: ["frame_0001.png"],
  risks: ["The model may miss motion issues."],
  counterarguments: ["The selected frame may be representative."],
  recommendation: "Review the evidence before publishing.",
  tradeoffs: ["More review takes longer."],
  what_would_change_recommendation: ["A full-frame pass finds no blockers."],
} as const;

function renderVerdict(payload: Record<string, unknown>) {
  return render(
    <VerdictDetail
      verdict={{
        id: "v1",
        shot_id: "shot_001",
        final_status: "PASS",
        has_panel_review: Boolean(payload.panel),
        submitted_at: "2026-06-18T10:00:00Z",
        payload,
      }}
    />,
  );
}

describe("VerdictDetail", () => {
  it("shows a missing-mode report as invalid instead of relabeling it", () => {
    renderVerdict({
      status: "PASS",
      response_quality: {
        ...baseReport,
        mode: undefined,
      },
    });

    expect(
      screen.getByText("No valid response-quality contract was included in this verdict."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Ignored invalid response-quality blocks: payload.response_quality/),
    ).toBeInTheDocument();
  });

  it("does not relabel an evidence report as a red-team report", async () => {
    const user = userEvent.setup();
    renderVerdict({
      status: "PASS",
      response_quality: baseReport,
    });

    await user.click(screen.getByRole("button", { name: "Red Team Mode" }));

    expect(
      screen.getByText("No Hostile red-team review report was included in this verdict."),
    ).toBeInTheDocument();
    expect(screen.getByText("Included reports: Evidence-based answer.")).toBeInTheDocument();
  });

  it("treats incomplete mode-only reports as invalid", () => {
    renderVerdict({
      status: "PASS",
      response_quality: {
        mode: "evidence_based",
        recommendation: "Ship it.",
      },
    });

    expect(
      screen.getByText("No valid response-quality contract was included in this verdict."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Ignored invalid response-quality blocks: payload.response_quality/),
    ).toBeInTheDocument();
  });

  it("finds persona-level response-quality reports", async () => {
    const user = userEvent.setup();
    renderVerdict({
      panel: {
        per_persona: [
          {
            name: "animator",
            publish_ready: false,
            summary: "Motion risk found.",
            flags: [],
            response_quality: {
              ...baseReport,
              mode: "red_team",
              risks: ["Foot sliding may survive the sampled check."],
            },
          },
        ],
      },
    });

    await user.click(screen.getByRole("button", { name: "Red Team Mode" }));

    expect(screen.getByText("Hostile red-team review")).toBeInTheDocument();
    expect(
      screen.getByText("Source: panel.per_persona[0].response_quality"),
    ).toBeInTheDocument();
  });

  it("renders malformed scores and personas without crashing", () => {
    renderVerdict({
      status: "PASS",
      quality_scores_aggregated: {
        lighting_quality: "not-a-number",
      },
      failures: [{ signal: 42, frame: null }],
      panel: {
        per_persona: [{ name: "director", flags: "bad-shape" }],
      },
      response_quality: baseReport,
    });

    expect(screen.getByText("No numeric quality scores.")).toBeInTheDocument();
    expect(screen.getByText("unknown_signal")).toBeInTheDocument();
    expect(screen.getByText("director")).toBeInTheDocument();
  });
});
