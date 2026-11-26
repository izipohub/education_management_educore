"""Service requests: a student asks the university for a service, and the office that handles it answers.

The Registrar keeps the categories (Service Request Category): a letter of enrolment, an ID card replacement, a change
of name, a results query, an IT account... each with the office that handles it, the working days it has to respond,
an optional fee and what the student should include. A student asks on My studies (Requests), with a document where
the category needs one; a fee is invoiced at once to their fee account, like the transcript fee.

The office works its queue (educore.api.v1.service_requests): someone takes the request (In progress), writes to the
student (each message is kept on the request, and the student is emailed), and resolves it, or declines it with the
reason. A request is due a number of working days after it was asked; one not resolved by then is overdue. The student
may write back while it is open, and withdraw it before it is taken; a declined or withdrawn request's unpaid fee is
cancelled, and a request is resolved only once its fee is paid.

Who sees what: the student their own requests; an office the requests of its categories, for the campuses and faculty
it works on (their User Permissions on Student); the Registrar every office's.
"""

import os

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

SUBMITTED, IN_PROGRESS, RESOLVED, DECLINED, WITHDRAWN = "Submitted", "In progress", "Resolved", "Declined", "Withdrawn"
OPEN = (SUBMITTED, IN_PROGRESS)
#: the office a category names, and the position that works its queue
OFFICES = {
	"Registry": "Registry Officer",
	"Student Affairs": "Student Affairs Officer",
	"Faculty": "Faculty Officer",
	"Examinations": "Examinations Officer",
	"Student fees": "Student Fees Officer",
	"Financial aid": "Financial Aid Officer",
	"Accommodation": "Accommodation Officer",
	"ICT": "System Manager",
}
FEE_ITEM = "Service Fee"
ALLOWED_FILE_TYPES = (".pdf", ".jpg", ".jpeg", ".png")
MAX_FILE_MB = 5


#: the categories a university starts with (category, office, working days, fee, document needed, what to include)
STARTING = (
	("Letter of enrolment", "Registry", 2, 0, 0, "Who the letter is for (an embassy, an employer, a sponsor) and anything it must say."),
	("ID card replacement", "Student Affairs", 5, 0, 0, "Whether the card was lost, stolen or damaged; a stolen card needs a police case number."),
	("Change of name", "Registry", 5, 0, 1, "Your new name as it must appear; attach a certified copy of the document that changed it."),
	("Results query", "Examinations", 5, 0, 0, "The module, the assessment or examination, and what you query."),
	("IT account", "ICT", 1, 0, 0, "What does not work: signing in, email, Moodle or Wi-Fi."),
)


def ensure_defaults():
	"""From every migrate: a starting list of categories, while the university has none (the Registrar adjusts it)"""
	if frappe.db.count("Service Request Category"):
		return
	for name, office, days, fee, document, guidance in STARTING:
		frappe.get_doc(
			{
				"doctype": "Service Request Category",
				"category_name": name,
				"office": office,
				"response_days": days,
				"fee": fee,
				"needs_attachment": document,
				"guidance": guidance,
			}
		).insert(ignore_permissions=True)


def offices_of(roles: list[str] | None = None) -> list[str]:
	"""The offices whose queues this person works (the Registrar oversees them all)"""
	roles = set(roles if roles is not None else frappe.get_roles())
	if "Registrar" in roles:
		return list(OFFICES)
	return [office for office, role in OFFICES.items() if role in roles]


def due_on(start, working_days: int):
	"""The day a request is due: this many working days (Monday to Friday) after it was asked"""
	day, left = getdate(start), max(0, cint(working_days))
	while left:
		day = add_days(day, 1)
		if day.weekday() < 5:
			left -= 1
	return day


def overdue(doc) -> bool:
	return doc.get("status") in OPEN and bool(doc.get("due_on")) and getdate(doc.due_on) < getdate(nowdate())


def _check_file(upload: tuple[bytes, str] | None):
	"""Refused before anything is saved: not a PDF, JPG or PNG, empty, or too large"""
	if not upload:
		return
	content, filename = upload
	if os.path.splitext(filename or "")[1].lower() not in ALLOWED_FILE_TYPES:
		frappe.throw(_("Upload a PDF, JPG or PNG file"))
	if not content:
		frappe.throw(_("The file is empty"))
	if len(content) > MAX_FILE_MB * 1024 * 1024:
		frappe.throw(_("The file is larger than {0} MB").format(MAX_FILE_MB))


def _file(content: bytes, filename: str, request: str) -> str:
	"""A document stored privately on the request"""
	_check_file((content, filename))
	extension = os.path.splitext(filename or "")[1].lower()
	try:
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{request}-{frappe.generate_hash(length=6)}{extension}",
				"attached_to_doctype": "Service Request",
				"attached_to_name": request,
				"is_private": 1,
				"content": content,
			}
		).insert(ignore_permissions=True)
	except frappe.ValidationError:
		raise
	except Exception:
		frappe.throw(_("The file could not be read. Scan it again as a PDF, JPG or PNG and upload that."))
	return doc.file_url


