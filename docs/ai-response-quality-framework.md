# AI Response Quality Framework

## Purpose

SlateCloud uses an "Accuracy, Evidence, and Honest Feedback" framework so uploaded AI verdicts cannot present unsupported conclusions as verified facts. New verdict uploads must include at least one `response_quality` object, and every `response_quality` object in the payload must pass the same contract before the backend stores it.

The backend contract lives in `backend/app/ai_response_quality.py`. The dashboard mode selector and display labels live in `frontend/lib/ai-response-quality.ts`.

## Required Sections

Every AI-generated report must include:

- Response mode (`mode`)
- Facts
- Assumptions
- Unknowns
- Confidence score from `0.0` to `1.0`
- Evidence / citations
- Risks
- Counterarguments
- Recommendation
- Tradeoffs
- What would change the recommendation

If direct evidence is unavailable, the report must say that explicitly in the evidence and unknowns sections. Empty evidence is not valid.

## Available Modes

- `standard`: concise answer with assumptions and confidence when needed.
- `evidence_based`: accuracy mode with the full evidence-first contract.
- `red_team`: hostile review focused on risks, missing evidence, and failure modes.
- `executive_memo`: CEO review with decision options, tradeoffs, and next proof needed.
- `technical_review`: architecture/runtime/test-focused review.
- `legal_risk_review`: legal and compliance issue spotting with source limits and non-attorney caveats.

The dashboard exposes Standard Answer, Accuracy Mode, Red Team Mode, CEO Review
Mode, Technical Review Mode, and Legal Risk Review Mode. It only displays a
mode panel when the uploaded verdict contains a valid `response_quality.mode`
for that exact mode; it does not relabel one report as another mode.

## Prompt Templates

Prompt templates are centralized in `PROMPT_TEMPLATES`:

- `anti_hallucination_checks`
- `red_team_review`
- `ceo_reality_check`
- `evidence_based_recommendations`
- `legal_compliance_review`
- `technical_architecture_review`
- `bias_detection`
- `executive_decision_matrix`

Use `build_response_quality_prompt()` when adding a new AI call path. It injects the active mode, guardrails, required sections, and JSON schema.

## Guardrails

The framework rejects reports that:

- omit required sections
- omit response-mode provenance
- omit confidence scores
- provide empty evidence
- omit assumptions, risks, counterarguments, tradeoffs, or change criteria
- contain unresolved placeholders such as `TODO`, `TBD`, `{{value}}`, or `[insert ...]`
- store non-object `response_quality` values

The framework does not verify whether an evidence citation is factually true. It verifies that the model did not skip the evidence discipline. Source authenticity still depends on the Slate CLI/provider evidence bundle and any human review process around it.

## How To Extend

1. Add new modes only in `ResponseMode` and `MODE_TEMPLATES`.
2. Add prompt wording only in `PROMPT_TEMPLATES`.
3. Keep required section names centralized in `REQUIRED_SECTIONS`.
4. Call `validate_verdict_response_quality()` before storing any new AI verdict-like payload.
5. Add dashboard labels in `frontend/lib/ai-response-quality.ts` if the mode should be user selectable.
6. Add tests for mode behavior, placeholder rejection, missing evidence, confidence, assumptions, tradeoffs, and red-team risks.

## Good Output

```json
{
  "response_quality": {
    "mode": "evidence_based",
    "facts": ["Panel recorded one critical animator flag"],
    "assumptions": ["Sampled frames represent the shot"],
    "unknowns": ["Unsampled frames were not reviewed"],
    "confidence_score": 0.82,
    "evidence": ["frame_0042.png", "animator flag: foot slide"],
    "risks": ["The issue could be intentional stylization"],
    "counterarguments": ["The motion may read correctly at full speed"],
    "recommendation": "Block publish until motion is reviewed",
    "tradeoffs": ["Blocking protects quality but slows delivery"],
    "what_would_change_recommendation": [
      "Full-speed review shows the slide is not visible"
    ]
  }
}
```

## Bad Output

```json
{
  "summary": "The render is good. Ship it."
}
```

This is bad because it asserts readiness without facts, assumptions, unknowns, evidence, confidence, risks, counterarguments, tradeoffs, or change criteria. SlateCloud rejects new uploads like this with `422 Unprocessable Entity`.
