/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
          hover: '#334155',
        },
        severity: {
          error: '#ef4444',
          warning: '#f59e0b',
          info: '#3b82f6',
        },
        accent: '#22d3ee',
      },
    },
  },
  plugins: [],
};
