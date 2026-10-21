"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error.digest ?? "global_error");
  }, [error]);

  return (
    <main className="grid min-h-dvh place-items-center bg-background px-6 text-center">
      <div className="max-w-sm">
        <span className="mx-auto grid size-11 place-items-center rounded-full bg-st-urgent/10 text-st-urgent">
          <AlertTriangle aria-hidden className="size-5" />
        </span>
        <h1 className="mt-3 text-lg font-semibold">Algo deu errado · Something went wrong</h1>
        <p className="mt-1 text-sm text-muted">Tente novamente. · Try again.</p>
        <button
          type="button"
          onClick={reset}
          className="mt-5 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-contrast"
        >
          Tentar novamente · Try again
        </button>
      </div>
    </main>
  );
}
