'use client';

import { Bell } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useMarkAllRead, useNotifications, useUnreadCount } from '@/hooks/use-notifications';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { cn } from '@/lib/utils';

export function NotificationsBell() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const [open, setOpen] = useState(false);
  const unread = useUnreadCount(orgId);
  const notifications = useNotifications(orgId);
  const markAll = useMarkAllRead(orgId ?? '');
  const count = unread.data?.unread ?? 0;

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
      >
        <Bell />
        {count > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg border bg-popover text-popover-foreground shadow-lg">
            <div className="flex items-center justify-between border-b px-4 py-2.5">
              <span className="text-sm font-medium">Notifications</span>
              {count > 0 && (
                <button
                  className="text-xs text-primary hover:underline"
                  onClick={() => markAll.mutate()}
                >
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {notifications.data && notifications.data.length > 0 ? (
                notifications.data.slice(0, 12).map((n) => (
                  <div
                    key={n.id}
                    className={cn('border-b px-4 py-3 text-sm', !n.is_read && 'bg-accent/40')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{n.title}</span>
                      <Badge
                        variant={
                          n.severity === 'critical'
                            ? 'destructive'
                            : n.severity === 'warning'
                              ? 'warning'
                              : 'secondary'
                        }
                      >
                        {n.type}
                      </Badge>
                    </div>
                    {n.body && <p className="mt-1 text-xs text-muted-foreground">{n.body}</p>}
                  </div>
                ))
              ) : (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No notifications yet.
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
