'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Organization } from '@/lib/types';
import { useOrgSelection } from '@/providers/org-provider';

export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: () => api.get<Organization[]>('/organizations'),
  });
}

/** The active organization: the user's selection, else their first workspace. */
export function useCurrentOrg() {
  const query = useOrganizations();
  const { selectedOrgId, setSelectedOrgId } = useOrgSelection();
  const org = query.data?.find((o) => o.id === selectedOrgId) ?? query.data?.[0] ?? null;
  return { ...query, org, setSelectedOrgId };
}

export function useCreateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.post<Organization>('/organizations', { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['organizations'] }),
  });
}
