'use client';

import { motion } from 'framer-motion';
import {
  Activity,
  CheckCircle2,
  DollarSign,
  Megaphone,
  MousePointerClick,
  Plug,
  Target,
  TrendingUp,
  Wand2,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useAiRuns } from '@/hooks/use-ai';
import { useAnalyticsSummary } from '@/hooks/use-analytics';
import { useBlueprints, useOnboarding } from '@/hooks/use-campaigns';
import { useConnection } from '@/hooks/use-google-ads';
import { useCurrentOrg } from '@/hooks/use-organizations';

const money = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-semibold">{value}</p>
        </div>
        <Icon className="size-8 text-muted-foreground/40" />
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { org, isLoading: orgLoading } = useCurrentOrg();
  const orgId = org?.id;
  const onboarding = useOnboarding(orgId);
  const blueprints = useBlueprints(orgId);
  const runs = useAiRuns(orgId);
  const connection = useConnection(orgId);
  const analytics = useAnalyticsSummary(orgId);

  const created = blueprints.data?.filter((b) => b.status === 'created').length ?? 0;
  const isConnected = !!connection.data && connection.data.status === 'active';
  const totals = analytics.data?.totals;
  const hasPerformance = !!totals && totals.cost > 0;

  // Brand-new accounts (no profile, no campaigns) start at the onboarding wizard.
  const router = useRouter();
  useEffect(() => {
    if (
      !onboarding.isLoading &&
      onboarding.data === null &&
      !blueprints.isLoading &&
      (blueprints.data?.length ?? 0) === 0
    ) {
      router.replace('/onboarding');
    }
  }, [onboarding.isLoading, onboarding.data, blueprints.isLoading, blueprints.data, router]);

  if (orgLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">{org?.name}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/onboarding">
              <Wand2 className="size-4" /> Onboarding
            </Link>
          </Button>
          <Button asChild>
            <Link href="/campaigns">
              <Megaphone className="size-4" /> Campaigns
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Campaigns created" value={String(created)} icon={Megaphone} />
        <StatCard label="AI runs" value={String(runs.data?.length ?? 0)} icon={Activity} />
        <StatCard
          label="Business profile"
          value={onboarding.data ? 'Complete' : 'Pending'}
          icon={CheckCircle2}
        />
        <StatCard label="Google Ads" value={isConnected ? 'Connected' : 'Not linked'} icon={Plug} />
      </div>

      {hasPerformance && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">Performance</h2>
            <Link href="/analytics" className="text-xs text-primary hover:underline">
              View analytics
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Spend" value={money(totals!.cost)} icon={DollarSign} />
            <StatCard label="ROAS" value={`${totals!.roas.toFixed(2)}x`} icon={TrendingUp} />
            <StatCard
              label="Conversions"
              value={totals!.conversions.toLocaleString()}
              icon={Target}
            />
            <StatCard
              label="CTR"
              value={`${(totals!.ctr * 100).toFixed(2)}%`}
              icon={MousePointerClick}
            />
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent AI activity</CardTitle>
            <CardDescription>Autonomous agent runs across your workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {runs.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12" />)
            ) : runs.data && runs.data.length > 0 ? (
              runs.data.slice(0, 6).map((run) => (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  className="flex items-center justify-between rounded-md border px-4 py-3 transition-colors hover:bg-accent"
                >
                  <div>
                    <p className="text-sm font-medium capitalize">
                      {run.workflow.replace('_', ' ')}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(run.created_at).toLocaleString()} · {run.total_tokens} tokens
                    </p>
                  </div>
                  <Badge
                    variant={
                      run.status === 'completed'
                        ? 'success'
                        : run.status === 'failed'
                          ? 'destructive'
                          : 'secondary'
                    }
                  >
                    {run.status}
                  </Badge>
                </Link>
              ))
            ) : (
              <div className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
                <Activity className="size-8 opacity-40" />
                <p className="text-sm">No AI runs yet.</p>
                <Button asChild size="sm" variant="outline">
                  <Link href="/campaigns">Create your first campaign</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Get started</CardTitle>
            <CardDescription>Three steps to autonomous ads.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Step
              done={!!onboarding.data}
              label="Complete business onboarding"
              href="/onboarding"
            />
            <Step done={isConnected} label="Connect Google Ads" href="/settings" />
            <Step done={created > 0} label="Generate & launch a campaign" href="/campaigns" />
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}

function Step({ done, label, href }: { done: boolean; label: string; href: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-md border px-3 py-2 transition-colors hover:bg-accent"
    >
      <CheckCircle2
        className={done ? 'size-5 text-emerald-500' : 'size-5 text-muted-foreground/30'}
      />
      <span className={done ? 'text-muted-foreground line-through' : ''}>{label}</span>
    </Link>
  );
}
