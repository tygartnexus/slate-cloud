import { redirect } from "next/navigation";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { getDashboardAuth } from "@/lib/dashboard-auth";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId, isBypass } = await getDashboardAuth();
  if (!userId) redirect("/");

  return (
    <div className="min-h-screen">
      <nav className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="font-mono text-lg">
            slate
          </Link>
          <Link href="/dashboard" className="text-zinc-400 hover:text-zinc-100">
            Verdicts
          </Link>
          <Link
            href="/dashboard/license"
            className="text-zinc-400 hover:text-zinc-100"
          >
            Access
          </Link>
        </div>
        {isBypass ? (
          <span className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-400">
            E2E user
          </span>
        ) : (
          <UserButton />
        )}
      </nav>
      <main className="px-6 py-8 max-w-6xl mx-auto">{children}</main>
    </div>
  );
}
