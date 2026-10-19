// The browser only ever calls same-origin /api/v1 (proxied to the FastAPI service by next.config.ts).
export class ApiError extends Error {
  constructor(public status: number, public code: string) {
    super(`${status}: ${code}`);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!res.ok) {
    let code = "error";
    try {
      code = ((await res.json()) as { detail?: string }).detail ?? code;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code);
  }
  return (await res.json()) as T;
}
