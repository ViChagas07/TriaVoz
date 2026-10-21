import { cookies } from "next/headers";
import type { Me } from "./types";

const API_ORIGIN = (process.env.API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");

export class ServerApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(`${status}: ${code}`);
  }
}

/** Server-side same-origin-equivalent call; cookies never leave the server process. */
export async function serverApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${API_ORIGIN}/api/v1${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(cookieHeader ? { cookie: cookieHeader } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    let code = "error";
    try {
      const body = (await response.json()) as { detail?: string };
      code = body.detail ?? code;
    } catch {
      /* non-JSON error */
    }
    throw new ServerApiError(response.status, code);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function getSession(): Promise<Me | null> {
  try {
    return await serverApi<Me>("/auth/me");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 401) return null;
    throw error;
  }
}
