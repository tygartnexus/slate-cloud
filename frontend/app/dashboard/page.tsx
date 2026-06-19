import Link from "next/link";
import { listVerdicts } from "@/lib/api";
import { VerdictCard } from "@/components/verdict-card";
import { getDashboardAuth } from "@/lib/dashboard-auth";

export default async function DashboardPage() {
  const { token } = await getDashboardAuth();
  const verdicts = token ? await listVerdicts(token) : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Verdicts</h1>
        <div className="text-sm text-zinc-500">
          {verdicts.length} {verdicts.length === 1 ? "verdict" : "verdicts"} uploaded
        </div>
      </div>

      {verdicts.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-slate-surface p-10 text-center text-zinc-400">
          <p className="mb-3">No verdicts yet.</p>
          <p className="text-sm">
            Run{" "}
            <code className="text-slate-accent">
              slate verify -f frames/ -m shot.json --panel
            </code>{" "}
            and POST the resulting JSON to{" "}
            <code className="text-slate-accent">/verdicts</code> with your Clerk
            JWT.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {verdicts.map((v) => (
            <Link key={v.id} href={`/dashboard/verdicts/${v.id}`}>
              <VerdictCard verdict={v} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
