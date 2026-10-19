import { getTranslations } from "next-intl/server";

export default async function DemoPage() {
  const t = await getTranslations("demo");
  // TODO(P06): request a session from the API (server picks the demo clinic, creates the LiveKit
  // room with metadata and returns a participant token), then connect with livekit-client and show
  // a live voice visualizer + captions. Respect the demo cost limits (see docs/specs/04-abuse-protection.md).
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-3xl font-semibold">{t("title")}</h1>
      <button
        type="button"
        className="rounded-full bg-voice px-8 py-4 text-lg font-semibold text-black hover:brightness-110"
      >
        {t("start")}
      </button>
      <p className="text-sm text-muted">{t("disclaimer")}</p>
    </main>
  );
}
