import { get, post } from "@/core/api/client";

export type FeeStatus = "Unpaid" | "Paid" | "Waived" | "Not required";

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
/** who receipts student payments (educore.api.v1.student_payments.FINANCE_ROLES): Finance and the Cashier */
export const PAYMENT_ROLES = [...FINANCE_ROLES, "Cashier"];

export const listFees = (status: FeeStatus, search?: string) => get<FeesPage>("educore.api.v1.application_fees.fees", { status, search });
export const waiveFee = (name: string, reason: string) =>
  post<{ status: string; note: string }>("educore.api.v1.admissions.waive_fee", { name, reason });

// --- fee settings (educore.api.v1.fee_settings): the Bursar changes them, finance officers read them -------

export interface FeeSettings {
  application: {
    fee_namibian: number;
    fee_international: number;
    /** empty: the international fee */
    fee_regional: number | null;
    fee_paper_local: number;
    fee_paper_international: number;
    fee_paper_regional: number | null;
    fee_bank_account: string | null;
    fee_income_account: string | null;
  };
  registration: { max_outstanding: number; deposit_type: string; deposit_value: number; clearance_max_owing: number; graduation_needs_clearance: 0 | 1 };
  late_fees: { name: string; academic_year: string; late_until: string | null; late_fee: number }[];
  bank_accounts: { name: string; label: string; bank: string | null; account_number: string | null; branch_code: string | null; holder: string | null }[];
  income_accounts: string[];
  deposit_types: string[];
  /** who pays the regional fee */
  regional_countries: string[];
  /** which funding routes pay the application fee (educore.admissions.funding) */
  funding_routes: { name: string; pays_application_fee: 0 | 1; active: 0 | 1 }[];
  countries: string[];
  can_edit: boolean;
}

export const FEE_SETTINGS_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "System Manager"];
export const getFeeSettings = () => get<FeeSettings>("educore.api.v1.fee_settings.settings");
export const saveFeeSettings = (
  data: Partial<Pick<FeeSettings, "application" | "registration" | "late_fees" | "regional_countries">> & { fee_free_routes?: string[] },
) =>
  post<FeeSettings>("educore.api.v1.fee_settings.save", { data });

// --- student payments (educore.api.v1.student_payments) ---------------------------------------------------

export interface ReceivedPayment {
  name: string;
  posting_date: string;
  student: string | null;
  student_name: string | null;
  campus: string | null;
  paid_amount: number;
  unallocated_amount: number;
  reference_no: string | null;
}

export interface WaitingDeposit {
  name: string;
  date: string;
  amount: number;
  description: string | null;
  reference_number: string | null;
  bank_account: string;
  /** student numbers read from the line that are not on record */
  numbers_found: string[];
}

export const listStudentPayments = <T>(view: "received" | "waiting", search?: string) =>
  get<{ rows: T[]; counts: { waiting: number } }>("educore.api.v1.student_payments.payments", { view, search });
export const assignDeposit = (bankTransaction: string, payer: { student?: string; sponsor?: string }) =>
  post<{ payment_entry: string }>("educore.api.v1.student_payments.assign", { bank_transaction: bankTransaction, ...payer });
export const findPayingSponsors = (search: string) =>
  get<{ name: string; sponsor_name: string }[]>("educore.api.v1.student_payments.find_sponsors", { search });
export const matchStudentPayments = () => post<{ matched: number }>("educore.api.v1.student_payments.match_now", {});
export const findStudents = (search: string) =>
  get<{ name: string; student_name: string; campus: string | null }[]>("educore.api.v1.student_payments.find_students", { search });
