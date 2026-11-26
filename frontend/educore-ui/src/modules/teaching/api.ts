import { get } from "@/core/api/client";

export interface ClassStudent {
  student: string;
  student_name: string;
  programme: string | null;
  offering: string | null;
  mode_of_study: string | null;
}

export interface CourseClass {
  name: string;
  course: string;
  code: string | null;
  credits: number | null;
  nqf_level: number | null;
  campus: string | null;
  academic_year: string;
  academic_term: string | null;
  students: ClassStudent[];
  /** other lecturers on the same course group */
  co_lecturers: string[];
  /** where the module's marks stand: Not started, Draft (with the lecturer), Submitted... */
  marks_status: string;
  /** the assessment plan: null (none yet), Draft (with the lecturer), Proposed, Approved */
  plan_status: "Draft" | "Proposed" | "Approved" | null;
}

export interface MyClasses {
  /** false: this login is not yet linked to an HR Employee and Instructor record */
  linked: boolean;
  academic_year: string | null;
  academic_years: string[];
  classes: CourseClass[];
}

/** The signed-in lecturer's own classes: the server takes who they are from the session */
export function getMyClasses(academicYear?: string) {
  return get<MyClasses>("educore.api.v1.teaching.my_classes", { academic_year: academicYear });
}
