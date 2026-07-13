import { z } from 'zod';

/**
 * Validated, typed access to public environment variables.
 * Fails fast at module load if configuration is missing/invalid.
 */
const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default('http://localhost:8000/api/v1'),
  NEXT_PUBLIC_APP_NAME: z.string().min(1).default('AI Ads Agent'),
});

const parsed = publicEnvSchema.safeParse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
});

if (!parsed.success) {
  // eslint-disable-next-line no-console
  console.error('Invalid public environment variables:', parsed.error.flatten().fieldErrors);
  throw new Error('Invalid public environment configuration');
}

export const env = parsed.data;
