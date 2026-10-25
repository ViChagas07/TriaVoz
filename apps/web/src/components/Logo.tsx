import Image from "next/image";
import Link from "next/link";

type Props = {
  compact?: boolean;
  href?: string | null;
  className?: string;
};

/** Official mark (public/triavoice-mark.png) + typographic wordmark.
 * The mark keeps its own colors in both themes; only the wordmark follows tokens. */
export function Logo({ compact = false, href = "/", className }: Props) {
  const content = (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <Image
        src="/triavoice-mark.png"
        alt=""
        width={30}
        height={30}
        priority
        className="size-[30px] shrink-0"
      />
      {!compact && (
        <span className="font-display text-lg font-extrabold tracking-tight text-heading">
          Tria<span className="text-primary">Voice</span>
        </span>
      )}
    </span>
  );
  if (href === null) return content;
  return (
    <Link href={href} className="rounded-lg focus-visible:outline-offset-4" aria-label="TriaVoice">
      {content}
    </Link>
  );
}
