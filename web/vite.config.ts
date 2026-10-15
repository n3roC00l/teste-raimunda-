import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api vai para o servidor_visao.py (porta 8765 por padrão).
const API = process.env.VISAO_API ?? "http://127.0.0.1:8765";

export default defineConfig({
  base: "./", // caminhos relativos: o mesmo build serve no Pi e num HTML exportado
  plugins: [react()],
  server: { proxy: { "/api": API } },
  build: { outDir: "dist", chunkSizeWarningLimit: 2000 },
});
