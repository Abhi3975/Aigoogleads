import { env } from '@/lib/env';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="rounded-full border border-border px-4 py-1 text-sm text-muted-foreground">
        Foundation ready · Milestone 1
      </span>
      <h1 className="max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
        {env.NEXT_PUBLIC_APP_NAME}
      </h1>
      <p className="max-w-xl text-balance text-muted-foreground">
        An autonomous AI marketing agent that plans, launches, monitors, and optimizes your Google
        Ads — end to end, within your safety limits.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3 text-sm text-muted-foreground">
        <code className="rounded bg-muted px-2 py-1">Next.js</code>
        <code className="rounded bg-muted px-2 py-1">FastAPI</code>
        <code className="rounded bg-muted px-2 py-1">PostgreSQL</code>
        <code className="rounded bg-muted px-2 py-1">Redis</code>
        <code className="rounded bg-muted px-2 py-1">Celery</code>
        <code className="rounded bg-muted px-2 py-1">LangGraph</code>
      </div>
    </main>
  );
}
