import { get } from "@/core/api/client";

export interface Count {
  label: string;
  value: number;
}

/** something waiting for the signed-in person: how many, and where to act on it */
export interface WorkItem {
  label: string;
  count: number;
  to: { path: string; query?: Record<string, string> };
}

/** a lecturer's lesson today, with whether its register is taken */
export interface TodayLesson {
  group: string;
  code: string;
  course: string;
  start_time: string;
  end_time: string;
  room_name: string;
  kind: string;
  taken: boolean;
}

export interface DashboardStats {
  /** what is waiting for this person, from every queue their positions work on */
  work: WorkItem[];
  /** a lecturer's lessons today */
  lessons: TodayLesson[];
  today: string;
  /** the campus shown; null: every campus the user may see */
  campus: string | null;
  campuses: string[];
  sections: {
    students?: { total: number; by_campus: Count[]; by_gender: Count[] };
    admissions?: {
      academic_year: string | null;
      pipeline: Count[];
      unsuccessful: number;
      declined_or_lapsed: number;
      fee_unpaid: number;
      offers_pending: number;
      total: number;
      /** last twelve months, oldest first; label YYYY-MM */
      by_month: Count[];
      by_programme: Count[];
      by_pathway: Count[];
      by_channel: Count[];
      offer_responses: Count[];
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

export const getStats = (campus?: string) => get<DashboardStats>("educore.api.v1.dashboard.stats", campus ? { campus } : {});
