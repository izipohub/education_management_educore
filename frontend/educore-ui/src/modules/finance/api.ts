import { get, post } from "@/core/api/client";

export type FeeStatus = "Unpaid" | "Paid" | "Waived";

export interface ApplicationFee {
  name: string;
  applicant: string;
  campus: string | null;
  academic_year: string;
  application_date: string | null;
  online: boolean;
  amount: number;
  paid_on: string | null;
  note: string | null;
  international: 0 | 1;
}

export interface FeesPage {
  rows: ApplicationFee[];
  counts: Record<FeeStatus, number>;
}

/** who waives an application fee (educore.admissions.fees.WAIVE_ROLES) */
export const FINANCE_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "System Manager"];

export const listFees = (status: FeeStatus, search?: string) => get<FeesPage>("educore.api.v1.application_fees.fees", { status, search });
export const waiveFee = (name: string, reason: string) =>
  post<{ status: string; note: string }>("educore.api.v1.admissions.waive_fee", { name, reason });
