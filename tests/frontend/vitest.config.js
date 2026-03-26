import { defineConfig } from "vitest/config";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "../..");

export default defineConfig({
  test: {
    globals: false,
    environment: "node",
    include: ["**/*.test.js"],
  },
  resolve: {
    alias: {
      "@static": resolve(root, "backend/static"),
    },
  },
});
