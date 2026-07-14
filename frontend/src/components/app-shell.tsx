'use client';

import {
  LayoutDashboard,
  LogOut,
  Megaphone,
  Settings,
  Sparkles,
  TrendingUp,
  Wand2,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';
import { NotificationsBell } from '@/components/notifications-bell';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/providers/auth-provider';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/onboarding', label: 'Onboarding', icon: Wand2 },
  { href: '/campaigns', label: 'Campaigns', icon: Megaphone },
  { href: '/optimization', label: 'Optimization', icon: TrendingUp },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 flex-col border-r bg-card/40 md:flex">
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <Sparkles className="size-5 text-primary" />
          <span className="font-semibold">AI Ads Agent</span>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t p-3 text-xs text-muted-foreground">Autonomous AI marketing</div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b px-4 md:px-8">
          <div className="text-sm text-muted-foreground md:hidden">AI Ads Agent</div>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {user?.full_name || user?.email}
            </span>
            <NotificationsBell />
            <ThemeToggle />
            <Button variant="ghost" size="icon" aria-label="Log out" onClick={() => void logout()}>
              <LogOut />
            </Button>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
