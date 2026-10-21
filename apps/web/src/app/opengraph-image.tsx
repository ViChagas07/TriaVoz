import { ImageResponse } from "next/og";

export const alt = "TriaVoz — recepção por voz com IA para clínicas";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          overflow: "hidden",
          background: "linear-gradient(135deg, #071923 0%, #0b2f3d 55%, #0e7c86 100%)",
          color: "#e8f1f5",
          padding: "64px",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            position: "absolute",
            right: -140,
            top: -120,
            width: 560,
            height: 560,
            borderRadius: 9999,
            background: "radial-gradient(circle, rgba(56,189,248,.55), rgba(56,189,248,0) 70%)",
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div
              style={{
                width: 58,
                height: 58,
                borderRadius: 18,
                background: "#2dd4bf",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#04241f",
                fontSize: 28,
                fontWeight: 700,
              }}
            >
              T
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5 }}>TriaVoz</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 820 }}>
            <div style={{ fontSize: 62, fontWeight: 700, lineHeight: 1.05, letterSpacing: -2 }}>
              A recepção que atende, entende e agenda por voz.
            </div>
            <div style={{ fontSize: 26, color: "#b7d2de", lineHeight: 1.35 }}>
              Agenda real, transcrição, handoff humano e SAMU 192 para emergências.
            </div>
          </div>
          <div style={{ display: "flex", gap: 28, fontSize: 20, color: "#9db2c0" }}>
            <span>PostgreSQL + RLS</span>
            <span>LiveKit</span>
            <span>Next.js</span>
            <span>pt-BR / en</span>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
