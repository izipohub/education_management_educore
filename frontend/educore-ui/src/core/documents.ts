/** Links to the PDFs the server makes (educore.api.v1.documents); opened in a new tab, the browser shows or saves them */
const METHOD = "/api/method/educore.api.v1.documents";

export const offerLetterUrl = (application: string) => `${METHOD}.offer_letter?name=${encodeURIComponent(application)}`;
export const academicRecordUrl = (student: string) => `${METHOD}.academic_record?student=${encodeURIComponent(student)}`;
export const awardCertificateUrl = (student: string) => `${METHOD}.award_certificate?student=${encodeURIComponent(student)}`;
export const graduationListUrl = (year: number) => `${METHOD}.ceremony_list?year=${year}`;
/** who prints award certificates and graduation lists (educore.api.v1.documents.CERTIFICATE_ROLES) */
export const CERTIFICATE_ROLES = ["Registrar", "Registry Officer", "System Manager"];
export const sponsorStatementUrl = (sponsor: string, year: string) =>
  `${METHOD}.sponsor_statement?sponsor=${encodeURIComponent(sponsor)}&academic_year=${encodeURIComponent(year)}`;
export const proofOfRegistrationUrl = (enrollment: string) =>
  `${METHOD}.proof_of_registration?enrollment=${encodeURIComponent(enrollment)}`;
