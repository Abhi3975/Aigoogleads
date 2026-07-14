'use client';

import { motion } from 'framer-motion';
import { Gauge, History, Play, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useAccounts } from '@/hooks/use-google-ads';
import {
  useOptimizationLogs,
  usePolicy,
  useRunOptimization,
  useUpdatePolicy,
} from '@/hooks/use-optimization';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';
import type { OptimizationPolicy } from '@/lib/types';

const STATUS_VARIANT: Record<string, 'success' | 'secondary' | 'warning' | 'destructive'> = {
  executed: 'success',
  pending: 'warning',
  rejected: 'secondary',
  failed: 'destructive',
};

export default function OptimizationPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const policy = usePolicy(orgId);
  const logs = useOptimizationLogs(orgId);
  const accounts = useAccounts(orgId);
  const updatePolicy = useUpdatePolicy(orgId ?? '');
  const runOpt = useRunOptimization(orgId ?? '');
  const [customerId, setCustomerId] = useState('');

  async function onRun() {
    const cid = customerId || accounts.data?.[0]?.customer_id;
    if (!cid) {
      toast.error('Connect Google Ads and pick an account first');
      return;
    }
    try {
      const res = await runOpt.mutateAsync({ customer_id: cid });
      toast.success(`Optimization complete — ${res.applied} applied, ${res.pending} pending`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Optimization failed');
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Optimization center</h1>
          <p className="text-sm text-muted-foreground">
            AI recommendations, safety rules, and applied changes.
          </p>
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
          <Button onClick={() => void onRun()} disabled={runOpt.isPending}>
            {runOpt.isPending ? <Spinner className="size-4" /> : <Play className="size-4" />}
            Run optimization
          </Button>
        </div>
      </div>

      {policy.data && (
        <PolicyControls
          policy={policy.data}
          onSave={updatePolicy.mutateAsync}
          saving={updatePolicy.isPending}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="size-5" /> Optimization history
          </CardTitle>
          <CardDescription>Every AI decision, with reasoning and outcome.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {logs.isLoading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16" />)
          ) : logs.data && logs.data.length > 0 ? (
            logs.data.map((log) => (
              <div key={log.id} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium capitalize">
                    {log.action_type.replace(/_/g, ' ')}
                    {log.target ? ` · campaign ${log.target}` : ''}
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{Math.round(log.confidence * 100)}% conf</Badge>
                    <Badge variant={STATUS_VARIANT[log.status] ?? 'secondary'}>{log.status}</Badge>
                  </div>
                </div>
                {(log.previous_value != null || log.new_value != null) && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {log.previous_value ?? '—'} → {log.new_value ?? '—'}
                  </p>
                )}
                {log.explanation && (
                  <p className="mt-1 text-sm text-muted-foreground">{log.explanation}</p>
                )}
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
              <Gauge className="size-8 opacity-40" />
              <p className="text-sm">No optimizations yet. Run one to see AI decisions here.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function PolicyControls({
  policy,
  onSave,
  saving,
}: {
  policy: OptimizationPolicy;
  onSave: (patch: Partial<OptimizationPolicy>) => Promise<OptimizationPolicy>;
  saving: boolean;
}) {
  const [form, setForm] = useState(policy);
  useEffect(() => setForm(policy), [policy]);

  function num(key: keyof OptimizationPolicy) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: Number(e.target.value) }));
  }

  async function save() {
    try {
      await onSave(form);
      toast.success('Safety policy updated');
    } catch {
      toast.error('Could not update policy');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-5" /> Safety rules
        </CardTitle>
        <CardDescription>Bounds the AI must respect when optimizing autonomously.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-4">
          <Toggle
            label="Autonomous optimization"
            checked={form.enabled}
            onChange={(v) => setForm((f) => ({ ...f, enabled: v }))}
          />
          <Toggle
            label="Auto-execute changes"
            checked={form.auto_execute}
            onChange={(v) => setForm((f) => ({ ...f, auto_execute: v }))}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <NumField
            label="Max budget increase %"
            value={form.max_budget_increase_pct}
            onChange={num('max_budget_increase_pct')}
          />
          <NumField
            label="Max budget decrease %"
            value={form.max_budget_decrease_pct}
            onChange={num('max_budget_decrease_pct')}
          />
          <NumField
            label="Max bid change %"
            value={form.max_bid_change_pct}
            onChange={num('max_bid_change_pct')}
          />
          <NumField
            label="Min clicks to pause"
            value={form.min_clicks_required}
            onChange={num('min_clicks_required')}
          />
          <NumField
            label="Min days active"
            value={form.min_days_active}
            onChange={num('min_days_active')}
          />
          <NumField
            label="Min confidence (0-1)"
            value={form.min_confidence}
            onChange={num('min_confidence')}
            step="0.05"
          />
        </div>
        <Button onClick={() => void save()} disabled={saving}>
          {saving && <Spinner className="size-4" />} Save rules
        </Button>
      </CardContent>
    </Card>
  );
}

function NumField({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  step?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input type="number" step={step} value={value} onChange={onChange} />
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-sm"
    >
      <span
        className={`flex h-5 w-9 items-center rounded-full p-0.5 transition-colors ${
          checked ? 'bg-primary' : 'bg-muted'
        }`}
      >
        <span
          className={`size-4 rounded-full bg-background transition-transform ${
            checked ? 'translate-x-4' : ''
          }`}
        />
      </span>
      {label}
    </button>
  );
}
