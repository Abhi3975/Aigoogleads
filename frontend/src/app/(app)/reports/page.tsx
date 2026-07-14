'use client';

import { motion } from 'framer-motion';
import { FileText, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useAccounts } from '@/hooks/use-google-ads';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { useGenerateReport, useReports } from '@/hooks/use-reports';
import { ApiError } from '@/lib/api';

export default function ReportsPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const accounts = useAccounts(orgId);
  const reports = useReports(orgId);
  const generate = useGenerateReport(orgId ?? '');
  const [customerId, setCustomerId] = useState('');

  async function onGenerate() {
    const cid = customerId || accounts.data?.[0]?.customer_id;
    if (!cid) {
      toast.error('Connect Google Ads and pick an account first');
      return;
    }
    try {
      await generate.mutateAsync(cid);
      toast.success('Report generated');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not generate report');
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">Daily performance summaries.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">Account…</option>
            {accounts.data?.map((a) => (
              <option key={a.customer_id} value={a.customer_id}>
                {a.descriptive_name || a.customer_id}
              </option>
            ))}
          </select>
          <Button onClick={() => void onGenerate()} disabled={generate.isPending}>
            {generate.isPending ? <Spinner className="size-4" /> : <Sparkles className="size-4" />}
            Generate report
          </Button>
        </div>
      </div>

      {reports.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : reports.data && reports.data.length > 0 ? (
        <div className="space-y-3">
          {reports.data.map((r) => (
            <Card key={r.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="text-sm font-medium">{r.date}</p>
                  <p className="text-sm text-muted-foreground">{r.summary}</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="outline">Spend ${r.totals.cost ?? 0}</Badge>
                  <Badge variant="outline">{r.totals.conversions ?? 0} conv.</Badge>
                  <Badge variant="secondary">ROAS {r.totals.roas ?? 0}x</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <FileText className="size-10 opacity-40" />
            <p className="text-sm">No reports yet. Generate one from a connected account.</p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
