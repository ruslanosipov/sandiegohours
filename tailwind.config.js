/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        // Brand colors from banner
        'brand-teal': '#5DB5A4',
        'brand-yellow': '#F4C430',
        'brand-orange': '#E8913A',
        'brand-cream': '#FFF8E7',
      },
    },
  },
  plugins: [],
}
