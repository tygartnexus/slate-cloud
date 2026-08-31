import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "..");

// Scan roots are repo-relative. Earlier revisions also reached into sibling
// private-monorepo directories, which silently scanned nothing in a clone.
const scanRoots = [
  path.join(root, "README.md"),
  path.join(root, "docs"),
  path.join(root, "frontend", "app"),
  path.join(root, "frontend", "components"),
  path.join(root, "frontend", "lib"),
  path.join(root, "backend", "app"),
];

const PROSE = new Set([".md"]);
const CODE = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".py"]);

// A file may opt out of one rule with an auditable marker comment:
//   content-check-allow: <rule-id>
// This exists so legitimate legacy-compatibility code does not have to obscure
// itself from the scanner (it previously did, via string concatenation).
const ALLOW_MARKER = /content-check-allow:\s*([a-z0-9-]+)/gi;

const banned = [
  {
    id: "thrawn-naming",
    // Prose only. The legacy key is still accepted in code for backward
    // compatibility with older verdict JSON.
    scope: "prose",
    pattern: /\bThrawn\b/i,
    reason:
      "public copy should use Panel naming; thrawn is legacy JSON compatibility only",
  },
  {
    id: "absolute-frame-privacy",
    scope: "all",
    pattern: /frames never leave/i,
    reason: "frame privacy must be provider-scoped, not absolute",
  },
  {
    id: "unverified-pypi",
    scope: "all",
    pattern: /Core is on PyPI now/i,
    reason: "PyPI release must be verified before launch copy says it is live",
  },
  {
    id: "slate-product-levels",
    scope: "all",
    pattern: /\bSlate\s+(Core|Pro)\b/i,
    reason:
      "public copy should present one Slate product, not multiple Slate levels",
  },
  {
    id: "paid-plans",
    scope: "all",
    pattern:
      /\$\s*(29|149|290|1,490|5K)|Start Pro|Start Studio|Buy at|Stripe Checkout|customer portal|pricing tier/i,
    reason: "public copy should not advertise paid Slate plans",
  },
  {
    id: "chain-of-thought",
    scope: "all",
    pattern: /chains?-of-thought/i,
    reason:
      "evidence copy should promise persona reports, not chain-of-thought",
  },
  {
    id: "enterprise-tier",
    scope: "all",
    pattern: /self-hosted\s*\+\s*SSO\s*\+\s*SLA/i,
    reason: "Enterprise paid-tier claims should not remain in public copy",
  },
  {
    id: "license-gating",
    scope: "all",
    pattern: /license[- ]gated|valid license key|purchase a plan/i,
    reason:
      "Slate features are free and must not require activation or purchase",
  },
  {
    id: "overbroad-claims",
    scope: "prose",
    pattern: /not good enough|every shot/i,
    reason:
      "public claims should be evidence-bounded, not overbroad or self-dismissive",
  },
  {
    id: "public-api-url",
    scope: "all",
    pattern: /NEXT_PUBLIC_API_URL/i,
    reason: "authenticated backend calls must use server-only SLATE_API_URL",
  },
  {
    id: "unimplemented-comparison",
    scope: "all",
    pattern:
      /view history, and compare|history and comparisons|side-by-side verdict|dashboard stores verdict JSON for history and comparisons/i,
    reason:
      "public copy must not claim comparison features until they are implemented",
  },
  {
    id: "commercial-split",
    scope: "all",
    pattern:
      /Pro \/ Studio \/ Enterprise are commercial|private `?slate-cloud`? repo|Pro's value proposition|OSS Panel-equivalent/i,
    reason:
      "public copy must present one free/open-source Slate, including Panel and evidence bundles",
  },
];

const candidateFiles = scanRoots.flatMap((entry) => collectFiles(entry));

const failures = [];
for (const file of candidateFiles) {
  const text = fs.readFileSync(file, "utf8");
  const isProse = PROSE.has(path.extname(file).toLowerCase());
  const allowed = new Set(
    [...text.matchAll(ALLOW_MARKER)].map((m) => m[1].toLowerCase()),
  );

  for (const rule of banned) {
    if (rule.scope === "prose" && !isProse) continue;
    if (allowed.has(rule.id)) continue;
    if (rule.pattern.test(text)) {
      failures.push(`${path.relative(root, file)} [${rule.id}]: ${rule.reason}`);
    }
  }
}

if (failures.length) {
  console.error("Content claim check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Content claim check passed (${candidateFiles.length} files scanned).`);

function collectFiles(entry) {
  if (!fs.existsSync(entry)) return [];
  const stat = fs.statSync(entry);
  if (stat.isFile()) return isScannable(entry) ? [entry] : [];
  if (!stat.isDirectory()) return [];
  return fs.readdirSync(entry, { withFileTypes: true }).flatMap((child) => {
    const childPath = path.join(entry, child.name);
    if (child.isDirectory()) {
      if (
        [
          "node_modules",
          ".next",
          "__pycache__",
          ".git",
          ".venv",
          "dist",
          "build",
          ".mypy_cache",
          ".pytest_cache",
          ".ruff_cache",
        ].includes(child.name)
      ) {
        return [];
      }
      return collectFiles(childPath);
    }
    return isScannable(childPath) ? [childPath] : [];
  });
}

function isScannable(file) {
  const ext = path.extname(file).toLowerCase();
  return PROSE.has(ext) || CODE.has(ext);
}