def ask(student: str, category: str, details: str, upload: tuple[bytes, str] | None = None) -> "frappe.model.document.Document":
	"""The student's request: checked against its category, due in its working days, its fee invoiced"""
	c = frappe.db.get_value("Service Request Category", category, ["office", "response_days", "fee", "needs_attachment", "disabled"], as_dict=True)
	if not c or c.disabled:
		frappe.throw(_("Choose what you are asking for"))
	details = (details or "").strip()
	if not details:
		frappe.throw(_("Say what you need"))
	if c.needs_attachment and not upload:
		frappe.throw(_("{0} needs a document: attach it").format(category))
	_check_file(upload)
	if frappe.db.exists("Service Request", {"student": student, "category": category, "status": ("in", OPEN)}):
		frappe.throw(_("Your request for {0} is open already: write on it instead").format(category))
	doc = frappe.get_doc(
		{
			"doctype": "Service Request",
			"student": student,
			"category": category,
			"office": c.office,
			"status": SUBMITTED,
			"submitted_on": now_datetime(),
			"due_on": due_on(nowdate(), c.response_days),
			"details": details,
			"fee": flt(c.fee, 2),
		}
	).insert(ignore_permissions=True)
	if upload:
		doc.db_set("attachment", _file(upload[0], upload[1], doc.name))
	if flt(c.fee):
		from educore.finance import charges

		doc.db_set(
			"fee_invoice",
			charges.invoice(doc.student, doc.campus, FEE_ITEM, category, c.fee, _("Service request {0}: {1}").format(doc.name, category)),
		)
	return doc


def write(doc, message: str, from_student: bool, upload: tuple[bytes, str] | None = None):
	"""A message on the request, from the student or the office; the student is emailed when the office writes"""
	from educore.academics import notify

	message = (message or "").strip()
	if not message:
		frappe.throw(_("Write the message"))
	if doc.status not in OPEN:
		frappe.throw(_("This request is {0}").format(doc.status.lower()))
	attachment = _file(upload[0], upload[1], doc.name) if upload else None
	doc.append(
		"messages",
		{
			"posted_by": frappe.session.user,
			"posted_by_name": frappe.utils.get_fullname(frappe.session.user),
			"from_student": 1 if from_student else 0,
			"posted_on": now_datetime(),
			"message": message,
			"attachment": attachment,
		},
	)
	if not from_student and doc.status == SUBMITTED:
		doc.update({"status": IN_PROGRESS, "assigned_to": doc.assigned_to or frappe.session.user})
	doc.save(ignore_permissions=True)
	if not from_student:
		notify.send(doc.student, "service_request_message", doc, category=doc.category, office=doc.office, message=message)


def take(doc):
	if doc.status != SUBMITTED:
		frappe.throw(_("This request is {0}").format(doc.status.lower()))
	doc.update({"status": IN_PROGRESS, "assigned_to": frappe.session.user})
	doc.save(ignore_permissions=True)


def close(doc, status: str, note: str):
	"""Resolved (once any fee is paid) or declined (with the reason; an unpaid fee cancelled); the student is emailed"""
	from educore.academics import notify
	from educore.finance import charges

	note = (note or "").strip()
	if doc.status not in OPEN:
		frappe.throw(_("This request is {0}").format(doc.status.lower()))
	if status == DECLINED and not note:
		frappe.throw(_("Tell the student why"))
	if status == RESOLVED and charges.unpaid(doc.fee_invoice):
		frappe.throw(_("Not resolved: the fee is not paid yet"))
	if status == DECLINED:
		charges.cancel_if_unpaid(doc.fee_invoice)
	doc.update({"status": status, "closed_by": frappe.session.user, "closed_on": now_datetime(), "outcome_note": note or None})
	doc.save(ignore_permissions=True)
	notify.send(
		doc.student,
		"service_request_resolved" if status == RESOLVED else "service_request_declined",
		doc,
		category=doc.category,
		office=doc.office,
		note=note,
	)


def withdraw(doc):
	from educore.finance import charges

	if doc.status != SUBMITTED:
		frappe.throw(_("The office is handling it already: write on it instead"))
	charges.cancel_if_unpaid(doc.fee_invoice)
	doc.update({"status": WITHDRAWN, "closed_by": frappe.session.user, "closed_on": now_datetime()})
	doc.save(ignore_permissions=True)


def serialise(doc, for_student: bool = False) -> dict:
	from educore.finance import charges

	return {
		"name": doc.name,
		"student": doc.student,
		"student_name": doc.student_name,
		"campus": doc.campus,
		"category": doc.category,
		"office": doc.office,
		"status": doc.status,
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"due_on": str(doc.due_on) if doc.due_on else None,
		"overdue": overdue(doc),
		"assigned_to": frappe.utils.get_fullname(doc.assigned_to) if doc.assigned_to else None,
		"details": doc.details,
		"attachment": bool(doc.attachment),
		"fee": flt(doc.fee),
		"fee_unpaid": charges.unpaid(doc.fee_invoice),
		"outcome_note": doc.outcome_note,
		"closed_on": str(doc.closed_on) if doc.closed_on else None,
		"messages": [
			{
				"idx": m.idx,
				"from_student": bool(m.from_student),
				# the student sees the office, not who in it wrote
				"by": (_("You") if m.from_student else doc.office) if for_student else m.posted_by_name,
				"on": str(m.posted_on),
				"message": m.message,
				"attachment": bool(m.attachment),
			}
			for m in doc.messages
		],
	}
