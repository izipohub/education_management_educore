import { get, post } from "@/core/api/client";

const API = "educore.api.v1.course_changes";

export type ChangeStatus = "Submitted" | "Approved" | "Declined";

export interface CourseChange {
  name: string;
  student: string;
  student_name: string;
  program: string;
  campus: string | null;
  academic_year: string;
  status: ChangeStatus;
  submitted_on: string | null;
  reviewed_on: string | null;
  reason: string | null;
  review_note: string | null;
  items: { action: "Add" | "Drop"; course: string; course_name: string; credits: number }[];
}

export interface ChangeCourse {
  course: string;
  course_name: string;
  code: string | null;
  credits: number;
  year: number;
  semester: string;
  required: boolean;
  registered: boolean;
  state: "passed" | "repeat" | "blocked" | "open";
  missing: string[];
}

export interface MyChanges {
  academic_year: string | null;
  changes_until: string | null;
  open: boolean;
  max_credits?: number;
  registration: { name: string; program: string; year_of_study: number; courses: ChangeCourse[] } | null;
  changes: CourseChange[];
}

export interface ChangeQueue {
  academic_year: string | null;
  changes_until: string | null;
  open: boolean;
  rows: CourseChange[];
  counts: Record<ChangeStatus, number>;
}

export const myChanges = () => get<MyChanges>(`${API}.mine`);
export const requestChange = (add: string[], drop: string[], reason: string) => post<MyChanges>(`${API}.request`, { add, drop, reason });
export const changeQueue = (status: ChangeStatus) => get<ChangeQueue>(`${API}.queue`, { status });
export const approveChange = (name: string) => post<ChangeQueue>(`${API}.approve`, { name });
export const declineChange = (name: string, note: string) => post<ChangeQueue>(`${API}.decline`, { name, note });
