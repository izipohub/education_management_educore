import { get, post } from "@/core/api/client";

export type SheetStatus = "Not started" | "Draft" | "Submitted" | "Moderated" | "Approved" | "Published";
export type Result = "Pass" | "Supplementary" | "Fail" | "Not admitted" | "Absent";

/** who sees the Examinations screen (educore.api.v1.examinations.READ_ROLES) */
export const EXAMINATION_ROLES = [
  "Head of Department",
  "Dean",
  "Examinations Officer",
  "Registrar",
  "Faculty Officer",
  "Campus Director",
  "Quality Assurance Officer",
  "Executive Management",
  "System Manager",
];

export interface Rules {
  ca_weight: number;
  exam_admission_ca: number;
  /** class attendance below it is flagged; 0: none */
  min_attendance: number;
  pass_mark: number;
  supplementary_from: number;
  supplementary_cap: number;
  probation_share: number;
  grading_scale: string | null;
  /** 1: students see their assessment scores as marked; 0: once the results are published */
  students_see_scores: 0 | 1;
  bands: { grade: string; from: number }[];
}

export interface Entry {
  student: string;
  student_name: string;
  ca_mark: number | null;
  exam_mark: number | null;
  absent: 0 | 1;
  final_mark: number | null;
  grade: string | null;
  result: Result | null;
  moderation_note: string | null;
  /** the supplementary sitting: its mark, and the first attempt kept */
  supp_exam_mark: number | null;
  first_final_mark: number | null;
  first_result: Result | null;
  writes_supplementary: boolean;
  /** the examination written at the supplementary sitting */
  sitting: "Supplementary" | "Special" | null;
  special_reason: string | null;
}

export interface Summary {
  counts: Record<Result, number>;
  average: number | null;
  pass_rate: number | null;
  complete: boolean;
}

export interface Sheet {
  group: string;
  course: string;
  code: string | null;
  campus: string | null;
  academic_year: string;
  lecturers: string[];
  status: SheetStatus;
  return_note: string | null;
  entries: Entry[];
  summary: Summary | null;
  trail: Record<"submitted_by" | "submitted_on" | "moderated_by" | "moderated_on" | "approved_by" | "approved_on" | "board_reference" | "published_on", string | null>;
  rules: Rules;
  supp_status: "Open" | "Submitted" | "Published" | null;
  supp_board_reference: string | null;
  can_publish_supp?: boolean;
  can_grant_special?: boolean;
  can_edit?: boolean;
  can_moderate?: boolean;
  can_approve?: boolean;
  can_publish?: boolean;
  /** the assessment plan: approved or returned by the department while the marks are with the lecturer */
  can_approve_plan?: boolean;
  can_return_plan?: boolean;
  /** the lecturer's assessments and each student's scores (student: assessment key: score); the CA comes from them */
  assessments: Assessment[];
  scores: Record<string, Record<string, number | null>>;
  ca_from_gradebook: boolean;
  /** null: with the lecturer (with the reason if it was returned); Proposed: with the department; Approved: scores go in */
  plan: { status: PlanStatus | null; note: string | null; approved_by: string | null; approved_on: string | null };
  /** the faculty's assessment types the lecturer chooses from */
  assessment_types?: { type_name: string; online: 0 | 1; max_share: number }[];
  /** Moodle connected, and the class's course made in it */
  moodle?: { connected: boolean; in_moodle: boolean };
}

export type PlanStatus = "Proposed" | "Approved";

export interface Assessment {
  assessment_key?: string;
  title: string;
  kind: string;
  out_of: number;
  weight: number;
  due_date?: string | null;
  /** an online assessment's Moodle activity */
  moodle_cmid?: number | null;
  moodle_activity?: string | null;
  moodle_url?: string | null;
}

export interface MoodleActivity {
  cmid: number;
  name: string;
  kind: string;
  section: string | null;
  url: string | null;
}

export interface AssessmentType {
  name?: string;
  type_name: string;
  online: 0 | 1;
  max_share: number;
  disabled: 0 | 1;
  /** used in assessment plans: its name is kept */
  used?: boolean;
}

export interface FacultyTypes {
  faculty: string;
  label: string;
  types: AssessmentType[];
}

/** a student's CA from the gradebook: the weighted sum of their scores, once every assessment is scored */
export function caFrom(assessments: Assessment[], scores: Record<string, number | null | undefined> | undefined): number | null {
  if (!assessments.length) return null;
  let total = 0;
  for (const a of assessments) {
    const score = a.assessment_key ? scores?.[a.assessment_key] : undefined;
    if (score === null || score === undefined) return null;
    total += (score / a.out_of) * a.weight;
  }
  return Math.round(total * 10) / 10;
}

export interface SheetRow {
  group: string;
  course: string;
  code: string | null;
  campus: string | null;
  lecturers: string[];
  students: number;
  status: SheetStatus;
  plan_status: PlanStatus | null;
  pass_rate: number | null;
  supp_status: "Open" | "Submitted" | "Published" | null;
}

export interface SheetsPage {
  academic_year: string | null;
  academic_years: string[];
  rows: SheetRow[];
  can_publish: boolean;
  can_set_rules: boolean;
}

export type MarkInput = Pick<Entry, "student" | "ca_mark" | "exam_mark" | "absent">;

const API = "educore.api.v1.examinations";
export const mySheet = (group: string) => get<Sheet>(`${API}.my_sheet`, { group });
export const saveMarks = (group: string, entries: MarkInput[]) => post<Sheet>(`${API}.save_marks`, { group, entries });
export const saveGradebook = (group: string, assessments: Assessment[], scores: Record<string, Record<string, number | null>>) =>
  post<Sheet>(`${API}.save_gradebook`, { group, assessments, scores });
