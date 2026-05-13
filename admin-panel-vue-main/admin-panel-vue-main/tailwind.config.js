/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    screens: {
      sm: '480px',
      md: '576px',
      lg: '768px',
      xl: '960px',
      '2xl': '1152px',
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'Play', 'sans-serif'],
      },
      colors: {
        sidebar: '#2d3035',
        active: '#0090FF',
        dashboard: '#F4F7FE',
        // Dark theme palette
        dark: {
          bg: '#1A1C2C',
          surface: '#2C2F3D',
          content: '#232637',
          card: '#2A2D3C',
          'card-elevated': '#2D303D',
          text: '#E0E0E0',
          muted: '#9CA3AF',
        },
        brand: {
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          800: '#1e40af',
          950: '#172554',
        },
        error: {
          500: '#ef4444',
        },
      },
      fontSize: {
        'title-sm': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'title-md': ['2rem', { lineHeight: '2.5rem', fontWeight: '600' }],
      },
      boxShadow: {
        'theme-xs': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        card: '0px 4px 20px rgba(0, 0, 0, 0.05)',
      },
      backgroundImage: {
        'btn-gradient':
          'linear-gradient(270deg, #06B5D4 0.35%, #1F9DE4 32.08%, #2563EB 96.51%)',
      },
    },
  },
  plugins: [],
}
