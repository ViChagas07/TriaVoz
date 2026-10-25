import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TriaVoice — recepção por voz com IA",
    short_name: "TriaVoice",
    description: "Atende, entende e agenda por voz. Com dados reais da clínica.",
    start_url: "/",
    display: "standalone",
    background_color: "#edf1f7",
    theme_color: "#2563eb",
    lang: "pt-BR",
    icons: [
      { src: "/icon.png", sizes: "512x512", type: "image/png" },
      { src: "/apple-icon.png", sizes: "180x180", type: "image/png" },
    ],
  };
}
