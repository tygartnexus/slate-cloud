"""Reusable AI response-quality contract for Slate Cloud."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ResponseMode(str, Enum):
    """Supported AI output modes."""

    STANDARD = "standard"
    EVIDENCE_BASED = "evidence_based"
    RED_TEAM = "red_team"
    EXECUTIVE_MEMO = "executive_memo"
    TECHNICAL_REVIEW = "technical_review"
    LEGAL_RISK_REVIEW = "legal_risk_review"


REQUIRED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("mode", "Response mode"),
    ("facts", "Facts"),
    ("assumptions", "Assumptions"),
    ("unknowns", "Unknowns"),
    ("confidence_score", "Confidence score"),
    ("evidence", "Evidence / citations"),
    ("risks", "Risks"),
    ("counterarguments", "Counterarguments"),
    ("recommendation", "Recommendation"),
    ("tradeoffs", "Tradeoffs"),
    ("what_would_change_recommendation", "What would change the recommendation"),
)

PROMPT_TEMPLATES: dict[str, str] = {
    "anti_hallucination_checks": (
        "Separate verified facts from assumptions and unknowns. If evidence is missing, "
        "say so directly. Do not invent dates, measurements, sources, approvals, or "
        "runtime status."
    ),
    "red_team_review": (
        "Act as a hostile reviewer. Lead with failure modes, missing evidence, weak "
        "claims, counterarguments, and reasons the recommendation could be wrong."
    ),
    "ceo_reality_check": (
        "Give an executive reality check. Identify the decision, the evidence that "
        "supports it, the tradeoffs, the biggest risks, and the next proof needed."
    ),
    "evidence_based_recommendations": (
        "Make recommendations only from stated evidence. Mark unsupported claims as "
        "unknown and include what evidence would change the conclusion."
    ),
    "legal_compliance_review": (
        "Issue-spot legal and compliance exposure without giving legal advice. State "
        "jurisdiction/source limits, missing facts, controls, and counsel review needs."
    ),
    "technical_architecture_review": (
        "Review technical claims against architecture, runtime behavior, failure modes, "
        "test evidence, operational risk, and rollback or mitigation options."
    ),
    "bias_detection": (
        "Identify biased framing, one-sided evidence, missing stakeholder views, and "
        "where the recommendation may favor convenience over correctness."
    ),
    "executive_decision_matrix": (
        "Compare decision options by evidence, upside, downside, reversibility, cost, "
        "risk, and what would change the preferred option."
    ),
}

MODE_TEMPLATES: dict[ResponseMode, tuple[str, ...]] = {
    ResponseMode.STANDARD: ("anti_hallucination_checks",),
    ResponseMode.EVIDENCE_BASED: (
        "anti_hallucination_checks",
        "evidence_based_recommendations",
    ),
    ResponseMode.RED_TEAM: (
        "anti_hallucination_checks",
        "red_team_review",
        "bias_detection",
    ),
    ResponseMode.EXECUTIVE_MEMO: (
        "anti_hallucination_checks",
        "ceo_reality_check",
        "executive_decision_matrix",
    ),
    ResponseMode.TECHNICAL_REVIEW: (
        "anti_hallucination_checks",
        "technical_architecture_review",
    ),
    ResponseMode.LEGAL_RISK_REVIEW: (
        "anti_hallucination_checks",
        "legal_compliance_review",
    ),
}

PLACEHOLDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b", re.IGNORECASE),
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"\[(?:insert|add|todo|tbd)[^\]]*\]", re.IGNORECASE),
)


class ResponseQualityReport(BaseModel):
    """Structured response-quality report required for AI-generated reviews."""

    model_config = ConfigDict(extra="allow")

    mode: ResponseMode
    facts: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    confidence_score: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    counterarguments: list[str] = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    tradeoffs: list[str] = Field(min_length=1)
    what_would_change_recommendation: list[str] = Field(min_length=1)

    @field_validator(
        "facts",
        "assumptions",
        "unknowns",
        "evidence",
        "risks",
        "counterarguments",
        "tradeoffs",
        "what_would_change_recommendation",
    )
    @classmethod
    def _list_items_must_be_substantive(cls, values: list[str]) -> list[str]:
        cleaned = [_clean_text(item) for item in values]
        if any(not item for item in cleaned):
            raise ValueError("items must not be blank")
        return cleaned

    @field_validator("recommendation")
    @classmethod
    def _recommendation_must_be_substantive(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("recommendation must not be blank")
        return cleaned


class ResponseQualityValidationError(ValueError):
    """Raised when an AI response-quality report violates the contract."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


