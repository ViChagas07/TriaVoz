import { expect, test } from "@playwright/test";
import { useEnglish } from "./helpers";

test.beforeEach(async ({ context }) => {
  await useEnglish(context);
});

test("demo page connects with the stubbed LiveKit room and shows captions", async ({ page }) => {
  await page.addInitScript(() => {
    type Handler = (...args: unknown[]) => void;
    const handlers = new Map<string, Handler[]>();
    const emit = (event: string, ...args: unknown[]) => {
      for (const handler of handlers.get(event) ?? []) handler(...args);
    };
    const room = {
      canPlaybackAudio: true,
      localParticipant: {
        setMicrophoneEnabled: async () => {},
      },
      on(event: string, handler: Handler) {
        handlers.set(event, [...(handlers.get(event) ?? []), handler]);
        return room;
      },
      async connect() {
        window.setTimeout(() => {
          emit(
            "transcriptionReceived",
            [{ id: "e2e-agent", text: "Olá! Sou a assistente virtual da Clínica Horizonte." }],
            { isLocal: false },
          );
          emit(
            "transcriptionReceived",
            [{ id: "e2e-patient", text: "Quero marcar uma consulta amanhã de manhã." }],
            { isLocal: true },
          );
          emit(
            "dataReceived",
            new TextEncoder().encode(
              JSON.stringify({ type: "tool", name: "list_available_slots", ok: true }),
            ),
            {},
            undefined,
            "triavoz.events",
          );
        }, 150);
      },
      async startAudio() {},
      async disconnect() {
        emit("disconnected");
      },
    };
    (window as unknown as { __TRIAVOZ_E2E_ROOM__: () => typeof room }).__TRIAVOZ_E2E_ROOM__ =
      () => room;
  });

  await page.route("**/api/v1/voice/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mode: "session",
        reason: "allowed",
        message: null,
        handoff: false,
        call_id: "00000000-0000-4000-8000-000000000001",
        room_name: "e2e-room",
        token: "e2e-token",
        url: "ws://e2e.invalid",
        max_call_seconds: 300,
        timezone: "America/Bahia",
      }),
    });
  });

  await page.goto("/demo");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start conversation" }).click();

  await expect(page.getByText("You can talk").first()).toBeVisible();
  const log = page.getByRole("log", { name: "Live captions" });
  await expect(log.getByText("Olá! Sou a assistente virtual da Clínica Horizonte.")).toBeVisible();
  await expect(log.getByText("Quero marcar uma consulta amanhã de manhã.")).toBeVisible();
  await expect(page.getByText("Checked availability")).toBeVisible();
  await expect(page.getByText("Tool finished")).toBeVisible();

  await page.getByRole("button", { name: "End conversation" }).click();
  await expect(page.getByRole("heading", { name: "Conversation ended" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See it on the dashboard" })).toBeVisible();
});
