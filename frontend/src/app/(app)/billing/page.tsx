'use client';

import { motion } from 'framer-motion';
import { Check, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useBillingStatus, useChangePlan, usePlans } from '@/hooks/use-billing';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';

const limitLabel = (n: number) => (n < 0 ? 'Unlimited' : n.toLocaleString());

const PLAN_ORDER = ['free', 'starter', 'growth', 'enterprise'];

function planLimitRows(limits: Record<string, number>) {
  return [
    { label: 'AI runs / month', value: limitLabel(limits.monthly_ai_runs ?? 0) },
    { label: 'Google Ads accounts', value: limitLabel(limits.max_google_ads_accounts ?? 0) },
    { label: 'Active campaigns', value: limitLabel(limits.max_active_campaigns ?? 0) },
  ];
}

export default function BillingPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const status = useBillingStatus(orgId);
  const plans = usePlans(orgId);
  const changePlan = useChangePlan(orgId ?? '');
  const isOwner = org?.role === 'owner';

  async function onSwitch(plan: string) {
    try {
      await changePlan.mutateAsync(plan);
      toast.success(`Switched to the ${plan} plan`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not change plan');
    }
  }

  const aiLimit = status.data?.limits.monthly_ai_runs ?? 0;
  const aiUsed = status.data?.usage.ai_run ?? 0;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <CreditCard className="size-6" /> Billing
        </h1>
        <p className="text-sm text-muted-foreground">Your plan and usage for {org?.name}.</p>
      </div>

      {status.isLoading ? (
        <Skeleton className="h-32" />
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Current plan</CardTitle>
                <CardDescription>Usage resets monthly.</CardDescription>
              </div>
              <Badge className="capitalize">{status.data?.plan}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">AI runs this month</span>
              <span className="font-medium">
                {aiUsed} / {aiLimit < 0 ? '∞' : aiLimit}
              </span>
            </div>
            <Progress value={aiLimit > 0 ? Math.min(100, (aiUsed / aiLimit) * 100) : 0} />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {plans.isLoading
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-64" />)
          : [...(plans.data ?? [])]
              .sort((a, b) => PLAN_ORDER.indexOf(a.plan) - PLAN_ORDER.indexOf(b.plan))
              .map((p) => {
                const current = p.plan === status.data?.plan;
                return (
                  <Card key={p.plan} className={current ? 'border-primary' : ''}>
                    <CardHeader>
                      <CardTitle className="text-base capitalize">{p.plan}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <ul className="space-y-2 text-sm">
                        {planLimitRows(p.limits).map((row) => (
                          <li key={row.label} className="flex items-center gap-2">
                            <Check className="size-4 text-emerald-500" />
                            <span className="text-muted-foreground">{row.label}:</span>
                            <span className="font-medium">{row.value}</span>
                          </li>
                        ))}
                      </ul>
                      {current ? (
                        <Button variant="outline" className="w-full" disabled>
                          Current plan
                        </Button>
                      ) : (
                        <Button
                          className="w-full"
                          disabled={!isOwner || changePlan.isPending}
                          onClick={() => void onSwitch(p.plan)}
                        >
                          {changePlan.isPending && <Spinner className="size-4" />}
                          {isOwner ? `Switch to ${p.plan}` : 'Owner only'}
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
      </div>
    </motion.div>
  );
}
