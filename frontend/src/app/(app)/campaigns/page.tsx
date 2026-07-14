'use client';

import { Megaphone, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useBlueprints, useOnboarding, usePlanCampaign } from '@/hooks/use-campaigns';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';
import type { CampaignBlueprint } from '@/lib/types';

const STATUS_VARIANT: Record<string, 'success' | 'secondary' | 'warning' | 'destructive'> = {
  created: 'success',
  draft: 'secondary',
  executing: 'warning',
  failed: 'destructive',
};

export default function CampaignsPage() {
  const router = useRouter();
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const onboarding = useOnboarding(orgId);
  const blueprints = useBlueprints(orgId);
  const plan = usePlanCampaign(orgId ?? '');

  async function generate() {
    if (!onboarding.data) {
      toast.error('Complete onboarding first');
      router.push('/onboarding');
      return;
    }
    try {
      const res = await plan.mutateAsync({ analyze_website: true });
      toast.success('AI strategy generated');
      router.push(`/campaigns/${res.blueprint.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Planning failed');
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
          <p className="text-sm text-muted-foreground">AI-generated campaign blueprints.</p>
        </div>
        <Button onClick={() => void generate()} disabled={plan.isPending}>
          {plan.isPending ? <Spinner className="size-4" /> : <Sparkles className="size-4" />}
          Generate AI strategy
        </Button>
      </div>

      {plan.isPending && (
        <Card>
          <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
            <Spinner className="size-4" />
            The AI agents are analyzing your business and designing a campaign…
          </CardContent>
        </Card>
      )}

      {blueprints.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : blueprints.data && blueprints.data.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {blueprints.data.map((bp) => (
            <BlueprintCard key={bp.id} blueprint={bp} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <Megaphone className="size-10 opacity-40" />
            <p className="text-sm">No campaigns yet.</p>
            <Button onClick={() => void generate()} disabled={plan.isPending}>
              <Sparkles className="size-4" /> Generate your first campaign
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BlueprintCard({ blueprint }: { blueprint: CampaignBlueprint }) {
  return (
    <Link href={`/campaigns/${blueprint.id}`}>
      <Card className="h-full transition-colors hover:border-primary/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{blueprint.campaign_name}</CardTitle>
            <Badge variant={STATUS_VARIANT[blueprint.status] ?? 'secondary'}>
              {blueprint.status}
            </Badge>
          </div>
          <CardDescription>{blueprint.objective}</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-4 text-sm text-muted-foreground">
          <span>{blueprint.campaign_type}</span>
          <span>·</span>
          <span>{blueprint.structure?.ad_groups?.length ?? 0} ad groups</span>
          <span>·</span>
          <span>${blueprint.daily_budget}/day</span>
        </CardContent>
      </Card>
    </Link>
  );
}
