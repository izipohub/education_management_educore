import { get, post } from "@/core/api/client";

/** who sees the Graduation screen (educore.api.v1.graduation.READ_ROLES); the Registrar confirms */
export const GRADUATION_ROLES = [
  "Registrar",
  "Registry Officer",
  "Examinations Officer",
  "Faculty Officer",
  "Dean",
  "Head of Department",
  "Campus Director",
  "Executive Management",
  "System Manager",
];

const API = "educore.api.v1.graduation";

export type Completion = "Eligible" | "Not yet" | "Completed";

export interface Candidate {
  name: string;
  student_name: string;
  campus: string | null;
  program: string | null;
  year_of_study: number | null;
  standing: string | null;
  /** a standing set by hand that holds back completion */
  held: string | null;
  credits_passed: number;
  credits_needed: number;
  /** required courses not yet passed */
  outstanding: string[];
  status: Completion;
  completed_on: string | null;
  reference: string | null;
}

export interface Candidates {
  rows: Candidate[];
  programmes: string[];
  campuses: string[];
  can_confirm: boolean;
}

export const listCandidates = (params: { program?: string; campus?: string } = {}) => get<Candidates>(`${API}.candidates`, params);
export const confirmCompletion = (students: string[], reference: string, completed_on: string) =>
  post<{ confirmed: number }>(`${API}.confirm`, { students, reference, completed_on });
