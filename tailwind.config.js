/** @type {import('tailwindcss').Config} */
module.exports = {
  // تلویند تمام فایل‌های این دو پوشه را اسکن می‌کند تا کلاس‌های CSS را پیدا کند
  content: [
    "./templates/**/*.html",
    "./static_build/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#2d6064",
        "on-primary": "#ffffff",
        "primary-container": "#00f0ff",
        "on-primary-container": "#006970",
        "secondary": "#5f5e5e",
        "on-secondary": "#ffffff",
        "background": "#f7f9fb",
        "on-background": "#191c1e",
        "surface": "#f7f9fb",
        "on-surface": "#191c1e",
        "on-surface-variant": "#3b494b",
        "surface-container-low": "#f2f4f6",
        "surface-container": "#eceef0",
        "surface-container-highest": "#e0e3e5",
        "surface-container-lowest": "#ffffff",
        "outline-variant": "#b9cacb",
        "error": "#ba1a1a",
        // در صورت نیاز بقیه رنگ‌های قالب خود را اینجا اضافه کنید
      },
      fontFamily: {
        "headline-xl": ["Vazirmatn"],
        "headline-lg": ["Vazirmatn"],
        "headline-md": ["Vazirmatn"],
        "body-lg": ["Vazirmatn"],
        "body-md": ["Vazirmatn"],
        "label-md": ["Vazirmatn"],
        "label-sm": ["Vazirmatn"],
      }
    }
  },
  plugins: [],
}