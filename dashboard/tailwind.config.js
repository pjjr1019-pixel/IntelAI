/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        vanguard: {
          50: '#eef2ff',
          100: '#dbe4ff',
          200: '#bac8ff',
          300: '#91a7ff',
          400: '#748ffc',
          500: '#5c7cfa',
          600: '#4c6ef5',
          700: '#4263eb',
          800: '#3b5bdb',
          900: '#364fc7',
          950: '#1e3a5f',
        },
        severity: {
          critical: '#ef4444',
          high: '#f97316',
          medium: '#eab308',
          low: '#22c55e',
        },
        status: {
          active:    '#3b82f6',
          watching:  '#a855f7',
          confirmed: '#22c55e',
          dismissed: '#6b7280',
          resolved:  '#14b8a6',
          archived:  '#9ca3af',
        },
        surface: {
          0: '#050a18',
          1: '#0a1128',
          2: '#111a35',
          3: '#182244',
          4: '#1e2d52',
        },
        accent: {
          cyan: '#22d3ee',
          emerald: '#34d399',
          violet: '#a78bfa',
          rose: '#fb7185',
          amber: '#fbbf24',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'mesh-gradient': 'linear-gradient(135deg, rgba(76, 110, 245, 0.08) 0%, rgba(34, 211, 238, 0.05) 50%, rgba(167, 139, 250, 0.08) 100%)',
      },
      boxShadow: {
        'glow-sm': '0 0 15px -3px rgba(76, 110, 245, 0.2)',
        'glow-md': '0 0 30px -5px rgba(76, 110, 245, 0.25)',
        'glow-lg': '0 0 60px -10px rgba(76, 110, 245, 0.3)',
        'inner-glow': 'inset 0 1px 0 0 rgba(255,255,255,0.05)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-critical': 'pulse-critical 2s ease-in-out infinite',
        'gradient-x': 'gradient-x 6s ease infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
      },
      keyframes: {
        'pulse-critical': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 8px rgba(239, 68, 68, 0.5)' },
          '50%': { opacity: '0.7', boxShadow: '0 0 16px rgba(239, 68, 68, 0.8)' },
        },
        'gradient-x': {
          '0%, 100%': { 'background-position': '0% 50%' },
          '50%': { 'background-position': '100% 50%' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'shimmer': {
          '0%': { 'background-position': '-200% 0' },
          '100%': { 'background-position': '200% 0' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(100%)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
};
