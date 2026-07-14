'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { DailyReport } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/reports`;

export function useReports(orgId: string | undefined) {
  return useQuery({
    queryKey: ['reports', orgId],
    queryFn: () => api.get<DailyReport[]>(base(orgId!)),
    enabled: !!orgId,
  });
}

export function useGenerateReport(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (customerId: string) =>
      api.post<DailyReport>(`${base(orgId)}/generate`, { customer_id: customerId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports', orgId] }),
  });
}
