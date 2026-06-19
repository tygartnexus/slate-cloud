"use client";

import { useMemo, useState } from "react";

import {
  formatConfidence,
  modeTitle,
  REVIEW_MODES,
  type ResponseQuality,
  type ReviewMode,
} from "@/lib/ai-response-quality";

interface PersonaFlag {
  severity: string;
  frame: string | null;
  description: string;
}

interface PersonaVerdict {
  name: string;
  publish_ready: boolean;
  summary: string;
  flags: PersonaFlag[];
  response_quality?: ResponseQuality | null;
}

interface PanelVerdict {
  per_persona: PersonaVerdict[];
  response_quality?: ResponseQuality | null;
}

interface CoreVerdict {
  failures: { signal: string; frame: string; description: string }[];
  quality_scores_aggregated: Record<string, number>;
  response_quality?: ResponseQuality | null;
  frame_analyses: { response_quality?: ResponseQuality | null }[];
}

interface QualityReportEntry {
  source: string;
  report: ResponseQuality & { mode: ReviewMode };
}

interface NormalizedVerdictPayload {
  core: CoreVerdict | null;
  panel: PanelVerdict | null;
  reports: QualityReportEntry[];
  invalidReportSources: string[];
}

interface VerdictDetailData {
  id: string;
  shot_id: string;
  final_status: string;
  has_panel_review: boolean;
  submitted_at: string;
  payload: Record<string, unknown>;
}

