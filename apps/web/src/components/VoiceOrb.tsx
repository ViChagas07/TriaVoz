import { clsx } from "clsx";

export type OrbState =
  | "idle"
  | "connecting"
  | "listening"
  | "speaking"
  | "ended"
  | "error";

const SIZES = {
  sm: "size-24 [--bar-gap:2px]",
  md: "size-44 [--bar-gap:3px]",
  lg: "size-64 [--bar-gap:4px]",
  xl: "size-80 [--bar-gap:5px]",
} as const;

export function VoiceOrb({
  state,
  size = "lg",
  label,
  className,
}: {
  state: OrbState;
  size?: keyof typeof SIZES;
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={clsx("orb", SIZES[size], className)}
      data-state={state}
      role="img"
      aria-label={label ?? state}
    >
      <span className="orb-halo" aria-hidden="true" />
      <span className="orb-halo-2" aria-hidden="true" />
      <span
        className="orb-core"
        style={{ width: "58%", height: "58%", gap: "var(--bar-gap, 4px)" }}
        aria-hidden="true"
      >
        {[0, 1, 2, 3, 4].map((bar) => (
          <span key={bar} className="orb-bar" />
        ))}
      </span>
    </div>
  );
}
