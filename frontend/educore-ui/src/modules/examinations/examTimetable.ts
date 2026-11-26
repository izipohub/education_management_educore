import { get, post } from "@/core/api/client";

const API = "educore.api.v1.exam_timetable";

export type SessionKind = "Main" | "Supplementary and special";

export interface ExamSession {
  name: string;
  academic_year: string;
  semester: string;
  kind: SessionKind;
  starts_on: string;
  ends_on: string;
  status: "Draft" | "Published";
  papers: number;
}

export interface Paper {
  name: string;
  session: string;
  student_group: string;
  code: string;
  course_name: string;
  campus: string;
  exam_date: string;
  start_time: string;
  end_time: string;
  rooms: { room: string; room_name: string }[];
  invigilators: { user: string; full_name: string }[];
  /** how many write it */
  sitting: number;
  /** on the student's and invigilator's lists: the day has passed */
  written?: boolean;
}

export interface ExamTimetablePage {
  academic_year: string | null;
  academic_years: string[];
  sessions: ExamSession[];
  session: ExamSession | null;
  campus: string | null;
  campuses: string[];
  papers: Paper[];
  to_schedule: { group: string; code: string; course_name: string; sitting: number }[];
  rooms: { name: string; room_name: string; seating_capacity: number }[];
  invigilators: { user: string; full_name: string }[];
  semesters: string[];
  kinds: SessionKind[];
  can_edit: boolean;
  can_publish: boolean;
}

export interface PaperInput {
  name?: string;
  session: string;
  student_group: string;
  exam_date: string;
  start_time: string;
  end_time: string;
  rooms: string[];
  invigilators: string[];
}

export interface SessionInput {
  name?: string;
  session_name?: string;
  academic_year?: string;
  semester?: string;
  kind?: SessionKind;
  starts_on: string;
  ends_on: string;
  campus?: string | null;
}

export const getExamTimetable = (params: { academic_year?: string; session?: string; campus?: string }) =>
  get<ExamTimetablePage>(`${API}.page`, Object.fromEntries(Object.entries(params).filter(([, v]) => v)));
export const saveSession = (session: SessionInput) => post<ExamTimetablePage>(`${API}.save_session`, { session });
export const savePaper = (paper: PaperInput) => post<ExamTimetablePage>(`${API}.save_paper`, { paper });
export const deletePaper = (name: string) => post<ExamTimetablePage>(`${API}.delete_paper`, { name });
export const publishSession = (session: string, campus?: string | null) => post<ExamTimetablePage>(`${API}.publish`, { session, campus });
export const getMyExams = () => get<{ papers: Paper[]; duties: Paper[] }>(`${API}.mine`);
