import { fromIsoDate, toIsoDate } from "@/core/format";
import type { Personal } from "./api";

/**
 * The applicant's particulars as the form edits them (dates as Date, the disability answer as a boolean), with
 * the conversion to and from what the server keeps. The same fields Namibian universities ask on their forms
 * (UNAM, NUST); the online form and the paper form captured by staff both use them.
 */
export interface DetailsForm {
  educore_title: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  educore_previous_surname: string;
  date_of_birth: Date | null;
  gender: string;
  educore_marital_status: string;
  educore_home_language: string;
  nationality: string;
  educore_national_id: string;
  educore_region_of_origin: string;
  educore_home_town: string;
  educore_minority_group: string;
  educore_passport_number: string;
  educore_passport_expiry: Date | null;
  educore_study_permit: string;
  student_mobile_number: string;
  educore_alternative_phone: string;
  address_line_1: string;
  city: string;
  educore_postal_address: string;
  educore_kin_relationship: string;
  educore_kin_name: string;
  educore_kin_phone: string;
  educore_kin_email: string;
  educore_kin_address: string;
  educore_fee_payer: string;
  educore_fee_payer_name: string;
  educore_fee_payer_email: string;
  educore_fee_payer_phone: string;
  educore_disability: boolean;
  educore_support_needs: string;
}

export const TITLES = ["Mr", "Ms", "Mrs", "Dr", "Prof"];
export const GENDERS = ["Female", "Male", "Other", "Prefer not to say"];
export const MARITAL_STATUSES = ["Single", "Married", "Divorced", "Widowed"];
export const REGIONS = [
  "Erongo",
  "Hardap",
  "Karas",
  "Kavango East",
  "Kavango West",
  "Khomas",
  "Kunene",
  "Ohangwena",
  "Omaheke",
  "Omusati",
  "Oshana",
  "Oshikoto",
  "Otjozondjupa",
  "Zambezi",
];
export const MINORITY_GROUPS = ["None", "San", "Ovahimba", "Ovazemba", "Ovatue", "Ovatjimba"];
export const KIN_RELATIONSHIPS = ["Mother", "Father", "Guardian", "Spouse or partner", "Other"];
export const FEE_PAYERS = ["Self", "Parent or guardian", "Sponsor or bursary", "Employer"];

const DATES = ["date_of_birth", "educore_passport_expiry"] as const;

export function emptyDetails(nationality = ""): DetailsForm {
  return {
    educore_title: "",
    first_name: "",
    middle_name: "",
    last_name: "",
    educore_previous_surname: "",
    date_of_birth: null,
    gender: "",
    educore_marital_status: "",
    educore_home_language: "",
    nationality,
    educore_national_id: "",
    educore_region_of_origin: "",
    educore_home_town: "",
    educore_minority_group: "",
    educore_passport_number: "",
    educore_passport_expiry: null,
    educore_study_permit: "",
    student_mobile_number: "",
    educore_alternative_phone: "",
    address_line_1: "",
    city: "",
    educore_postal_address: "",
    educore_kin_relationship: "",
    educore_kin_name: "",
    educore_kin_phone: "",
    educore_kin_email: "",
    educore_kin_address: "",
    educore_fee_payer: "",
    educore_fee_payer_name: "",
    educore_fee_payer_email: "",
    educore_fee_payer_phone: "",
    educore_disability: false,
    educore_support_needs: "",
  };
}

/** the form, filled from what the server keeps */
export function detailsFrom(p: Partial<Personal>, nationality = ""): DetailsForm {
  const form = emptyDetails(nationality);
  for (const key of Object.keys(form) as (keyof DetailsForm)[]) {
    const value = p[key as keyof Personal];
    if (value === null || value === undefined) continue;
    if ((DATES as readonly string[]).includes(key)) (form as unknown as Record<string, unknown>)[key] = fromIsoDate(String(value));
    else if (key === "educore_disability") form.educore_disability = Boolean(value);
    else (form as unknown as Record<string, unknown>)[key] = String(value);
  }
  return form;
}

/** what the server takes: dates as ISO, empty answers as null */
export function detailsToApi(form: DetailsForm): Partial<Personal> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(form)) {
    if (value instanceof Date) out[key] = toIsoDate(value);
    else if (typeof value === "boolean") out[key] = value ? 1 : 0;
    else out[key] = typeof value === "string" ? value.trim() || null : value;
  }
  if (!form.educore_disability) out.educore_support_needs = null;
  if (form.educore_fee_payer === "Self") {
    out.educore_fee_payer_name = null;
    out.educore_fee_payer_email = null;
    out.educore_fee_payer_phone = null;
  }
  return out as Partial<Personal>;
}
