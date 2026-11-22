import { get } from "@/core/api/client";

export interface Count {
  label: string;
  value: number;
}

export interface DashboardStats {
  today: string;
  sections: {
    students?: { total: number; by_campus: Count[] };
    admissions?: {
      academic_year: string | null;
      pipeline: Count[];
      unsuccessful: number;
      declined_or_lapsed: number;
      fee_unpaid: number;
      offers_pending: number;
      offerings: { label: string; applied: number; taken: number; capacity: number }[];
    };
    enrolment?: { academic_year: string | null; waiting: number; enrolled: number };
    registration?: {
      academic_year: string | null;
      state?: "upcoming" | "open" | "late" | "closed";
      closes_on?: string;
      submitted?: number;
      returned?: number;
      approved?: number;
    };
    fees?: {
      year: number;
      invoiced: number;
      collected: number;
      outstanding: number;
      by_campus: { label: string; invoiced: number; collected: number }[];
    };
  };
}

export const getStats = () => get<DashboardStats>("educore.api.v1.dashboard.stats");
