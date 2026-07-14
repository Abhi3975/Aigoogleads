'use client';

import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useCurrentOrg, useOrganizations } from '@/hooks/use-organizations';

export function OrgSwitcher() {
  const orgs = useOrganizations();
  const { org, setSelectedOrgId } = useCurrentOrg();

  if (!orgs.data || orgs.data.length === 0) return null;

  return (
    <div className="space-y-1 border-b px-3 py-2">
      <select
        value={org?.id ?? ''}
        onChange={(e) => setSelectedOrgId(e.target.value)}
        className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
        aria-label="Select organization"
      >
        {orgs.data.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
      <Link
        href="/organizations/new"
        className="flex items-center gap-1 px-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <Plus className="size-3" /> New organization
      </Link>
    </div>
  );
}
