// The browser only ever calls same-origin /api/v1 (proxied to FastAPI by next.config.ts).
// Authentication is an httpOnly cookie set by the API; no token ever touches localStorage.
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(`${status}: ${code}`);
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    let code = "error";
    try {
      const body = (await response.json()) as { detail?: string };
      code = body.detail ?? code;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code);
  }
  return response;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await request(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function apiVoid(path: string, init: RequestInit = {}): Promise<void> {
  await request(path, init);
}
