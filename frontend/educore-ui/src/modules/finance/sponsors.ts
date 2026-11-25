import { get, post } from "@/core/api/client";

/** who records sponsors and the students they pay for (educore.api.v1.sponsors.SPONSOR_ROLES) */
export const SPONSOR_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "Financial Aid Officer", "System Manager"];

export type SponsorshipStatus = "Recorded" | "Invoiced" | "Withdrawn";
export type CoverType = "Full fees" | "Percent of fees" | "Amount";

export interface SponsorRow {
  name: string;
  sponsor_name: string;
  sponsor_type: string;
  disabled: 0 | 1;
  students: number;
  invoiced: number;
  owing: number;
}

export interface SponsorDetails {
  sponsor_name: string;
  sponsor_type: string;
  contact_person: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  payment_days: number;
  disabled: 0 | 1;
}

export interface SponsoredStudent {
  name: string;
  student: string;
  student_name: string;
  program: string | null;
  campus: string | null;
  cover: string;
  amount: number;
  owing: number;
  status: SponsorshipStatus;
  sponsor_reference: string | null;
  sponsor_invoice: string | null;
  can_withdraw: boolean;
}

export interface Sponsor extends SponsorDetails {
  name: string;
  customer: string | null;
  academic_year: string | null;
  academic_years: string[];
  students: SponsoredStudent[];
  /** registered students who named this sponsor on their application, with no sponsorship recorded yet */
  named: { student: string; student_name: string; program: string | null; campus: string | null }[];
  payments: { name: string; posting_date: string; paid_amount: number; unallocated_amount: number; reference_no: string | null }[];
  totals: { students: number; invoiced: number; owing_year: number; owing: number; waiting: number };
  types: string[];
  cover_types: CoverType[];
}

const API = "educore.api.v1.sponsors";
export const listSponsors = (academicYear?: string) =>
  get<{ academic_year: string | null; academic_years: string[]; rows: SponsorRow[]; types: string[] }>(`${API}.sponsors`, academicYear ? { academic_year: academicYear } : {});
export const getSponsor = (name: string, academicYear?: string) => get<Sponsor>(`${API}.sponsor`, { name, ...(academicYear ? { academic_year: academicYear } : {}) });
export const saveSponsor = (data: Partial<SponsorDetails>, name?: string) => post<Sponsor>(`${API}.save_sponsor`, { data, ...(name ? { name } : {}) });
export const addSponsoredStudent = (args: { sponsor_id: string; student: string; academic_year: string; cover_type: CoverType; cover_value?: number; sponsor_reference?: string }) =>
  post<Sponsor>(`${API}.add_student`, args);
export const withdrawSponsorship = (name: string) => post<Sponsor>(`${API}.withdraw`, { name });
export const findSponsorStudents = (search: string) =>
  get<{ name: string; student_name: string; campus: string | null }[]>(`${API}.find_students`, { search });
