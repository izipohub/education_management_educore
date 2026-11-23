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
  entries: StatementEntry[];
  /** paid and not yet set against an invoice */
  in_advance: number;
  how_to_pay: {
    bank: { bank_name: string | null; account_name: string | null; account_number: string | null; branch_code: string | null };
    /** the student number: payments are matched to the student by it */
    reference: string;
  };
}

export interface StudentOverview {
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
