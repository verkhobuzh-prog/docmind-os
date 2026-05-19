/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dde6ff',
          200: '#c3d1ff',
          300: '#9ab0ff',
          400: '#7088fb',
          500: '#4d64f5',
          600: '#3845ea',
          700: '#2e36ce',
          800: '#2830a7',
          900: '#272e83',
        },
        surface: {
          0:   'hsl(220 20% 98%)',
          1:   'hsl(220 16% 96%)',
          2:   'hsl(220 14% 92%)',
          3:   'hsl(220 12% 87%)',
        },
        'surface-dark': {
          0:   'hsl(222 24% 8%)',
          1:   'hsl(222 20% 11%)',
          2:   'hsl(222 18% 15%)',
          3:   'hsl(222 16% 20%)',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in':   'fadeIn 0.3s ease forwards',
        'slide-up':  'slideUp 0.4s cubic-bezier(.16,1,.3,1) forwards',
        'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:   { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:  { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseDot: { '0%,100%': { transform: 'scale(.8)', opacity: .5 }, '50%': { transform: 'scale(1.2)', opacity: 1 } },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
