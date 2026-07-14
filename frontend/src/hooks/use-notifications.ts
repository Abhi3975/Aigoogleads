'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AppNotification } from '@/lib/types';

const base = (orgId: string) => `/organizations/${orgId}/notifications`;

export function useNotifications(orgId: string | undefined) {
  return useQuery({
    queryKey: ['notifications', orgId],
    queryFn: () => api.get<AppNotification[]>(base(orgId!)),
    enabled: !!orgId,
    refetchInterval: 60_000,
  });
}

export function useUnreadCount(orgId: string | undefined) {
  return useQuery({
    queryKey: ['notifications-unread', orgId],
    queryFn: () => api.get<{ unread: number }>(`${base(orgId!)}/unread-count`),
    enabled: !!orgId,
    refetchInterval: 60_000,
  });
}

export function useMarkAllRead(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`${base(orgId)}/read-all`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', orgId] });
      qc.invalidateQueries({ queryKey: ['notifications-unread', orgId] });
    },
  });
}
