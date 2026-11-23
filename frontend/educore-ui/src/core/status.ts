/**
 * Status tags: one short label and one colour per stored value, the same on every screen. The server keeps its
 * full values (workflow states and stored values); a tag shows one word where it can, and the sentence beside it
 * says the rest.
 */

export type Severity = "success" | "info" | "warn" | "danger" | "secondary" | "contrast";
export type StatusKind = "application" | "offer" | "eligibility" | "registration" | "document" | "fee" | "standing" | "period" | "class";

type Entry = [label: string, severity: Severity];

const TAGS: Record<StatusKind, Record<string, Entry>> = {
  application: {
    Draft: ["Draft", "secondary"],
    Applied: ["Submitted", "info"],
    Approved: ["Offered", "success"],
    Rejected: ["Unsuccessful", "danger"],
    Declined: ["Declined", "secondary"],
    Lapsed: ["Lapsed", "secondary"],
    Admitted: ["Admitted", "success"],
  },
  offer: {
    "Awaiting response": ["Pending", "warn"],
    Accepted: ["Accepted", "success"],
    Declined: ["Declined", "danger"],
    Lapsed: ["Lapsed", "secondary"],
  },
  eligibility: {
    "Meets requirements": ["Eligible", "success"],
    "Does not meet requirements": ["Not eligible", "danger"],
    "Needs review": ["Review", "warn"],
  },
  registration: {
    Draft: ["Draft", "secondary"],
    Submitted: ["Submitted", "info"],
    Returned: ["Returned", "warn"],
    Approved: ["Approved", "success"],
  },
  document: {
    Pending: ["Pending", "secondary"],
    Verified: ["Verified", "success"],
    Rejected: ["Rejected", "danger"],
  },
  fee: {
    Unpaid: ["Unpaid", "warn"],
    Paid: ["Paid", "success"],
    Waived: ["Waived", "success"],
  },
  standing: {
    "Good standing": ["Good standing", "success"],
    Probation: ["Probation", "warn"],
    "On hold": ["On hold", "danger"],
    Excluded: ["Excluded", "danger"],
  },
  class: {
    ready: ["Ready", "success"],
    "no-lecturer": ["No lecturer", "warn"],
    "to-update": ["List out of date", "warn"],
    "no-class": ["No class yet", "secondary"],
  },
  period: {
    upcoming: ["Opens soon", "secondary"],
    open: ["Open", "success"],
    late: ["Late", "warn"],
    closed: ["Closed", "secondary"],
  },
};

const EMPTY: Partial<Record<StatusKind, Entry>> = { eligibility: ["Not assessed", "secondary"] };

export function statusTag(kind: StatusKind, value: string | null | undefined): { label: string; severity: Severity } {
  const entry = (value && TAGS[kind][value]) || (!value && EMPTY[kind]) || [value ?? "", "secondary"];
  return { label: entry[0], severity: entry[1] };
}

export const applicationLabel = (status: string | null | undefined) => statusTag("application", status).label;
export const offerLabel = (status: string | null | undefined) => statusTag("offer", status).label;
export const eligibilityLabel = (value: string | null | undefined) => statusTag("eligibility", value).label;
