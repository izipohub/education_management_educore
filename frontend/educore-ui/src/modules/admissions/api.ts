import { get, post } from "@/core/api/client";
import type { Employment, PriorQualification, Referee } from "@/modules/apply/api";

export const STATUSES = ["Applied", "Approved", "Rejected", "Admitted"] as const;
export type Status = (typeof STATUSES)[number];
export type Action = "Approve" | "Reject" | "Withdraw Offer" | "Reconsider";

/** Actions that need a written reason (the server checks this too) */
export const NEEDS_REASON: Action[] = ["Reject", "Withdraw Offer"];

export interface Application {
  name: string;
  applicant: string;
  offering: string;
  program: string;
  campus: string;
  mode_of_study: string;
  academic_year: string;
  application_date: string | null;
  status: Status;
  decided_by: string | null;
  decided_on: string | null;
  decision_reason: string | null;
  /** what this user may do now, from the admission workflow */
  actions: Action[];
  points: number | null;
  fee_status: "Unpaid" | "Paid" | "Waived" | null;
  /** an online application (paper applications are checked in person) */
  online: boolean;
  documents_required: number;
  documents_verified: number;
  documents_rejected: string[];
  /** what stops approving it; empty: ready */
  blockers: string[];
  ready: boolean;
}

export interface ReviewDocument {
  document_type: string;
  required: boolean;
  file_url: string | null;
  file_name: string;
  certified_on: string | null;
  certification_problem: string | null;
  status: "Pending" | "Verified" | "Rejected";
  rejection_reason: string | null;
  verified_by: string | null;
  verified_on: string | null;
}

export interface Review {
  name: string;
  applicant: string;
  status: string;
  intake: string;
  pathway: string | null;
  international: boolean;
  /** on 1 January of the intake's year */
  age: number | null;
  submitted_on: string | null;
  personal: { email: string; date_of_birth: string | null; gender: string | null; nationality: string | null; mobile: string | null; city: string | null };
  school: { school_name: string; town: string | null; region: string | null; centre_number: string | null; emis_number: string | null; added_by_applicant: 0 | 1 } | null;
  exam_number: string | null;
  exam_year: number | null;
  results: { subject: string; level: string; grade: string; points: number | null }[];
  points: number | null;
  prior_qualifications: PriorQualification[];
  previous_student_number: string | null;
  employment: Employment[];
  work_years: number | null;
  referees: Referee[];
  choices: { rank: number; offering: string; program: string; campus: string; eligibility: string | null; eligibility_note: string | null }[];
  documents: ReviewDocument[];
  missing_documents: string[];
  fee: { amount: number | null; status: string | null; paid_on: string | null; voucher: string | null; bank_transaction: string | null; note: string | null };
  can_review: boolean;
  actions: Action[];
  online: boolean;
  documents_required: number;
  documents_verified: number;
  blockers: string[];
  ready: boolean;
}

export function getReview(name: string) {
  return get<Review>("educore.api.v1.admissions.review", { name });
}

export function verifyDocument(name: string, documentType: string, verdict: "Verified" | "Rejected", reason?: string) {
  return post<Review>("educore.api.v1.admissions.verify_document", { name, document_type: documentType, verdict, reason });
}

export function waiveFee(name: string, reason: string) {
  return post<Review>("educore.api.v1.admissions.waive_fee", { name, reason });
}

export interface Places {
  capacity: number | null;
  taken: number;
}

export interface ApplicationsPage {
  rows: Application[];
  counts: Record<Status, number>;
  /** the year shown: the one asked for, else the newest with applications */
  academic_year: string | null;
  academic_years: string[];
  /** keyed "<offering>|<academic year>" */
  capacity: Record<string, Places>;
}

export function listApplications(params: { status: Status; academic_year?: string; search?: string }) {
  return get<ApplicationsPage>("educore.api.v1.admissions.applications", params);
}

export function decide(name: string, action: Action, reason?: string) {
  return post<Application>("educore.api.v1.admissions.decide", { name, action, reason });
}
