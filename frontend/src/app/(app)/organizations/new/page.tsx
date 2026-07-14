'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { useCreateOrganization } from '@/hooks/use-organizations';
import { ApiError } from '@/lib/api';
import { useOrgSelection } from '@/providers/org-provider';

const schema = z.object({ name: z.string().min(1, 'Required').max(255) });
type FormValues = z.infer<typeof schema>;

export default function NewOrganizationPage() {
  const router = useRouter();
  const create = useCreateOrganization();
  const { setSelectedOrgId } = useOrgSelection();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    try {
      const org = await create.mutateAsync(values.name);
      setSelectedOrgId(org.id);
      toast.success('Organization created');
      router.push('/dashboard');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not create organization');
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Dashboard
      </Link>
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Create organization</CardTitle>
          <CardDescription>
            A separate workspace with its own campaigns and billing.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Organization name</Label>
              <Input id="name" placeholder="Acme Marketing" {...register('name')} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <Button type="submit" disabled={isSubmitting || create.isPending}>
              {(isSubmitting || create.isPending) && <Spinner className="size-4" />} Create
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
