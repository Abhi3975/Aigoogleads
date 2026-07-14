'use client';

import { Plug, RefreshCw, Unplug } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import {
  useAccounts,
  useConnectGoogleAds,
  useConnection,
  useDisconnectGoogleAds,
  useSyncAccounts,
} from '@/hooks/use-google-ads';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';

export default function SettingsPage() {
  const { org } = useCurrentOrg();
  const orgId = org?.id;
  const connection = useConnection(orgId);
  const accounts = useAccounts(orgId);
  const connect = useConnectGoogleAds(orgId ?? '');
  const sync = useSyncAccounts(orgId ?? '');
  const disconnect = useDisconnectGoogleAds(orgId ?? '');

  const isConnected = !!connection.data && connection.data.status === 'active';

  async function onConnect() {
    try {
      const res = await connect.mutateAsync();
      window.location.href = res.authorization_url;
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Google Ads is not configured');
    }
  }

  async function onSync() {
    try {
      await sync.mutateAsync();
      toast.success('Accounts synced');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Sync failed');
    }
  }

  async function onDisconnect() {
    if (!window.confirm('Disconnect Google Ads? The AI will no longer manage your campaigns.')) {
      return;
    }
    try {
      await disconnect.mutateAsync();
      toast.success('Google Ads disconnected');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not disconnect');
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">{org?.name}</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Plug className="size-5" /> Google Ads
              </CardTitle>
              <CardDescription>
                Connect your account so the AI can manage campaigns.
              </CardDescription>
            </div>
            {connection.isLoading ? (
              <Skeleton className="h-6 w-20" />
            ) : (
              <Badge variant={isConnected ? 'success' : 'secondary'}>
                {isConnected ? 'Connected' : 'Not connected'}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button onClick={() => void onConnect()} disabled={connect.isPending}>
              {connect.isPending && <Spinner className="size-4" />}
              {isConnected ? 'Reconnect' : 'Connect Google Ads'}
            </Button>
            {isConnected && (
              <>
                <Button variant="outline" onClick={() => void onSync()} disabled={sync.isPending}>
                  {sync.isPending ? (
                    <Spinner className="size-4" />
                  ) : (
                    <RefreshCw className="size-4" />
                  )}
                  Sync accounts
                </Button>
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => void onDisconnect()}
                  disabled={disconnect.isPending}
                >
                  {disconnect.isPending ? (
                    <Spinner className="size-4" />
                  ) : (
                    <Unplug className="size-4" />
                  )}
                  Disconnect
                </Button>
              </>
            )}
          </div>

          {isConnected && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Linked accounts</p>
              {accounts.isLoading ? (
                <Skeleton className="h-16" />
              ) : accounts.data && accounts.data.length > 0 ? (
                <div className="space-y-2">
                  {accounts.data.map((a) => (
                    <div
                      key={a.customer_id}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <span>{a.descriptive_name || a.customer_id}</span>
                      <span className="text-xs text-muted-foreground">
                        {a.customer_id}
                        {a.is_test_account ? ' · test' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No accounts yet — click “Sync accounts”.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
