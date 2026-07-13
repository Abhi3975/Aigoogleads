# AI Ads Agent — Frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui client.

## Stack

React Query · React Hook Form · Zod · Framer Motion · next-themes (dark mode) ·
sonner (toasts) · lucide-react.

## Layout

```
src/
├── app/            # App Router routes, layouts, providers
├── components/     # UI + feature components (shadcn/ui under components/ui)
├── lib/            # utils, env, API client, query helpers
└── hooks/          # reusable React hooks
```

## Local development

```bash
corepack enable
pnpm install
cp .env.example .env.local
pnpm dev            # http://localhost:3000
```

## Quality

```bash
pnpm lint
pnpm typecheck
pnpm format
```
