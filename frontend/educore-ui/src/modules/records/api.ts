import { get } from "@/core/api/client";
import type { Personal } from "@/modules/apply/api";
import type { Semester } from "@/modules/curriculum/api";

export interface StudentRow {
  name: string;
  student_name: string;
  campus: string | null;
  student_email_id: string | null;
  standing: string | null;
  joining_date: string | null;
  program: string | null;
  offering: string | null;
  academic_year: string | null;
  year_of_study: number | null;
  owing: number;
}

export interface StudentsPage {
  rows: StudentRow[];
  campuses: string[];
  programmes: string[];
  standings: string[];
}

export interface Enrolment {
  name: string;
  program: string;
  offering: string | null;
  campus: string | null;
  academic_year: string;
  year_of_study: number | null;
  enrollment_date: string | null;
  status: string;
  courses: { course: string; course_name: string; credits: number; semester: Semester }[];
  credits: number;
}

export interface StudentRecord {
  name: string;
  student_name: string;
  enabled: boolean;
  campus: string | null;
  joining_date: string | null;
  application: string | null;
  login: string | null;
  standing: string | null;
  standing_note: string | null;
  /** the programme completed, as the Senate approved it */
  studies: { left_on: string | null; interrupted_until: string | null; note: string | null };
  completion: { on: string; programme: string | null; reference: string | null } | null;
  personal: { email: string | null; mobile: string | null; date_of_birth: string | null; gender: string | null; nationality: string | null; address: string | null; city: string | null };
  particulars: Partial<Personal>;
  guardians: { name: string; relation: string | null; phone: string | null; email: string | null; address: string | null }[];
  /** sponsors paying the student's fees, by year (educore.finance.sponsors) */
  /** Finance's active holds */
  holds: { reason: string; placed_on: string }[];
  sponsors: { sponsor_name: string; academic_year: string; cover: string; amount: number; status: string; sponsor_reference: string | null }[];
  enrolments: Enrolment[];
  invoices: { name: string; posting_date: string; grand_total: number; outstanding_amount: number; status: string }[];
  owing: number;
  documents: { document_type: string; status: string; file_url: string | null }[];
}

const API = "educore.api.v1.student_records";

export const listStudents = (params: { search?: string; campus?: string; program?: string; standing?: string; status?: string }) =>
  get<StudentsPage>(`${API}.students`, params);
export const getStudent = (name: string) => get<StudentRecord>(`${API}.student`, { name });

/** who opens student records (educore.api.v1.student_records.RECORD_ROLES) */
export const RECORD_ROLES = [
  "Registrar",
  "Registry Officer",
  "Faculty Officer",
  "Dean",
  "Head of Department",
  "Campus Director",
  "Executive Management",
  "Examinations Officer",
  "Student Affairs Officer",
  "Financial Aid Officer",
  "Accommodation Officer",
  "System Manager",
];
