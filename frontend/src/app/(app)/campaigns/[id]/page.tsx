'use client';

import { motion } from 'framer-motion';
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, Rocket } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useBlueprint, useExecuteBlueprint, useExecutionLogs } from '@/hooks/use-campaigns';
import { useAccounts } from '@/hooks/use-google-ads';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';
import type { CampaignBlueprint } from '@/lib/types';

export default function BlueprintDetailPage() {
  const params = useParams<{ id: string }>();
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const blueprint = useBlueprint(orgId, params.id);
  const accounts = useAccounts(orgId);
  const logs = useExecutionLogs(orgId, params.id);
  const execute = useExecuteBlueprint(orgId ?? '', params.id);
  const [customerId, setCustomerId] = useState('');

  if (blueprint.isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }
  if (!blueprint.data) {
    return <p className="text-sm text-muted-foreground">Blueprint not found.</p>;
  }
  const bp = blueprint.data;
  const created = bp.status === 'created';

  async function onExecute() {
    const cid = customerId || accounts.data?.[0]?.customer_id;
    if (!cid) {
      toast.error('Connect Google Ads and select an account first');
      return;
    }
    try {
      await execute.mutateAsync({ customer_id: cid, start_paused: true });
      toast.success('Campaign created (paused) in Google Ads');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Execution failed');
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-4xl space-y-6"
    >
      <Link
        href="/campaigns"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Campaigns
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{bp.campaign_name}</h1>
          <p className="text-sm text-muted-foreground">{bp.objective}</p>
        </div>
        <Badge variant={created ? 'success' : bp.status === 'failed' ? 'destructive' : 'secondary'}>
          {bp.status}
        </Badge>
      </div>

      <StatusStages blueprint={bp} />

      {bp.structure?.validation_warnings?.length > 0 && (
        <Card className="border-amber-500/40">
          <CardContent className="flex gap-3 p-4 text-sm">
            <AlertTriangle className="size-5 shrink-0 text-amber-500" />
            <ul className="list-inside list-disc text-muted-foreground">
              {bp.structure.validation_warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Meta label="Type" value={bp.campaign_type} />
        <Meta label="Daily budget" value={`$${bp.daily_budget}`} />
        <Meta label="Bidding" value={bp.bidding_strategy} />
        <Meta label="Locations" value={bp.structure?.location_targeting?.join(', ') || '—'} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ad groups</CardTitle>
          <CardDescription>Keywords and generated ads per group.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {bp.structure?.ad_groups?.map((ag) => (
            <div key={ag.name} className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="font-medium">{ag.name}</p>
                <span className="text-xs text-muted-foreground">{ag.theme}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {ag.keywords.map((k, i) => (
                  <Badge key={`${k.text}-${i}`} variant="outline" className="font-normal">
                    {k.text} · {k.match_type.toLowerCase()}
                  </Badge>
                ))}
              </div>
              {ag.ad && (
                <div className="rounded-md bg-muted/50 p-3 text-sm">
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Headlines</p>
                  <p>{ag.ad.headlines.slice(0, 5).join(' · ')}</p>
                  <p className="mb-1 mt-2 text-xs font-medium text-muted-foreground">
                    Descriptions
                  </p>
                  <p>{ag.ad.descriptions.join(' ')}</p>
                </div>
              )}
              <Separator />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Launch</CardTitle>
          <CardDescription>
            {created
              ? 'This campaign has been created in Google Ads (paused).'
              : 'Create this campaign in your Google Ads account. It starts paused.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {created ? (
            <p className="text-sm">
              Google campaign id:{' '}
              <code className="rounded bg-muted px-1.5 py-0.5">{bp.google_campaign_id}</code>
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">Select account…</option>
                {accounts.data?.map((a) => (
                  <option key={a.customer_id} value={a.customer_id}>
                    {a.descriptive_name || a.customer_id}
                  </option>
                ))}
              </select>
              <Button onClick={() => void onExecute()} disabled={execute.isPending}>
                {execute.isPending ? <Spinner className="size-4" /> : <Rocket className="size-4" />}
                Create in Google Ads
              </Button>
              {(!accounts.data || accounts.data.length === 0) && (
                <Link href="/settings" className="text-sm text-primary hover:underline">
                  Connect Google Ads
                </Link>
              )}
            </div>
          )}

          {logs.data && logs.data.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <p className="text-sm font-medium">Execution log</p>
              {logs.data.map((log) => (
                <div key={log.id} className="flex items-center gap-2 text-sm">
                  <CheckCircle2
                    className={
                      log.status === 'success'
                        ? 'size-4 text-emerald-500'
                        : 'size-4 text-destructive'
                    }
                  />
                  <span className="text-muted-foreground">
                    {log.action} {log.google_resource_id ? `· ${log.google_resource_id}` : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function StatusStages({ blueprint }: { blueprint: CampaignBlueprint }) {
  const s = blueprint.structure;
  const stages = [
    { label: 'Business analyzed', done: !!s },
    { label: 'Strategy generated', done: !!s?.campaign_name },
    { label: 'Keywords generated', done: !!s?.ad_groups?.some((g) => g.keywords.length > 0) },
    { label: 'Ads generated', done: !!s?.ad_groups?.some((g) => g.ad) },
    { label: 'Campaign created', done: blueprint.status === 'created' },
  ];
  return (
    <Card>
      <CardContent className="flex flex-wrap gap-x-6 gap-y-2 p-4">
        {stages.map((stage) => (
          <div key={stage.label} className="flex items-center gap-2 text-sm">
            {stage.done ? (
              <CheckCircle2 className="size-4 text-emerald-500" />
            ) : (
              <Circle className="size-4 text-muted-foreground/40" />
            )}
            <span className={stage.done ? '' : 'text-muted-foreground'}>{stage.label}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 truncate text-sm font-medium">{value}</p>
      </CardContent>
    </Card>
  );
}
