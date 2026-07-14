import { env } from '@/lib/env';
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/lib/tokens';

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
}

let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${env.NEXT_PUBLIC_API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return false;
        const data = (await res.json()) as { access_token: string; refresh_token: string };
        setTokens(data.access_token, data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function parseError(res: Response): Promise<ApiError> {
  let code = 'error';
  let message = res.statusText || 'Request failed';
  let details: unknown;
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details;
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message, details);
}

async function rawRequest<T>(path: string, options: RequestOptions, retry = true): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = options;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (res.status === 401 && auth && retry) {
    const refreshed = await attemptRefresh();
    if (refreshed) return rawRequest<T>(path, options, false);
    clearTokens();
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, opts: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    rawRequest<T>(path, { ...opts, method: 'GET' }),
  post: <T>(path: string, body?: unknown, opts: Omit<RequestOptions, 'method'> = {}) =>
    rawRequest<T>(path, { ...opts, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, opts: Omit<RequestOptions, 'method'> = {}) =>
    rawRequest<T>(path, { ...opts, method: 'PATCH', body }),
  del: <T>(path: string, opts: Omit<RequestOptions, 'method' | 'body'> = {}) =>
    rawRequest<T>(path, { ...opts, method: 'DELETE' }),
};
