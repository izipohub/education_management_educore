import { get, http, post, toApiError } from "@/core/api/client";

/** Service requests: the student asks and follows; each office works its queue; the Registrar keeps the categories
 * (educore.api.v1.service_requests) */
const API = "educore.api.v1.service_requests";

/** the positions that work an office's queue (educore.academics.service_requests.OFFICES), and the Registrar */
export const SERVICE_ROLES = [
  "Registrar",
  "Registry Officer",
  "Student Affairs Officer",
  "Faculty Officer",
  "Examinations Officer",
  "Student Fees Officer",
  "Financial Aid Officer",
  "Accommodation Officer",
  "System Manager",
];
export const CATEGORY_ROLES = ["Registrar", "System Manager"];

export type ServiceStatus = "Submitted" | "In progress" | "Resolved" | "Declined" | "Withdrawn";

export interface ServiceMessage {
  idx: number;
  from_student: boolean;
  /** to the student: "You" or the office; to staff: who wrote */
  by: string;
  on: string;
  message: string;
  attachment: boolean;
}

export interface ServiceRequest {
  name: string;
  student: string;
  student_name: string;
  campus: string | null;
  category: string;
  office: string;
  status: ServiceStatus;
  submitted_on: string | null;
  due_on: string | null;
  overdue: boolean;
  assigned_to: string | null;
  details: string;
  attachment: boolean;
  fee: number;
  fee_unpaid: boolean;
  outcome_note: string | null;
  closed_on: string | null;
  messages: ServiceMessage[];
  can_act?: boolean;
}

export interface ServiceCategory {
  name: string;
  office: string;
  response_days: number;
  fee: number;
  needs_attachment: 0 | 1;
  guidance: string | null;
  disabled?: 0 | 1;
}

export interface QueueRow {
  name: string;
  student: string;
  student_name: string;
  campus: string | null;
  category: string;
  office: string;
  status: ServiceStatus;
  submitted_on: string | null;
  due_on: string | null;
  overdue: boolean;
  assigned_to: string | null;
  mine: boolean;
}

/** a POST with the form's fields and an optional file (multipart) */
async function send<T>(method: string, fields: Record<string, string>, file?: File | null): Promise<T> {
  const form = new FormData();
  for (const [k, v] of Object.entries(fields)) form.append(k, v);
  if (file) form.append("file", file);
  try {
    const response = await http.post<{ message: T }>(`/api/method/${API}.${method}`, form);
    return response.data.message;
  } catch (error) {
    throw toApiError(error);
  }
}

// the student
export const myServiceRequests = () => get<{ categories: ServiceCategory[]; requests: ServiceRequest[] }>(`${API}.mine`);
export const askService = (category: string, details: string, file?: File | null) => send<ServiceRequest>("ask", { category, details }, file);
export const writeMine = (name: string, message: string, file?: File | null) => send<ServiceRequest>("write_mine", { name, message }, file);
export const withdrawService = (name: string) => post<ServiceRequest>(`${API}.withdraw`, { name });

// the offices
export const serviceQueue = () => get<{ rows: QueueRow[]; offices: string[] }>(`${API}.queue`);
export const getServiceRequest = (name: string) => get<ServiceRequest>(`${API}.request`, { name });
export const takeService = (name: string) => post<ServiceRequest>(`${API}.take`, { name });
export const writeService = (name: string, message: string, file?: File | null) => send<ServiceRequest>("write", { name, message }, file);
export const resolveService = (name: string, note: string) => post<ServiceRequest>(`${API}.resolve`, { name, note });
export const declineService = (name: string, note: string) => post<ServiceRequest>(`${API}.decline`, { name, note });

/** the request's document, or a message's */
export const documentUrl = (name: string, message?: number) =>
  `/api/method/${API}.document?name=${encodeURIComponent(name)}${message ? `&message=${message}` : ""}`;

// the categories (Registrar)
export const serviceCategories = () => get<{ rows: ServiceCategory[]; offices: string[]; can_edit: boolean }>(`${API}.categories`);
export const saveServiceCategory = (data: Partial<ServiceCategory> & { category_name?: string }) =>
  post<{ rows: ServiceCategory[]; offices: string[]; can_edit: boolean }>(`${API}.save_category`, { data });
