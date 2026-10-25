import Link from "next/link";
import { Logo } from "@/components/Logo";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center bg-background px-6 text-center">
      <div>
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>
        <p className="eyebrow">404</p>
        <h1 className="display-title mt-2 text-2xl">Página não encontrada</h1>
        <p className="mt-1 text-sm text-muted">Page not found</p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-contrast transition-colors hover:bg-primary-strong"
        >
          Voltar ao início · Back home
        </Link>
      </div>
    </main>
  );
}
