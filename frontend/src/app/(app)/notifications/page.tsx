'use client';

import { motion } from 'framer-motion';
import { BellOff, CheckCheck } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useMarkAllRead, useMarkRead, useNotifications } from '@/hooks/use-notifications';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { cn } from '@/lib/utils';

function severityVariant(s: string): 'destructive' | 'warning' | 'secondary' {
  if (s === 'critical') return 'destructive';
  if (s === 'warning') return 'warning';
  return 'secondary';
}

export default function NotificationsPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const [unreadOnly, setUnreadOnly] = useState(false);
  const notifications = useNotifications(orgId, unreadOnly);
  const markRead = useMarkRead(orgId ?? '');
  const markAll = useMarkAllRead(orgId ?? '');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-2xl space-y-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">Alerts and AI activity for {org?.name}.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border p-0.5 text-sm">
            <button
              onClick={() => setUnreadOnly(false)}
              className={cn(
                'rounded px-3 py-1',
                !unreadOnly && 'bg-primary text-primary-foreground',
              )}
            >
              All
            </button>
            <button
              onClick={() => setUnreadOnly(true)}
              className={cn(
                'rounded px-3 py-1',
                unreadOnly && 'bg-primary text-primary-foreground',
              )}
            >
              Unread
            </button>
          </div>
          <Button variant="outline" onClick={() => markAll.mutate()} disabled={markAll.isPending}>
            <CheckCheck className="size-4" /> Mark all read
          </Button>
        </div>
      </div>

      {notifications.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : notifications.data && notifications.data.length > 0 ? (
        <div className="space-y-2">
          {notifications.data.map((n) => (
            <Card
              key={n.id}
              className={cn('cursor-pointer transition-colors', !n.is_read && 'border-primary/40')}
              onClick={() => !n.is_read && markRead.mutate(n.id)}
            >
              <CardContent className="flex items-start justify-between gap-3 p-4">
                <div>
                  <div className="flex items-center gap-2">
                    {!n.is_read && <span className="size-2 rounded-full bg-primary" />}
                    <p className="text-sm font-medium">{n.title}</p>
                  </div>
                  {n.body && <p className="mt-1 text-sm text-muted-foreground">{n.body}</p>}
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(n.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={severityVariant(n.severity)}>{n.type}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <BellOff className="size-10 opacity-40" />
            <p className="text-sm">
              {unreadOnly ? 'No unread notifications.' : 'No notifications yet.'}
            </p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
