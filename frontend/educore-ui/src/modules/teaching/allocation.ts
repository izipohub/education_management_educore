import { get, post } from "@/core/api/client";
import type { Semester } from "@/modules/curriculum/api";
import type { AttendanceSummary } from "./attendance";

/** who allocates lecturers and updates class lists; who reads (educore.api.v1.teaching_allocation) */
export const ALLOCATION_ROLES = [
  "Head of Department",
  "Dean",
  "System Manager",
  "Faculty Officer",
  "Timetable Officer",
  "Registrar",
  "Campus Director",
  "Examinations Officer",
  "Quality Assurance Officer",
  "Executive Management",
];

export type ClassState = "ready" | "no-lecturer" | "to-update" | "no-class";

export interface ClassRow {
  key: string;
  group: string | null;
  course: string;
  course_name: string;
  code: string | null;
  credits: number | null;
  department: string;
  campus: string | null;
  semester: Semester;
  registered: number;
  in_class: number;
  lecturers: string[];
  state: ClassState;
}

export interface Allocation {
  academic_year: string | null;
  academic_years: string[];
  campuses: string[];
  rows: ClassRow[];
  can_edit: boolean;
}

export interface ClassDetail {
  /** each student's class attendance so far */
  attendance: AttendanceSummary;
  name: string;
  course: string;
  code: string | null;
  credits: number | null;
  department: string;
  campus: string | null;
  academic_year: string;
  semester: Semester;
  students: { student: string; student_name: string; offering: string | null; year_of_study: number | null }[];
  lecturers: { instructor: string; instructor_name: string }[];
  /** hours a week: each lecturer's contact hours when the class runs */
  instructors: { name: string; instructor_name: string; department: string; hours: number }[];
  can_edit: boolean;
  /** the class's course in Moodle, once ICT connects it */
  moodle: { connected: boolean; course_id: number | null; synced_on: string | null; error: string | null };
}

const API = "educore.api.v1.teaching_allocation";
export const getAllocation = (academicYear?: string) => get<Allocation>(`${API}.classes`, academicYear ? { academic_year: academicYear } : {});
export const updateClassLists = (academicYear: string) =>
  post<Allocation & { made: number; updated: number }>(`${API}.update_class_lists`, { academic_year: academicYear });
export const getClass = (group: string) => get<ClassDetail>(`${API}.class_detail`, { group });
export const setLecturers = (group: string, instructors: string[]) => post<ClassDetail>(`${API}.set_lecturers`, { group, instructors });
