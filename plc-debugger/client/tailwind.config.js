/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#1a1d2e',
          surface: '#232738',
          border: '#353a50',
          hover: '#2d3148',
        },
        plc: '#3b82f6',
        hmi: '#a855f7',
        cross: '#f97316',
        severity: {
          critical: '#ef4444',
          warning: '#f59e0b',
          info: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
};
