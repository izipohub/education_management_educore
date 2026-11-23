<script setup lang="ts">
import { offerLetterUrl } from "@/core/documents";
import Button from "primevue/button";
import Message from "primevue/message";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref } from "vue";
import { offerLabel } from "@/core/status";
import { formatDate, formatMoney } from "@/core/format";
import { type Application, acceptOffer, declineOffer } from "./api";

const props = defineProps<{ application: Application }>();
const emit = defineEmits<{ changed: [Application] }>();
const toast = useToast();

const offer = computed(() => props.application.offer!);
const awaiting = computed(() => offer.value.status === "Awaiting response");
const busy = ref(false);
const declining = ref(false);
const declineReason = ref("");
const showLetter = ref(false);

async function respond(run: () => Promise<Application>, message: string) {
  busy.value = true;
  try {
    emit("changed", await run());
    toast.add({ severity: "success", summary: message, life: 4000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not recorded", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}

const accept = () => respond(acceptOffer, "Offer accepted");
async function decline() {
  await respond(() => declineOffer(declineReason.value.trim() || null), "Offer declined");
  declining.value = false;
}

function print() {
  showLetter.value = true;
  requestAnimationFrame(() => window.print());
}

const SEVERITY = { "Awaiting response": "warn", Accepted: "success", Declined: "danger", Lapsed: "secondary" } as const;
</script>

<template>
  <article class="card offer">
    <div class="offer-head">
      <h2>Offer of a place</h2>
      <Tag :severity="SEVERITY[offer.status]" :value="offerLabel(offer.status)" />
    </div>

    <p class="programme">
      <strong>{{ offer.programme }}</strong><br />
      <span class="sub">{{ offer.campus }} · {{ offer.mode_of_study }} · {{ offer.academic_year }}</span>
    </p>
    <p v-if="offer.conditions" class="conditions">Conditions: {{ offer.conditions }}</p>

    <template v-if="awaiting">
      <p v-if="offer.deadline">Please respond by <strong>{{ formatDate(offer.deadline) }}</strong>. After this date the offer lapses.</p>
      <div v-if="!declining" class="actions">
        <Button label="Accept offer" :loading="busy" @click="accept" />
        <Button label="Decline" severity="secondary" outlined :disabled="busy" @click="declining = true" />
      </div>
      <div v-else class="decline">
        <label for="decline-reason">Reason (optional)</label>
        <Textarea id="decline-reason" v-model="declineReason" rows="2" auto-resize fluid />
        <Message severity="warn" :closable="false">Declining cannot be undone in the portal: the place is offered to another applicant.</Message>
        <div class="actions">
          <Button label="Confirm decline" severity="danger" :loading="busy" @click="decline" />
          <Button label="Cancel" text :disabled="busy" @click="declining = false" />
        </div>
      </div>
    </template>
    <p v-else-if="offer.status === 'Accepted'">
      Accepted on {{ formatDate(offer.responded_on) }}. The Registry will contact you about registration.
    </p>
    <p v-else-if="offer.status === 'Declined'">Declined on {{ formatDate(offer.responded_on) }}.</p>
    <p v-else>This offer lapsed on {{ formatDate(offer.deadline) }}. Please contact the Admissions Office.</p>

    <div class="letter-actions">
      <Button :label="showLetter ? 'Hide offer letter' : 'View offer letter'" text size="small" @click="showLetter = !showLetter" />
      <Button label="Print" text size="small" icon="pi pi-print" @click="print" />
      <a class="pdf" :href="offerLetterUrl(application.name)" target="_blank" rel="noopener">Download PDF</a>
    </div>

    <!-- the letter: on screen on request, and what is printed -->
    <section v-if="showLetter" class="letter offer-letter" aria-label="Offer letter">
      <p class="letter-from">{{ offer.university }}<br />Admissions Office</p>
      <p>{{ formatDate(offer.decided_on) }}</p>
      <p>
        {{ application.personal.first_name }} {{ application.personal.last_name }}<br />
        Application {{ application.name }}
      </p>
      <p><strong>Offer of a place: {{ offer.programme }}</strong></p>
      <p>Dear {{ application.personal.first_name }},</p>
      <p>
        We are pleased to offer you a place in the {{ offer.programme }} at {{ offer.campus }}, {{ offer.mode_of_study.toLowerCase() }},
        for the {{ offer.academic_year }} academic year<template v-if="offer.starts_on">, starting on {{ formatDate(offer.starts_on) }}</template>.
      </p>
      <p v-if="offer.conditions">This offer is subject to the following conditions: {{ offer.conditions }}</p>
      <p v-if="offer.annual_fees">First-year fees: {{ formatMoney(offer.annual_fees) }}.</p>
      <p v-if="offer.deadline">Please accept or decline this offer in the applicant portal by {{ formatDate(offer.deadline) }}.</p>
      <p>Yours sincerely,<br />Admissions Office<br />{{ offer.university }}</p>
    </section>
  </article>
</template>

<style scoped>
.offer {
  display: grid;
  gap: 0.75rem;
  border-color: var(--color-brand-navy);
}

.offer-head,
.actions,
.pdf {
  align-self: center;
  color: var(--ec-accent);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
}

.letter-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.offer-head {
  justify-content: space-between;
}

h2 {
  margin: 0;
  font-size: 1.1rem;
}

p {
  margin: 0;
}

.sub {
  font-size: 0.85rem;
  color: #6b7280;
}

.conditions {
  padding: 0.6rem 0.75rem;
  background: #fffbeb;
  border-radius: 0.5rem;
  font-size: 0.9rem;
}

.decline {
  display: grid;
  gap: 0.5rem;
}

.decline label {
  font-size: 0.875rem;
}

.letter {
  display: grid;
  gap: 0.75rem;
  padding: 1.25rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  line-height: 1.5;
}

.letter-from {
  font-weight: 600;
}

</style>

<style>
/* printing the offer prints the letter alone, not the app around it */
@media print {
  body * {
    visibility: hidden;
  }

  .offer-letter,
  .offer-letter * {
    visibility: visible;
  }

  .offer-letter {
    position: absolute;
    inset: 0 auto auto 0;
    width: 100%;
    border: 0 !important;
  }
}
</style>
