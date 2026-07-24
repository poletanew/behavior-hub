/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#1D4ED8",
          blueLight: "#3B82F6",
          turquoise: "#14B8A6",
          green: "#22C55E",
          greenLight: "#84CC16",
          purple: "#8B5CF6",
          graphite: "#334155",
          grayLight: "#F1F5F9",
          navy: "#0f2557",
        },
        success: "#22C55E",
        info: "#3B82F6",
        warning: "#F59E0B",
        danger: "#EF4444",
        neutralState: "#64748B",
        borderMuted: "#E2E8F0",
      },
      borderRadius: {
        card: "14px",
        btn: "9px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(15,37,87,0.06)",
      },
    },
  },
  plugins: [],
};
