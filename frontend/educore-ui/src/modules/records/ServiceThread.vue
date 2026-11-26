<script setup lang="ts">
import { Paperclip } from "@lucide/vue";
import Textarea from "primevue/textarea";
import { ref } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import { type ServiceRequest, documentUrl } from "./serviceRequests";

/**
 * A service request's messages, oldest first, and (while it is open) a reply with an optional document. Used by the
 * student's page and the office's page; `send` posts the reply and returns the request as it is now.
 */
const props = defineProps<{ request: ServiceRequest; canReply: boolean; send: (message: string, file: File | null) => Promise<void>; placeholder?: string }>();
const message = ref("");
const file = ref<File | null>(null);
const input = ref<HTMLInputElement | null>(null);
const busy = ref(false);
const when = (v: string) => `${formatDate(v)} ${v.slice(11, 16)}`;

async function reply() {
  busy.value = true;
  try {
    await props.send(message.value.trim(), file.value);
    message.value = "";
    file.value = null;
    if (input.value) input.value.value = "";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <ol v-if="request.messages.length" class="thread">
    <li v-for="m in request.messages" :key="m.idx" :class="{ student: m.from_student }">
      <div class="meta"><strong>{{ m.by }}</strong> · {{ when(m.on) }}</div>
      <p>{{ m.message }}</p>
      <a v-if="m.attachment" :href="documentUrl(request.name, m.idx)" class="doc" target="_blank" rel="noopener"><Paperclip :size="13" /> Document</a>
    </li>
  </ol>
  <p v-else class="none ec-muted">No messages yet.</p>

  <div v-if="canReply" class="reply">
    <Textarea v-model="message" rows="3" auto-resize :placeholder="placeholder ?? 'Write a message'" aria-label="Message" fluid />
    <div class="reply-bar">
      <label class="attach">
        <Paperclip :size="14" />
        <span>{{ file ? file.name : "Attach a document" }}</span>
        <input ref="input" type="file" accept=".pdf,.jpg,.jpeg,.png" @change="(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)" />
      </label>
      <EcButton label="Send" size="sm" variant="primary" :loading="busy" :disabled="!message.trim()" @click="reply" />
    </div>
  </div>
</template>

<style scoped>
.thread {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.thread li {
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--ec-border-soft);
  border-radius: var(--ec-radius-sm);
}

.thread li.student {
  background: var(--ec-surface-muted);
}

.meta {
  color: var(--ec-muted);
  font-size: 0.78rem;
}

.thread p {
  margin: 0.3rem 0 0;
  white-space: pre-line;
}

.doc {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.4rem;
  color: var(--ec-accent);
  font-size: 0.85rem;
  text-decoration: none;
}

.none {
  margin: 0;
}

.reply {
  display: grid;
  gap: 0.5rem;
  margin-top: 1rem;
}

.reply-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.attach {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--ec-accent);
  font-size: 0.85rem;
  cursor: pointer;
}

.attach input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}
</style>
