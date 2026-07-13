import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from './providers';
import { env } from '@/lib/env';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: {
    default: env.NEXT_PUBLIC_APP_NAME,
    template: `%s · ${env.NEXT_PUBLIC_APP_NAME}`,
  },
  description: 'Autonomous AI agent that plans, launches, and optimizes your Google Ads.',
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#020817' },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} min-h-screen font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
