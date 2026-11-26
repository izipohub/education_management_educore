import { get, post } from "@/core/api/client";

const API = "educore.api.v1.transcripts";

/** who issues transcripts (educore.api.v1.transcripts.ISSUE_ROLES) */
export const ISSUE_ROLES = ["Registrar", "Registry Officer", "System Manager"];

export type Delivery = "Collect at the campus" | "Email" | "Post";
export type TranscriptStatus = "Requested" | "Issued" | "Declined";

export interface TranscriptRequest {
  name: string;
  student: string;
  student_name: string;
  campus: string | null;
  copies: number;
  delivery: Delivery;
  recipient: string | null;
  email: string | null;
  postal_address: string | null;
  status: TranscriptStatus;
  fee: number;
  fee_invoice: string | null;
  paid: boolean;
  requested_on: string | null;
  issued_on: string | null;
  review_note: string | null;
  /** for the Registry: what stops issuing it now */
  blockers?: string[];
}

export interface MyTranscripts {
  requests: TranscriptRequest[];
  fee: number;
  needs_clearance: boolean;
  deliveries: Delivery[];
  has_results: boolean;
}

export interface TranscriptQueue {
  rows: TranscriptRequest[];
  counts: Record<TranscriptStatus, number>;
}

/** how it reaches the recipient, in words */
export function deliveryText(r: Pick<TranscriptRequest, "delivery" | "recipient" | "email">): string {
  if (r.delivery === "Email") return `Emailed to ${r.recipient} (${r.email})`;
  if (r.delivery === "Post") return `Posted to ${r.recipient}`;
  return "Collected at the campus";
}

export const myTranscripts = () => get<MyTranscripts>(`${API}.mine`);
export const requestTranscript = (body: { copies: number; delivery: Delivery; recipient?: string; email?: string; postal_address?: string }) =>
  post<MyTranscripts>(`${API}.request`, body);
export const transcriptQueue = (status: TranscriptStatus) => get<TranscriptQueue>(`${API}.queue`, { status });
export const issueTranscript = (name: string) => post<TranscriptQueue>(`${API}.issue`, { name });
export const declineTranscript = (name: string, note: string) => post<TranscriptQueue>(`${API}.decline`, { name, note });
