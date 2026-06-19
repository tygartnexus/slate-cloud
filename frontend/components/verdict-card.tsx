interface VerdictSummary {
  id: string;
  shot_id: string;
  final_status: string;
  has_panel_review: boolean;
  submitted_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  PASS: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  FAIL: "bg-red-500/10 text-red-400 border-red-500/30",
  THRAWN_BLOCKED: "bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30",
  INDETERMINATE: "bg-amber-500/10 text-amber-400 border-amber-500/30",
};

export function VerdictCard({ verdict }: { verdict: VerdictSummary }) {
  const statusStyle =
    STATUS_STYLES[verdict.final_status] ??
    "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
  const when = new Date(verdict.submitted_at).toLocaleString();

  return (
    <div className="rounded-lg border border-zinc-800 bg-slate-surface p-4 flex items-center justify-between hover:border-zinc-700 transition">
      <div>
        <div className="font-mono text-sm text-zinc-300">{verdict.shot_id}</div>
        <div className="text-xs text-zinc-500 mt-1">
          {when}
          {verdict.has_panel_review ? " • Panel" : ""}
        </div>
      </div>
      <span
        className={`px-3 py-1 text-xs rounded border ${statusStyle} font-medium`}
      >
        {verdict.final_status}
      </span>
    </div>
  );
}
