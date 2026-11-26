import { get, post } from "@/core/api/client";

/** who sets a lecturer's department and campuses; who links the HR staff record; who reads (educore.api.v1.academic_staff) */
export const STAFF_EDIT_ROLES = ["Head of Department", "Dean", "System Manager"];
export const STAFF_HR_ROLES = ["HR Manager", "HR User", "System Manager"];
export const STAFF_ROLES = [
  ...STAFF_EDIT_ROLES,
  ...STAFF_HR_ROLES,
  "Faculty Officer",
  "Registrar",
  "Campus Director",
  "Timetable Officer",
  "Quality Assurance Officer",
  "Executive Management",
];

export type LecturerState = "Ready" | "Incomplete" | "Left";

export interface LecturerRow {
  name: string;
  instructor_name: string;
  user: string | null;
  department: string;
  campuses: string[];
  /** classes in the latest academic year */
  classes: number;
  missing: string[];
  state: LecturerState;
}

export interface Lecturer {
  name: string;
  instructor_name: string;
  user: string | null;
  department: string | null;
  department_label: string;
  campuses: string[];
  employee: string | null;
  state: LecturerState;
  missing: string[];
  login: { name: string; full_name: string; enabled: 0 | 1; last_login: string | null } | null;
  staff_record: { name: string; employee_name: string; designation: string | null; date_of_joining: string | null; status: string } | null;
  positions: string[];
  classes: { name: string; course: string; course_name: string | null; code: string | null; campus: string | null; academic_year: string; students: number }[];
  /** the current semester's workload; null for a lecturer who left */
  workload: (Workload & { academic_year: string | null; semester: string; rule: WorkloadRule; modules?: WorkloadModule[] }) | null;
  can_edit: boolean;
  can_link: boolean;
  choices: { departments: { name: string; label: string }[]; campuses: string[] };
}

export interface StaffRecord {
  name: string;
  employee_name: string;
  department: string;
  user_id: string | null;
}

export type WorkloadStatus = "Over" | "Within" | "Light" | "None";
/** contact hours a week, at least and at most: the university's rule (Registrar) */
export interface WorkloadRule {
  min_hours: number;
  max_hours: number;
}
export interface Workload {
  students?: number;
  /** contact hours a week, from the timetable; a co-taught class counts in full for each lecturer */
  hours?: number;
  /** hours invigilating in the semester's examinations, in all */
  invigilation?: number;
  campuses?: string[];
  status?: WorkloadStatus;
}
export interface WorkloadModule {
  group: string;
  course: string;
  course_name: string | null;
  code: string | null;
  campus: string | null;
  students: number;
  hours: number;
  /** the co-lecturers */
  with: string[];
}
export interface WorkloadRow extends Workload {
  name: string;
  instructor_name: string;
  department: string;
  modules: number;
}
export interface WorkloadPage {
  academic_year: string | null;
  academic_years: string[];
  semester: string;
  semesters: string[];
  rule: WorkloadRule;
  can_edit_rule: boolean;
  rows: WorkloadRow[];
}

const API = "educore.api.v1.academic_staff";
export const listStaff = () => get<{ academic_year: string | null; rows: LecturerRow[] }>(`${API}.staff`);
export const getLecturer = (name: string) => get<Lecturer>(`${API}.lecturer`, { name });
export const saveLecturer = (name: string, data: { department?: string; campuses?: string[] }) => post<Lecturer>(`${API}.save`, { name, ...data });
export const setLeft = (name: string, left: boolean) => post<Lecturer>(`${API}.set_left`, { name, left: left ? 1 : 0 });
export const findStaffRecords = (search: string) => get<StaffRecord[]>(`${API}.unlinked_staff`, { search });
export const linkStaffRecord = (name: string, employee: string) => post<Lecturer>(`${API}.link_staff_record`, { name, employee });
export const getWorkload = (academicYear?: string | null, semester?: string | null) =>
  get<WorkloadPage>(`${API}.workload`, { ...(academicYear ? { academic_year: academicYear } : {}), ...(semester ? { semester } : {}) });
export const saveWorkloadRule = (rule: WorkloadRule) => post<WorkloadRule>(`${API}.save_workload_rule`, { ...rule });
