"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Keep the detail server-side; the UI only needs a stable, translated fallback.
    console.error(error.digest ?? "app_error");
  }, [error]);

  return (
    <section className="mx-auto max-w-lg rounded-2xl border border-border bg-surface p-6 text-center">
      <span className="mx-auto grid size-11 place-items-center rounded-full bg-st-urgent/10 text-st-urgent">
        <AlertTriangle aria-hidden className="size-5" />
      </span>
      <h1 className="mt-3 text-lg font-semibold">Algo deu errado</h1>
      <p className="mt-1 text-sm text-muted">Não foi possível carregar esta página.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-contrast"
      >
        Tentar novamente
      </button>
    </section>
  );
}
