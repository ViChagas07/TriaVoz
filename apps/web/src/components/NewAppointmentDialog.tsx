"use client";

import { CalendarPlus, Check, Loader2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { Appointment, Professional, Service } from "@/lib/types";

type Strings = {
  trigger: string;
  title: string;
  hint: string;
  service: string;
  professional: string;
  date: string;
  name: string;
  phone: string;
  create: string;
  creating: string;
  cancel: string;
  created: string;
  error: string;
};

export function NewAppointmentDialog({
  services,
  professionals,
  strings,
}: {
  services: Service[];
  professionals: Professional[];
  strings: Strings;
}) {
  const router = useRouter();
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [serviceId, setServiceId] = useState(services[0]?.id ?? "");
  const [professionalId, setProfessionalId] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState(false);
  const closeRef = useRef<HTMLButtonElement | null>(null);

  const available = professionals.filter(
    (professional) => !serviceId || professional.service_ids.includes(serviceId),
  );

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api<Appointment>("/agenda", {
        method: "POST",
        body: JSON.stringify({
          service_id: serviceId,
          professional_id: professionalId,
          starts_at: new Date(startsAt).toISOString(),
          customer_name: name.trim(),
          customer_phone: phone.trim(),
        }),
      });
      setCreated(true);
      setOpen(false);
      setStartsAt("");
      setName("");
      setPhone("");
      router.refresh();
      window.setTimeout(() => setCreated(false), 4000);
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? strings.error
          : strings.error,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast"
      >
        <CalendarPlus aria-hidden className="size-3.5" />
        {strings.trigger}
      </button>
      {created && (
        <span role="status" className="text-xs font-medium text-st-done">
          {strings.created}
        </span>
      )}

      {open && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" role="presentation">
          <button
            type="button"
            aria-label={strings.cancel}
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/35 backdrop-blur-[1px]"
          />
          <form
            onSubmit={submit}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="panel-in relative z-10 w-full max-w-lg rounded-2xl border border-border bg-surface p-5 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 id={titleId} className="text-lg font-semibold">
                  {strings.title}
                </h2>
                <p className="mt-1 text-xs text-muted">{strings.hint}</p>
              </div>
              <button
                ref={closeRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label={strings.cancel}
                className="grid size-8 place-items-center rounded-full border border-border text-muted"
              >
                <X aria-hidden className="size-4" />
              </button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-xs sm:col-span-2">
                <span className="font-medium text-muted">{strings.service}</span>
                <select
                  required
                  value={serviceId}
                  onChange={(event) => {
                    setServiceId(event.target.value);
                    setProfessionalId("");
                  }}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                >
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} · {service.duration_min} min
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1 text-xs sm:col-span-2">
                <span className="font-medium text-muted">{strings.professional}</span>
                <select
                  required
                  value={professionalId}
                  onChange={(event) => setProfessionalId(event.target.value)}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value="">—</option>
                  {available.map((professional) => (
                    <option key={professional.id} value={professional.id}>
                      {professional.name}
                      {professional.specialty ? ` · ${professional.specialty}` : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1 text-xs sm:col-span-2">
                <span className="font-medium text-muted">{strings.date}</span>
                <input
                  required
                  type="datetime-local"
                  value={startsAt}
                  onChange={(event) => setStartsAt(event.target.value)}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="font-medium text-muted">{strings.name}</span>
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={120}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="font-medium text-muted">{strings.phone}</span>
                <input
                  required
                  type="tel"
                  inputMode="tel"
                  pattern="^\+[1-9][0-9]{7,14}$"
                  placeholder="+5571999990000"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
              </label>
            </div>

            {error && (
              <p role="alert" className="mt-3 rounded-lg border border-st-urgent/30 bg-st-urgent/10 px-3 py-2 text-xs text-st-urgent">
                {error}
              </p>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg border border-border px-3.5 py-2 text-xs font-medium"
              >
                {strings.cancel}
              </button>
              <button
                type="submit"
                disabled={busy || !serviceId || !professionalId}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60"
              >
                {busy ? <Loader2 aria-hidden className="size-3.5 animate-spin" /> : <Check aria-hidden className="size-3.5" />}
                {busy ? strings.creating : strings.create}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
