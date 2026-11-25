/** Links to the PDFs the server makes (educore.api.v1.documents); opened in a new tab, the browser shows or saves them */
const METHOD = "/api/method/educore.api.v1.documents";

export const offerLetterUrl = (application: string) => `${METHOD}.offer_letter?name=${encodeURIComponent(application)}`;
export const academicRecordUrl = (student: string) => `${METHOD}.academic_record?student=${encodeURIComponent(student)}`;
export const proofOfRegistrationUrl = (enrollment: string) =>
  `${METHOD}.proof_of_registration?enrollment=${encodeURIComponent(enrollment)}`;
