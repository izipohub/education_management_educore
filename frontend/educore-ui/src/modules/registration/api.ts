import { get, post } from "@/core/api/client";

export type RegistrationStatus = "Draft" | "Submitted" | "Returned" | "Approved";

export interface CurriculumCourse {
  course: string;
  course_name: string;
  code: string | null;
  credits: number;
  year: number;
  semester: string;
  required: boolean;
}

export interface MyRegistration {
  name: string;
  status: RegistrationStatus;
  courses: string[];
  submitted_on: string | null;
  late: boolean;
  review_note: string | null;
  online: boolean;
}

export interface RegistrationState {
  period: {
    academic_year: string;
    opens_on: string;
    closes_on: string;
    late_until: string | null;
    late_fee: number;
    state: "upcoming" | "open" | "late" | "closed";
  } | null;
  standing: string | null;
  standing_note: string | null;
  programme: string | null;
  offering: string | null;
  year_of_study?: number;
  courses?: CurriculumCourse[];
  max_credits?: number;
  fees?: { year: number; outstanding: number; deposit_required: number; paid_in_advance: number };
  /** what stops registering, in plain words; empty: nothing */
  blockers?: string[];
  registration?: MyRegistration | null;
}

export interface QueueRow {
  name: string;
  student: string;
  student_name: string;
  program: string;
  offering: string;
  campus: string;
  academic_year: string;
  year_of_study: number;
  status: RegistrationStatus;
  submitted_on: string | null;
  late: 0 | 1;
  review_note: string | null;
  standing: string;
  credits: number;
  courses: { course: string; course_name: string; credits: number }[];
}

export interface Queue {
  academic_year: string | null;
  rows: QueueRow[];
  counts: Record<"Submitted" | "Returned" | "Approved", number>;
}

const API = "educore.api.v1.registration";

export const myRegistration = () => get<RegistrationState>(`${API}.status`);
export const saveCourses = (courses: string[]) => post<RegistrationState>(`${API}.save`, { courses });
export const submitRegistration = () => post<RegistrationState>(`${API}.submit`, {});
export const getQueue = (status: string) => get<Queue>(`${API}.queue`, { status });
export const approveRegistration = (name: string) => post<{ name: string; status: string }>(`${API}.approve`, { name });
export const returnRegistration = (name: string, note: string) =>
  post<{ name: string; status: string }>(`${API}.return_registration`, { name, note });
