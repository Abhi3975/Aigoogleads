'use client';

import { useId } from 'react';
import { cn } from '@/lib/utils';

interface TrendChartProps {
  values: number[];
  className?: string;
  /** Tailwind text-color class driving the line/area color (uses currentColor). */
  colorClassName?: string;
  height?: number;
}

const WIDTH = 600;
const PAD = 6;

/** Lightweight, dependency-free line+area chart scaled to its container. */
export function TrendChart({
  values,
  className,
  colorClassName = 'text-primary',
  height = 120,
}: TrendChartProps) {
  const gradientId = useId();

  if (!values.length) {
    return (
      <div
        className={cn('flex items-center justify-center text-sm text-muted-foreground', className)}
        style={{ height }}
      >
        No data yet
      </div>
    );
  }

  const max = Math.max(...values);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const stepX = values.length > 1 ? (WIDTH - PAD * 2) / (values.length - 1) : 0;

  const toY = (v: number) => PAD + (1 - (v - min) / range) * (height - PAD * 2);
  const points = values.map((v, i) => [PAD + i * stepX, toY(v)] as const);

  const line = points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' ');
  const lastX = (points[points.length - 1] ?? [PAD, 0])[0];
  const area = `${line} L${lastX.toFixed(1)},${height - PAD} L${PAD},${height - PAD} Z`;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${height}`}
      preserveAspectRatio="none"
      className={cn('w-full', colorClassName, className)}
      style={{ height }}
      role="img"
      aria-label="trend chart"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradientId})`} stroke="none" />
      <path
        d={line}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
