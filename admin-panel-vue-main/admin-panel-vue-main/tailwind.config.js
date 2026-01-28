/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Play', 'sans-serif'],
      },
      colors: {
        sidebar: '#2d3035',
        active: '#0090FF',
        dashboard: '#F4F7FE',
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
      },
    },
  },
  plugins: [],
}
