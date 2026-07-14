import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-6xl font-bold text-primary">404</p>
      <h1 className="text-xl font-semibold tracking-tight">Page not found</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        The page you are looking for doesn&apos;t exist or has moved.
      </p>
      <Button asChild>
        <Link href="/dashboard">Back to dashboard</Link>
      </Button>
    </div>
  );
}
