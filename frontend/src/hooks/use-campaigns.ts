'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  BusinessProfile,
  CampaignBlueprint,
  CampaignPlanResponse,
  ExecutionLog,
  OnboardingPayload,
} from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/campaigns`;

export function useOnboarding(orgId: string | undefined) {
  return useQuery({
    queryKey: ['onboarding', orgId],
    queryFn: () => api.get<BusinessProfile | null>(`${base(orgId!)}/onboarding`),
    enabled: !!orgId,
  });
}

export function useSaveOnboarding(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: OnboardingPayload) =>
      api.post<BusinessProfile>(`${base(orgId)}/onboarding`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['onboarding', orgId] }),
  });
}

export function usePlanCampaign(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { analyze_website: boolean; customer_id?: string | null }) =>
      api.post<CampaignPlanResponse>(`${base(orgId)}/plan`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['blueprints', orgId] }),
  });
}

export function useBlueprints(orgId: string | undefined) {
  return useQuery({
    queryKey: ['blueprints', orgId],
    queryFn: () => api.get<CampaignBlueprint[]>(base(orgId!)),
    enabled: !!orgId,
  });
}

export function useBlueprint(orgId: string | undefined, blueprintId: string | undefined) {
  return useQuery({
    queryKey: ['blueprint', orgId, blueprintId],
    queryFn: () => api.get<CampaignBlueprint>(`${base(orgId!)}/${blueprintId}`),
    enabled: !!orgId && !!blueprintId,
  });
}

export function useExecuteBlueprint(orgId: string, blueprintId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { customer_id: string; start_paused: boolean }) =>
      api.post<CampaignBlueprint>(`${base(orgId)}/${blueprintId}/execute`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['blueprint', orgId, blueprintId] });
      qc.invalidateQueries({ queryKey: ['execution-logs', orgId, blueprintId] });
    },
  });
}

export function useExecutionLogs(orgId: string | undefined, blueprintId: string | undefined) {
  return useQuery({
    queryKey: ['execution-logs', orgId, blueprintId],
    queryFn: () => api.get<ExecutionLog[]>(`${base(orgId!)}/${blueprintId}/execution-logs`),
    enabled: !!orgId && !!blueprintId,
  });
}
