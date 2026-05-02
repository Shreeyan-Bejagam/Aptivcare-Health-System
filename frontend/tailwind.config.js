/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#fafafa",
          primaryDark: "#e4e4e7",
          onPrimary: "#0a0a0a",
          bg: "#0a0a0a",
          surface: "#141414",
          elevated: "#1a1a1a",
          ink: "#fafafa",
          mute: "#a3a3a3",
          success: "#d4d4d4",
          error: "#a8a8a8",
          warn: "#737373",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Avenir", "Helvetica", "Arial", "sans-serif"],
      },
      borderRadius: {
        xl: "0.875rem",
      },
      boxShadow: {
        card: "0 4px 24px -2px rgba(0, 0, 0, 0.55)",
        glow: "0 0 0 6px rgba(255, 255, 255, 0.08)",
        soft: "0 12px 40px -16px rgba(0, 0, 0, 0.65)",
      },
      keyframes: {
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        speakingGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(255, 255, 255, 0.2)" },
          "50%": { boxShadow: "0 0 0 14px rgba(255, 255, 255, 0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        slideIn: "slideIn 0.32s cubic-bezier(0.2, 0.8, 0.2, 1)",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
        speakingGlow: "speakingGlow 1.6s ease-in-out infinite",
        fadeIn: "fadeIn 200ms ease-out",
        shimmer: "shimmer 1.7s linear infinite",
      },
    },
  },
  plugins: [],
};
