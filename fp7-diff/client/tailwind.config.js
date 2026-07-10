/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // FP7アクセントカラー（パナソニック青系）
        accent: {
          50: '#eff6ff',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        dark: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
          hover: '#475569',
        },
        diff: {
          add: '#10b981',
          remove: '#ef4444',
          change: '#f59e0b',
          same: '#64748b',
        },
      },
    },
  },
  plugins: [],
};
