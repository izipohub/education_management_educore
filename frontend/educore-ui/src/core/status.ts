/**
 * Status tags: one short label and one colour per stored value, the same on every screen. The server keeps its
 * full values (workflow states and stored values); a tag shows one word where it can, and the sentence beside it
 * says the rest.
 */

export type Severity = "success" | "info" | "warn" | "danger" | "secondary" | "contrast";
export type StatusKind = "application" | "offer" | "eligibility" | "registration" | "document" | "fee" | "standing" | "period" | "class" | "marks" | "result" | "completion" | "change" | "request" | "lecturer" | "sponsorship" | "waiver" | "transcript" | "exam" | "workload" | "plan" | "service";

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
    "Not required": ["Not required", "secondary"],
  },
  standing: {
    "Good standing": ["Good standing", "success"],
    Probation: ["Probation", "warn"],
    "On hold": ["On hold", "danger"],
    Excluded: ["Excluded", "danger"],
  },
  marks: {
    "Not started": ["Not started", "secondary"],
    Draft: ["With lecturer", "secondary"],
    Submitted: ["To moderate", "info"],
    Moderated: ["To approve", "info"],
    Approved: ["Approved", "success"],
    Published: ["Published", "success"],
  },
  result: {
    Pass: ["Pass", "success"],
    Supplementary: ["Supplementary", "warn"],
    Fail: ["Fail", "danger"],
    "Not admitted": ["Not admitted", "danger"],
    Absent: ["Absent", "warn"],
  },
  request: {
    Submitted: ["With the Registry", "info"],
    Approved: ["Approved", "success"],
    Declined: ["Declined", "danger"],
  },
  change: {
    Submitted: ["With faculty", "info"],
    Approved: ["Approved", "success"],
    Declined: ["Declined", "danger"],
  },
  completion: {
    Eligible: ["Eligible", "info"],
    "Not yet": ["Not yet", "secondary"],
    Completed: ["Completed", "success"],
  },
  class: {
    ready: ["Ready", "success"],
    "no-lecturer": ["No lecturer", "warn"],
    "to-update": ["List out of date", "warn"],
    "no-class": ["No class yet", "secondary"],
  },
  exam: {
    Draft: ["Draft", "secondary"],
    Published: ["Published", "success"],
  },
  transcript: {
    Requested: ["Requested", "info"],
    Issued: ["Issued", "success"],
    Declined: ["Declined", "danger"],
  },
  waiver: {
    Requested: ["Waiting for the Bursar", "warn"],
    Approved: ["Approved", "success"],
    Rejected: ["Rejected", "danger"],
    Withdrawn: ["Withdrawn", "secondary"],
  },
  sponsorship: {
    Recorded: ["Recorded", "info"],
    Invoiced: ["Invoiced", "success"],
    Withdrawn: ["Withdrawn", "secondary"],
  },
  service: {
    Submitted: ["Submitted", "info"],
    "In progress": ["In progress", "warn"],
    Resolved: ["Resolved", "success"],
    Declined: ["Declined", "danger"],
    Withdrawn: ["Withdrawn", "secondary"],
  },
  plan: {
    Proposed: ["To approve", "warn"],
    Approved: ["Approved", "success"],
  },
  workload: {
    Over: ["Over", "warn"],
    Within: ["Within", "success"],
    Light: ["Light", "info"],
    None: ["Not allocated", "secondary"],
  },
  lecturer: {
    Ready: ["Ready", "success"],
    Incomplete: ["Incomplete", "warn"],
    Left: ["Left", "secondary"],
  },
  period: {
    upcoming: ["Opens soon", "secondary"],
    open: ["Open", "success"],
    late: ["Late", "warn"],
    closed: ["Closed", "secondary"],
  },
};

const EMPTY: Partial<Record<StatusKind, Entry>> = { eligibility: ["Not assessed", "secondary"], plan: ["Draft", "secondary"] };

export function statusTag(kind: StatusKind, value: string | null | undefined): { label: string; severity: Severity } {
  const entry = (value && TAGS[kind][value]) || (!value && EMPTY[kind]) || [value ?? "", "secondary"];
  return { label: entry[0], severity: entry[1] };
}

export const applicationLabel = (status: string | null | undefined) => statusTag("application", status).label;
export const offerLabel = (status: string | null | undefined) => statusTag("offer", status).label;
export const eligibilityLabel = (value: string | null | undefined) => statusTag("eligibility", value).label;
