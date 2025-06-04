/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
      './src/components/**/*.{js,ts,jsx,tsx,mdx}',
      './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
      extend: {
        typography: {
          DEFAULT: {
            css: {
              maxWidth: '100%',
              p: {
                marginTop: '0.75em',
                marginBottom: '0.75em',
              },
              'ul, ol': {
                paddingLeft: '1.5em',
                marginTop: '0.5em',
                marginBottom: '0.5em',
              },
              li: {
                marginTop: '0.25em',
                marginBottom: '0.25em',
              },
              strong: {
                fontWeight: '600',
                color: 'inherit',
              },
            },
          },
        },
      },
    },
    plugins: [require('@tailwindcss/typography')],
  }