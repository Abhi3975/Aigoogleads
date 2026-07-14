'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { BillingStatus, PlanInfo } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/billing`;

export function useBillingStatus(orgId: string | undefined) {
  return useQuery({
    queryKey: ['billing-status', orgId],
    queryFn: () => api.get<BillingStatus>(`${base(orgId!)}/status`),
    enabled: !!orgId,
  });
}

export function usePlans(orgId: string | undefined) {
  return useQuery({
    queryKey: ['billing-plans', orgId],
    queryFn: () => api.get<PlanInfo[]>(`${base(orgId!)}/plans`),
    enabled: !!orgId,
  });
}

export function useChangePlan(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (plan: string) => api.patch<BillingStatus>(`${base(orgId)}/plan`, { plan }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['billing-status', orgId] });
      qc.invalidateQueries({ queryKey: ['organizations'] });
    },
  });
}
