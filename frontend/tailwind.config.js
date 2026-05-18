/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'DM Sans'", "system-ui", "sans-serif"],
        display: ["'Syne'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        ink: {
          50: "#f0f0f5", 100: "#e1e1eb", 200: "#c3c3d7",
          300: "#9494b8", 400: "#6b6b99", 500: "#4d4d7a",
          600: "#3a3a5c", 700: "#27273e", 800: "#161625",
          900: "#0d0d17", 950: "#07070f",
        },
        accent: {
          400: "#ff5ea3", 500: "#ff2d82", 600: "#f0006b",
        },
      },
    },
  },
  plugins: [],
};
