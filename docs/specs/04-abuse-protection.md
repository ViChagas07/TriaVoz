# Spec 04 — Anti-prank, abuse & cost protection

Principle: **progressive friction**; filter cheap BEFORE spending voice/LLM credits; **never block an emergency**.

1. **Gatekeeper** (before connecting the agent / creating the room): Token Bucket per caller number (Redis Lua, tenant-prefixed keys) · blocklist per clinic + global · hidden-number policy · concurrent-call cap per clinic · daily minute budget · **cost circuit breaker** (switch to a fixed "high demand" message or direct handoff) · business hours · **per-clinic kill switch**.
2. **In-call friction:** silence timeout after the greeting · max duration · max turns · consecutive-misunderstanding handoff · abusive language: one calm warning, then end + log · a simple first question ("your name?") filters dialers.
3. **Agent hardening:** minimum privilege · server-side validation of every tool payload · prompt-injection resistance · clinic id never from the model.
4. **Post-call:** `abuse_score` (very short call, no valid data, repeat caller, low STT confidence) · "review" badge in the dashboard · **"Mark as prank"** → status `spam` + number added to the clinic blocklist · dedupe · alerts on spikes (calls, cost, prank flags).
5. **Web demo specifics:** the public `/api/v1/voice/session` has per-IP + global limits, a hard duration cap and a global daily budget; consider a challenge (CAPTCHA/Turnstile) if abused.

Tests: bucket refill/expiry · blocklist · emergency never blocked · breaker trips and recovers · invalid/replayed signature rejected · `mark-spam` blocks the number.
