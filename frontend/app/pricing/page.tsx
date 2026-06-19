import Link from "next/link";

const SLATE_REPO_URL = process.env.NEXT_PUBLIC_SLATE_REPO_URL ?? "#";

const CAPABILITIES = [
  {
    name: "Provider verdicts",
    description:
      "Frame sampling, configured-provider VLM checks, signal fusion, and JSON verdicts.",
  },
  {
    name: "Panel review",
    description:
      "Four-persona adversarial review with local or Anthropic panel providers.",
  },
  {
    name: "Evidence bundles",
    description:
      "Shareable tarballs with frame hashes, verdict JSON, optional thumbnails, and raw-output redaction.",
  },
];

export default function PricingPage() {
  return (
    <main className="px-6 py-16 max-w-5xl mx-auto">
      <header className="text-center mb-16">
        <Link href="/" className="font-mono text-xl tracking-tight inline-block mb-8">
          slate
        </Link>
        <h1 className="text-5xl font-semibold tracking-tight mb-4">
          One free Slate.
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          The CLI, Panel review, evidence bundles, and dashboard are MIT-licensed.
          There is no checkout, activation token, subscription, or paid upgrade.
        </p>
      </header>

      <div className="grid md:grid-cols-3 gap-6">
        {CAPABILITIES.map((item) => (
          <div
            key={item.name}
            className="rounded-lg border border-zinc-800 bg-slate-surface p-6"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">{item.name}</h2>
              <span className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
                MIT
              </span>
            </div>
            <p className="text-sm text-zinc-400 mt-4">{item.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 text-center">
        {SLATE_REPO_URL === "#" ? (
          <span className="text-sm text-zinc-500">Repository URL pending</span>
        ) : (
          <a
            href={SLATE_REPO_URL}
            className="inline-block rounded bg-slate-accent px-4 py-2 text-sm font-medium text-slate-bg"
          >
            Open repository
          </a>
        )}
      </div>

      <section className="mt-20 max-w-3xl mx-auto text-zinc-400 space-y-4 text-sm">
        <h3 className="text-zinc-100 text-lg font-semibold">Notes</h3>
        <div>
          <strong className="text-zinc-100">Do my frames go to the cloud?</strong>
          <br />
          Slate Cloud stores verdict JSON only, not frame bytes or API keys.
          Local Ollama keeps sampled frames on your hardware. NVIDIA and
          Anthropic lanes send sampled frames to those providers through your
          own account.
        </div>
        <div>
          <strong className="text-zinc-100">Who pays provider costs?</strong>
          <br />
          You still pay NVIDIA, Anthropic, or other model providers directly
          when you choose cloud lanes. Slate does not proxy those keys or rates.
        </div>
      </section>
    </main>
  );
}
