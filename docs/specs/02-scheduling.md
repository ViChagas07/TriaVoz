# Spec 02 — Scheduling

- S1 `free_slots(day, tz, windows, busy, duration, now, step=15min, min_notice=30min)` is pure; a slot is valid iff it fits a work window, does not overlap busy intervals (appointments `booked` + time off) and respects notice. Back-to-back is allowed (half-open intervals).
- S2 `BookAppointment` re-computes the offered slots and refuses anything not offered (`SlotUnavailable`); the insert is protected by `appointments_no_overlap` (`SlotTaken` on race). Insert/update run inside a SAVEPOINT.
- S3 `CancelAppointment` / `RescheduleAppointment` / `ListMyAppointments` operate only on the verified caller's own appointments: a provider-verified phone (`calls.caller_verified` + `calls.caller_number`) for telephony, or the opaque browser identity hash recorded on the call for the public web demo. A phone typed into a browser is never proof of ownership; otherwise `NotFound`.
- S4 Reschedule validates the new slot like a booking and moves the row in a single UPDATE.
- S5 Times: tz-aware everywhere; the clinic timezone comes from `clinics.timezone`; naive datetimes are rejected with 422.
- S6 Caching (optional): availability reads may be cached with SWR + TTL jitter + single-flight lock and invalidated on booking; **booking never trusts the cache**.
- S7 Staff can also create/move/cancel appointments from the dashboard (`created_via='staff'`).

Tests: `tests/unit/test_slots.py`, `tests/integration/test_scheduling_db.py` (12-way race → exactly one winner), `test_internal_api.py`.
