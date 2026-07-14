'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AgentRun } from '@/lib/types';

export function useAiRuns(orgId: string | undefined) {
  return useQuery({
    queryKey: ['ai-runs', orgId],
    queryFn: () => api.get<AgentRun[]>(`/organizations/${orgId}/ai/runs`),
    enabled: !!orgId,
  });
}