export function VerdictDetail({ verdict }: { verdict: VerdictDetailData }) {
  const [selectedMode, setSelectedMode] = useState<ReviewMode>("evidence_based");
  const normalized = useMemo(
    () => normalizeVerdictPayload(verdict.payload),
    [verdict.payload],
  );
  const selectedReport =
    normalized.reports.find((entry) => entry.report.mode === selectedMode) ?? null;

  return (
    <div>
      <header className="mb-8">
        <div className="font-mono text-2xl text-zinc-100">{verdict.shot_id}</div>
        <div className="text-sm text-zinc-500 mt-1">
          {new Date(verdict.submitted_at).toLocaleString()}
        </div>
        <div className="mt-3 inline-block rounded-md border border-zinc-700 px-3 py-1 text-sm font-medium">
          {verdict.final_status}
        </div>
      </header>

      <section className="mb-8">
        <div className="flex flex-wrap gap-2">
          {REVIEW_MODES.map((item) => {
            const included = normalized.reports.some(
              (entry) => entry.report.mode === item.id,
            );
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selectedMode === item.id}
                onClick={() => setSelectedMode(item.id)}
                className={
                  selectedMode === item.id
                    ? "rounded-md bg-slate-accent px-3 py-2 text-sm font-medium text-slate-bg"
                    : included
                      ? "rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:border-zinc-500"
                      : "rounded-md border border-zinc-900 px-3 py-2 text-sm text-zinc-500"
                }
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </section>

      <QualityPanel
        mode={selectedMode}
        reportEntry={selectedReport}
        reports={normalized.reports}
        invalidReportSources={normalized.invalidReportSources}
      />

      {normalized.core && <CorePanel core={normalized.core} />}
      {normalized.panel && <PanelPersonas panel={normalized.panel} />}
    </div>
  );
}

function CorePanel({ core }: { core: CoreVerdict }) {
  const scoreEntries = Object.entries(core.quality_scores_aggregated);
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-lg font-semibold">Core</h2>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
          <div className="mb-2 text-sm text-zinc-400">Quality scores</div>
          {scoreEntries.length === 0 ? (
            <div className="text-sm text-zinc-500">No numeric quality scores.</div>
          ) : (
            <dl className="space-y-1 text-sm">
              {scoreEntries.map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4">
                  <dt className="text-zinc-500">{key.replace("_quality", "")}</dt>
                  <dd className="font-mono">{value.toFixed(2)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
        <div className="rounded-md border border-zinc-800 bg-slate-surface p-4">
          <div className="mb-2 text-sm text-zinc-400">
            Failures ({core.failures.length})
          </div>
          {core.failures.length === 0 ? (
            <div className="text-sm text-emerald-400">No failures.</div>
          ) : (
            <ul className="space-y-2 text-sm">
              {core.failures.slice(0, 5).map((failure, index) => (
                <li key={`${failure.signal}-${index}`} className="text-zinc-300">
                  <span className="font-mono text-red-400">{failure.signal}</span>{" "}
                  - {failure.frame}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function PanelPersonas({ panel }: { panel: PanelVerdict }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">Panel personas</h2>
      {panel.per_persona.length === 0 ? (
        <div className="rounded-md border border-zinc-800 bg-slate-surface p-4 text-sm text-zinc-500">
          No personas provided.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {panel.per_persona.map((persona) => (
            <div
              key={persona.name}
              className="rounded-md border border-zinc-800 bg-slate-surface p-4"
            >
              <div className="mb-2 flex items-center justify-between gap-4">
                <div className="font-medium capitalize">
                  {persona.name.replace("_", " ")}
                </div>
                <div
                  className={
                    persona.publish_ready
                      ? "text-xs text-emerald-400"
                      : "text-xs text-red-400"
                  }
                >
                  {persona.publish_ready ? "PASS" : "BLOCK"}
                </div>
              </div>
              <div className="mb-3 text-sm text-zinc-400">{persona.summary}</div>
              {persona.flags.length > 0 && (
                <ul className="space-y-1 text-xs">
                  {persona.flags.slice(0, 3).map((flag, index) => (
                    <li key={`${persona.name}-${index}`} className="text-zinc-300">
                      <span className="font-mono text-amber-400">
                        [{flag.severity}]
                      </span>{" "}
                      {flag.description}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function QualityPanel({
  mode,
  reportEntry,
  reports,
  invalidReportSources,
}: {
  mode: ReviewMode;
  reportEntry: QualityReportEntry | null;
  reports: QualityReportEntry[];
  invalidReportSources: string[];
}) {
  if (!reportEntry) {
    const availableModes = Array.from(
      new Set(reports.map((entry) => modeTitle(entry.report.mode))),
    );
    return (
      <section className="mb-8 rounded-md border border-amber-500/40 bg-amber-500/5 p-4">
        <h2 className="mb-2 text-lg font-semibold">Evidence status</h2>
        <p className="text-sm text-amber-200">
          {reports.length === 0
            ? "No valid response-quality contract was included in this verdict."
            : `No ${modeTitle(mode)} report was included in this verdict.`}
        </p>
        {availableModes.length > 0 && (
          <p className="mt-2 text-xs text-zinc-400">
            Included reports: {availableModes.join(", ")}.
          </p>
        )}
        {invalidReportSources.length > 0 && (
          <p className="mt-2 text-xs text-zinc-500">
            Ignored invalid response-quality blocks: {invalidReportSources.join(", ")}.
          </p>
        )}
      </section>
    );
  }

  const report = reportEntry.report;
  return (
    <section className="mb-8 rounded-md border border-zinc-800 bg-slate-surface p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{modeTitle(report.mode)}</h2>
          <p className="text-xs text-zinc-500">Source: {reportEntry.source}</p>
        </div>
        <div className="font-mono text-sm text-slate-accent">
          confidence {formatConfidence(report.confidence_score)}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {report.mode === "standard" && (
          <>
            <TextBlock title="Recommendation" value={report.recommendation} />
            <SectionList title="Facts" items={report.facts} />
            <SectionList title="Assumptions" items={report.assumptions} />
            <SectionList title="Unknowns" items={report.unknowns} />
          </>
        )}
        {report.mode === "evidence_based" && (
          <>
            <SectionList title="Facts" items={report.facts} />
            <SectionList title="Assumptions" items={report.assumptions} />
            <SectionList title="Unknowns" items={report.unknowns} />
            <SectionList title="Evidence" items={report.evidence} />
            <TextBlock title="Recommendation" value={report.recommendation} />
            <SectionList
              title="Would change"
              items={report.what_would_change_recommendation}
            />
          </>
        )}
        {report.mode === "red_team" && (
          <>
            <SectionList title="Risks" items={report.risks} />
            <SectionList title="Counterarguments" items={report.counterarguments} />
            <SectionList title="Unknowns" items={report.unknowns} />
            <SectionList
              title="Would change"
              items={report.what_would_change_recommendation}
            />
          </>
        )}
        {report.mode === "executive_memo" && (
          <>
            <TextBlock title="Recommendation" value={report.recommendation} />
            <SectionList title="Tradeoffs" items={report.tradeoffs} />
            <SectionList title="Facts" items={report.facts} />
            <SectionList title="Risks" items={report.risks} />
          </>
        )}
        {report.mode === "technical_review" && (
          <>
            <SectionList title="Facts" items={report.facts} />
            <SectionList title="Evidence" items={report.evidence} />
            <SectionList title="Unknowns" items={report.unknowns} />
            <SectionList title="Risks" items={report.risks} />
          </>
        )}
        {report.mode === "legal_risk_review" && (
          <>
            <TextBlock title="Caveat" value="Not legal advice." />
            <SectionList title="Risks" items={report.risks} />
            <SectionList title="Unknowns" items={report.unknowns} />
            <SectionList title="Evidence" items={report.evidence} />
          </>
        )}
      </div>
    </section>
  );
}

function normalizeVerdictPayload(payload: Record<string, unknown>): NormalizedVerdictPayload {
  const root = isRecord(payload) ? payload : {};
  const core = normalizeCore(root);
  const panel = normalizePanel(root.panel) ?? normalizePanel(root["th" + "rawn"]);
  const reports: QualityReportEntry[] = [];
  const invalidReportSources: string[] = [];

  addReport(reports, invalidReportSources, "payload.response_quality", root.response_quality);
  if (core) {
    addReport(reports, invalidReportSources, "core.response_quality", core.response_quality);
    core.frame_analyses.forEach((analysis, index) => {
      addReport(
        reports,
        invalidReportSources,
        `core.frame_analyses[${index}].response_quality`,
        analysis.response_quality,
      );
    });
  }
  if (panel) {
    addReport(reports, invalidReportSources, "panel.response_quality", panel.response_quality);
    panel.per_persona.forEach((persona, index) => {
      addReport(
        reports,
        invalidReportSources,
        `panel.per_persona[${index}].response_quality`,
        persona.response_quality,
      );
    });
  }

  return { core, panel, reports, invalidReportSources };
}

function normalizeCore(payload: Record<string, unknown>): CoreVerdict | null {
  const candidate = isRecord(payload.core) ? payload.core : payload;
  const hasCoreShape =
    typeof candidate.status === "string" ||
    Array.isArray(candidate.failures) ||
    isRecord(candidate.quality_scores_aggregated);
  if (!hasCoreShape) return null;
  return {
    failures: normalizeFailures(candidate.failures),
    quality_scores_aggregated: normalizeQualityScores(candidate.quality_scores_aggregated),
    response_quality: normalizeResponseQuality(candidate.response_quality),
    frame_analyses: Array.isArray(candidate.frame_analyses)
      ? candidate.frame_analyses.map((item) => ({
          response_quality: isRecord(item)
            ? normalizeResponseQuality(item.response_quality)
            : null,
        }))
      : [],
  };
}

function normalizePanel(value: unknown): PanelVerdict | null {
  if (!isRecord(value)) return null;
  return {
    per_persona: Array.isArray(value.per_persona)
      ? value.per_persona.map(normalizePersona)
      : [],
    response_quality: normalizeResponseQuality(value.response_quality),
  };
}

function normalizePersona(value: unknown): PersonaVerdict {
  const record = isRecord(value) ? value : {};
  return {
    name: asString(record.name, "unknown_persona"),
    publish_ready:
      typeof record.publish_ready === "boolean" ? record.publish_ready : false,
    summary: asString(record.summary, "No summary provided."),
    flags: Array.isArray(record.flags) ? record.flags.map(normalizeFlag) : [],
    response_quality: normalizeResponseQuality(record.response_quality),
  };
}

function normalizeFlag(value: unknown): PersonaFlag {
  const record = isRecord(value) ? value : {};
  return {
    severity: asString(record.severity, "unknown"),
    frame: typeof record.frame === "string" ? record.frame : null,
    description: asString(record.description, "No description provided."),
  };
}

function normalizeFailures(value: unknown): CoreVerdict["failures"] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const record = isRecord(item) ? item : {};
    return {
      signal: asString(record.signal, "unknown_signal"),
      frame: asString(record.frame, "unknown_frame"),
      description: asString(record.description, "No description provided."),
    };
  });
}

function normalizeQualityScores(value: unknown): Record<string, number> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, number] => {
      return typeof entry[1] === "number" && Number.isFinite(entry[1]);
    }),
  );
}

function addReport(
  reports: QualityReportEntry[],
  invalidReportSources: string[],
  source: string,
  value: unknown,
) {
  if (value == null) return;
  const report = normalizeResponseQuality(value);
  if (report) {
    reports.push({ source, report });
  } else {
    invalidReportSources.push(source);
  }
}

function normalizeResponseQuality(
  value: unknown,
): (ResponseQuality & { mode: ReviewMode }) | null {
  if (!isRecord(value) || !isReviewMode(value.mode)) return null;
  const facts = asRequiredStringList(value.facts);
  const assumptions = asRequiredStringList(value.assumptions);
  const unknowns = asRequiredStringList(value.unknowns);
  const evidence = asRequiredStringList(value.evidence);
  const risks = asRequiredStringList(value.risks);
  const counterarguments = asRequiredStringList(value.counterarguments);
  const tradeoffs = asRequiredStringList(value.tradeoffs);
  const whatWouldChange = asRequiredStringList(
    value.what_would_change_recommendation,
  );
  const confidence =
    typeof value.confidence_score === "number" &&
    Number.isFinite(value.confidence_score) &&
    value.confidence_score >= 0 &&
    value.confidence_score <= 1
      ? value.confidence_score
      : null;
  const recommendation =
    typeof value.recommendation === "string" && value.recommendation.trim()
      ? value.recommendation
      : null;
  if (
    !facts ||
    !assumptions ||
    !unknowns ||
    !evidence ||
    !risks ||
    !counterarguments ||
    !tradeoffs ||
    !whatWouldChange ||
    confidence === null ||
    !recommendation
  ) {
    return null;
  }
  return {
    mode: value.mode,
    facts,
    assumptions,
    unknowns,
    confidence_score: confidence,
    evidence,
    risks,
    counterarguments,
    recommendation,
    tradeoffs,
    what_would_change_recommendation: whatWouldChange,
  };
}

function isReviewMode(value: unknown): value is ReviewMode {
  return REVIEW_MODES.some((mode) => mode.id === value);
}

function SectionList({ title, items }: { title: string; items?: string[] }) {
  const values = items?.filter(Boolean) ?? [];
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-zinc-300">{title}</h3>
      {values.length === 0 ? (
        <p className="text-sm text-zinc-500">Not provided.</p>
      ) : (
        <ul className="space-y-1 text-sm text-zinc-400">
          {values.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TextBlock({ title, value }: { title: string; value?: string }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-zinc-300">{title}</h3>
      <p className="text-sm text-zinc-400">{value || "Not provided."}</p>
    </div>
  );
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asStringList(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const items = value.filter((item): item is string => {
    return typeof item === "string" && item.trim().length > 0;
  });
  return items.length > 0 ? items : undefined;
}

function asRequiredStringList(value: unknown): string[] | null {
  return asStringList(value) ?? null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
