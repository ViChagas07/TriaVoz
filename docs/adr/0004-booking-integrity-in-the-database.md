# ADR 0004 — Booking integrity enforced by the database

**Status:** accepted · **Decision:** `EXCLUDE USING gist (clinic_id =, professional_id =, tstzrange(starts_at, ends_at, '[)') &&) WHERE status = 'booked'` on `appointments`; the use case re-validates the slot and translates SQLSTATE 23P01 into `SlotTaken`; writes run in a SAVEPOINT.
**Why:** the LLM and caches can be wrong or racing; only the database can serialize concurrent bookings. A 12-way concurrent test proves exactly one winner.
