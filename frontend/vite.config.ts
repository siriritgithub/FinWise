import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://localhost:8000",
      "/users": "http://localhost:8000",
      "/accounts": "http://localhost:8000",
      "/transactions": "http://localhost:8000",
      "/categories": "http://localhost:8000",
      "/budgets": "http://localhost:8000",
      "/recurring": "http://localhost:8000",
      "/goals": "http://localhost:8000",
      "/receipts": "http://localhost:8000",
      "/analytics": "http://localhost:8000",
      "/chat": "http://localhost:8000",
    },
  },
});
