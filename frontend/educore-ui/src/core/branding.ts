import { ref } from "vue";
import { get } from "@/core/api/client";
import type { Branding } from "@/types/session";

/** EduCore's own brand, used until (or if) the university's EduCore Branding cannot be fetched */
export const DEFAULT_BRANDING: Branding = {
  institution_name: "EduCore",
  login_subtitle: "University Management",
  logo: "/assets/educore_theme/images/educore-logo.svg",
  logo_on_dark: "/assets/educore_theme/images/educore-logo-white.svg",
  mark: "/assets/educore_theme/images/educore-mark-192.png",
  favicon: "/assets/educore_theme/images/favicon.ico",
  primary_color: "#1E3A8A",
  accent_color: "#F2B33D",
  background_color: "#07142B",
  text_on_accent: "#0B1F3A",
  login_heading: "One university,",
  login_heading_accent: "every campus connected.",
  login_text: "",
  facts: [],
  login_background: "",
};

const branding = ref<Branding>(DEFAULT_BRANDING);
let loading: Promise<void> | null = null;

/** The university's name, logos and colours (educore_theme's EduCore Branding), fetched once */
export function useBranding() {
  loading ??= get<Branding>("educore_theme.branding.public_branding")
    .then((data) => {
      branding.value = data;
    })
    .catch(() => {
      // the defaults stand; the login page must never fail because branding did
    });
  return { branding, ready: loading };
}
