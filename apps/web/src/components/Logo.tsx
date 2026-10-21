import Link from "next/link";

type Props = {
  compact?: boolean;
  href?: string;
  className?: string;
};

/** Original placeholder mark: a speech bubble with a voice waveform. Swap the SVG for the
 * official asset when it lands; the sizing and dark-mode behavior stay the same. */
export function Logo({ compact = false, href = "/", className }: Props) {
  const content = (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <svg
        viewBox="0 0 40 40"
        aria-hidden="true"
        className="size-8 shrink-0"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="40" height="40" rx="12" fill="var(--primary)" />
        <path
          d="M11 13.5h18a3.5 3.5 0 0 1 3.5 3.5v6a3.5 3.5 0 0 1-3.5 3.5h-8.2L14 31v-4.5h-3a3.5 3.5 0 0 1-3.5-3.5v-6A3.5 3.5 0 0 1 11 13.5Z"
          fill="var(--primary-contrast)"
          opacity="0.18"
        />
        <rect x="12" y="18" width="2.6" height="5" rx="1.3" fill="var(--primary-contrast)" />
        <rect x="17" y="15.5" width="2.6" height="10" rx="1.3" fill="var(--primary-contrast)" />
        <rect x="22" y="17" width="2.6" height="7" rx="1.3" fill="var(--primary-contrast)" />
        <rect x="27" y="19" width="2.6" height="4" rx="1.3" fill="var(--primary-contrast)" />
      </svg>
      {!compact && (
        <span className="hidden text-[1.05rem] font-semibold tracking-tight text-text sm:inline">
          Tria<span className="text-primary-strong">Voz</span>
        </span>
      )}
    </span>
  );
  return href ? (
    <Link href={href} className="rounded-lg focus-visible:outline-offset-4" aria-label="TriaVoz">
      {content}
    </Link>
  ) : (
    content
  );
}
