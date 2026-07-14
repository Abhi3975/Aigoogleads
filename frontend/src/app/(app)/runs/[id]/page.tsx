'use client';

import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useAiRun } from '@/hooks/use-ai';
import { useCurrentOrg } from '@/hooks/use-organizations';

const STATUS_VARIANT: Record<string, 'success' | 'secondary' | 'destructive'> = {
  completed: 'success',
  running: 'secondary',
  failed: 'destructive',
};

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const { org } = useCurrentOrg();
  const run = useAiRun(org?.id, params.id);

  if (run.isLoading) return <Skeleton className="h-96 w-full" />;
  if (!run.data) return <p className="text-sm text-muted-foreground">Run not found.</p>;
  const r = run.data;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-3xl space-y-6"
    >
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Dashboard
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold capitalize tracking-tight">
            {r.workflow.replace(/_/g, ' ')}
          </h1>
          <p className="text-sm text-muted-foreground">
            {new Date(r.created_at).toLocaleString()} · {r.total_tokens} tokens
          </p>
        </div>
        <Badge variant={STATUS_VARIANT[r.status] ?? 'secondary'}>{r.status}</Badge>
      </div>

      {r.error && (
        <Card className="border-destructive/40">
          <CardContent className="p-4 text-sm text-destructive">{r.error}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Decision log</CardTitle>
          <CardDescription>Each agent step, in order, with its reasoning.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {r.steps && r.steps.length > 0 ? (
            r.steps.map((step) => (
              <div key={step.id} className="rounded-md border p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">
                    {step.sequence}. {step.agent_name.replace(/_/g, ' ')}
                  </span>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {step.usage?.total_tokens ? <span>{step.usage.total_tokens} tok</span> : null}
                    <Badge variant={step.status === 'completed' ? 'success' : 'secondary'}>
                      {step.status}
                    </Badge>
                  </div>
                </div>
                {step.reasoning && (
                  <p className="mt-2 text-sm text-muted-foreground">{step.reasoning}</p>
                )}
                {step.tool_calls && step.tool_calls.length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {step.tool_calls.length} tool call{step.tool_calls.length > 1 ? 's' : ''}
                  </p>
                )}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No steps recorded.</p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
