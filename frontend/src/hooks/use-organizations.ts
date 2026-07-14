'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Organization } from '@/lib/types';

export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: () => api.get<Organization[]>('/organizations'),
  });
}

/** The user's primary organization (their default workspace). */
export function useCurrentOrg() {
  const query = useOrganizations();
  return { ...query, org: query.data?.[0] ?? null };
}
