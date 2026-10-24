/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        serif: ['"DM Serif Display"', 'Georgia', 'serif'],
        sans: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        campus: {
          ivory: 'rgb(var(--campus-ivory) / <alpha-value>)',
          espresso: {
            DEFAULT: 'rgb(var(--campus-espresso) / <alpha-value>)',
            muted: 'rgb(var(--campus-espresso-muted) / <alpha-value>)',
            subtle: 'rgb(var(--campus-espresso-subtle) / <alpha-value>)',
          },
          terracotta: {
            DEFAULT: 'rgb(var(--campus-terracotta) / <alpha-value>)',
            hover: 'rgb(var(--campus-terracotta-hover) / <alpha-value>)',
            light: 'rgb(var(--campus-terracotta-light) / <alpha-value>)',
            border: 'rgb(var(--campus-terracotta-border) / <alpha-value>)',
            text: 'rgb(var(--campus-terracotta-text) / <alpha-value>)',
          },
          turmeric: {
            DEFAULT: 'rgb(var(--campus-turmeric) / <alpha-value>)',
            hover: 'rgb(var(--campus-turmeric-hover) / <alpha-value>)',
            light: 'rgb(var(--campus-turmeric-light) / <alpha-value>)',
            border: 'rgb(var(--campus-turmeric-border) / <alpha-value>)',
            text: 'rgb(var(--campus-turmeric-text) / <alpha-value>)',
          },
          sandstone: {
            DEFAULT: 'rgb(var(--campus-sandstone) / <alpha-value>)',
            surface: 'rgb(var(--campus-sandstone-surface) / <alpha-value>)',
            border: 'rgb(var(--campus-sandstone-border) / <alpha-value>)',
          },
        },
      },
      boxShadow: {
        warm: '0 2px 8px -2px rgba(28, 35, 31, 0.08), 0 1px 3px -1px rgba(28, 35, 31, 0.05)',
        'warm-md': '0 8px 20px -4px rgba(28, 35, 31, 0.11), 0 2px 6px -2px rgba(28, 35, 31, 0.05)',
      },
    },
  },
  plugins: [],
};