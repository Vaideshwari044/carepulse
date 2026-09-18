/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#3B82F6",
        muted: "#6B7280",
        raised: "#1F2937",
        surface: "#111827",
        line: "#374151",
        risk: {
          stable: "#10B981",
          early: "#F59E0B",
          warning: "#F97316",
          high: "#EF4444",
          recovery: "#6366F1",
          insufficient: "#6B7280",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        card: "0.75rem",
      },
      boxShadow: {
        elevate: "0 4px 20px rgba(0, 0, 0, 0.3)",
      },
    },
  },
  plugins: [],
};