def build_response_quality_prompt(
    *,
    mode: ResponseMode | str,
    task: str,
    evidence: str | None = None,
    additional_context: str | None = None,
) -> str:
    """Build a mode-specific prompt with the required structured-output contract."""

    response_mode = ResponseMode(mode)
    template_text = "\n".join(
        f"- {name}: {PROMPT_TEMPLATES[name]}" for name in MODE_TEMPLATES[response_mode]
    )
    sections = "\n".join(f"- {label} (`{key}`)" for key, label in REQUIRED_SECTIONS)
    evidence_text = evidence or "No direct evidence was supplied. Say this explicitly."
    context_text = additional_context or "No additional context was supplied."
    schema = json.dumps(ResponseQualityReport.model_json_schema(), indent=2)

    return "\n".join(
        [
            "You must optimize for correctness over agreement.",
            f"Mode: {response_mode.value}",
            "",
            "Task:",
            task,
            "",
            "Evidence available:",
            evidence_text,
            "",
            "Additional context:",
            context_text,
            "",
            "Mode instructions:",
            template_text,
            "",
            "Required response_quality sections:",
            sections,
            "",
            "Guardrails:",
            "- Say when evidence is missing.",
            "- Do not invent facts or sources.",
            "- Distinguish opinion from verified fact.",
            "- Challenge weak ideas directly.",
            "- Include confidence as a number from 0.0 to 1.0.",
            "- Include tradeoffs and what evidence would change the recommendation.",
            f"- Set `mode` exactly to `{response_mode.value}`.",
            "",
            "Return JSON matching this response_quality schema:",
            schema,
        ]
    )


def validate_response_quality_report(
    report: Mapping[str, Any],
    *,
    mode: ResponseMode | str | None = None,
) -> ResponseQualityReport:
    """Validate one response-quality report and raise with actionable issues."""

    issues: list[str] = []
    if "mode" not in report:
        issues.append("mode: required; upgrade Slate CLI to emit response_quality.mode")
    try:
        validated = ResponseQualityReport.model_validate(report)
    except ValidationError as exc:
        issues.extend(_format_pydantic_issues(exc))
        raise ResponseQualityValidationError(issues) from exc

    issues.extend(_placeholder_issues(validated))
    response_mode = ResponseMode(mode) if mode is not None else validated.mode
    if validated.mode != response_mode:
        issues.append(
            f"mode: expected {response_mode.value}, got {validated.mode.value}"
        )
    if response_mode == ResponseMode.RED_TEAM and not validated.risks:
        issues.append("red_team mode requires explicit risks")
    if response_mode == ResponseMode.LEGAL_RISK_REVIEW and not _mentions_legal_limits(
        validated
    ):
        issues.append(
            "legal_risk_review mode requires a non-advice/counsel/source-limit caveat"
        )
    if (
        response_mode == ResponseMode.TECHNICAL_REVIEW
        and not _mentions_technical_evidence(validated)
    ):
        issues.append(
            "technical_review mode requires runtime, test, or architecture evidence"
        )
    if issues:
        raise ResponseQualityValidationError(issues)
    return validated


def validate_verdict_response_quality(
    payload: Mapping[str, Any],
) -> list[ResponseQualityReport]:
    """Validate every response_quality block in a verdict payload.

    A verdict must contain at least one response_quality object, and every object
    present must satisfy the same contract.
    """

    reports = list(_iter_response_quality_reports(payload))
    if not reports:
        raise ResponseQualityValidationError(
            ["verdict must include at least one response_quality object"]
        )

    validated_reports: list[ResponseQualityReport] = []
    issues: list[str] = []
    for path, report in reports:
        if not isinstance(report, Mapping):
            issues.append(f"{path}: response_quality must be an object")
            continue
        try:
            validated_reports.append(validate_response_quality_report(report))
        except ResponseQualityValidationError as exc:
            issues.extend(f"{path}: {issue}" for issue in exc.issues)

    if issues:
        raise ResponseQualityValidationError(issues)
    return validated_reports


def _iter_response_quality_reports(
    value: Any, path: str = "$"
) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "response_quality":
                yield child_path, child
            else:
                yield from _iter_response_quality_reports(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_response_quality_reports(child, f"{path}[{index}]")


def _format_pydantic_issues(exc: ValidationError) -> list[str]:
    issues: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        message = str(error["msg"])
        issues.append(f"{location}: {message}")
    return issues


def _placeholder_issues(report: ResponseQualityReport) -> list[str]:
    issues: list[str] = []
    for field, value in report.model_dump().items():
        strings: list[str]
        if isinstance(value, str):
            strings = [value]
        elif isinstance(value, list):
            strings = [item for item in value if isinstance(item, str)]
        else:
            continue
        for item in strings:
            if any(pattern.search(item) for pattern in PLACEHOLDER_PATTERNS):
                issues.append(f"{field}: unresolved placeholder text is not allowed")
                break
    return issues


def _report_text(report: ResponseQualityReport) -> str:
    pieces: list[str] = []
    for value in report.model_dump().values():
        if isinstance(value, str):
            pieces.append(value)
        elif isinstance(value, list):
            pieces.extend(item for item in value if isinstance(item, str))
    return " ".join(pieces).lower()


def _mentions_legal_limits(report: ResponseQualityReport) -> bool:
    text = _report_text(report)
    return any(
        phrase in text
        for phrase in (
            "not legal advice",
            "counsel",
            "jurisdiction",
            "source limit",
            "source limits",
        )
    )


def _mentions_technical_evidence(report: ResponseQualityReport) -> bool:
    text = _report_text(report)
    return any(
        phrase in text
        for phrase in (
            "runtime",
            "test",
            "architecture",
            "operational",
            "migration",
            "schema",
        )
    )


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())
