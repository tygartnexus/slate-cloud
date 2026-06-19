"""AI response-quality framework tests."""

from __future__ import annotations

import pytest

from app.ai_response_quality import (
    PROMPT_TEMPLATES,
    REQUIRED_SECTIONS,
    ResponseMode,
    ResponseQualityValidationError,
    build_response_quality_prompt,
    validate_response_quality_report,
    validate_verdict_response_quality,
)


def valid_report() -> dict[str, object]:
    return {
        "mode": "evidence_based",
        "facts": ["The backend received a Slate verdict payload."],
        "assumptions": ["The uploaded payload came from a trusted Slate CLI run."],
        "unknowns": ["The original frames were not uploaded to SlateCloud."],
        "confidence_score": 0.74,
        "evidence": ["verdict.json response_quality block"],
        "risks": ["The uploaded evidence could omit unsampled frame failures."],
        "counterarguments": [
            "A complete local evidence bundle may support the verdict."
        ],
        "recommendation": "Keep the verdict but review the source evidence before publishing.",
        "tradeoffs": [
            "Strict validation blocks vague uploads but may require CLI retries."
        ],
        "what_would_change_recommendation": [
            "A complete evidence bundle with validated frame hashes."
        ],
    }


def test_required_sections_and_prompt_templates_are_centralized() -> None:
    section_keys = {key for key, _label in REQUIRED_SECTIONS}
    assert section_keys == {
        "mode",
        "facts",
        "assumptions",
        "unknowns",
        "confidence_score",
        "evidence",
        "risks",
        "counterarguments",
        "recommendation",
        "tradeoffs",
        "what_would_change_recommendation",
    }
    assert {
        "anti_hallucination_checks",
        "red_team_review",
        "ceo_reality_check",
        "evidence_based_recommendations",
        "legal_compliance_review",
        "technical_architecture_review",
        "bias_detection",
        "executive_decision_matrix",
    }.issubset(PROMPT_TEMPLATES)


def test_valid_report_with_missing_evidence_acknowledgement_passes() -> None:
    report = valid_report()
    report["evidence"] = ["No direct evidence was provided in the upload."]
    report["unknowns"] = ["Frame-level evidence is missing."]

    validated = validate_response_quality_report(report)

    assert validated.confidence_score == 0.74
    assert validated.evidence == ["No direct evidence was provided in the upload."]


def test_missing_evidence_is_rejected() -> None:
    report = valid_report()
    report["evidence"] = []

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "evidence" in str(exc.value)


def test_confidence_score_is_required() -> None:
    report = valid_report()
    del report["confidence_score"]

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "confidence_score" in str(exc.value)


def test_mode_is_required_for_provenance() -> None:
    report = valid_report()
    del report["mode"]

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "upgrade Slate CLI" in str(exc.value)


def test_mode_mismatch_is_rejected() -> None:
    report = valid_report()
    report["mode"] = "standard"

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report, mode=ResponseMode.RED_TEAM)

    assert "expected red_team" in str(exc.value)


def test_assumptions_are_required() -> None:
    report = valid_report()
    report["assumptions"] = []

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "assumptions" in str(exc.value)


def test_recommendations_require_tradeoffs() -> None:
    report = valid_report()
    report["tradeoffs"] = []

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "tradeoffs" in str(exc.value)


def test_red_team_prompt_identifies_risks_and_failure_modes() -> None:
    prompt = build_response_quality_prompt(
        mode=ResponseMode.RED_TEAM,
        task="Review a publish-ready verdict.",
        evidence="Panel blocked on animator risk.",
    )

    assert "hostile reviewer" in prompt
    assert "risks" in prompt
    assert "failure modes" in prompt
    assert "counterarguments" in prompt


def test_legal_mode_requires_caveat() -> None:
    report = valid_report()
    report["mode"] = "legal_risk_review"

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "non-advice" in str(exc.value)


def test_technical_mode_requires_technical_evidence() -> None:
    report = valid_report()
    report["mode"] = "technical_review"

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "runtime, test, or architecture" in str(exc.value)


def test_unresolved_placeholders_are_rejected() -> None:
    report = valid_report()
    report["recommendation"] = "TODO: fill in recommendation"

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_response_quality_report(report)

    assert "placeholder" in str(exc.value)


def test_verdict_validation_checks_nested_response_quality_blocks() -> None:
    payload = {
        "status": "PASS",
        "response_quality": valid_report(),
        "panel": {
            "response_quality": {
                **valid_report(),
                "recommendation": "{{panel_recommendation}}",
            }
        },
    }

    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_verdict_response_quality(payload)

    assert "$.panel.response_quality" in str(exc.value)
    assert "placeholder" in str(exc.value)


def test_verdict_validation_requires_at_least_one_response_quality_block() -> None:
    with pytest.raises(ResponseQualityValidationError) as exc:
        validate_verdict_response_quality({"status": "PASS"})

    assert "at least one response_quality" in str(exc.value)
