import { get } from "@/core/api/client";

export interface Course {
  course: string;
  code: string | null;
  credits: number | null;
  nqf_level: number | null;
}

export interface Enrolment {
  name: string;
  program: string;
  programme_code: string | null;
  qualification: string | null;
  nqf_level: number | null;
  offering: string;
  campus: string;
  mode_of_study: string;
  academic_year: string;
  enrollment_date: string;
  courses: Course[];
}

export interface StatementEntry {
  date: string;
  kind: "invoice" | "payment";
  reference: string;
  description: string;
  /** charges positive, payments negative */
  amount: number;
  balance: number;
}

export interface Fees {
  billed: number;
  paid: number;
  owing: number;
  overdue: number;
  next_due: string | null;
  /** the next instalment still to pay (educore.finance.instalments) */
  next_amount: number;
  instalments: { invoice: string; due_date: string; amount: number; left: number }[];
  entries: StatementEntry[];
  /** paid and not yet set against an invoice */
  in_advance: number;
  how_to_pay: {
    bank: { bank_name: string | null; account_name: string | null; account_number: string | null; branch_code: string | null };
    /** the student number: payments are matched to the student by it */
    reference: string;
  };
}

/** class attendance this year, per class (educore.academics.attendance) */
export interface ClassAttendance {
  group: string;
  course: string;
  code: string | null;
  academic_year: string;
  present: number;
  absent: number;
  excused: number;
  rate: number | null;
  below: boolean;
  minimum: number;
}

export interface StudentOverview {
  attendance: ClassAttendance[];
  /** Finance's holds: they block registration until lifted */
  holds: { reason: string; placed_on: string }[];
  /** the overview: today's classes, assessments due in the next three weeks, examinations ahead */
  ahead: {
    lessons: { code: string | null; course: string; start_time: string; end_time: string; room_name: string; kind: string }[];
    due: { code: string | null; course: string; title: string; due_date: string; moodle_url: string | null }[];
    papers: { code: string; course_name: string; exam_date: string; start_time: string; end_time: string; rooms: { room_name: string }[] }[];
  };
  student: {
    number: string;
    name: string;
    email: string;
    campus: string | null;
    faculty: string | null;
    joining_date: string | null;
  };
  /** newest first */
  enrolments: Enrolment[];
  fees: Fees;
}

/** The signed-in student's own data: the server takes who they are from the session */
export function getOverview() {
  return get<StudentOverview>("educore.api.v1.student.overview");
}

export interface MyAssessment {
  title: string;
  kind: string;
  out_of: number;
  /** its share of the CA, in % */
  weight: number;
  due_date: string | null;
  moodle_activity: string | null;
  moodle_url: string | null;
  /** null: not marked yet, or not shown yet */
  score: number | null;
}

export interface MyModuleAssessments {
  group: string;
  code: string | null;
  course: string;
  lecturers: string[];
  /** empty until the module's assessment plan is approved */
  assessments: MyAssessment[];
  /** scores are shown as marked, or once the results are published, as the university decides */
  scores_shown: boolean;
  marked: number;
  /** the CA from the scores, once every assessment is marked */
  ca: number | null;
}

/** The signed-in student's modules this year, their assessments and scores */
export function getAssessments() {
  return get<{ academic_year: string | null; modules: MyModuleAssessments[] }>("educore.api.v1.student.assessments");
}
