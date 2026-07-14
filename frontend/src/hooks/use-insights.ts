'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AIInsight } from '@/lib/types';

export function useInsights(orgId: string | undefined, insightType?: string) {
  return useQuery({
    queryKey: ['ai-insights', orgId, insightType ?? null],
    queryFn: () => {
      const q = insightType ? `?insight_type=${encodeURIComponent(insightType)}` : '';
      return api.get<AIInsight[]>(`/organizations/${orgId}/ai/insights${q}`);
    },
    enabled: !!orgId,
  });
}