export const submitMarks = (group: string) => post<Sheet>(`${API}.submit`, { group });
export const listSheets = (academicYear?: string) => get<SheetsPage>(`${API}.sheets`, academicYear ? { academic_year: academicYear } : {});
export const getSheet = (group: string) => get<Sheet>(`${API}.sheet`, { group });
export const moderate = (group: string, entries?: MarkInput[], note?: string) => post<Sheet>(`${API}.moderate`, { group, entries, note });
export const returnSheet = (group: string, note: string) => post<Sheet>(`${API}.return_sheet`, { group, note });
export const approve = (group: string, boardReference: string) => post<Sheet>(`${API}.approve`, { group, board_reference: boardReference });
export const publish = (groups: string[]) => post<{ published: number }>(`${API}.publish`, { groups });
export const getRules = () => get<Rules & { grading_scales: string[]; can_edit: boolean }>(`${API}.rules`);
export const saveRules = (data: Partial<Rules>) => post<Rules & { grading_scales: string[]; can_edit: boolean }>(`${API}.save_rules`, { data });
export const saveSupplementary = (group: string, entries: { student: string; supp_exam_mark: number | null }[]) =>
  post<Sheet>(`${API}.save_supplementary`, { group, entries });
export const submitSupplementary = (group: string) => post<Sheet>(`${API}.submit_supplementary`, { group });
export const publishSupplementary = (group: string, boardReference: string) =>
  post<Sheet>(`${API}.publish_supplementary`, { group, board_reference: boardReference });

export const grantSpecial = (group: string, student: string, reason: string) => post<Sheet>(`${API}.grant_special`, { group, student, reason });

/** the second sitting as the server works it out: a special stands as the first attempt (normal rules, no cap);
 *  a supplementary keeps the CA, and a pass is capped */
export function workOutSitting(e: Pick<Entry, "ca_mark" | "supp_exam_mark" | "sitting">, rules: Rules): Pick<Entry, "final_mark" | "grade" | "result"> {
  if (e.sitting === "Special") return workOut({ ca_mark: e.ca_mark, exam_mark: e.supp_exam_mark, absent: 0 }, rules);
  return workOutSupplementary(e, rules);
}

/** a supplementary sitting as the server works it out: CA still counts, a pass is capped */
export function workOutSupplementary(e: Pick<Entry, "ca_mark" | "supp_exam_mark">, rules: Rules): Pick<Entry, "final_mark" | "grade" | "result"> {
  if (e.supp_exam_mark === null || e.supp_exam_mark === undefined || (e.supp_exam_mark as unknown) === "") return { final_mark: null, grade: null, result: null };
  let final = Math.round((e.ca_mark ?? 0) * (rules.ca_weight / 100) + e.supp_exam_mark * (1 - rules.ca_weight / 100));
  const pass = final >= rules.pass_mark;
  if (pass) final = Math.min(final, Math.round(rules.supplementary_cap || rules.pass_mark));
  const grade = [...rules.bands].sort((a, b) => b.from - a.from).find((b) => final >= b.from)?.grade ?? null;
  return { final_mark: final, grade, result: pass ? "Pass" : "Fail" };
}

export const myResults = () =>
  get<{ results: { academic_year: string; course: string; code: string | null; credits: number; final_mark: number | null; grade: string | null; result: Result | null; student_group: string }[] }>(
    `${API}.my_results`,
  );

/** the final mark, grade and result as the server works them out (shown live while marks are typed) */
export function workOut(e: Pick<Entry, "ca_mark" | "exam_mark" | "absent">, rules: Rules): Pick<Entry, "final_mark" | "grade" | "result"> {
  const none = { final_mark: null, grade: null, result: null };
  if (e.ca_mark === null || e.ca_mark === undefined || (e.ca_mark as unknown) === "") return none;
  if (e.ca_mark < rules.exam_admission_ca) return { ...none, result: "Not admitted" };
  if (e.absent) return { ...none, result: "Absent" };
  if (e.exam_mark === null || e.exam_mark === undefined || (e.exam_mark as unknown) === "") return none;
  const final = Math.round(e.ca_mark * (rules.ca_weight / 100) + e.exam_mark * (1 - rules.ca_weight / 100));
  const grade = [...rules.bands].sort((a, b) => b.from - a.from).find((b) => final >= b.from)?.grade ?? null;
  const result: Result = final >= rules.pass_mark ? "Pass" : final >= rules.supplementary_from ? "Supplementary" : "Fail";
  return { final_mark: final, grade, result };
}
export const proposePlan = (group: string) => post<Sheet>(`${API}.propose_plan`, { group });
export const approvePlan = (group: string) => post<Sheet>(`${API}.approve_plan`, { group });
export const returnPlan = (group: string, note: string) => post<Sheet>(`${API}.return_plan`, { group, note });
export const moodleActivities = (group: string) => get<MoodleActivity[]>(`${API}.moodle_activities`, { group });
export const moodleScores = (group: string, assessmentKey: string) =>
  get<{ scores: Record<string, number>; not_graded: number }>(`${API}.moodle_scores`, { group, assessment_key: assessmentKey });

const TYPES_API = "educore.api.v1.assessment_types";
export const getAssessmentTypes = () => get<{ faculties: FacultyTypes[]; can_edit: boolean }>(`${TYPES_API}.types`);
export const saveAssessmentTypes = (faculty: string, rows: AssessmentType[]) =>
  post<{ faculties: FacultyTypes[]; can_edit: boolean }>(`${TYPES_API}.save`, { faculty, rows });
