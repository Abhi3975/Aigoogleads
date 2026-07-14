import { Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <div className="flex items-center gap-2 text-lg font-semibold">
        <Sparkles className="size-5 text-primary" />
        AI Ads Agent
      </div>
      {children}
    </div>
  );
}
