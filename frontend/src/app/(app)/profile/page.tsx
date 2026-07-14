'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { UserRound } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { ApiError, api } from '@/lib/api';
import type { User } from '@/lib/types';
import { useAuth } from '@/providers/auth-provider';

const schema = z.object({
  full_name: z.string().max(255).optional(),
  avatar_url: z.string().url('Enter a valid URL').or(z.literal('')).optional(),
});
type FormValues = z.infer<typeof schema>;

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: user?.full_name ?? '', avatar_url: user?.avatar_url ?? '' },
  });

  const avatar = watch('avatar_url') || user?.avatar_url;

  async function onSubmit(values: FormValues) {
    try {
      await api.patch<User>('/users/me', {
        full_name: values.full_name || null,
        avatar_url: values.avatar_url || null,
      });
      await refreshUser();
      toast.success('Profile updated');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not update profile');
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-lg space-y-6"
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        <p className="text-sm text-muted-foreground">Your account details.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personal information</CardTitle>
          <CardDescription>Update how you appear across the workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-6 flex items-center gap-4">
            <div className="flex size-16 items-center justify-center overflow-hidden rounded-full border bg-muted">
              {avatar ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={avatar} alt="Avatar" className="size-full object-cover" />
              ) : (
                <UserRound className="size-7 text-muted-foreground" />
              )}
            </div>
            <div>
              <p className="font-medium">{user?.full_name || user?.email}</p>
              <p className="text-xs text-muted-foreground">
                {user?.is_email_verified ? 'Email verified' : 'Email not verified'}
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={user?.email ?? ''} disabled />
            </div>
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" {...register('full_name')} />
              {errors.full_name && (
                <p className="text-xs text-destructive">{errors.full_name.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="avatar_url">Avatar URL</Label>
              <Input id="avatar_url" placeholder="https://" {...register('avatar_url')} />
              {errors.avatar_url && (
                <p className="text-xs text-destructive">{errors.avatar_url.message}</p>
              )}
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Spinner className="size-4" />} Save changes
            </Button>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  );
}
