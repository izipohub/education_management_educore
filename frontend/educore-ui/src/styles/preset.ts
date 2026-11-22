import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

/** PrimeVue's Aura theme in EduCore's 60/30/10 colours (styles/main.css): warm neutral surfaces, the brand's
 *  primary for links and controls, the brand accent for the solid primary button only */
export const EduCorePreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: "{blue.50}",
      100: "{blue.100}",
      200: "{blue.200}",
      300: "{blue.300}",
      400: "{blue.400}",
      500: "{blue.500}",
      600: "{blue.600}",
      700: "{blue.700}",
      800: "{blue.800}",
      900: "{blue.900}",
      950: "{blue.950}",
    },
    colorScheme: {
      light: {
        // navy (the 30%): links, text buttons, checkboxes, focus rings
        primary: {
          color: "var(--ec-accent)",
          contrastColor: "#ffffff",
          hoverColor: "color-mix(in srgb, var(--ec-accent) 88%, black)",
          activeColor: "color-mix(in srgb, var(--ec-accent) 76%, black)",
        },
        surface: {
          0: "#ffffff",
          50: "#faf9f5",
          100: "#f4f2ec",
          200: "#e6e2d8",
          300: "#d6d1c4",
          400: "#a3a6ad",
          500: "#6b6f7a",
          600: "#4b4f5a",
          700: "#363a45",
          800: "#242833",
          900: "#161a24",
          950: "#0b0e15",
        },
      },
    },
  },
  components: {
    // the loud 10%: only the solid primary button (the one thing to do) wears the brand accent
    button: {
      colorScheme: {
        light: {
          root: {
            primary: {
              background: "var(--ec-loud)",
              hoverBackground: "color-mix(in srgb, var(--ec-loud) 86%, black)",
              activeBackground: "color-mix(in srgb, var(--ec-loud) 76%, black)",
              borderColor: "var(--ec-loud)",
              hoverBorderColor: "color-mix(in srgb, var(--ec-loud) 86%, black)",
              activeBorderColor: "color-mix(in srgb, var(--ec-loud) 76%, black)",
              color: "var(--ec-on-loud)",
              hoverColor: "var(--ec-on-loud)",
              activeColor: "var(--ec-on-loud)",
              focusRing: { color: "var(--ec-accent)", shadow: "none" },
            },
          },
        },
      },
    },
  },
});
