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

// --- fee settings (educore.api.v1.fee_settings): the Bursar changes them, finance officers read them -------

export interface FeeSettings {
  application: {
    fee_namibian: number;
    fee_international: number;
    fee_paper_local: number;
    fee_paper_international: number;
    fee_bank_account: string | null;
    fee_income_account: string | null;
  };
  registration: { max_outstanding: number; deposit_type: string; deposit_value: number };
  late_fees: { name: string; academic_year: string; late_until: string | null; late_fee: number }[];
  bank_accounts: { name: string; label: string; bank: string | null; account_number: string | null; branch_code: string | null; holder: string | null }[];
  income_accounts: string[];
  deposit_types: string[];
  can_edit: boolean;
}

export const FEE_SETTINGS_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "System Manager"];
export const getFeeSettings = () => get<FeeSettings>("educore.api.v1.fee_settings.settings");
export const saveFeeSettings = (data: Partial<Pick<FeeSettings, "application" | "registration" | "late_fees">>) =>
  post<FeeSettings>("educore.api.v1.fee_settings.save", { data });
