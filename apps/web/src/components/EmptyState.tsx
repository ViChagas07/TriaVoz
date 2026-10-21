import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { clsx } from "clsx";

export function EmptyState({
  title,
  body,
  action,
  icon,
  className,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border bg-surface/60 px-6 py-10 text-center",
        className,
      )}
    >
      <span className="grid size-10 place-items-center rounded-full bg-primary/10 text-primary-strong">
        {icon ?? <Inbox aria-hidden className="size-5" />}
      </span>
      <p className="text-sm font-medium">{title}</p>
      {body && <p className="max-w-sm text-xs text-muted">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-xl", className)} aria-hidden="true" />;
}
