import { get, post } from "@/core/api/client";

export type Semester = "Semester 1" | "Semester 2" | "Year";
export const SEMESTERS: Semester[] = ["Semester 1", "Semester 2", "Year"];
export const semesterLabel = (s: Semester) => (s === "Year" ? "Full year" : s);

/** who lays out a curriculum (educore.api.v1.curriculum.CURRICULUM_ROLES) */
export const CURRICULUM_ROLES = [
  "Registrar",
  "Faculty Officer",
  "Head of Department",
  "Dean",
  "Timetable Officer",
  "Examinations Officer",
  "Quality Assurance Officer",
  "System Manager",
];

export interface ProgrammeRow {
  name: string;
  code: string | null;
  qualification: string | null;
  nqf_level: number | null;
  duration: number | null;
  faculty: string;
  level: string | null;
  courses: number;
  credits: number;
  years_laid_out: number;
}

export interface CurriculumCourse {
  course: string;
  course_name: string;
  code: string | null;
  credits: number;
  nqf_level: number | null;
  year: number;
  semester: Semester;
  required: boolean;
}

export interface CatalogueCourse {
  course: string;
  code: string | null;
  credits: number | null;
  nqf_level: number | null;
}

export interface Curriculum {
  name: string;
  code: string | null;
  qualification: string | null;
  nqf_level: number | null;
  duration: number | null;
  faculty: string;
  level: string | null;
  courses: CurriculumCourse[];
  catalogue: CatalogueCourse[];
  semesters: Semester[];
  /** the faculty lays it out; the Registrar's office reads it */
  can_edit: boolean;
}

const API = "educore.api.v1.curriculum";
export const listProgrammes = () => get<ProgrammeRow[]>(`${API}.programmes`);
export const getCurriculum = (name: string) => get<Curriculum>(`${API}.programme`, { name });
export const saveCurriculum = (name: string, courses: Pick<CurriculumCourse, "course" | "year" | "semester" | "required">[]) =>
  post<Curriculum>(`${API}.save`, { name, courses });
