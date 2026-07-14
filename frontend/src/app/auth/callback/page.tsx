'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { setTokens } from '@/lib/tokens';
import { useAuth } from '@/providers/auth-provider';

/** Receives tokens from the OAuth redirect (URL fragment) and signs the user in. */
export default function AuthCallbackPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, '');
    const params = new URLSearchParams(hash);
    const access = params.get('access_token');
    const refresh = params.get('refresh_token');

    if (access && refresh) {
      setTokens(access, refresh);
      // Strip tokens from the URL before doing anything else.
      window.history.replaceState(null, '', window.location.pathname);
      void refreshUser().then(() => router.replace('/dashboard'));
    } else {
      router.replace('/login');
    }
  }, [refreshUser, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner className="size-6 text-muted-foreground" />
    </div>
  );
}
