'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { OrgMember, OrgRole } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/members`;

export function useMembers(orgId: string | undefined) {
  return useQuery({
    queryKey: ['members', orgId],
    queryFn: () => api.get<OrgMember[]>(base(orgId!)),
    enabled: !!orgId,
  });
}

export function useAddMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; role: OrgRole }) => api.post<OrgMember>(base(orgId), body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members', orgId] }),
  });
}

export function useUpdateMemberRole(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: OrgRole }) =>
      api.patch<OrgMember>(`${base(orgId)}/${userId}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members', orgId] }),
  });
}

export function useRemoveMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.del<void>(`${base(orgId)}/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members', orgId] }),
  });
}
