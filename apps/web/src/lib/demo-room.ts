import { Room } from "livekit-client";

type RoomOptions = ConstructorParameters<typeof Room>[0];

type E2ERoomFactory = () => Room;

/**
 * Test seam for the browser E2E suite. Playwright injects `__TRIAVOZ_E2E_ROOM__` before the app
 * boots so the UI can exercise connect/captions/tool events without a LiveKit server. The branch is
 * compiled out of production builds, where the factory is never consulted.
 */
export function createDemoRoom(options: RoomOptions): Room {
  const e2eBuild = process.env.NEXT_PUBLIC_TRIAVOZ_E2E === "1";
  if (e2eBuild || process.env.NODE_ENV !== "production") {
    const factory = (globalThis as { __TRIAVOZ_E2E_ROOM__?: E2ERoomFactory }).__TRIAVOZ_E2E_ROOM__;
    if (factory) return factory();
  }
  return new Room(options);
}
