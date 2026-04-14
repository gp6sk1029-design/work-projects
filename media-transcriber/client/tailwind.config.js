/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f1117',
          surface: '#1a1d2e',
          card: '#232738',
          border: '#353a50',
          hover: '#2d3148',
        },
        accent: {
          blue: '#3b82f6',
          purple: '#8b5cf6',
          green: '#10b981',
          orange: '#f97316',
          red: '#ef4444',
        },
      },
    },
  },
  plugins: [],
};
