import type { Config } from "tailwindcss";

// Tokens mirror the mockup's shared.css. Keep them centralised here so
// component CSS can reach for them via theme() if needed; most usage is
// via the Tailwind utility classes below.
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#030303",
        surface: {
          0: "#060606",
          1: "#0a0a0a",
          2: "#101010",
          3: "#050505",
        },
        line: {
          DEFAULT: "rgba(255, 255, 255, 0.06)",
          strong: "rgba(255, 255, 255, 0.12)",
        },
        violet: {
          DEFAULT: "#8B5CF6",
          soft: "rgba(139, 92, 246, 0.14)",
          fg: "#c4b5fd",
        },
        cyan: {
          DEFAULT: "#06B6D4",
          soft: "rgba(6, 182, 212, 0.14)",
          fg: "#67e8f9",
        },
        emerald: {
          DEFAULT: "#10B981",
          fg: "#6ee7b7",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      transitionTimingFunction: {
        snap: "cubic-bezier(0.23, 1, 0.32, 1)",
      },
      keyframes: {
        pulseDot: {
          "0%":   { boxShadow: "0 0 0 0 rgba(16,185,129,0.5)" },
          "70%":  { boxShadow: "0 0 0 9px rgba(16,185,129,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(16,185,129,0)" },
        },
        spinConic: {
          to: { transform: "rotate(360deg)" },
        },
        rise: {
          "0%":   { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%":   { transform: "translateX(0%)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "pulse-dot": "pulseDot 2.4s cubic-bezier(0.23, 1, 0.32, 1) infinite",
        "spin-conic": "spinConic 4s linear infinite",
        rise: "rise 0.6s cubic-bezier(0.23, 1, 0.32, 1) both",
        marquee: "marquee 40s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
