import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TriaVoz — recepção por voz com IA",
    short_name: "TriaVoz",
    description: "Atende, entende e agenda por voz. Com dados reais da clínica.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f8fa",
    theme_color: "#0e7c86",
    lang: "pt-BR",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
    ],
  };
}
