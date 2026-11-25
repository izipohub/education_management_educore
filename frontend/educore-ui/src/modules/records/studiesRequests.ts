import { get, post } from "@/core/api/client";

const API = "educore.api.v1.studies_requests";

/** who decides requests to interrupt or cancel studies (educore.api.v1.studies_requests.DECIDE_ROLES) */
export const DECIDE_ROLES = ["Registrar", "Registry Officer", "System Manager"];

export type RequestType = "Interruption" | "Cancellation";
export type RequestStatus = "Submitted" | "Approved" | "Declined";

export interface StudiesRequest {
  name: string;
  request_type: RequestType;
  student: string;
  student_name: string;
  program: string | null;
  campus: string | null;
  academic_year: string | null;
  last_day: string | null;
  return_year: string | null;
  reason: string;
  status: RequestStatus;
  submitted_on: string | null;
  reviewed_on: string | null;
  review_note: string | null;
}

export interface MyStudiesRequests {
  requests: StudiesRequest[];
  can_request: boolean;
  academic_year: string | null;
  return_years: string[];
  interrupted_until: string | null;
}

export interface RequestQueue {
  rows: StudiesRequest[];
  counts: Record<RequestStatus, number>;
}

export const myStudiesRequests = () => get<MyStudiesRequests>(`${API}.mine`);
export const requestStudiesChange = (request_type: RequestType, last_day: string, reason: string, return_year?: string | null) =>
  post<MyStudiesRequests>(`${API}.request`, { request_type, last_day, reason, return_year });
export const requestQueue = (status: RequestStatus) => get<RequestQueue>(`${API}.queue`, { status });
export const approveRequest = (name: string) => post<RequestQueue>(`${API}.approve`, { name });
export const declineRequest = (name: string, note: string) => post<RequestQueue>(`${API}.decline`, { name, note });
export const resumeStudies = (student: string) => post<{ student: string }>(`${API}.resume`, { student });
