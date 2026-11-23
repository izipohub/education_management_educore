import { get, post } from "@/core/api/client";

/** An approved applicant waiting to be enrolled */
export interface Offer {
  name: string;
  applicant: string;
  email: string | null;
  offering: string;
  program: string;
  campus: string;
  mode_of_study: string;
  academic_year: string;
  decided_on: string | null;
  /** the year's fees for the offering; null: no fee structure yet (enrolment is not invoiced) */
  fees: number | null;
  /** suggested: the first term's start, or today once that has passed */
  enrollment_date: string;
  online: boolean;
  offer_status: "Awaiting response" | "Accepted" | null;
  offer_deadline: string | null;
  /** online offers wait for the applicant to accept (Admission Settings) */
  needs_acceptance: boolean;
}

export interface Invoice {
  name: string;
  grand_total: number;
  outstanding_amount: number;
  status: string;
}

/** An admitted applicant, now a student */
export interface Enrolled {
  name: string;
  applicant: string;
  offering: string;
  program: string;
  campus: string;
  academic_year: string;
  student: string | null;
  student_login: string | null;
  enrollment: string | null;
  enrollment_date: string | null;
  invoice: Invoice | null;
}

export interface EnrolmentsPage {
  academic_year: string | null;
  academic_years: string[];
  can_enrol: boolean;
  waiting: Offer[];
  enrolled: Enrolled[];
}

export function listEnrolments(params: { academic_year?: string; search?: string }) {
  return get<EnrolmentsPage>("educore.api.v1.registry.enrolments", params);
}

export interface EnrolmentRecord {
  can_enrol: boolean;
  waiting: Offer | null;
  enrolled: Enrolled | null;
}

export function getEnrolment(name: string) {
  return get<EnrolmentRecord>("educore.api.v1.registry.enrolment", { name });
}

export function enrol(name: string, email: string, enrollmentDate: string) {
  return post<Enrolled>("educore.api.v1.registry.enrol", { name, email, enrollment_date: enrollmentDate });
}
