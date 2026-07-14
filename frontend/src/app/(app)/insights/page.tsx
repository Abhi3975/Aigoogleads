'use client';

import { motion } from 'framer-motion';
import { Brain, Lightbulb } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useInsights } from '@/hooks/use-insights';
import { useCurrentOrg } from '@/hooks/use-organizations';

export default function InsightsPage() {
  const { org } = useCurrentOrg();
  const insights = useInsights(org?.id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-3xl space-y-6"
    >
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Brain className="size-6 text-primary" /> AI Brain
        </h1>
        <p className="text-sm text-muted-foreground">
          Durable learnings the AI records from outcomes, ranked by importance.
        </p>
      </div>

      {insights.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : insights.data && insights.data.length > 0 ? (
        <div className="space-y-3">
          {insights.data.map((insight) => (
            <Card key={insight.id}>
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm">{insight.observation}</p>
                  <Badge variant="outline" className="shrink-0 capitalize">
                    {insight.insight_type}
                  </Badge>
                </div>
                {insight.outcome && (
                  <p className="text-sm text-muted-foreground">Outcome: {insight.outcome}</p>
                )}
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
                  <span>{insight.agent_name.replace(/_/g, ' ')}</span>
                  <span>{new Date(insight.created_at).toLocaleString()}</span>
                  <span className="flex items-center gap-2">
                    importance
                    <Progress value={insight.importance_score * 100} className="h-1.5 w-20" />
                  </span>
                  <span>{Math.round(insight.confidence * 100)}% confidence</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <Lightbulb className="size-10 opacity-40" />
            <p className="text-sm">
              No learnings yet. As the AI runs optimizations, it records what worked here.
            </p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
