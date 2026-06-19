import { notFound } from "next/navigation";
import { getVerdict } from "@/lib/api";
import { VerdictDetail } from "@/components/verdict-detail";
import { getDashboardAuth } from "@/lib/dashboard-auth";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function VerdictDetailPage({ params }: PageProps) {
  const { id } = await params;
  const { token } = await getDashboardAuth();
  if (!token) notFound();
  const verdict = await getVerdict(token, id);
  if (!verdict) notFound();
  return <VerdictDetail verdict={verdict} />;
}
