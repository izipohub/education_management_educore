import { get, http, post, toApiError } from "@/core/api/client";

export type Level = "NSSCO" | "NSSCAS" | "NSSCH";
export const LEVELS: Level[] = ["NSSCO", "NSSCAS", "NSSCH"];

export interface Intake {
  name: string;
  title: string;
  academic_year: string;
  admission_start_date: string | null;
  admission_end_date: string | null;
}

export interface OfferingOption {
  name: string;
  program: string;
  campus: string;
  mode_of_study: string;
  code: string | null;
  qualification: string | null;
  nqf_level: number | null;
  duration_years: number | null;
  faculty: string;
  level: StudyLevel;
  min_points: number | null;
  /** postgraduate: the prior qualification's minimum NQF level and average */
  min_prior_nqf: number | null;
  min_prior_average: number | null;
  subject_requirements: { subject: string; level: Level; grade: string }[];
}

export type StudyLevel = "Undergraduate" | "Postgraduate";
export type Evidence = "School results" | "Work experience" | "Studies elsewhere" | "Studies here" | "Prior qualification";

/** A route into the university; every setting is the university's (Admission Pathway) */
export interface Pathway {
  name: string;
  level: StudyLevel;
  evidence: Evidence;
  min_age: number;
  referees_required: number;
  description: string | null;
  documents: { document_type: string; applies_to: string; required: boolean }[];
}

export interface DocumentType {
  name: string;
  required_for: string;
  must_be_certified: 0 | 1;
  description: string | null;
}

export interface ApplyOptions {
  intakes: Intake[];
  offerings: OfferingOption[];
  subjects: string[];
  grades: Partial<Record<Level, string[]>>;
  best_subjects: number;
  scale_is_placeholder: boolean;
  documents: DocumentType[];
  certification_max_age_months: number;
  max_file_size_mb: number;
  max_choices: number;
  home_country: string;
  countries: string[];
  pathways: Pathway[];
}

export interface School {
  name: string;
  school_name: string;
  town: string | null;
  region: string | null;
  centre_number?: string | null;
}

export interface Result {
  subject: string;
  level: Level;
  grade: string;
  points?: number | null;
}

export interface Choice {
  rank: number;
  offering: string;
  program: string;
  campus: string;
  eligibility: string | null;
  eligibility_note: string | null;
}

export interface PriorQualification {
  qualification: string;
  institution: string;
  country: string | null;
  nqf_level: number | null;
  /** empty: still studying */
  year_completed: number | null;
  average: number | null;
}

export interface Employment {
  employer: string;
  position: string;
  from_date: string | null;
  /** empty: current */
  to_date: string | null;
  duties: string | null;
}

export interface Referee {
  full_name: string;
  position: string | null;
  institution: string | null;
  email: string;
  phone: string | null;
}

export interface ApplicationDocument {
  document_type: string;
  uploaded: boolean;
  file_name: string | null;
  file_url: string | null;
  certified_on: string | null;
  status: "Pending" | "Verified" | "Rejected" | null;
  rejection_reason: string | null;
  required: boolean;
}

export interface Personal {
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  nationality: string | null;
  student_mobile_number: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  country: string | null;
  student_email_id: string | null;
}

export interface Application {
  name: string;
  status: "Draft" | "Applied" | "Approved" | "Rejected" | "Admitted";
  editable: boolean;
  intake: string;
  academic_year: string;
  pathway: string | null;
  /** not a citizen or permanent resident of the home country */
  international: boolean;
  personal: Personal;
  school: School | null;
  exam_number: string | null;
  exam_year: number | null;
  results: Result[];
  points: number | null;
  prior_qualifications: PriorQualification[];
  previous_student_number: string | null;
  employment: Employment[];
  work_years: number | null;
  referees: Referee[];
  choices: Choice[];
  documents: ApplicationDocument[];
  /** what still stops submitting; empty: ready */
  missing: string[];
  declaration: boolean;
  submitted_on: string | null;
  decision_reason: string | null;
  fee: Fee;
}

export interface Fee {
  amount: number | null;
  status: "Unpaid" | "Paid" | "Waived";
  paid_on: string | null;
  /** the application number: the EFT reference */
  reference: string;
  bank: { bank_name: string | null; account_name: string | null; account_number: string | null; branch_code: string | null };
  /** DPO card payments, once the university's merchant account is connected */
  card_payments: boolean;
}

/** What the browser may send: the server takes only these fields */
export interface DraftChanges {
  intake?: string;
  pathway?: string;
  international?: boolean;
  prior_qualifications?: PriorQualification[];
  previous_student_number?: string | null;
  employment?: Employment[];
  referees?: Referee[];
  personal?: Partial<Personal>;
  school?: { name?: string; school_name?: string; town?: string } | null;
  exam_number?: string | null;
  exam_year?: number | null;
  results?: Result[];
  choices?: string[];
}

const API = "educore.api.v1.apply";

export const getOptions = () => get<ApplyOptions>(`${API}.options`);
export const register = (data: { first_name: string; last_name: string; email: string; password: string }) =>
  post<{ email: string }>(`${API}.register`, data);
export const findSchools = (search: string) => get<School[]>(`${API}.schools`, { search });
export const myApplication = () => get<Application | null>(`${API}.my_application`);
export const saveDraft = (data: DraftChanges) => post<Application>(`${API}.save`, { data });
export const removeDocument = (documentType: string) =>
  post<Application>(`${API}.remove_document`, { document_type: documentType });
export const submitApplication = () => post<Application>(`${API}.submit`, { declaration: true });

/** A document upload (multipart): the file, its type and the certification date */
export async function uploadDocument(documentType: string, file: File, certifiedOn: string | null): Promise<Application> {
  const form = new FormData();
  form.append("document_type", documentType);
  if (certifiedOn) form.append("certified_on", certifiedOn);
  form.append("file", file);
  try {
    const response = await http.post<{ message: Application }>(`/api/method/${API}.upload_document`, form);
    return response.data.message;
  } catch (error) {
    throw toApiError(error);
  }
}
