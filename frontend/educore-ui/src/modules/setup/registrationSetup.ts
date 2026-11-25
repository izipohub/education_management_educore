import { get, post } from "@/core/api/client";

export interface RegistrationSettings {
  max_outstanding: number;
  deposit_type: string;
  deposit_value: number;
  max_credits: number;
  approval_needed: 0 | 1;
}

export interface Period {
  name: string;
  academic_year: string;
  opens_on: string | null;
  closes_on: string | null;
  late_until: string | null;
  late_fee: number;
  changes_until: string | null;
  state: "upcoming" | "open" | "late" | "closed" | null;
  registrations: number;
}

export interface RegistrationSetup {
  settings: RegistrationSettings;
  periods: Period[];
  /** academic years without a period yet */
  academic_years: string[];
  deposit_types: string[];
}

const API = "educore.api.v1.registration_setup";
export const getRegistrationSetup = () => get<RegistrationSetup>(`${API}.setup`);
export const saveRegistrationSettings = (data: Partial<RegistrationSettings>) => post<RegistrationSetup>(`${API}.save_settings`, { data });
export const savePeriod = (data: Partial<Period>, name?: string) => post<RegistrationSetup>(`${API}.save_period`, { data, name });
