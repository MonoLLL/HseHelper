/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,jsx,ts,tsx}",
    "./styles/**/*.{css}",
    "./lib/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hse: {
          blue: "rgb(15 45 105)",
          blue2: "rgb(35 75 155)",
          sky: "rgb(205 220 240)",
          cyan: "rgb(15 160 215)",
        },
        ink: {
          900: "rgb(17 24 39)",
          700: "rgb(55 65 81)",
          500: "rgb(107 114 128)",
          200: "rgb(229 231 235)",
          100: "rgb(243 244 246)",
        },
      },
      boxShadow: {
        soft: "0 10px 30px rgba(17,24,39,0.08)",
      },
      borderRadius: {
        xl: "16px",
      },
    },
  },
  plugins: [],
};
