/**
 * Short labels for status tags. The server keeps its full values (they are workflow states and stored
 * values); a tag shows one word where it can, and the sentence beside it says the rest.
 */

const APPLICATION: Record<string, string> = {
  Draft: "Draft",
  Applied: "Submitted",
  Approved: "Offered",
  Rejected: "Unsuccessful",
  Declined: "Declined",
  Lapsed: "Lapsed",
  Admitted: "Admitted",
};

const OFFER: Record<string, string> = {
  "Awaiting response": "Pending",
  Accepted: "Accepted",
  Declined: "Declined",
  Lapsed: "Lapsed",
};

const ELIGIBILITY: Record<string, string> = {
  "Meets requirements": "Eligible",
  "Does not meet requirements": "Not eligible",
  "Needs review": "Review",
};

export const applicationLabel = (status: string | null | undefined) => (status ? (APPLICATION[status] ?? status) : "");
export const offerLabel = (status: string | null | undefined) => (status ? (OFFER[status] ?? status) : "");
export const eligibilityLabel = (value: string | null | undefined) => (value ? (ELIGIBILITY[value] ?? value) : "Not assessed");
