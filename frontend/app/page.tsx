import Link from "next/link";
import { SignInButton } from "@clerk/nextjs";

const SLATE_REPO_URL = process.env.NEXT_PUBLIC_SLATE_REPO_URL ?? "#";

export default function Home() {
  return (
    <main className="min-h-screen px-6 py-16 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-20">
        <div className="font-mono text-xl tracking-tight">slate</div>
        <div className="flex items-center gap-4">
          <Link href="/dashboard">Dashboard</Link>
          <SignInButton>
            <button className="px-4 py-2 rounded bg-slate-accent text-slate-bg font-medium">
              Sign in
            </button>
          </SignInButton>
        </div>
      </header>

      <section className="mb-20">
        <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-[1.05]">
          Don&apos;t ship broken AI animation.
        </h1>
        <p className="mt-6 text-xl text-zinc-400 max-w-2xl">
          Slate checks sampled render frames with your configured vision-model
          providers and a four-persona adversarial Panel. Catch the failure
          modes that AI render tools don&apos;t catch themselves.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="px-5 py-3 rounded bg-slate-accent text-slate-bg font-medium"
          >
            Open dashboard
          </Link>
          <a
            href={SLATE_REPO_URL}
            className="px-5 py-3 rounded border border-zinc-700 text-zinc-200"
          >
            {SLATE_REPO_URL === "#" ? "GitHub pending launch" : "Slate on GitHub"}
          </a>
        </div>
      </section>

      <section className="grid md:grid-cols-3 gap-6 mb-20">
        {[
          {
            title: "Configurable VLM review",
            body: "Use local Gemma through Ollama, NVIDIA cloud lanes, or both depending on your privacy and cost requirements.",
          },
          {
            title: "Panel persona ensemble",
            body: "Director, Color Grader, Animator, and Audience reports are shown when the uploaded verdict includes Panel review evidence.",
          },
          {
            title: "Audit-ready bundles",
            body: "Single .tar.gz with frame hashes, verdict JSON, persona reports, optional thumbnails, and raw-output redaction for external sharing.",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="rounded-lg border border-zinc-800 bg-slate-surface p-6"
          >
            <h3 className="text-lg font-semibold mb-2">{card.title}</h3>
            <p className="text-zinc-400 text-sm">{card.body}</p>
          </div>
        ))}
      </section>

      <section className="text-zinc-500 text-sm">
        Slate, Panel review, evidence bundles, and the dashboard are free and
        MIT-licensed.
      </section>
    </main>
  );
}
