'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { GoogleAdsAccount, GoogleAdsConnection } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/google-ads`;

export function useConnection(orgId: string | undefined) {
  return useQuery({
    queryKey: ['ga-connection', orgId],
    queryFn: () => api.get<GoogleAdsConnection | null>(`${base(orgId!)}/connection`),
    enabled: !!orgId,
  });
}

export function useAccounts(orgId: string | undefined) {
  return useQuery({
    queryKey: ['ga-accounts', orgId],
    queryFn: () => api.get<GoogleAdsAccount[]>(`${base(orgId!)}/accounts`),
    enabled: !!orgId,
  });
}

export function useConnectGoogleAds(orgId: string) {
  return useMutation({
    mutationFn: () =>
      api.post<{ authorization_url: string; state: string }>(`${base(orgId)}/connect`),
  });
}

export function useSyncAccounts(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<GoogleAdsAccount[]>(`${base(orgId)}/accounts/sync`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ga-accounts', orgId] }),
  });
}

export function useDisconnectGoogleAds(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.del<void>(`${base(orgId)}/connection`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ga-connection', orgId] });
      qc.invalidateQueries({ queryKey: ['ga-accounts', orgId] });
    },
  });
}
