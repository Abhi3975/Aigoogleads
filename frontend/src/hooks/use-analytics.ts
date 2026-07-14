'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AnalyticsSummary, AnalyticsTimeseries } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/analytics`;

function withCustomer(path: string, customerId?: string): string {
  return customerId ? `${path}?customer_id=${encodeURIComponent(customerId)}` : path;
}

export function useAnalyticsSummary(orgId: string | undefined, customerId?: string) {
  return useQuery({
    queryKey: ['analytics-summary', orgId, customerId ?? null],
    queryFn: () => api.get<AnalyticsSummary>(withCustomer(`${base(orgId!)}/summary`, customerId)),
    enabled: !!orgId,
  });
}

export function useAnalyticsTimeseries(orgId: string | undefined, customerId?: string) {
  return useQuery({
    queryKey: ['analytics-timeseries', orgId, customerId ?? null],
    queryFn: () =>
      api.get<AnalyticsTimeseries>(withCustomer(`${base(orgId!)}/timeseries`, customerId)),
    enabled: !!orgId,
  });
}
