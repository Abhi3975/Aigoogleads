'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { OptimizationLog, OptimizationPolicy, OptimizationRunSummary } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/optimization`;

export function usePolicy(orgId: string | undefined) {
  return useQuery({
    queryKey: ['opt-policy', orgId],
    queryFn: () => api.get<OptimizationPolicy>(`${base(orgId!)}/policy`),
    enabled: !!orgId,
  });
}

export function useUpdatePolicy(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<OptimizationPolicy>) =>
      api.patch<OptimizationPolicy>(`${base(orgId)}/policy`, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['opt-policy', orgId] }),
  });
}

export function useOptimizationLogs(orgId: string | undefined) {
  return useQuery({
    queryKey: ['opt-logs', orgId],
    queryFn: () => api.get<OptimizationLog[]>(`${base(orgId!)}/logs`),
    enabled: !!orgId,
  });
}

export function useRunOptimization(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { customer_id: string; auto_execute?: boolean }) =>
      api.post<OptimizationRunSummary>(`${base(orgId)}/run`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['opt-logs', orgId] });
      qc.invalidateQueries({ queryKey: ['notifications', orgId] });
    },
  });
}
