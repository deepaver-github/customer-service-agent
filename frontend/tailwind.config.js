/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        surface: '#FAFAFA',
        'surface-sidebar': '#F4F4F5',
        'surface-hover': '#ECECEE',
        'user-tint': '#E8F5EA',
        'user-border': '#CDE6D2',
        brand: {
          green: '#1e7e2d',
          'green-dark': '#1c4f0f',
          'green-soft': '#DCEFDC',
          teal: '#7ebec5',
          'teal-soft': '#E4F1F3',
        },
        'tool-bg': '#F4F4F5',
        'tool-border': '#E4E4E7',
        'escalation-bg': '#FEF3C7',
        'escalation-border': '#F59E0B',
        'escalation-text': '#78350F',
        ink: {
          900: '#18181B',
          700: '#3F3F46',
          500: '#71717A',
          400: '#A1A1AA',
          300: '#D4D4D8',
          200: '#E4E4E7',
          100: '#F4F4F5',
        },
        accent: {
          DEFAULT: '#1e7e2d',
          hover: '#1c4f0f',
          soft: '#DCEFDC',
        },
      },
      fontFamily: {
        display: ['Poppins', 'system-ui', 'sans-serif'],
        sans: ['"Open Sans"', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: {
        composer: '24px',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(24,24,27,0.04)',
        card: '0 4px 12px rgba(24,24,27,0.06)',
        composer: '0 4px 12px rgba(24,24,27,0.06)',
        send: '0 2px 6px rgba(30,126,45,0.35)',
      },
      maxWidth: {
        thread: '720px',
      },
      keyframes: {
        blink: { to: { opacity: '0' } },
        spinslow: { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        blink: 'blink 1s steps(2, start) infinite',
        spinslow: 'spinslow 1s linear infinite',
      },
    },
  },
  plugins: [],
};
