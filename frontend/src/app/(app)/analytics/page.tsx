'use client';

import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';
import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendChart } from '@/components/ui/trend-chart';
import { useAnalyticsSummary, useAnalyticsTimeseries } from '@/hooks/use-analytics';
import { useAccounts } from '@/hooks/use-google-ads';
import { useCurrentOrg } from '@/hooks/use-organizations';
import type { KpiTotals } from '@/lib/types';

const money = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const pct = (n: number) => `${(n * 100).toFixed(2)}%`;

function kpiCards(t: KpiTotals) {
  return [
    { label: 'Spend', value: money(t.cost) },
    { label: 'ROAS', value: `${t.roas.toFixed(2)}x` },
    { label: 'Conversions', value: t.conversions.toLocaleString() },
    { label: 'CPA', value: money(t.cpa) },
    { label: 'CTR', value: pct(t.ctr) },
    { label: 'Avg CPC', value: money(t.average_cpc) },
    { label: 'Impressions', value: t.impressions.toLocaleString() },
    { label: 'Clicks', value: t.clicks.toLocaleString() },
  ];
}

export default function AnalyticsPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const accounts = useAccounts(orgId);
  const [customerId, setCustomerId] = useState<string>('');
  const summary = useAnalyticsSummary(orgId, customerId || undefined);
  const timeseries = useAnalyticsTimeseries(orgId, customerId || undefined);

  const totals = summary.data?.totals;
  const points = timeseries.data?.points ?? [];
  const hasData = !!totals && (totals.cost > 0 || (summary.data?.campaigns.length ?? 0) > 0);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Performance across your campaigns
            {summary.data?.as_of ? ` · as of ${summary.data.as_of}` : ''}
          </p>
        </div>
        <select
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All accounts</option>
          {accounts.data?.map((a) => (
            <option key={a.customer_id} value={a.customer_id}>
              {a.descriptive_name || a.customer_id}
            </option>
          ))}
        </select>
      </div>

      {summary.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : !hasData ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <BarChart3 className="size-10 opacity-40" />
            <p className="text-sm">
              No performance data yet. Connect Google Ads and run the optimization loop to collect
              metrics.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kpiCards(totals!).map((k) => (
              <Card key={k.label}>
                <CardContent className="p-5">
                  <p className="text-sm text-muted-foreground">{k.label}</p>
                  <p className="mt-1 text-2xl font-semibold">{k.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Spend over time</CardTitle>
                <CardDescription>Daily cost trend</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart values={points.map((p) => p.cost)} colorClassName="text-sky-500" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Conversions over time</CardTitle>
                <CardDescription>Daily conversions trend</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart
                  values={points.map((p) => p.conversions)}
                  colorClassName="text-emerald-500"
                />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Campaign performance</CardTitle>
              <CardDescription>Latest snapshot per campaign, by spend</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Campaign</th>
                    <th className="py-2 pr-4 font-medium">Spend</th>
                    <th className="py-2 pr-4 font-medium">Clicks</th>
                    <th className="py-2 pr-4 font-medium">Conv.</th>
                    <th className="py-2 pr-4 font-medium">CPA</th>
                    <th className="py-2 font-medium">ROAS</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data!.campaigns.map((c) => (
                    <tr key={c.campaign_id} className="border-b last:border-0">
                      <td className="py-2 pr-4">{c.campaign_name || c.campaign_id}</td>
                      <td className="py-2 pr-4">{money(c.cost)}</td>
                      <td className="py-2 pr-4">{c.clicks.toLocaleString()}</td>
                      <td className="py-2 pr-4">{c.conversions.toLocaleString()}</td>
                      <td className="py-2 pr-4">{money(c.cpa)}</td>
                      <td className="py-2">{c.roas.toFixed(2)}x</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </motion.div>
  );
}
