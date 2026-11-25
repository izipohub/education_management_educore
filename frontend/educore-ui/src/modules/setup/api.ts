import { get, post } from "@/core/api/client";

export interface Settings {
  home_country: string;
  max_choices: number;
  approval_needs_verified_documents: 0 | 1;
  approval_needs_fee: 0 | 1;
  offer_response_days: number;
  offer_reminder_days: number;
  enrolment_needs_acceptance: 0 | 1;
  notify_applicants: 0 | 1;
  certification_max_age_months: number;
  max_file_size_mb: number;
  /** online, local and international */
  fee_namibian: number;
  fee_international: number;
  /** a paper form handed in at a campus */
  fee_paper_local: number;
  fee_paper_international: number;
  /** ERPNext: the Bank Account applicants pay into, and the income account fees are booked to */
  fee_bank_account: string | null;
  fee_income_account: string | null;
  best_subjects: number;
}

/** one of the university's bank accounts in ERPNext, with what applicants are shown */
export interface BankAccountChoice {
  name: string;
  label: string;
  bank: string | null;
  account_number: string | null;
  branch_code: string | null;
  holder: string | null;
}

export interface ScaleRow {
  level: string;
  grade: string;
  points: number;
}

export interface PathwayDocument {
  document_type: string;
  applies_to: string;
  required: boolean;
}

export interface Pathway {
  name: string;
  level: "Undergraduate" | "Postgraduate";
  evidence: string;
  min_age: number;
  min_work_years: number;
  referees_required: number;
  sort_order: number;
  active: 0 | 1;
  description: string | null;
  documents: PathwayDocument[];
  /** applications made on it so far */
  applications: number;
}

export interface DocumentType {
  name: string;
  required_for: string;
  must_be_certified: 0 | 1;
  description: string | null;
  active: 0 | 1;
}

export interface SubjectRequirement {
  subject: string;
  level: string;
  grade: string;
}

export interface Programme {
  name: string;
  code: string;
  qualification: string | null;
  nqf_level: number | null;
  level: "Undergraduate" | "Postgraduate";
  min_points: number | null;
  subject_requirements: SubjectRequirement[];
  min_prior_nqf: number | null;
  min_prior_average: number | null;
}

export interface Setup {
  settings: Settings;
  points_scale: ScaleRow[];
  pathways: Pathway[];
  documents: DocumentType[];
  programmes: Programme[];
  funding_routes: FundingRoute[];
  choices: {
    bank_accounts: BankAccountChoice[];
    income_accounts: string[];
    countries: string[];
    subjects: string[];
    school_levels: string[];
    evidence: string[];
    required_for: string[];
    applies_to: string[];
    funding_kinds: string[];
    sponsors: { name: string; sponsor_name: string }[];
  };
}

/** who pays: a funding route (educore.admissions.funding); whether it pays the application fee is the Bursar's */
export interface FundingRoute {
  name: string;
  route_name: string;
  kind: string;
  sponsor: string | null;
  sponsor_name: string | null;
  description: string | null;
  ask_who: 0 | 1;
  sort_order: number;
  active: 0 | 1;
  pays_application_fee: boolean;
  documents: PathwayDocument[];
}

const API = "educore.api.v1.admission_setup";

export const getSetup = () => get<Setup>(`${API}.setup`);
export const saveSettings = (data: Partial<Settings>) => post<Setup>(`${API}.save_settings`, { data });
export const savePointsScale = (rows: ScaleRow[]) => post<Setup>(`${API}.save_points_scale`, { rows });
export const savePathway = (data: Partial<Pathway> & { pathway_name?: string }, name?: string) =>
  post<Setup>(`${API}.save_pathway`, { data, name });
export const saveDocumentType = (data: Partial<DocumentType> & { document_name?: string }, name?: string) =>
  post<Setup>(`${API}.save_document_type`, { data, name });
export const saveFundingRoute = (data: Partial<FundingRoute>, name?: string) => post<Setup>(`${API}.save_funding_route`, { data, name });
export const saveProgramme = (name: string, data: Partial<Programme>) => post<Setup>(`${API}.save_programme`, { name, data });
