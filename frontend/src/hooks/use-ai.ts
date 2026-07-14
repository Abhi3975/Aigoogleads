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

export function useAiRun(orgId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: ['ai-run', orgId, runId],
    queryFn: () => api.get<AgentRun>(`/organizations/${orgId}/ai/runs/${runId}`),
    enabled: !!orgId && !!runId,
  });
}
