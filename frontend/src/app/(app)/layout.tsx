'use client';

import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { AppShell } from '@/components/app-shell';
import { Spinner } from '@/components/ui/spinner';
import { useAuth } from '@/providers/auth-provider';

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
