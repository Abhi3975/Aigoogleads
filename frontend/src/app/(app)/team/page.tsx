'use client';

import { motion } from 'framer-motion';
import { Trash2, UserPlus, Users } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import {
  useAddMember,
  useMembers,
  useRemoveMember,
  useUpdateMemberRole,
} from '@/hooks/use-members';
import { useCurrentOrg } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';
import type { OrgRole } from '@/lib/types';
import { useAuth } from '@/providers/auth-provider';

const ASSIGNABLE: OrgRole[] = ['admin', 'manager', 'analyst', 'viewer'];

function roleVariant(role: OrgRole): 'default' | 'secondary' | 'outline' {
  if (role === 'owner') return 'default';
  if (role === 'admin') return 'secondary';
  return 'outline';
}

export default function TeamPage() {
  const { org } = useCurrentOrg();
  const { user } = useAuth();
  const orgId = org?.id;
  const members = useMembers(orgId);
  const addMember = useAddMember(orgId ?? '');
  const updateRole = useUpdateMemberRole(orgId ?? '');
  const removeMember = useRemoveMember(orgId ?? '');

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<OrgRole>('viewer');

  const canManage = org?.role === 'owner' || org?.role === 'admin';

  async function onAdd() {
    if (!email) return;
    try {
      await addMember.mutateAsync({ email, role });
      toast.success('Member added');
      setEmail('');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not add member');
    }
  }

  async function onRoleChange(userId: string, newRole: OrgRole) {
    try {
      await updateRole.mutateAsync({ userId, role: newRole });
      toast.success('Role updated');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not update role');
    }
  }

  async function onRemove(userId: string) {
    try {
      await removeMember.mutateAsync(userId);
      toast.success('Member removed');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not remove member');
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-3xl space-y-6"
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Team</h1>
        <p className="text-sm text-muted-foreground">Manage members and roles for {org?.name}.</p>
      </div>

      {canManage && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserPlus className="size-5" /> Add member
            </CardTitle>
            <CardDescription>Add an existing user to this organization by email.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <Input
              type="email"
              placeholder="teammate@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="max-w-xs"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as OrgRole)}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              {ASSIGNABLE.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <Button onClick={() => void onAdd()} disabled={addMember.isPending}>
              {addMember.isPending ? (
                <Spinner className="size-4" />
              ) : (
                <UserPlus className="size-4" />
              )}
              Add
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="size-5" /> Members
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {members.isLoading
            ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14" />)
            : members.data?.map((m) => {
                const editable = canManage && m.role !== 'owner' && m.user_id !== user?.id;
                return (
                  <div
                    key={m.user_id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{m.full_name || m.email}</p>
                      <p className="text-xs text-muted-foreground">{m.email}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {editable ? (
                        <select
                          value={m.role}
                          onChange={(e) => void onRoleChange(m.user_id, e.target.value as OrgRole)}
                          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                        >
                          {ASSIGNABLE.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <Badge variant={roleVariant(m.role)}>{m.role}</Badge>
                      )}
                      {editable && (
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label="Remove member"
                          onClick={() => void onRemove(m.user_id)}
                        >
                          <Trash2 className="size-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
        </CardContent>
      </Card>
    </motion.div>
  );
}
