<script setup lang="ts">
import Tag from "primevue/tag";
import { formatDate, formatMoney } from "@/core/format";
import type { Fee } from "./api";

defineProps<{ fee: Fee }>();
</script>

<template>
  <div class="fee-panel">
    <div class="fee-head">
      <strong>Application fee {{ formatMoney(fee.amount) }}</strong>
      <Tag
        :severity="fee.status === 'Unpaid' ? 'warn' : 'success'"
        :value="fee.status === 'Paid' ? `Received ${formatDate(fee.paid_on)}` : fee.status === 'Waived' ? 'Waived' : 'Not received yet'"
      />
    </div>
    <template v-if="fee.status === 'Unpaid'">
      <p class="sub">Pay by EFT or deposit. Use your application number as the reference, exactly as shown:</p>
      <dl class="bank">
        <div><dt>Reference</dt><dd class="reference">{{ fee.reference }}</dd></div>
        <div v-if="fee.bank.bank_name"><dt>Bank</dt><dd>{{ fee.bank.bank_name }}</dd></div>
        <div v-if="fee.bank.account_name"><dt>Account name</dt><dd>{{ fee.bank.account_name }}</dd></div>
        <div v-if="fee.bank.account_number"><dt>Account number</dt><dd>{{ fee.bank.account_number }}</dd></div>
        <div v-if="fee.bank.branch_code"><dt>Branch code</dt><dd>{{ fee.bank.branch_code }}</dd></div>
      </dl>
      <p class="sub">
        You do not need to upload proof of payment: the payment is matched to your application from the university's bank
        statement, usually within a few working days. You can submit your application before it arrives; it is decided once
        the fee is received.
      </p>
      <p v-if="!fee.card_payments" class="sub">Card payments are coming soon.</p>
    </template>
  </div>
</template>

<style scoped>
.fee-panel {
  display: grid;
  gap: 0.5rem;
}

.fee-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.bank {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.4rem 1rem;
  margin: 0;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.bank dt {
  font-size: 0.75rem;
  color: #6b7280;
}

.bank dd {
  margin: 0;
  font-weight: 600;
}

/* never broken across lines: applicants copy it into their banking app */
.reference {
  font-family: ui-monospace, monospace;
  color: var(--color-brand-navy);
  white-space: nowrap;
}
</style>
