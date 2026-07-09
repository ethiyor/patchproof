import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        surface: "#f7f8fb",
        line: "#dfe4ee",
        ready: "#167c52",
        caution: "#b45309",
        blocked: "#b42318",
      },
    },
  },
  plugins: [],
} satisfies Config;
