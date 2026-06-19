export default async function LicensePage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Access</h1>

      <div className="rounded-lg border border-zinc-800 bg-slate-surface p-8 text-zinc-300">
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          All Slate features are free.
        </h2>
        <p className="text-sm text-zinc-400 mb-4">
          Slate has no checkout, activation tokens, or billing management.
          Install from source or the public package source once published, then
          run the CLI directly.
        </p>
        <div className="font-mono text-xs bg-slate-bg border border-zinc-800 rounded p-3 text-slate-accent">
          slate verify -f frames/ -m shot.json --panel --bundle evidence.tar.gz
        </div>
      </div>
    </div>
  );
}
