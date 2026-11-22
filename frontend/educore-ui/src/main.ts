import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";
import App from "@/app/App.vue";
import { router } from "@/app/router";
import { EduCorePreset } from "@/styles/preset";
import "@/styles/main.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: EduCorePreset,
      options: {
        darkModeSelector: ".app-dark",
        // matches the layer order declared in styles/main.css
        cssLayer: { name: "primevue", order: "theme, base, primevue" },
      },
    },
  })
  .use(ToastService)
  .mount("#app");
